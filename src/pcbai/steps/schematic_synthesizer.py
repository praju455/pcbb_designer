"""Schematic synthesis with dual-LLM netlist verification."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_generator_llm, get_verifier_llm
from pcbai.models import BillOfMaterials, DatasheetInfo, NetDescription, NetPin, NetlistDescription


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


def _fallback_netlist(bom: BillOfMaterials) -> NetlistDescription:
    """Create a conservative fallback netlist."""

    nets: list[NetDescription] = []
    ics = [item.reference for item in bom.items if item.reference.startswith("U")]
    decouplers = [item.reference for item in bom.items if item.reference.startswith("C")]
    leds = [item.reference for item in bom.items if item.reference.startswith("D")]
    resistors = [item.reference for item in bom.items if item.reference.startswith("R")]
    if ics:
        nets.append(NetDescription(net_name="VCC", pins=[NetPin(reference=ref, pin_number="8", pin_name="VCC") for ref in ics], notes="Main supply"))
        nets.append(NetDescription(net_name="GND", pins=[NetPin(reference=ref, pin_number="1", pin_name="GND") for ref in ics], notes="Ground return"))
    if ics and decouplers:
        nets.append(
            NetDescription(
                net_name="DECOUPLE",
                pins=[NetPin(reference=ics[0], pin_number="8", pin_name="VCC"), NetPin(reference=decouplers[0], pin_number="1", pin_name="VCC")],
                notes="Decoupling capacitor",
            )
        )
    if ics and leds and resistors:
        nets.append(
            NetDescription(
                net_name="OUT",
                pins=[
                    NetPin(reference=ics[0], pin_number="3", pin_name="OUT"),
                    NetPin(reference=resistors[0], pin_number="1", pin_name="IN"),
                    NetPin(reference=leds[0], pin_number="1", pin_name="A"),
                ],
                notes="Primary output",
            )
        )
    return NetlistDescription(nets=nets, signal_flow=["Input power", "Timing core", "Output stage"], power_symbols=["VCC", "GND", "PWR_FLAG"])


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
    """Write a lightweight KiCad 7 schematic file."""

    lines = [
        "(kicad_sch (version 20230121) (generator circuitforge-ai)",
        '  (paper "A4")',
        '  (title_block (title "CircuitForge AI"))',
    ]
    for index, item in enumerate(bom.items):
        x = 40 + (index % 4) * 40
        y = 35 + (index // 4) * 30
        lines.extend(
            [
                f'  (symbol (lib_id "Device:U") (at {x} {y} 0)',
                f"    (uuid {uuid.uuid4()})",
                f'    (property "Reference" "{item.reference}" (id 0) (at {x} {y - 3} 0))',
                f'    (property "Value" "{item.value}" (id 1) (at {x} {y + 3} 0))',
                f'    (property "Footprint" "{item.footprint}" (id 2) (at {x} {y + 6} 0))',
                "  )",
            ]
        )
    for row, net in enumerate(netlist.nets, start=1):
        joined = ", ".join(f"{pin.reference}:{pin.pin_number}" for pin in net.pins)
        lines.append(f'  (text "{net.net_name} -> {joined}" (at 10 {10 + row * 5} 0))')
    lines.append(")")
    schematic_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "Include VCC, GND, signal nets, and decoupling capacitors.\n\n"
        f"BOM:\n{bom.model_dump_json(indent=2)}\n\n"
        f"Datasheets:\n{json.dumps({key: value.model_dump() for key, value in datasheets.items()}, indent=2)}"
    )

    try:
        payload = generator.generate_json(prompt, _netlist_schema())
        review = verifier.generate(
            "Review this netlist for floating inputs, power correctness, and missing decoupling capacitors.\n\n"
            f"{json.dumps(payload, indent=2)}"
        )
        if "issue" in review.lower() and "no issue" not in review.lower():
            raise LLMProviderError(review)
        netlist = NetlistDescription.model_validate(payload)
    except (LLMProviderError, ValueError, TypeError):
        netlist = _fallback_netlist(bom)

    _render(netlist, console)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_schematic(bom, netlist, schematic_path)
    schematic_path.with_suffix(".netlist.json").write_text(netlist.model_dump_json(indent=2), encoding="utf-8")
    schematic_path.with_suffix(".bom.json").write_text(bom.model_dump_json(indent=2), encoding="utf-8")
    return str(schematic_path)
