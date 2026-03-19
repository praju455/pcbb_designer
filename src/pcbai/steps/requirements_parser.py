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
            ComponentRequirement(name="Timing resistor A", type="resistor", value="10k", quantity=1, package="0603", notes="Charge path from VCC to discharge pin"),
            ComponentRequirement(name="Timing resistor B", type="resistor", value="100k", quantity=1, package="0603", notes="Charge and discharge timing resistor"),
            ComponentRequirement(name="Timing capacitor", type="capacitor", value="10uF", quantity=1, package="0805", notes="Astable timing capacitor"),
            ComponentRequirement(name="Decoupling capacitor", type="capacitor", value="100nF", quantity=1, package="0603", notes="Supply decoupling at the IC"),
            ComponentRequirement(name="Control pin capacitor", type="capacitor", value="10nF", quantity=1, package="0603", notes="Stabilizes the control voltage pin"),
            ComponentRequirement(name="Indicator LED", type="led", value="Red LED", quantity=1, package="0603", notes="Output indicator"),
            ComponentRequirement(name="Current limiting resistor", type="resistor", value="330R", quantity=1, package="0603", notes="LED current limit"),
        ]
    elif "op-amp" in lowered or "op amp" in lowered or "preamp" in lowered or "amplifier" in lowered:
        components = [
            ComponentRequirement(name="Amplifier IC", type="ic", value="LM358", quantity=1, package="SOIC-8", notes="Dual op-amp core"),
            ComponentRequirement(name="Feedback resistor", type="resistor", value="100k", quantity=1, package="0603", notes="Sets closed-loop gain"),
            ComponentRequirement(name="Input resistor", type="resistor", value="10k", quantity=1, package="0603", notes="Input network"),
            ComponentRequirement(name="Bias resistor", type="resistor", value="100k", quantity=1, package="0603", notes="Bias reference"),
            ComponentRequirement(name="Input capacitor", type="capacitor", value="1uF", quantity=1, package="0805", notes="AC coupling"),
            ComponentRequirement(name="Decoupling capacitor", type="capacitor", value="100nF", quantity=1, package="0603", notes="Supply decoupling"),
            ComponentRequirement(name="Input connector", type="connector", value="Audio In", quantity=1, package="THT", notes="Signal input"),
            ComponentRequirement(name="Output connector", type="connector", value="Audio Out", quantity=1, package="THT", notes="Signal output"),
        ]
    elif "sensor" in lowered or "i2c" in lowered or "breakout" in lowered:
        components = [
            ComponentRequirement(name="Sensor IC", type="ic", value="MCP9808", quantity=1, package="SOIC-8", notes="Example digital sensor"),
            ComponentRequirement(name="Header connector", type="connector", value="I2C Header", quantity=1, package="THT", notes="Power and bus breakout"),
            ComponentRequirement(name="Decoupling capacitor", type="capacitor", value="100nF", quantity=1, package="0603", notes="Local supply decoupling"),
            ComponentRequirement(name="Pull-up resistor SDA", type="resistor", value="4.7k", quantity=1, package="0603", notes="I2C bus pull-up"),
            ComponentRequirement(name="Pull-up resistor SCL", type="resistor", value="4.7k", quantity=1, package="0603", notes="I2C bus pull-up"),
            ComponentRequirement(name="Status LED", type="led", value="Amber LED", quantity=1, package="0603", notes="Power indicator"),
            ComponentRequirement(name="LED resistor", type="resistor", value="1k", quantity=1, package="0603", notes="Indicator current limit"),
        ]
    elif "transistor" in lowered or "relay" in lowered or "switch" in lowered or "driver" in lowered:
        components = [
            ComponentRequirement(name="Input connector", type="connector", value="Control Header", quantity=1, package="THT", notes="Power and control input"),
            ComponentRequirement(name="Switch transistor", type="transistor", value="MMBT3904", quantity=1, package="SOT-23", notes="Low-side switch"),
            ComponentRequirement(name="Base resistor", type="resistor", value="1k", quantity=1, package="0603", notes="Base or gate drive resistor"),
            ComponentRequirement(name="Pull-down resistor", type="resistor", value="100k", quantity=1, package="0603", notes="Keeps switch off at startup"),
            ComponentRequirement(name="Load LED", type="led", value="Green LED", quantity=1, package="0603", notes="Visible switched load"),
            ComponentRequirement(name="Load resistor", type="resistor", value="330R", quantity=1, package="0603", notes="Current limit for load"),
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
