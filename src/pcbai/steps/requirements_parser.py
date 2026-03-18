"""Requirements parsing using the dual-LLM verification pipeline."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from pcbai.llm.verifier import DualLLMVerifier
from pcbai.models import CircuitRequirements, ComponentRequirement


def _schema() -> dict[str, Any]:
    """Return the expected JSON schema for requirement extraction."""

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
                    "required": ["name", "type", "value", "quantity", "package", "notes"],
                },
            },
            "power_supply": {"type": "string"},
            "frequency": {"type": "string"},
            "special_requirements": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "circuit_name",
            "description",
            "components",
            "power_supply",
            "frequency",
            "special_requirements",
        ],
    }


def _fallback_requirements(natural_text: str) -> CircuitRequirements:
    """Return practical defaults when LLM generation is unavailable."""

    lowered = natural_text.lower()
    components: list[ComponentRequirement] = []
    if "555" in lowered:
        components = [
            ComponentRequirement(name="Timer IC", type="ic", value="NE555", quantity=1, package="DIP-8", notes="Core timer"),
            ComponentRequirement(name="Timing resistor", type="resistor", value="10k", quantity=1, package="0603", notes="Timing network"),
            ComponentRequirement(name="Timing capacitor", type="capacitor", value="100nF", quantity=1, package="0603", notes="Timing network"),
            ComponentRequirement(name="Indicator LED", type="led", value="Red LED", quantity=1, package="0603", notes="Output indicator"),
            ComponentRequirement(name="Current limiting resistor", type="resistor", value="330R", quantity=1, package="0603", notes="LED current limit"),
        ]
    if not components:
        components = [
            ComponentRequirement(
                name=natural_text.title() or "Custom Circuit",
                type="ic",
                value=natural_text or "Custom circuit",
                quantity=1,
                package="TBD",
                notes="Fallback interpretation",
            )
        ]
    return CircuitRequirements(
        circuit_name=natural_text.title() or "AI Generated Circuit",
        description=natural_text,
        components=components,
        power_supply="5V DC",
        frequency="",
        special_requirements=[],
    )


def _render(requirements: CircuitRequirements, console: Console) -> None:
    """Print the parsed requirements as a Rich table."""

    table = Table(title=f"Requirements: {requirements.circuit_name}")
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
    if requirements.frequency:
        console.print(f"[bold]Frequency:[/bold] {requirements.frequency}")


def parse_requirements(natural_text: str, console: Console | None = None) -> CircuitRequirements:
    """Parse a natural-language circuit description into validated requirements."""

    console = console or Console(stderr=True)
    verifier = DualLLMVerifier(console=console)
    prompt = (
        "Convert the following circuit idea into structured PCB requirements. "
        "Infer the obvious support components and mention any special requirements.\n\n"
        f"{natural_text}"
    )
    try:
        result = verifier.generate_and_verify(prompt, _schema())
        requirements = CircuitRequirements.model_validate(result.netlist)
    except Exception:
        requirements = _fallback_requirements(natural_text)

    _render(requirements, console)
    return requirements
