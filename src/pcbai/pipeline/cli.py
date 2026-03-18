"""Typer CLI entrypoint for the PCB AI agent."""

from __future__ import annotations

import json
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.core.logger import get_logger
from pcbai.llm.provider import LLMProviderError, get_llm_provider
from pcbai.models import OptimizationMode
from pcbai.steps.bom_generator import generate_bom
from pcbai.steps.datasheet_fetcher import fetch_datasheets
from pcbai.steps.dfm_validator import validate_pcb
from pcbai.steps.gerber_exporter import export_gerbers
from pcbai.steps.pcb_router import route_pcb
from pcbai.steps.requirements_parser import parse_requirements
from pcbai.steps.schematic_synthesizer import synthesize_schematic


app = typer.Typer(help="Plain English -> Manufacturable PCB, from your terminal")


def _console() -> Console:
    """Create the shared console instance."""

    return Console(stderr=True)


def _set_verbose(verbose: bool) -> None:
    """Adjust the shared logger level."""

    level = 10 if verbose else 20
    get_logger(level=level)


def _stdin_payload() -> str:
    """Read piped stdin if present."""

    return sys.stdin.read().strip() if not sys.stdin.isatty() else ""


def _path_from_input(value: str | None) -> Path:
    """Resolve an input path from CLI argument or piped JSON."""

    if value:
        return Path(value)

    piped = _stdin_payload()
    if not piped:
        raise typer.BadParameter("No input provided. Pass --input or pipe JSON/path into the command.")

    try:
        payload = json.loads(piped)
    except json.JSONDecodeError:
        return Path(piped)

    for key in ["pcb_path", "schematic_path", "path"]:
        if key in payload and payload[key]:
            return Path(str(payload[key]))
    raise typer.BadParameter("Unable to find a usable path in piped input.")


def _summary_table(summary: dict[str, Any], title: str) -> Table:
    """Build a compact summary table."""

    table = Table(title=title)
    table.add_column("Key")
    table.add_column("Value")
    for key, value in summary.items():
        table.add_row(str(key), str(value))
    return table


@app.command("generate")
def generate_command(
    description: str = typer.Argument(..., help="Natural-language circuit description."),
    output: str = typer.Option("", "--output", help="Output directory."),
    provider: str = typer.Option("", "--provider", help="Override LLM provider."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Run parse, BOM generation, datasheet fetch, and schematic synthesis."""

    _set_verbose(verbose)
    console = _console()
    settings = get_settings()
    if provider:
        settings.llm_provider = provider  # type: ignore[misc]
    output_dir = Path(output) if output else settings.ensure_output_dir()
    llm = get_llm_provider()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Generating PCB artifacts", total=4)
        requirements = parse_requirements(description, provider=llm, console=console)
        progress.advance(task)
        bom = generate_bom(requirements, provider=llm, output_dir=output_dir, console=console)
        progress.advance(task)
        datasheets = fetch_datasheets(bom, provider=llm, output_dir=output_dir, console=console)
        progress.advance(task)
        schematic_path = synthesize_schematic(bom, datasheets, provider=llm, output_dir=output_dir, console=console)
        progress.advance(task)

    summary = {
        "provider": llm.get_provider_name(),
        "components": len(requirements.components),
        "bom_items": len(bom.items),
        "datasheets_cached": sum(1 for item in datasheets.values() if item.local_path),
        "schematic_path": schematic_path,
    }
    console.print(_summary_table(summary, "Generation Summary"))
    typer.echo(json.dumps({"schematic_path": schematic_path, "output_dir": str(output_dir)}, indent=2))


@app.command("place")
def place_command(
    input_file: str = typer.Option("", "--input", help="KiCad schematic path."),
    optimize: OptimizationMode = typer.Option("default", "--optimize", help="Placement mode."),
    output: str = typer.Option("", "--output", help="Output directory."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Place and minimally route a PCB from an existing schematic."""

    _set_verbose(verbose)
    console = _console()
    schematic_path = _path_from_input(input_file)
    pcb_path = route_pcb(schematic_path, optimization_mode=optimize, output_dir=output or None, console=console)
    typer.echo(json.dumps({"pcb_path": pcb_path}, indent=2))


@app.command("validate")
def validate_command(
    input_file: str = typer.Option("", "--input", help="KiCad PCB path."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Run DFM validation and exit non-zero on manufacturing errors."""

    _set_verbose(verbose)
    console = _console()
    pcb_path = _path_from_input(input_file)
    report = validate_pcb(pcb_path, console=console)
    typer.echo(report.model_dump_json(indent=2))
    raise typer.Exit(code=0 if report.passed else 1)


@app.command("export")
def export_command(
    input_file: str = typer.Option("", "--input", help="KiCad PCB path."),
    output: str = typer.Option("", "--output", help="Gerber output directory."),
    gerber: bool = typer.Option(True, "--gerber/--no-gerber", help="Export Gerbers."),
    zip_output: bool = typer.Option(True, "--zip/--no-zip", help="Zip the fab package."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Export Gerber and drill artifacts."""

    _set_verbose(verbose)
    console = _console()
    pcb_path = _path_from_input(input_file)
    if not gerber:
        typer.echo(json.dumps({"exported_files": []}, indent=2))
        raise typer.Exit(code=0)
    output_dir = Path(output) if output else get_settings().ensure_output_dir() / "gerbers"
    files = export_gerbers(pcb_path, output_dir, zip_output=zip_output, console=console)
    raise typer.Exit(code=0 if files else 1)


@app.command("info")
def info_command(
    provider: str = typer.Option("", "--provider", help="Override LLM provider."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Show active config and dependency availability."""

    _set_verbose(verbose)
    console = _console()
    settings = get_settings()
    if provider:
        settings.llm_provider = provider  # type: ignore[misc]

    llm_provider = None
    llm_models: list[str] = []
    llm_error = ""
    try:
        llm_provider = get_llm_provider()
        llm_models = llm_provider.list_available_models()
    except (LLMProviderError, RuntimeError) as exc:
        llm_error = str(exc)

    table = Table(title="PCB AI Environment")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("LLM Provider", settings.llm_provider)
    table.add_row("Configured Model", settings.groq_model if settings.llm_provider == "groq" else settings.gemini_model if settings.llm_provider == "gemini" else settings.ollama_model)
    table.add_row("Output Dir", str(settings.kicad_output_dir))
    table.add_row("KiCad CLI", settings.kicad_cli_path)
    table.add_row("Available Models", ", ".join(llm_models) if llm_models else llm_error or "Unavailable")
    console.print(table)

    checks = Table(title="Dependency Checks")
    checks.add_column("Dependency")
    checks.add_column("Status")
    checks.add_row("kicad-cli", "[green]✅[/green]" if shutil.which(settings.kicad_cli_path) else "[red]❌[/red]")
    checks.add_row("Ollama", "[green]✅[/green]" if shutil.which("ollama") else "[red]❌[/red]")
    checks.add_row("Groq SDK", "[green]✅[/green]" if importlib.util.find_spec("groq") else "[red]❌[/red]")
    checks.add_row("PyMuPDF", "[green]✅[/green]" if importlib.util.find_spec("fitz") else "[red]❌[/red]")
    checks.add_row("SKiDL", "[green]✅[/green]" if importlib.util.find_spec("skidl") else "[red]❌[/red]")
    console.print(checks)


def main() -> None:
    """Launch the Typer application."""

    app()


if __name__ == "__main__":
    main()
