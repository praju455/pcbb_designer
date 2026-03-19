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


def _looks_like_op_amp(item: BOMItem) -> bool:
    """Return true when the BOM item resembles a common op-amp."""

    combined = f"{item.value} {item.part_number} {item.manufacturer}".upper()
    return any(token in combined for token in ("LM358", "LM324", "TL072", "OPAMP", "OPA"))


def _looks_like_sensor(item: BOMItem) -> bool:
    """Return true when the BOM item resembles a small digital sensor."""

    combined = f"{item.value} {item.part_number} {item.manufacturer}".upper()
    return any(token in combined for token in ("MCP", "BME", "BMP", "SHT", "SENSOR"))


def _dedupe_pins(pins: list[NetPin]) -> list[NetPin]:
    """Return pins with duplicate reference/pin combinations removed."""

    seen: set[tuple[str, str]] = set()
    unique: list[NetPin] = []
    for pin in pins:
        key = (pin.reference, pin.pin_number)
        if key in seen:
            continue
        seen.add(key)
        unique.append(pin)
    return unique


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
        nets=[NetDescription(net_name=net.net_name, pins=_dedupe_pins(net.pins), notes=net.notes) for net in nets if len(net.pins) >= 2 or net.net_name in {"OUTPUT", "CONTROL"}],
        signal_flow=[
            "5V rail powers the timer and holds RESET high.",
            "RA and RB charge/discharge the timing capacitor through DISCHARGE_NODE.",
            "Pins 2 and 6 sense the timing capacitor voltage at TIMING_NODE.",
            "Pin 3 drives the LED through a current-limiting resistor.",
        ],
        power_symbols=["VCC", "GND", "PWR_FLAG"],
    )


def _build_sensor_breakout_netlist(bom: BillOfMaterials, datasheets: dict[str, DatasheetInfo]) -> NetlistDescription:
    """Create a practical breakout-style netlist for a sensor with header and pull-ups."""

    sensor = next((item for item in bom.items if _looks_like_sensor(item)), None)
    header = _find_first(bom.items, "J")
    if sensor is None or header is None:
        return NetlistDescription()
    resistors = _find_items(bom.items, "R")
    capacitors = _find_items(bom.items, "C")
    leds = _find_items(bom.items, "D")
    vcc_pin = _find_pin_number(sensor, datasheets, ("VCC", "VDD", "VIN"), "1")
    gnd_pin = _find_pin_number(sensor, datasheets, ("GND", "VSS"), "2")
    sda_pin = _find_pin_number(sensor, datasheets, ("SDA", "SDI", "DATA"), "3")
    scl_pin = _find_pin_number(sensor, datasheets, ("SCL", "CLK", "SCK"), "4")
    decoupling = next((item for item in capacitors if "100N" in item.value.upper()), None)
    led_resistor = next((item for item in resistors if "1K" in item.value.upper() or "330" in item.value.upper()), None)
    pullups = [item for item in resistors if item != led_resistor][:2]

    nets: list[NetDescription] = [
        NetDescription(
            net_name="VCC",
            pins=[_net(header.reference, "1", "VCC"), _net(sensor.reference, vcc_pin, "VCC")],
            notes="Header supply into the sensor.",
        ),
        NetDescription(
            net_name="GND",
            pins=[_net(header.reference, "2", "GND"), _net(sensor.reference, gnd_pin, "GND")],
            notes="Shared ground between header and sensor.",
        ),
        NetDescription(
            net_name="SDA",
            pins=[_net(header.reference, "3", "SDA"), _net(sensor.reference, sda_pin, "SDA")],
            notes="I2C data line with pull-up support.",
        ),
        NetDescription(
            net_name="SCL",
            pins=[_net(header.reference, "4", "SCL"), _net(sensor.reference, scl_pin, "SCL")],
            notes="I2C clock line with pull-up support.",
        ),
    ]
    if decoupling is not None:
        nets[0].pins.append(_net(decoupling.reference, "1", "POS"))
        nets[1].pins.append(_net(decoupling.reference, "2", "NEG"))
    if len(pullups) >= 1:
        nets[0].pins.append(_net(pullups[0].reference, "1", "VCC"))
        nets[2].pins.append(_net(pullups[0].reference, "2", "SDA"))
    if len(pullups) >= 2:
        nets[0].pins.append(_net(pullups[1].reference, "1", "VCC"))
        nets[3].pins.append(_net(pullups[1].reference, "2", "SCL"))
    if leds and led_resistor is not None:
        nets.append(
            NetDescription(
                net_name="PWR_LED",
                pins=[
                    _net(header.reference, "1", "VCC"),
                    _net(led_resistor.reference, "1", "IN"),
                    _net(led_resistor.reference, "2", "OUT"),
                    _net(leds[0].reference, "1", "A"),
                ],
                notes="Power indicator chain from the header supply.",
            )
        )
        nets[1].pins.append(_net(leds[0].reference, "2", "K"))
    return NetlistDescription(
        nets=[NetDescription(net_name=net.net_name, pins=_dedupe_pins(net.pins), notes=net.notes) for net in nets],
        signal_flow=["Header power entry", "Sensor supply decoupling", "I2C breakout with pull-ups"],
        power_symbols=["VCC", "GND", "PWR_FLAG"],
    )


def _build_op_amp_netlist(bom: BillOfMaterials, datasheets: dict[str, DatasheetInfo]) -> NetlistDescription:
    """Create a simple non-inverting op-amp stage."""

    amplifier = next((item for item in bom.items if _looks_like_op_amp(item)), None)
    if amplifier is None:
        return NetlistDescription()
    resistors = _find_items(bom.items, "R")
    capacitors = _find_items(bom.items, "C")
    connectors = _find_items(bom.items, "J")
    vcc_pin = _find_pin_number(amplifier, datasheets, ("VCC", "VDD", "V+"), "8")
    gnd_pin = _find_pin_number(amplifier, datasheets, ("GND", "VSS", "V-"), "4")
    out_pin = _find_pin_number(amplifier, datasheets, ("OUT", "OUTPUT"), "1")
    minus_pin = _find_pin_number(amplifier, datasheets, ("IN-", "-", "INV"), "2")
    plus_pin = _find_pin_number(amplifier, datasheets, ("IN+", "+", "NON"), "3")
    feedback = resistors[0] if resistors else None
    input_resistor = resistors[1] if len(resistors) > 1 else feedback
    bias_resistor = resistors[2] if len(resistors) > 2 else None
    input_cap = next((item for item in capacitors if "100N" not in item.value.upper()), None)
    decoupling = next((item for item in capacitors if "100N" in item.value.upper()), None)
    input_conn = connectors[0] if connectors else None
    output_conn = connectors[1] if len(connectors) > 1 else input_conn

    nets: list[NetDescription] = [
        NetDescription(
            net_name="VCC",
            pins=[_net(amplifier.reference, vcc_pin, "VCC")],
            notes="Amplifier positive supply rail.",
        ),
        NetDescription(
            net_name="GND",
            pins=[_net(amplifier.reference, gnd_pin, "GND")],
            notes="Amplifier return and bias reference.",
        ),
        NetDescription(
            net_name="AMP_OUT",
            pins=[_net(amplifier.reference, out_pin, "OUT")],
            notes="Amplifier output node.",
        ),
        NetDescription(
            net_name="AMP_IN",
            pins=[_net(amplifier.reference, plus_pin, "IN+")],
            notes="Non-inverting input path.",
        ),
        NetDescription(
            net_name="FB_NODE",
            pins=[_net(amplifier.reference, minus_pin, "IN-")],
            notes="Feedback node around the amplifier.",
        ),
    ]
    if input_conn is not None:
        nets[3].pins.append(_net(input_conn.reference, "1", "SIG_IN"))
        nets[1].pins.append(_net(input_conn.reference, "2", "GND"))
    if output_conn is not None:
        nets[2].pins.append(_net(output_conn.reference, "1", "SIG_OUT"))
        nets[1].pins.append(_net(output_conn.reference, "2", "GND"))
    if input_cap is not None:
        nets[3].pins.append(_net(input_cap.reference, "1", "IN"))
        if input_conn is not None:
            nets.append(
                NetDescription(
                    net_name="INPUT_SOURCE",
                    pins=[_net(input_conn.reference, "1", "SIG_IN"), _net(input_cap.reference, "2", "SRC")],
                    notes="AC-coupled source into the amplifier input.",
                )
            )
    if feedback is not None:
        nets[2].pins.append(_net(feedback.reference, "1", "OUT"))
        nets[4].pins.append(_net(feedback.reference, "2", "FB"))
    if input_resistor is not None:
        nets[4].pins.append(_net(input_resistor.reference, "1", "FB"))
        nets[1].pins.append(_net(input_resistor.reference, "2", "GND"))
    if bias_resistor is not None:
        nets[3].pins.append(_net(bias_resistor.reference, "1", "BIAS"))
        nets[1].pins.append(_net(bias_resistor.reference, "2", "GND"))
    if decoupling is not None:
        nets[0].pins.append(_net(decoupling.reference, "1", "POS"))
        nets[1].pins.append(_net(decoupling.reference, "2", "NEG"))
    return NetlistDescription(
        nets=[NetDescription(net_name=net.net_name, pins=_dedupe_pins(net.pins), notes=net.notes) for net in nets if len(net.pins) >= 2],
        signal_flow=["Signal input and biasing", "Closed-loop op-amp gain stage", "Buffered output"],
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
    if any(_looks_like_sensor(item) for item in bom.items) and _find_first(bom.items, "J") is not None:
        sensor_netlist = _build_sensor_breakout_netlist(bom, datasheets)
        if sensor_netlist.nets:
            return sensor_netlist
    if any(_looks_like_op_amp(item) for item in bom.items):
        op_amp_netlist = _build_op_amp_netlist(bom, datasheets)
        if op_amp_netlist.nets:
            return op_amp_netlist
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


def _effects(hidden: bool = False, justify: str = "left") -> str:
    """Return a standard KiCad text effects block."""

    hide = " hide" if hidden else ""
    return f'(effects (font (size 1.27 1.27)) (justify {justify}){hide})'


def _stroke(width: float = 0.254) -> str:
    """Return a simple default stroke block."""

    return f'(stroke (width {width:.4f}) (type default))'


def _wire(points: list[tuple[float, float]]) -> list[str]:
    """Render a schematic wire block."""

    pts = " ".join(f'(xy {x:.2f} {y:.2f})' for x, y in points)
    return [f'  (wire (pts {pts}) {_stroke(0)} (uuid "{uuid.uuid4()}"))']


def _label(text: str, x: float, y: float) -> list[str]:
    """Render a local label block."""

    return [f'  (label "{text}" (at {x:.2f} {y:.2f} 0) {_effects()} (uuid "{uuid.uuid4()}"))']


def _property_block(name: str, value: str, identifier: int, x: float, y: float, hidden: bool = False) -> str:
    """Render a schematic property block."""

    return f'    (property "{name}" "{value}" (id {identifier}) (at {x:.2f} {y:.2f} 0) {_effects(hidden=hidden)})'


def _instance_block(item: BOMItem, lib_id: str, x: float, y: float, extra_pins: list[str]) -> list[str]:
    """Render a symbol instance block."""

    symbol_uuid = str(uuid.uuid4())
    lines = [
        f'  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)',
        f'    (uuid "{symbol_uuid}")',
        _property_block("Reference", item.reference, 0, x - 3.0, y - 4.0),
        _property_block("Value", item.value, 1, x - 3.0, y + 4.0),
        _property_block("Footprint", item.footprint, 2, x, y, hidden=True),
        _property_block("Datasheet", item.datasheet_url or "~", 3, x, y, hidden=True),
    ]
    lines.extend(f'    {pin}' for pin in extra_pins)
    lines.extend(
        [
            '    (instances',
            '      (project "Nexus"',
            f'        (path "/{symbol_uuid}"',
            f'          (reference "{item.reference}")',
            "          (unit 1)",
            "        )",
            "      )",
            "    )",
            "  )",
        ]
    )
    return lines


def _two_pin_symbol(symbol_name: str, graphic_kind: str) -> list[str]:
    """Return an embedded two-pin symbol definition."""

    if graphic_kind == "resistor":
        shape = '      (rectangle (start -2.54 1.27) (end 2.54 -1.27) ' + _stroke(0.2032) + ' (fill (type none)))'
    elif graphic_kind == "capacitor":
        shape = (
            '      (polyline (pts (xy -0.76 -1.52) (xy -0.76 1.52)) ' + _stroke(0.3048) + ' (fill (type none)))\n'
            '      (polyline (pts (xy 0.76 -1.52) (xy 0.76 1.52)) ' + _stroke(0.3048) + ' (fill (type none)))'
        )
    else:
        shape = (
            '      (polyline (pts (xy -2.03 0) (xy 0 -1.52) (xy 0 1.52) (xy -2.03 0)) '
            + _stroke(0.2032)
            + ' (fill (type none)))\n'
            '      (polyline (pts (xy 0.76 -1.52) (xy 0.76 1.52)) '
            + _stroke(0.2032)
            + ' (fill (type none)))'
        )
    return [
        f'    (symbol "{symbol_name}" (pin_numbers hide) (pin_names (offset 0.254) hide) (in_bom yes) (on_board yes)',
        '      (property "Reference" "X" (at 0 2.54 0) (effects (font (size 1.27 1.27))))',
        f'      (property "Value" "{symbol_name.split(":")[1]}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        f'      (symbol "{symbol_name.split(":")[1]}_0_1"',
        *shape.split("\n"),
        "      )",
        f'      (symbol "{symbol_name.split(":")[1]}_1_1"',
        '        (pin passive line (at -5.08 0 0) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))',
        '        (pin passive line (at 5.08 0 180) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))',
        "      )",
        "    )",
    ]


def _timer_symbol() -> list[str]:
    """Return an embedded NE555-like symbol definition."""

    return [
        '    (symbol "Nexus:Timer555" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)',
        '      (property "Reference" "U" (at 0 13.97 0) (effects (font (size 1.27 1.27))))',
        '      (property "Value" "NE555" (at 0 -13.97 0) (effects (font (size 1.27 1.27))))',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (symbol "Timer555_0_1"',
        '        (rectangle (start -7.62 10.16) (end 7.62 -10.16) (stroke (width 0.2032) (type default)) (fill (type none)))',
        '      )',
        '      (symbol "Timer555_1_1"',
        '        (pin power_in line (at -12.70 7.62 0) (length 5.08) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at -12.70 2.54 0) (length 5.08) (name "TRIG" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))',
        '        (pin output line (at -12.70 -2.54 0) (length 5.08) (name "OUT" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at -12.70 -7.62 0) (length 5.08) (name "RESET" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at 12.70 -7.62 180) (length 5.08) (name "CTRL" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at 12.70 -2.54 180) (length 5.08) (name "THRESH" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at 12.70 2.54 180) (length 5.08) (name "DISCH" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))',
        '        (pin power_in line (at 12.70 7.62 180) (length 5.08) (name "VCC" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))',
        "      )",
        "    )",
    ]


def _connector_symbol(pin_count: int) -> list[str]:
    """Return an embedded generic connector symbol."""

    symbol_name = f"Nexus:Conn_{pin_count}"
    lines = [
        f'    (symbol "{symbol_name}" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)',
        '      (property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))',
        f'      (property "Value" "Conn_{pin_count}" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        f'      (symbol "Conn_{pin_count}_0_1"',
        f'        (rectangle (start -2.54 {pin_count * 1.27 + 1.27:.2f}) (end 2.54 {-pin_count * 1.27 - 1.27:.2f}) {_stroke(0.2032)} (fill (type none)))',
        "      )",
        f'      (symbol "Conn_{pin_count}_1_1"',
    ]
    start_y = ((pin_count - 1) * 2.54) / 2
    for index in range(pin_count):
        y = start_y - (index * 2.54)
        lines.append(
            f'        (pin passive line (at -5.08 {y:.2f} 0) (length 2.54) (name "P{index + 1}" (effects (font (size 1.27 1.27)))) (number "{index + 1}" (effects (font (size 1.27 1.27)))))'
        )
    lines.extend(["      )", "    )"])
    return lines


def _transistor_symbol() -> list[str]:
    """Return an embedded simple transistor symbol."""

    return [
        '    (symbol "Nexus:Q3" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)',
        '      (property "Reference" "Q" (at 0 5.08 0) (effects (font (size 1.27 1.27))))',
        '      (property "Value" "Q3" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (symbol "Q3_0_1"',
        '        (rectangle (start -2.54 3.81) (end 2.54 -3.81) (stroke (width 0.2032) (type default)) (fill (type none)))',
        '      )',
        '      (symbol "Q3_1_1"',
        '        (pin input line (at -5.08 0 0) (length 2.54) (name "B/G" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))',
        '        (pin passive line (at 5.08 -2.54 180) (length 2.54) (name "E/S" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))',
        '        (pin passive line (at 5.08 2.54 180) (length 2.54) (name "C/D" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))',
        "      )",
        "    )",
    ]


def _opamp_symbol() -> list[str]:
    """Return an embedded simple op-amp symbol."""

    return [
        '    (symbol "Nexus:OpAmp" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)',
        '      (property "Reference" "U" (at 0 8.89 0) (effects (font (size 1.27 1.27))))',
        '      (property "Value" "OpAmp" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))',
        '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
        '      (symbol "OpAmp_0_1"',
        '        (polyline (pts (xy -5.08 5.08) (xy -5.08 -5.08) (xy 5.08 0) (xy -5.08 5.08)) (stroke (width 0.2032) (type default)) (fill (type none)))',
        "      )",
        '      (symbol "OpAmp_1_1"',
        '        (pin input line (at -10.16 2.54 0) (length 5.08) (name "+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))',
        '        (pin input line (at -10.16 -2.54 0) (length 5.08) (name "-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))',
        '        (pin output line (at 10.16 0 180) (length 5.08) (name "OUT" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))',
        '        (pin power_in line (at 0 10.16 270) (length 2.54) (name "V+" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))',
        '        (pin power_in line (at 0 -10.16 90) (length 2.54) (name "V-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))',
        "      )",
        "    )",
    ]


def _embedded_lib_symbols() -> list[str]:
    """Return embedded symbol library definitions used by the schematic writer."""

    lines = ["  (lib_symbols)"]
    lines = ["  (lib_symbols"] + _timer_symbol() + _two_pin_symbol("Nexus:R", "resistor") + _two_pin_symbol("Nexus:C", "capacitor") + _two_pin_symbol("Nexus:LED", "led") + _connector_symbol(2) + _connector_symbol(4) + _transistor_symbol() + _opamp_symbol() + ["  )"]
    return lines


def _instance_lib_id(item: BOMItem) -> str:
    """Return the embedded symbol id for a BOM item."""

    if _looks_like_timer(item):
        return "Nexus:Timer555"
    if _looks_like_op_amp(item):
        return "Nexus:OpAmp"
    if item.reference.startswith("R"):
        return "Nexus:R"
    if item.reference.startswith("C"):
        return "Nexus:C"
    if item.reference.startswith("D"):
        return "Nexus:LED"
    if item.reference.startswith("Q"):
        return "Nexus:Q3"
    if item.reference.startswith("J"):
        pin_count = 4 if "I2C" in item.value.upper() or "HEADER" in item.value.upper() else 2
        return f"Nexus:Conn_{pin_count}"
    return "Nexus:Timer555"


def _pin_uuids(pin_numbers: list[str]) -> list[str]:
    """Return pin uuid lines for a symbol instance."""

    return [f'(pin "{pin_number}" (uuid "{uuid.uuid4()}"))' for pin_number in pin_numbers]


def _pin_position(reference: str, center: tuple[float, float], pin_number: str) -> tuple[float, float]:
    """Return absolute pin positions for embedded symbols."""

    x, y = center
    if reference.startswith("U"):
        timer_pins = {
            "1": (x - 12.70, y + 7.62),
            "2": (x - 12.70, y + 2.54),
            "3": (x - 12.70, y - 2.54),
            "4": (x - 12.70, y - 7.62),
            "5": (x + 12.70, y - 7.62),
            "6": (x + 12.70, y - 2.54),
            "7": (x + 12.70, y + 2.54),
            "8": (x + 12.70, y + 7.62),
        }
        return timer_pins.get(pin_number, (x, y))
    if reference.startswith(("R", "C", "D")):
        return (x - 5.08, y) if pin_number == "1" else (x + 5.08, y)
    if reference.startswith("Q"):
        mapping = {"1": (x - 5.08, y), "2": (x + 5.08, y - 2.54), "3": (x + 5.08, y + 2.54)}
        return mapping.get(pin_number, (x, y))
    if reference.startswith("J"):
        if pin_number == "1":
            return (x - 5.08, y + 1.27)
        if pin_number == "2":
            return (x - 5.08, y - 1.27)
        if pin_number == "3":
            return (x - 5.08, y + 3.81)
        if pin_number == "4":
            return (x - 5.08, y - 3.81)
    return (x, y)


def _place_timer_schematic(bom: BillOfMaterials, schematic_uuid: str) -> list[str]:
    """Render a structured 555 timer schematic with visible wires."""

    items = {item.reference: item for item in bom.items}
    centers = {
        "U1": (100.0, 90.0),
        "R1": (150.0, 70.0),
        "R2": (150.0, 100.0),
        "C1": (100.0, 130.0),
        "C2": (65.0, 65.0),
        "C3": (135.0, 125.0),
        "R3": (60.0, 100.0),
        "D1": (30.0, 100.0),
    }
    lines: list[str] = []
    for reference, center in centers.items():
        item = items.get(reference)
        if item is None:
            continue
        pin_numbers = ["1", "2", "3", "4", "5", "6", "7", "8"] if reference == "U1" else ["1", "2"]
        lines.extend(_instance_block(item, _instance_lib_id(item), center[0], center[1], _pin_uuids(pin_numbers)))

    # VCC rail and RESET tie
    vcc = _pin_position("U1", centers["U1"], "8")
    reset = _pin_position("U1", centers["U1"], "4")
    r1_pin1 = _pin_position("R1", centers["R1"], "1")
    c2_pin1 = _pin_position("C2", centers["C2"], "1")
    lines.extend(_wire([(65.0, 50.0), (165.0, 50.0)]))
    lines.extend(_wire([vcc, (vcc[0], 50.0)]))
    lines.extend(_wire([reset, (reset[0], 50.0)]))
    lines.extend(_wire([r1_pin1, (r1_pin1[0], 50.0)]))
    lines.extend(_wire([c2_pin1, (c2_pin1[0], 50.0)]))
    lines.extend(_label("VCC", 67.0, 47.0))

    # Ground rail
    gnd = _pin_position("U1", centers["U1"], "1")
    c1_pin2 = _pin_position("C1", centers["C1"], "2")
    c2_pin2 = _pin_position("C2", centers["C2"], "2")
    c3_pin2 = _pin_position("C3", centers["C3"], "2")
    d1_pin2 = _pin_position("D1", centers["D1"], "2")
    lines.extend(_wire([(20.0, 150.0), (150.0, 150.0)]))
    for point in (gnd, c1_pin2, c2_pin2, c3_pin2, d1_pin2):
        lines.extend(_wire([point, (point[0], 150.0)]))
    lines.extend(_label("GND", 22.0, 147.0))

    # Timing node
    trig = _pin_position("U1", centers["U1"], "2")
    thresh = _pin_position("U1", centers["U1"], "6")
    r2_pin2 = _pin_position("R2", centers["R2"], "2")
    c1_pin1 = _pin_position("C1", centers["C1"], "1")
    lines.extend(_wire([trig, (trig[0] - 10.0, trig[1]), (trig[0] - 10.0, c1_pin1[1]), (c1_pin1[0], c1_pin1[1])]))
    lines.extend(_wire([thresh, (thresh[0] + 8.0, thresh[1]), (thresh[0] + 8.0, r2_pin2[1]), r2_pin2]))
    lines.extend(_wire([(trig[0] - 10.0, trig[1]), (thresh[0] + 8.0, trig[1])]))
    lines.extend(_label("TIMING_NODE", 109.0, 83.0))

    # Discharge node
    disch = _pin_position("U1", centers["U1"], "7")
    r1_pin2 = _pin_position("R1", centers["R1"], "2")
    r2_pin1 = _pin_position("R2", centers["R2"], "1")
    lines.extend(_wire([disch, (disch[0] + 10.0, disch[1]), (disch[0] + 10.0, r2_pin1[1]), r2_pin1]))
    lines.extend(_wire([(disch[0] + 10.0, disch[1]), (r1_pin2[0], disch[1]), r1_pin2]))
    lines.extend(_label("DISCHARGE_NODE", 116.0, 89.0))

    # Output LED chain
    out_pin = _pin_position("U1", centers["U1"], "3")
    r3_pin1 = _pin_position("R3", centers["R3"], "1")
    r3_pin2 = _pin_position("R3", centers["R3"], "2")
    d1_pin1 = _pin_position("D1", centers["D1"], "1")
    lines.extend(_wire([out_pin, (r3_pin1[0], out_pin[1]), r3_pin1]))
    lines.extend(_wire([r3_pin2, d1_pin1]))
    lines.extend(_label("OUTPUT", 66.0, 94.0))

    # Control capacitor
    ctrl = _pin_position("U1", centers["U1"], "5")
    c3_pin1 = _pin_position("C3", centers["C3"], "1")
    lines.extend(_wire([ctrl, (ctrl[0], c3_pin1[1]), c3_pin1]))
    lines.extend(_label("CONTROL", 118.0, 114.0))
    return lines


def _write_schematic(bom: BillOfMaterials, netlist: NetlistDescription, schematic_path: Path) -> None:
    """Write a more human-readable KiCad 7 schematic file."""

    schematic_uuid = str(uuid.uuid4())
    lines = [
        "(kicad_sch",
        '  (version 20250114)',
        '  (generator "nexus-backend")',
        f'  (uuid "{schematic_uuid}")',
        '  (paper "A4")',
        '  (title_block (title "Nexus Generated Circuit"))',
        *_embedded_lib_symbols(),
    ]
    if any(_looks_like_timer(item) for item in bom.items):
        lines.extend(_place_timer_schematic(bom, schematic_uuid))
    else:
        for index, item in enumerate(bom.items):
            x = 50 + (index % 4) * 40
            y = 55 + (index // 4) * 28
            pin_numbers = ["1", "2"]
            if item.reference.startswith("U") and _looks_like_op_amp(item):
                pin_numbers = ["1", "2", "3", "4", "8"]
            elif item.reference.startswith("U"):
                pin_numbers = ["1", "2", "3", "4", "5", "6", "7", "8"]
            elif item.reference.startswith("Q"):
                pin_numbers = ["1", "2", "3"]
            elif item.reference.startswith("J"):
                pin_numbers = ["1", "2", "3", "4"] if "I2C" in item.value.upper() or "HEADER" in item.value.upper() else ["1", "2"]
            lines.extend(_instance_block(item, _instance_lib_id(item), x, y, _pin_uuids(pin_numbers)))
        for net in netlist.nets:
            if len(net.pins) < 2:
                continue
            lines.extend(_label(net.net_name, 20.0, 20.0 + (len(lines) % 10) * 4.0))
    lines.extend(
        [
            '  (sheet_instances',
            '    (path "/" (page "1"))',
            "  )",
            ")",
        ]
    )
    schematic_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_usable_netlist(netlist: NetlistDescription) -> bool:
    """Return true when a netlist looks plausible enough to keep."""

    if len(netlist.nets) < 4:
        return False
    if not (any(net.net_name == "VCC" for net in netlist.nets) and any(net.net_name == "GND" for net in netlist.nets)):
        return False
    if any(len(_dedupe_pins(net.pins)) != len(net.pins) for net in netlist.nets):
        return False
    return any(len(net.pins) >= 3 for net in netlist.nets)


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
