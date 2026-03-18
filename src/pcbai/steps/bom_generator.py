"""BOM generation with Groq synthesis and Gemini footprint verification."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_generator_llm, get_verifier_llm
from pcbai.models import BOMItem, BillOfMaterials, CircuitRequirements, ComponentRequirement


_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
    "ic": "U",
    "led": "D",
    "transistor": "Q",
    "connector": "J",
}


def _bom_schema() -> dict[str, Any]:
    """Return the schema expected from the generator."""

    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "value": {"type": "string"},
                        "footprint": {"type": "string"},
                        "datasheet_url": {"type": "string"},
                        "manufacturer": {"type": "string"},
                        "part_number": {"type": "string"},
                        "lcsc_part": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1},
                        "unit_price_usd": {"type": "number", "minimum": 0},
                    },
                    "required": [
                        "reference",
                        "value",
                        "footprint",
                        "datasheet_url",
                        "manufacturer",
                        "part_number",
                        "lcsc_part",
                        "quantity",
                        "unit_price_usd",
                    ],
                },
            },
        },
        "required": ["items"],
    }


def _verify_footprints_schema() -> dict[str, Any]:
    """Return the schema used by Gemini to validate footprints."""

    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "footprint": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["reference", "footprint", "reason"],
                },
            }
        },
        "required": ["items"],
    }


def _default_footprint(component: ComponentRequirement) -> str:
    """Map a component to a likely KiCad footprint string."""

    package = component.package.upper()
    if component.type == "resistor":
        return "Resistor_SMD:R_0603_1608Metric" if "0603" in package else "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
    if component.type == "capacitor":
        return "Capacitor_SMD:C_0603_1608Metric" if "0603" in package else "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
    if component.type == "led":
        return "LED_SMD:LED_0603_1608Metric"
    if component.type == "connector":
        return "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    if component.type == "transistor":
        return "Package_TO_SOT_SMD:SOT-23"
    if "DIP" in package:
        return "Package_DIP:DIP-8_W7.62mm"
    return "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"


def _fallback_bom(requirements: CircuitRequirements) -> BillOfMaterials:
    """Build a deterministic BOM when LLMs are unavailable."""

    counters: defaultdict[str, int] = defaultdict(int)
    items: list[BOMItem] = []
    for component in requirements.components:
        prefix = _PREFIX[component.type]
        counters[prefix] += 1
        ref = f"{prefix}{counters[prefix]}"
        items.append(
            BOMItem(
                reference=ref,
                value=component.value,
                footprint=_default_footprint(component),
                datasheet_url="https://www.ti.com/lit/ds/symlink/ne555.pdf" if "555" in component.value.upper() else "",
                manufacturer="Texas Instruments" if "555" in component.value.upper() else "Generic",
                part_number=component.value.replace(" ", "_"),
                lcsc_part="C8012" if "555" in component.value.upper() else "C23138",
                quantity=component.quantity,
                unit_price_usd=0.18 if component.type == "ic" else 0.02,
            )
        )
    total = sum(item.unit_price_usd * item.quantity for item in items)
    return BillOfMaterials(items=items, total_cost_usd=round(total, 2), total_components=sum(item.quantity for item in items))


def _is_valid_footprint(text: str) -> bool:
    """Check if a string looks like a KiCad footprint reference."""

    return bool(re.match(r"^[A-Za-z0-9_\-\.]+:[A-Za-z0-9_\-\.\(\)]+$", text))


def _render_bom(bom: BillOfMaterials, console: Console) -> None:
    """Render the BOM as a Rich table."""

    table = Table(title="Bill of Materials")
    table.add_column("Ref")
    table.add_column("Value")
    table.add_column("Footprint")
    table.add_column("Manufacturer")
    table.add_column("Part")
    table.add_column("LCSC")
    table.add_column("Qty", justify="right")
    table.add_column("USD", justify="right")
    for item in bom.items:
        table.add_row(
            item.reference,
            item.value,
            item.footprint,
            item.manufacturer,
            item.part_number,
            item.lcsc_part,
            str(item.quantity),
            f"{item.unit_price_usd:.2f}",
        )
    console.print(table)
    console.print(f"[bold green]Total cost:[/bold green] ${bom.total_cost_usd:.2f}")


def _write_csv(bom: BillOfMaterials, output_dir: Path) -> Path:
    """Write the BOM to disk."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "bom.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(BOMItem.model_fields.keys()))
        writer.writeheader()
        for item in bom.items:
            writer.writerow(item.model_dump())
    return path


def generate_bom(requirements: CircuitRequirements, console: Console | None = None, output_dir: str | Path | None = None) -> BillOfMaterials:
    """Generate a bill of materials from validated requirements."""

    console = console or Console(stderr=True)
    generator = get_generator_llm()
    verifier = get_verifier_llm()
    output_root = Path(output_dir) if output_dir else get_settings().ensure_output_dir()
    prompt = (
        "Generate a practical PCB bill of materials for this circuit. "
        "Prefer JLCPCB basic parts and valid KiCad footprints.\n\n"
        f"{requirements.model_dump_json(indent=2)}"
    )

    try:
        payload = generator.generate_json(prompt, _bom_schema())
        items = [BOMItem.model_validate(item) for item in payload.get("items", [])]
        bom = BillOfMaterials(
            items=items,
            total_cost_usd=round(sum(item.unit_price_usd * item.quantity for item in items), 2),
            total_components=sum(item.quantity for item in items),
        )
        verification = verifier.generate_json(
            "Review these KiCad footprint strings and normalize any invalid entries.\n\n"
            f"{bom.model_dump_json(indent=2)}",
            _verify_footprints_schema(),
        )
        replacements = {item["reference"]: item["footprint"] for item in verification.get("items", []) if _is_valid_footprint(item["footprint"])}
        for item in bom.items:
            if item.reference in replacements:
                item.footprint = replacements[item.reference]
    except (LLMProviderError, ValueError, KeyError):
        bom = _fallback_bom(requirements)

    _render_bom(bom, console)
    csv_path = _write_csv(bom, output_root)
    console.print(f"[green]BOM CSV saved to[/green] {csv_path}")
    return bom
