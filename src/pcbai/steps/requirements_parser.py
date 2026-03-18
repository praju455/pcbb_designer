"""Natural-language circuit requirements parsing."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from pcbai.llm.provider import BaseLLMProvider, LLMProviderError, get_llm_provider
from pcbai.models import CircuitRequirements, ComponentRequirement, ComponentType


def _component_type_for_text(name: str, value: str) -> ComponentType:
    """Infer a component type from loose text."""

    text = f"{name} {value}".lower()
    if "res" in text or "ohm" in text or text.endswith("k"):
        return "resistor"
    if "cap" in text or "uf" in text or "nf" in text or "pf" in text:
        return "capacitor"
    if "led" in text:
        return "led"
    if "transistor" in text or "mosfet" in text or "bjt" in text:
        return "transistor"
    if "conn" in text or "header" in text or "usb" in text or "jack" in text:
        return "connector"
    return "ic"


def _default_components_from_text(natural_text: str) -> list[ComponentRequirement]:
    """Create a conservative component list when the LLM is unavailable."""

    lowered = natural_text.lower()
    defaults: list[ComponentRequirement] = []
    if "555" in lowered or "timer" in lowered:
        defaults.extend(
            [
                ComponentRequirement(name="Timer IC", type="ic", value="NE555", quantity=1, package="DIP-8", notes="Core timing IC"),
                ComponentRequirement(name="Current limiting resistor", type="resistor", value="330R", quantity=1, package="0603", notes="LED current limiting"),
                ComponentRequirement(name="Timing resistor", type="resistor", value="10k", quantity=1, package="0603", notes="Timing network"),
                ComponentRequirement(name="Timing capacitor", type="capacitor", value="100nF", quantity=1, package="0603", notes="Timing network"),
                ComponentRequirement(name="Indicator LED", type="led", value="Red LED", quantity=1, package="0603", notes="Status output"),
                ComponentRequirement(name="Power connector", type="connector", value="2-pin header", quantity=1, package="TH_2.54mm", notes="Power input"),
            ]
        )
    elif "led" in lowered:
        defaults.extend(
            [
                ComponentRequirement(name="Indicator LED", type="led", value="Red LED", quantity=1, package="0603", notes="Main indicator"),
                ComponentRequirement(name="Current limiting resistor", type="resistor", value="330R", quantity=1, package="0603", notes="Series resistor"),
                ComponentRequirement(name="Power connector", type="connector", value="2-pin header", quantity=1, package="TH_2.54mm", notes="Power input"),
            ]
        )
    if not defaults:
        defaults.append(
            ComponentRequirement(
                name=natural_text.strip().title() or "General IC",
                type="ic",
                value=natural_text.strip() or "Custom Circuit",
                quantity=1,
                package="TBD",
                notes="Generated from natural language fallback",
            )
        )
    return defaults


def _schema() -> dict[str, Any]:
    """Return the JSON schema expected from the LLM."""

    return {
        "type": "object",
        "properties": {
            "circuit_name": {"type": "string"},
            "description": {"type": "string"},
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["resistor", "capacitor", "ic", "led", "transistor", "connector"],
                        },
                        "value": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1},
                        "package": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                },
            },
            "power_supply": {"type": "string"},
            "special_requirements": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["circuit_name", "description", "components", "power_supply", "special_requirements"],
    }


def _normalize_payload(payload: dict[str, Any], natural_text: str) -> CircuitRequirements:
    """Fill missing fields with safe defaults and validate the final structure."""

    payload = dict(payload)
    raw_components = payload.get("components") or []
    components: list[ComponentRequirement] = []

    for item in raw_components:
        item_dict = dict(item)
        name = item_dict.get("name") or "Generic Component"
        value = item_dict.get("value") or name
        item_dict.setdefault("type", _component_type_for_text(name, value))
        item_dict.setdefault("quantity", 1)
        item_dict.setdefault("package", "TBD")
        item_dict.setdefault("notes", "")
        components.append(ComponentRequirement.model_validate(item_dict))

    if not components:
        components = _default_components_from_text(natural_text)

    normalized = {
        "circuit_name": payload.get("circuit_name") or natural_text.strip().title() or "AI Generated Circuit",
        "description": payload.get("description") or natural_text.strip(),
        "components": [component.model_dump() for component in components],
        "power_supply": payload.get("power_supply") or "5V DC",
        "special_requirements": payload.get("special_requirements") or [],
    }
    return CircuitRequirements.model_validate(normalized)


def _render_requirements_table(requirements: CircuitRequirements, console: Console) -> None:
    """Print a rich summary of the parsed circuit requirements."""

    table = Table(title=f"Parsed Requirements: {requirements.circuit_name}")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Value")
    table.add_column("Qty", justify="right")
    table.add_column("Package")
    table.add_column("Notes")

    for component in requirements.components:
        table.add_row(
            component.name,
            component.type,
            component.value,
            str(component.quantity),
            component.package,
            component.notes,
        )

    console.print(table)
    console.print(f"[bold]Power:[/bold] {requirements.power_supply}")
    if requirements.special_requirements:
        console.print(f"[bold]Special requirements:[/bold] {', '.join(requirements.special_requirements)}")


def parse_requirements(
    natural_text: str,
    provider: BaseLLMProvider | None = None,
    console: Console | None = None,
) -> CircuitRequirements:
    """Parse natural language into validated circuit requirements."""

    console = console or Console()
    provider = provider or get_llm_provider()
    prompt = (
        "Extract structured PCB design requirements from the following request. "
        "Be practical and infer standard support components when they are obvious.\n\n"
        f"Request: {natural_text}"
    )

    try:
        payload = provider.generate_json(prompt, _schema())
    except (LLMProviderError, ValidationError, RuntimeError):
        payload = {
            "circuit_name": natural_text.strip().title() or "AI Generated Circuit",
            "description": natural_text.strip(),
            "components": [component.model_dump() for component in _default_components_from_text(natural_text)],
            "power_supply": "5V DC",
            "special_requirements": [],
        }

    requirements = _normalize_payload(payload, natural_text)
    _render_requirements_table(requirements, console)
    return requirements
