"""Schematic synthesis with stronger rule-based netlist generation."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_generator_llm, get_verifier_llm
from pcbai.models import BOMItem, BillOfMaterials, DatasheetInfo, NetDescription, NetPin, NetlistDescription


def _netlist_schema() -> dict[str, Any]:
    """Return the schema expected for synthesized netlists."""

    return {
        "type": "object",
        "properties": {
            "nets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "net_name": {"type": "string"},
                        "pins": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "reference": {"type": "string"},
                                    "pin_number": {"type": "string"},
                                    "pin_name": {"type": "string"},
                                },
                                "required": ["reference", "pin_number", "pin_name"],
                            },
                        },
                        "notes": {"type": "string"},
                    },
                    "required": ["net_name", "pins", "notes"],
                },
            },
            "signal_flow": {"type": "array", "items": {"type": "string"}},
            "power_symbols": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["nets", "signal_flow", "power_symbols"],
    }


def _net(reference: str, pin_number: str, pin_name: str) -> NetPin:
    """Create a net pin object."""

    return NetPin(reference=reference, pin_number=pin_number, pin_name=pin_name)


def _find_items(items: list[BOMItem], prefix: str) -> list[BOMItem]:
    """Return items matching a reference prefix."""

    return [item for item in items if item.reference.startswith(prefix)]


def _find_first(items: list[BOMItem], prefix: str) -> BOMItem | None:
    """Return the first matching item for a prefix."""

    for item in items:
        if item.reference.startswith(prefix):
            return item
    return None


def _part_key(item: BOMItem) -> str:
    """Return the likely lookup key for datasheet metadata."""

    return item.part_number or item.value


def _pin_name_map(item: BOMItem, datasheets: dict[str, DatasheetInfo]) -> dict[str, str]:
    """Return normalized pin names for a BOM item from cached datasheets."""

    candidates = [_part_key(item), item.value, item.reference]
    for candidate in candidates:
        if candidate in datasheets:
            return {pin: name.upper() for pin, name in datasheets[candidate].key_specs.pinout.items()}
    return {}


def _find_pin_number(item: BOMItem, datasheets: dict[str, DatasheetInfo], keywords: tuple[str, ...], default: str) -> str:
    """Find a pin number by searching datasheet pin names."""

    pin_names = _pin_name_map(item, datasheets)
    for pin_number, pin_name in pin_names.items():
        if any(keyword in pin_name for keyword in keywords):
            return pin_number
    return default


def _looks_like_timer(item: BOMItem) -> bool:
    """Return true when the BOM item resembles a 555 timer."""

    combined = f"{item.value} {item.part_number} {item.manufacturer}".upper()
    return "555" in combined


def _split_555_passives(
    bom: BillOfMaterials,
) -> tuple[BOMItem | None, BOMItem | None, BOMItem | None, BOMItem | None, BOMItem | None, BOMItem | None, BOMItem | None]:
    """Classify common passives for a 555 astable circuit."""

    resistors = _find_items(bom.items, "R")
    capacitors = _find_items(bom.items, "C")
    led_drive = next((item for item in resistors if "330" in item.value.upper() or "470" in item.value.upper()), None)
    timing_resistors = [item for item in resistors if item != led_drive]
    timing_resistor_a = timing_resistors[0] if timing_resistors else None
    timing_resistor_b = timing_resistors[1] if len(timing_resistors) > 1 else timing_resistor_a
    decoupling = next((item for item in capacitors if "100N" in item.value.upper()), None)
    control_cap = next((item for item in capacitors if "10N" in item.value.upper()), None)
    excluded_refs = {item.reference for item in (decoupling, control_cap) if item is not None}
    timing_cap = next((item for item in capacitors if item.reference not in excluded_refs), None)
    led = _find_first(bom.items, "D")
    return timing_resistor_a, timing_resistor_b, led_drive, timing_cap, decoupling, control_cap, led


def _build_555_astable_netlist(bom: BillOfMaterials) -> NetlistDescription:
    """Create a practical NE555 astable oscillator netlist."""

    timer = next((item for item in bom.items if _looks_like_timer(item)), None)
    if timer is None:
        return NetlistDescription()

    timing_resistor_a, timing_resistor_b, led_drive, timing_cap, decoupling, control_cap, led = _split_555_passives(bom)

    nets: list[NetDescription] = [
        NetDescription(
            net_name="VCC",
            pins=[_net(timer.reference, "8", "VCC"), _net(timer.reference, "4", "RESET")],
            notes="Primary 5V supply rail and reset tie-high.",
        ),
        NetDescription(
            net_name="GND",
            pins=[_net(timer.reference, "1", "GND")],
            notes="Ground reference for the timer and output stage.",
        ),
        NetDescription(
            net_name="TIMING_NODE",
            pins=[_net(timer.reference, "2", "TRIG"), _net(timer.reference, "6", "THRESH")],
            notes="Joined trigger and threshold node for astable timing.",
        ),
        NetDescription(
            net_name="DISCHARGE_NODE",
            pins=[_net(timer.reference, "7", "DISCH")],
            notes="Timing resistor junction at the discharge transistor.",
        ),
        NetDescription(
            net_name="OUTPUT",
            pins=[_net(timer.reference, "3", "OUT")],
            notes="Blinking output from the timer.",
        ),
        NetDescription(
            net_name="CONTROL",
            pins=[_net(timer.reference, "5", "CTRL")],
            notes="Control voltage stabilization node.",
        ),
    ]

    if timing_resistor_a is not None:
        nets[0].pins.append(_net(timing_resistor_a.reference, "1", "IN"))
        nets[3].pins.append(_net(timing_resistor_a.reference, "2", "OUT"))
    if timing_resistor_b is not None:
        nets[3].pins.append(_net(timing_resistor_b.reference, "1", "IN"))
        nets[2].pins.append(_net(timing_resistor_b.reference, "2", "OUT"))
    if timing_cap is not None:
        nets[2].pins.append(_net(timing_cap.reference, "1", "POS"))
        nets[1].pins.append(_net(timing_cap.reference, "2", "NEG"))
    if decoupling is not None:
        nets[0].pins.append(_net(decoupling.reference, "1", "POS"))
        nets[1].pins.append(_net(decoupling.reference, "2", "NEG"))
    if control_cap is not None:
        nets[5].pins.append(_net(control_cap.reference, "1", "POS"))
        nets[1].pins.append(_net(control_cap.reference, "2", "NEG"))
    if led_drive is not None:
        nets[4].pins.append(_net(led_drive.reference, "1", "IN"))
    if led is not None and led_drive is not None:
        nets.append(
            NetDescription(
                net_name="LED_DRIVE",
                pins=[_net(led_drive.reference, "2", "OUT"), _net(led.reference, "1", "A")],
                notes="Current-limited LED drive from the timer output.",
            )
        )
        nets[1].pins.append(_net(led.reference, "2", "K"))

    return NetlistDescription(
        nets=[net for net in nets if len(net.pins) >= 2 or net.net_name in {"OUTPUT", "CONTROL"}],
        signal_flow=[
            "5V rail powers the timer and holds RESET high.",
            "RA and RB charge/discharge the timing capacitor through DISCHARGE_NODE.",
            "Pins 2 and 6 sense the timing capacitor voltage at TIMING_NODE.",
            "Pin 3 drives the LED through a current-limiting resistor.",
        ],
        power_symbols=["VCC", "GND", "PWR_FLAG"],
    )


def _generic_rule_netlist(bom: BillOfMaterials, datasheets: dict[str, DatasheetInfo]) -> NetlistDescription:
    """Create a better-than-minimal generic fallback netlist."""

    nets: list[NetDescription] = []
    ics = _find_items(bom.items, "U")
    capacitors = _find_items(bom.items, "C")
    resistors = _find_items(bom.items, "R")
    connectors = _find_items(bom.items, "J")
    leds = _find_items(bom.items, "D")
    transistors = _find_items(bom.items, "Q")

    if connectors:
        vcc_pins = [_net(connectors[0].reference, "1", "VCC")]
        gnd_pins = [_net(connectors[0].reference, "2", "GND")]
    else:
        vcc_pins = []
        gnd_pins = []

    for ic in ics:
        vcc_pin = _find_pin_number(ic, datasheets, ("VCC", "VDD", "VIN", "V+"), "1")
        gnd_pin = _find_pin_number(ic, datasheets, ("GND", "VSS", "V-", "AGND", "DGND"), "2")
        vcc_pins.append(_net(ic.reference, vcc_pin, "VCC"))
        gnd_pins.append(_net(ic.reference, gnd_pin, "GND"))
    for transistor in transistors:
        source_pin = _find_pin_number(transistor, datasheets, ("SOURCE", "EMITTER", "S", "E"), "2")
        gnd_pins.append(_net(transistor.reference, source_pin, "GND"))
    nets.append(NetDescription(net_name="VCC", pins=vcc_pins, notes="Primary supply rail."))
    nets.append(NetDescription(net_name="GND", pins=gnd_pins, notes="Primary ground return."))

    for index, capacitor in enumerate(capacitors):
        target_ic = ics[min(index, len(ics) - 1)] if ics else None
        if target_ic:
            vcc_pin = _find_pin_number(target_ic, datasheets, ("VCC", "VDD", "VIN", "V+"), "1")
            gnd_pin = _find_pin_number(target_ic, datasheets, ("GND", "VSS", "V-", "AGND", "DGND"), "2")
            nets[0].pins.extend([_net(target_ic.reference, vcc_pin, "VCC"), _net(capacitor.reference, "1", "POS")])
            nets[1].pins.extend([_net(target_ic.reference, gnd_pin, "GND"), _net(capacitor.reference, "2", "NEG")])

    if ics and resistors:
        signal_pin = _find_pin_number(ics[0], datasheets, ("OUT", "IO", "SIG", "PWM"), "3")
        nets.append(
            NetDescription(
                net_name="SIGNAL_1",
                pins=[_net(ics[0].reference, signal_pin, "OUT"), _net(resistors[0].reference, "1", "IN")],
                notes="Primary signal path from the first active device.",
            )
        )
    if transistors and resistors:
        control_resistor = resistors[-1]
        drive_source = ics[0] if ics else None
        if drive_source is not None:
            drive_pin = _find_pin_number(drive_source, datasheets, ("OUT", "IO", "SIG", "PWM"), "3")
            base_pin = _find_pin_number(transistors[0], datasheets, ("BASE", "GATE", "B", "G"), "1")
            nets.append(
                NetDescription(
                    net_name="CONTROL_1",
                    pins=[
                        _net(drive_source.reference, drive_pin, "OUT"),
                        _net(control_resistor.reference, "1", "IN"),
                        _net(control_resistor.reference, "2", "OUT"),
                        _net(transistors[0].reference, base_pin, "CTRL"),
                    ],
                    notes="Drive path into the first switching transistor.",
                )
            )
        elif connectors:
            base_pin = _find_pin_number(transistors[0], datasheets, ("BASE", "GATE", "B", "G"), "1")
            nets.append(
                NetDescription(
                    net_name="CONTROL_1",
                    pins=[
                        _net(connectors[0].reference, "1", "SIG"),
                        _net(control_resistor.reference, "1", "IN"),
                        _net(control_resistor.reference, "2", "OUT"),
                        _net(transistors[0].reference, base_pin, "CTRL"),
                    ],
                    notes="External control path into the first switching transistor.",
                )
            )
    if resistors and leds:
        nets.append(
            NetDescription(
                net_name="SIGNAL_2",
                pins=[_net(resistors[0].reference, "2", "OUT"), _net(leds[0].reference, "1", "A")],
                notes="Output indicator stage.",
            )
        )
        nets[1].pins.append(_net(leds[0].reference, "2", "K"))
    elif leds:
        nets[0].pins.append(_net(leds[0].reference, "1", "A"))
        nets[1].pins.append(_net(leds[0].reference, "2", "K"))
    if transistors and leds:
        load_pin = _find_pin_number(transistors[0], datasheets, ("COLLECTOR", "DRAIN", "C", "D"), "3")
        nets.append(
            NetDescription(
                net_name="SWITCH_NODE",
                pins=[_net(transistors[0].reference, load_pin, "LOAD"), _net(leds[0].reference, "2", "K")],
                notes="Switched low-side node for the indicator load.",
            )
        )
        nets[1].pins = [pin for pin in nets[1].pins if not (pin.reference == leds[0].reference and pin.pin_number == "2")]
    return NetlistDescription(
        nets=[net for net in nets if len(net.pins) >= 2],
        signal_flow=["Power entry", "Active device stage", "Output indication"],
        power_symbols=["VCC", "GND", "PWR_FLAG"],
    )


def _fallback_netlist(bom: BillOfMaterials, datasheets: dict[str, DatasheetInfo]) -> NetlistDescription:
    """Create a deterministic fallback netlist."""

    if any(_looks_like_timer(item) for item in bom.items):
        timer_netlist = _build_555_astable_netlist(bom)
        if timer_netlist.nets:
            return timer_netlist
    return _generic_rule_netlist(bom, datasheets)


def _symbol_lib_id(item: BOMItem) -> str:
    """Return a likely KiCad symbol library id for a BOM item."""

    reference = item.reference[:1]
    if reference == "R":
        return "Device:R"
    if reference == "C":
        return "Device:C"
    if reference == "D":
        return "Device:LED"
    if reference == "J":
        return "Connector_Generic:Conn_01x02"
    if "555" in item.value.upper():
        return "Timer:NE555"
    return "Device:U"


def _render(netlist: NetlistDescription, console: Console) -> None:
    """Render the synthesized netlist summary."""

    table = Table(title="Schematic Netlist")
    table.add_column("Net")
    table.add_column("Pins")
    table.add_column("Notes")
    for net in netlist.nets:
        table.add_row(net.net_name, ", ".join(f"{pin.reference}:{pin.pin_number}" for pin in net.pins), net.notes)
    console.print(table)


def _write_schematic(bom: BillOfMaterials, netlist: NetlistDescription, schematic_path: Path) -> None:
    """Write a lightweight but more faithful KiCad 7 schematic file."""

    lines = [
        "(kicad_sch (version 20230121) (generator nexus-backend)",
        '  (paper "A4")',
        '  (title_block (title "Nexus Generated Circuit"))',
    ]
    for index, item in enumerate(bom.items):
        x = 40 + (index % 4) * 45
        y = 35 + (index // 4) * 35
        lines.extend(
            [
                f'  (symbol (lib_id "{_symbol_lib_id(item)}") (at {x} {y} 0)',
                f"    (uuid {uuid.uuid4()})",
                f'    (property "Reference" "{item.reference}" (id 0) (at {x} {y - 4} 0))',
                f'    (property "Value" "{item.value}" (id 1) (at {x} {y + 4} 0))',
                f'    (property "Footprint" "{item.footprint}" (id 2) (at {x} {y + 7} 0))',
                "  )",
            ]
        )
    for row, net in enumerate(netlist.nets, start=1):
        joined = ", ".join(f"{pin.reference}:{pin.pin_number}" for pin in net.pins)
        lines.append(f'  (text "{net.net_name}: {joined}" (at 12 {12 + row * 5} 0))')
    lines.append(")")
    schematic_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_usable_netlist(netlist: NetlistDescription) -> bool:
    """Return true when a netlist looks plausible enough to keep."""

    if len(netlist.nets) < 4:
        return False
    return any(net.net_name == "VCC" for net in netlist.nets) and any(net.net_name == "GND" for net in netlist.nets)


def synthesize_schematic(
    bom: BillOfMaterials,
    datasheets: dict[str, DatasheetInfo],
    console: Console | None = None,
    output_dir: str | Path | None = None,
) -> str:
    """Generate a schematic from the BOM and datasheet information."""

    console = console or Console(stderr=True)
    generator = get_generator_llm()
    verifier = get_verifier_llm()
    output_root = Path(output_dir) if output_dir else get_settings().ensure_output_dir()
    schematic_path = output_root / "design.kicad_sch"

    prompt = (
        "Generate KiCad-friendly net connections for this BOM. "
        "Include VCC, GND, signal nets, complete timing networks, and decoupling capacitors. "
        "If the BOM contains a 555 timer, produce a valid astable timer topology.\n\n"
        f"BOM:\n{bom.model_dump_json(indent=2)}\n\n"
        f"Datasheets:\n{json.dumps({key: value.model_dump() for key, value in datasheets.items()}, indent=2)}"
    )

    netlist = _fallback_netlist(bom, datasheets)
    try:
        payload = generator.generate_json(prompt, _netlist_schema())
        candidate = NetlistDescription.model_validate(payload)
        review = verifier.generate(
            "Review this netlist for floating inputs, power correctness, missing decoupling capacitors, "
            "and incorrect timer pin usage. Respond briefly.\n\n"
            f"{candidate.model_dump_json(indent=2)}"
        )
        if _is_usable_netlist(candidate) and "fatal" not in review.lower():
            netlist = candidate
    except (LLMProviderError, ValueError, TypeError):
        pass

    _render(netlist, console)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_schematic(bom, netlist, schematic_path)
    schematic_path.with_suffix(".netlist.json").write_text(netlist.model_dump_json(indent=2), encoding="utf-8")
    schematic_path.with_suffix(".bom.json").write_text(bom.model_dump_json(indent=2), encoding="utf-8")
    return str(schematic_path)
