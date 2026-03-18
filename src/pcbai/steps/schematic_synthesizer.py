"""Schematic synthesis from BOM and datasheet metadata."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError, get_llm_provider
from pcbai.models import BillOfMaterials, DatasheetInfo, NetDescription, NetPin, NetlistDescription


def _schema() -> dict[str, Any]:
    """Return the JSON schema used for netlist generation."""

    return {
        "type": "object",
        "properties": {
            "nets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "net_name": {"type": "string"},
                        "notes": {"type": "string"},
                        "pins": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "reference": {"type": "string"},
                                    "pin_number": {"type": "string"},
                                    "pin_name": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "signal_flow": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["nets", "signal_flow"],
    }


def _fallback_netlist(bom: BillOfMaterials) -> NetlistDescription:
    """Generate a practical default netlist when the LLM is unavailable."""

    nets: list[NetDescription] = []
    power_refs = [item.reference for item in bom.items if item.reference.startswith(("U", "D", "Q"))]
    if power_refs:
        nets.append(
            NetDescription(
                net_name="VCC",
                pins=[NetPin(reference=reference, pin_number="8", pin_name="VCC") for reference in power_refs],
                notes="Primary positive supply",
            )
        )
        nets.append(
            NetDescription(
                net_name="GND",
                pins=[NetPin(reference=reference, pin_number="1", pin_name="GND") for reference in power_refs],
                notes="Primary ground return",
            )
        )

    first_ic = next((item.reference for item in bom.items if item.reference.startswith("U")), None)
    led = next((item.reference for item in bom.items if item.reference.startswith("D")), None)
    resistor = next((item.reference for item in bom.items if item.reference.startswith("R")), None)
    if first_ic and led and resistor:
        nets.append(
            NetDescription(
                net_name="OUT",
                pins=[
                    NetPin(reference=first_ic, pin_number="3", pin_name="OUT"),
                    NetPin(reference=resistor, pin_number="1", pin_name="IN"),
                    NetPin(reference=led, pin_number="1", pin_name="A"),
                ],
                notes="Default signal path",
            )
        )
        nets.append(
            NetDescription(
                net_name="LED_RETURN",
                pins=[
                    NetPin(reference=resistor, pin_number="2", pin_name="OUT"),
                    NetPin(reference=led, pin_number="2", pin_name="K"),
                ],
                notes="LED return path",
            )
        )

    if not nets:
        refs = [item.reference for item in bom.items]
        nets.append(
            NetDescription(
                net_name="NET_MAIN",
                pins=[NetPin(reference=reference, pin_number="1", pin_name="IO") for reference in refs],
                notes="Fallback shared signal",
            )
        )

    return NetlistDescription(nets=nets, signal_flow=["Power enters via connector", "Main IC drives loads"])


def _render_netlist_summary(netlist: NetlistDescription, console: Console) -> None:
    """Print a rich netlist summary table."""

    table = Table(title="Netlist Summary")
    table.add_column("Net")
    table.add_column("Pins")
    table.add_column("Notes")
    for net in netlist.nets:
        pin_text = ", ".join(f"{pin.reference}:{pin.pin_number}" for pin in net.pins)
        table.add_row(net.net_name, pin_text, net.notes)
    console.print(table)


def _symbol_library_id(reference: str) -> str:
    """Map references to simple KiCad symbol library IDs."""

    if reference.startswith("R"):
        return "Device:R"
    if reference.startswith("C"):
        return "Device:C"
    if reference.startswith("D"):
        return "Device:LED"
    if reference.startswith("Q"):
        return "Device:Q_NPN_BEC"
    if reference.startswith("J"):
        return "Connector_Generic:Conn_01x02"
    return "Device:U"


def _write_basic_kicad_schematic(
    bom: BillOfMaterials,
    netlist: NetlistDescription,
    schematic_path: Path,
) -> None:
    """Write a minimal KiCad 7 schematic file with component properties."""

    lines = [
        "(kicad_sch (version 20230121) (generator pcbai)",
        '  (paper "A4")',
        '  (title_block (title "AI Generated PCB"))',
    ]
    base_x = 40.0
    base_y = 40.0

    for index, item in enumerate(bom.items):
        x = base_x + (index % 4) * 35.0
        y = base_y + (index // 4) * 25.0
        lines.extend(
            [
                f'  (symbol (lib_id "{_symbol_library_id(item.reference)}") (at {x:.2f} {y:.2f} 0)',
                f"    (uuid {uuid.uuid4()})",
                f'    (property "Reference" "{item.reference}" (id 0) (at {x:.2f} {y - 2:.2f} 0))',
                f'    (property "Value" "{item.value}" (id 1) (at {x:.2f} {y + 2:.2f} 0))',
                f'    (property "Footprint" "{item.footprint}" (id 2) (at {x:.2f} {y + 4:.2f} 0))',
                f'    (property "PartNumber" "{item.part_number}" (id 3) (at {x:.2f} {y + 6:.2f} 0))',
                "  )",
            ]
        )

    for index, net in enumerate(netlist.nets):
        joined = ", ".join(f"{pin.reference}:{pin.pin_number}" for pin in net.pins)
        lines.append(f'  (text "{net.net_name}: {joined}" (at 10 {15 + index * 5} 0))')

    lines.append(")")
    schematic_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_skidl_artifacts(bom: BillOfMaterials, schematic_path: Path) -> None:
    """Generate a SKiDL netlist companion file when SKiDL is available."""

    try:
        from skidl import ERC, Net, Part, generate_netlist, reset
    except ImportError:  # pragma: no cover - optional dependency
        return

    reset()
    vcc = Net("VCC")
    gnd = Net("GND")
    for item in bom.items:
        part = Part("Device", "R" if item.reference.startswith("R") else "U", ref=item.reference, value=item.value, footprint=item.footprint)
        if len(part.pins) >= 1:
            vcc += part[1]
        if len(part.pins) >= 2:
            gnd += part[2]
    ERC()
    netlist_text = generate_netlist()
    schematic_path.with_suffix(".net").write_text(netlist_text, encoding="utf-8")


def synthesize_schematic(
    bom: BillOfMaterials,
    datasheets: dict[str, DatasheetInfo],
    provider: BaseLLMProvider | None = None,
    output_dir: str | Path | None = None,
    console: Console | None = None,
) -> str:
    """Generate a KiCad schematic file path from BOM and datasheet info."""

    console = console or Console()
    provider = provider or get_llm_provider()
    root_dir = Path(output_dir) if output_dir else get_settings().ensure_output_dir()
    root_dir.mkdir(parents=True, exist_ok=True)
    schematic_path = root_dir / "design.kicad_sch"

    prompt = (
        "Create a compact PCB netlist description based on this BOM and datasheet summary. "
        "Include power, ground, and key signal flow nets.\n\n"
        f"BOM:\n{bom.model_dump_json(indent=2)}\n\n"
        f"Datasheets:\n{json.dumps({key: value.model_dump() for key, value in datasheets.items()}, indent=2)}"
    )

    try:
        payload = provider.generate_json(prompt, _schema())
        netlist = NetlistDescription.model_validate(payload)
    except (LLMProviderError, ValueError, TypeError):
        netlist = _fallback_netlist(bom)

    _render_netlist_summary(netlist, console)
    _write_basic_kicad_schematic(bom, netlist, schematic_path)
    schematic_path.with_suffix(".nets.json").write_text(netlist.model_dump_json(indent=2), encoding="utf-8")
    schematic_path.with_suffix(".bom.json").write_text(bom.model_dump_json(indent=2), encoding="utf-8")
    _write_skidl_artifacts(bom, schematic_path)
    console.print(f"[green]Schematic saved to[/green] {schematic_path}")
    return str(schematic_path)
