"""Bill-of-materials generation."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError, get_llm_provider
from pcbai.models import BOMItem, BillOfMaterials, CircuitRequirements, ComponentRequirement


PREFIX_MAP = {
    "resistor": "R",
    "capacitor": "C",
    "ic": "U",
    "led": "D",
    "transistor": "Q",
    "connector": "J",
}

FOOTPRINT_MAP = {
    "0603": {
        "resistor": "Resistor_SMD:R_0603_1608Metric",
        "capacitor": "Capacitor_SMD:C_0603_1608Metric",
        "led": "LED_SMD:LED_0603_1608Metric",
    },
    "DIP-8": {"ic": "Package_DIP:DIP-8_W7.62mm"},
    "SOIC-8": {"ic": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"},
    "SOP-8": {"ic": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"},
    "SOT-23": {"transistor": "Package_TO_SOT_SMD:SOT-23"},
    "TH_2.54mm": {"connector": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"},
    "TBD": {"ic": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"},
}


def _schema() -> dict[str, Any]:
    """Return the expected JSON schema for BOM generation."""

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
                },
            }
        },
        "required": ["items"],
    }


def _default_footprint(component: ComponentRequirement) -> str:
    """Map a component requirement to a KiCad footprint."""

    package_map = FOOTPRINT_MAP.get(component.package, {})
    if component.type in package_map:
        return package_map[component.type]
    if component.type == "connector":
        return "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    return "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"


def _default_part(component: ComponentRequirement, reference: str) -> BOMItem:
    """Generate a conservative BOM item without LLM assistance."""

    lcsc = {
        "resistor": "C23138",
        "capacitor": "C14663",
        "led": "C2286",
        "ic": "C8012" if "555" in component.value.upper() else "",
        "connector": "C49257",
        "transistor": "C20917",
    }.get(component.type, "")
    manufacturer = "Texas Instruments" if "555" in component.value.upper() else "Generic"
    part_number = component.value if component.type == "ic" else f"{component.value}-{component.package}".replace(" ", "_")
    datasheet_url = "https://www.ti.com/lit/ds/symlink/ne555.pdf" if "555" in component.value.upper() else ""
    return BOMItem(
        reference=reference,
        value=component.value,
        footprint=_default_footprint(component),
        datasheet_url=datasheet_url,
        manufacturer=manufacturer,
        part_number=part_number or "GENERIC-PART",
        lcsc_part=lcsc,
        quantity=component.quantity,
        unit_price_usd=0.02 if component.type in {"resistor", "capacitor"} else 0.18,
    )


def _fallback_bom(requirements: CircuitRequirements) -> BillOfMaterials:
    """Create a BOM using deterministic defaults."""

    counters: defaultdict[str, int] = defaultdict(int)
    items: list[BOMItem] = []
    for component in requirements.components:
        prefix = PREFIX_MAP[component.type]
        counters[prefix] += 1
        reference = f"{prefix}{counters[prefix]}"
        items.append(_default_part(component, reference))
    return BillOfMaterials(items=items)


def _render_bom_table(bom: BillOfMaterials, console: Console) -> None:
    """Display the BOM as a Rich table."""

    table = Table(title="Bill of Materials")
    table.add_column("Ref")
    table.add_column("Value")
    table.add_column("Footprint")
    table.add_column("Mfr")
    table.add_column("Part Number")
    table.add_column("LCSC")
    table.add_column("Qty", justify="right")
    table.add_column("Unit USD", justify="right")

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


def _write_bom_csv(bom: BillOfMaterials, output_dir: Path) -> Path:
    """Persist the BOM to CSV."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "bom.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
        )
        writer.writeheader()
        for item in bom.items:
            writer.writerow(item.model_dump())
    return path


def generate_bom(
    requirements: CircuitRequirements,
    provider: BaseLLMProvider | None = None,
    output_dir: str | Path | None = None,
    console: Console | None = None,
) -> BillOfMaterials:
    """Generate a validated BOM from parsed circuit requirements."""

    console = console or Console()
    provider = provider or get_llm_provider()
    output_path = Path(output_dir) if output_dir else get_settings().ensure_output_dir()

    prompt = (
        "Map the following circuit requirements to real purchasable BOM parts. "
        "Prefer common JLCPCB basic parts when practical and keep footprints KiCad-compatible.\n\n"
        f"{requirements.model_dump_json(indent=2)}"
    )

    try:
        payload = provider.generate_json(prompt, _schema())
        bom = BillOfMaterials.model_validate(payload)
    except (LLMProviderError, ValueError):
        bom = _fallback_bom(requirements)

    _render_bom_table(bom, console)
    csv_path = _write_bom_csv(bom, output_path)
    console.print(f"[green]BOM CSV saved to[/green] {csv_path}")
    return bom
