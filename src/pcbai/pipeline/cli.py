"""Nexus Typer CLI."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
import subprocess

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pcbai import __version__
from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_generator_llm, get_verifier_llm
from pcbai.llm.verifier import DualLLMVerifier
from pcbai.models import FabTarget, OptimizationMode
from pcbai.steps.bom_generator import generate_bom
from pcbai.steps.datasheet_fetcher import fetch_datasheets
from pcbai.steps.dfm_validator import validate_pcb
from pcbai.steps.gerber_exporter import export_gerbers
from pcbai.steps.pcb_router import route_pcb
from pcbai.steps.requirements_parser import parse_requirements
from pcbai.steps.schematic_synthesizer import synthesize_schematic


app = typer.Typer(help="Nexus command deck for AI-assisted PCB synthesis")


def _console() -> Console:
    """Return the shared CLI console."""

    return Console(stderr=True)


def _stdin_path_or_json(value: str) -> str:
    """Return an explicit path or piped stdin value."""

    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise typer.BadParameter("Provide --input or pipe a JSON/path value into this command.")


def _extract_path(value: str, key: str) -> str:
    """Extract a path from raw text or piped JSON."""

    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return value
    return str(payload.get(key) or payload.get("path") or "")


def _kicad_install_hint() -> str:
    """Return a short KiCad installation hint."""

    return (
        "If KiCad CLI is missing, run `powershell -ExecutionPolicy Bypass -File scripts\\setup-kicad-cli.ps1` "
        "or install KiCad 8/9 and restart the shell."
    )


@app.command("generate")
def generate_command(
    description: str = typer.Argument(..., help="Natural-language circuit description."),
    output: str = typer.Option("", "--output", help="Output directory."),
    provider: str = typer.Option("", "--provider", help="Override generator provider."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip dual-LLM verification."),
    optimize: OptimizationMode = typer.Option("default", "--optimize", help="Placement mode."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output."),
) -> None:
    """Run the end-to-end circuit generation pipeline."""

    console = _console()
    settings = get_settings()
    if provider:
        settings.generator_llm = provider

    requirements = parse_requirements(description, console=console)
    bom = generate_bom(requirements, console=console, output_dir=output or None)
    datasheets = fetch_datasheets(bom, console=console, output_dir=output or None)
    schematic_path = synthesize_schematic(bom, datasheets, console=console, output_dir=output or None)
    pcb_path = route_pcb(schematic_path, optimization_mode=optimize, console=console, output_dir=output or None)

    verification_data = None
    if not no_verify:
        verification_data = DualLLMVerifier(console=console).verify_existing(
            json.loads(Path(schematic_path).with_suffix(".netlist.json").read_text(encoding="utf-8"))
        )
        console.print(
            Panel.fit(
                f"Confidence: {verification_data.confidence_score}%\n"
                f"Rounds: {verification_data.rounds_taken}\n"
                f"Issues fixed: {len(verification_data.issues_fixed)}",
                title="Nexus Verification",
                border_style="green" if verification_data.passed else "yellow",
            )
        )

    summary = {
        "requirements": requirements.model_dump(),
        "bom": [item.model_dump() for item in bom.items],
        "files": [schematic_path, pcb_path],
        "total_cost": bom.total_cost_usd,
        "verification": verification_data.model_dump() if verification_data else {},
    }
    typer.echo(json.dumps(summary, indent=2))


@app.command("verify")
def verify_command(
    input_file: str = typer.Option("", "--input", help="Existing netlist JSON file."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output."),
) -> None:
    """Verify an existing netlist JSON file."""

    console = _console()
    raw = _stdin_path_or_json(input_file)
    path = _extract_path(raw, "path")
    netlist = json.loads(Path(path).read_text(encoding="utf-8"))
    result = DualLLMVerifier(console=console).verify_existing(netlist)
    typer.echo(result.model_dump_json(indent=2))


@app.command("place")
def place_command(
    input_file: str = typer.Option("", "--input", help="Schematic file path."),
    optimize: OptimizationMode = typer.Option("default", "--optimize", help="Placement mode."),
    output: str = typer.Option("", "--output", help="Output directory."),
) -> None:
    """Place a PCB from an existing schematic."""

    raw = _stdin_path_or_json(input_file)
    path = _extract_path(raw, "schematic_path")
    pcb_path = route_pcb(path, optimization_mode=optimize, console=_console(), output_dir=output or None)
    typer.echo(json.dumps({"pcb_path": pcb_path}, indent=2))


@app.command("validate")
def validate_command(
    input_file: str = typer.Option("", "--input", help="PCB file path."),
    fab: FabTarget = typer.Option("generic", "--fab", help="Fabrication target."),
) -> None:
    """Run DFM validation and exit non-zero if errors are found."""

    raw = _stdin_path_or_json(input_file)
    path = _extract_path(raw, "pcb_path")
    report = validate_pcb(path, fab_target=fab, console=_console())
    typer.echo(report.model_dump_json(indent=2))
    raise typer.Exit(code=0 if report.passed else 1)


@app.command("export")
def export_command(
    input_file: str = typer.Option("", "--input", help="PCB file path."),
    output: str = typer.Option("", "--output", help="Export directory."),
    gerber: bool = typer.Option(True, "--gerber/--no-gerber", help="Export Gerber files."),
    zip_output: bool = typer.Option(True, "--zip/--no-zip", help="Zip fabrication outputs."),
) -> None:
    """Export fabrication files."""

    raw = _stdin_path_or_json(input_file)
    path = _extract_path(raw, "pcb_path")
    files = export_gerbers(path, output or str(get_settings().ensure_output_dir() / "gerbers"), console=_console(), zip_output=zip_output) if gerber else []
    typer.echo(json.dumps({"files": files}, indent=2))


@app.command("info")
def info_command() -> None:
    """Display environment and provider status."""

    console = _console()
    settings = get_settings()
    env_table = Table(title="Nexus Environment")
    env_table.add_column("Item")
    env_table.add_column("Value")
    env_table.add_row("Version", __version__)
    env_table.add_row("Generator LLM", f"{settings.generator_llm} ({settings.groq_model if settings.generator_llm == 'groq' else settings.ollama_model})")
    env_table.add_row("Verifier LLM", f"{settings.verifier_llm} ({settings.gemini_model})")
    env_table.add_row("Output Dir", str(settings.kicad_output_dir))
    env_table.add_row("KiCad CLI", settings.resolve_kicad_cli_path())
    console.print(env_table)

    checks = Table(title="Dependency Status")
    checks.add_column("Dependency")
    checks.add_column("Status")
    try:
        get_generator_llm().test_connection()
        generator_status = "[green]connected[/green]"
    except Exception as exc:
        generator_status = f"[red]{exc}[/red]"
    try:
        get_verifier_llm().test_connection()
        verifier_status = "[green]connected[/green]"
    except Exception as exc:
        verifier_status = f"[red]{exc}[/red]"
    try:
        from pcbai.llm.providers.ollama_provider import OllamaLLMProvider

        OllamaLLMProvider().test_connection()
        ollama_status = "[green]running[/green]"
    except Exception:
        ollama_status = "[yellow]not running[/yellow]"
    checks.add_row("Groq", generator_status if settings.generator_llm == "groq" else "[dim]not selected[/dim]")
    checks.add_row("Gemini", verifier_status if settings.verifier_llm == "gemini" else "[dim]not selected[/dim]")
    resolved_kicad = settings.resolve_kicad_cli_path()
    checks.add_row("kicad-cli", "[green]found[/green]" if (shutil.which(resolved_kicad) or Path(resolved_kicad).exists()) else "[red]missing[/red]")
    checks.add_row("Ollama", ollama_status)
    checks.add_row("PyMuPDF", "[green]installed[/green]" if importlib.util.find_spec("fitz") else "[red]missing[/red]")
    checks.add_row("SKiDL", "[green]installed[/green]" if importlib.util.find_spec("skidl") else "[red]missing[/red]")
    console.print(checks)
    if not (shutil.which(resolved_kicad) or Path(resolved_kicad).exists()):
        console.print(f"[yellow]{_kicad_install_hint()}[/yellow]")
    typer.echo(json.dumps({"project": "Nexus", "version": __version__}, indent=2))


@app.command("setup-kicad")
def setup_kicad_command() -> None:
    """Attempt to help users install or detect KiCad CLI on Windows."""

    console = _console()
    settings = get_settings()
    resolved = settings.resolve_kicad_cli_path()
    if shutil.which(resolved) or Path(resolved).exists():
        console.print(f"[green]KiCad CLI already available at[/green] {resolved}")
        typer.echo(json.dumps({"kicad_cli": resolved, "status": "found"}, indent=2))
        return

    script_path = Path("scripts") / "setup-kicad-cli.ps1"
    if not script_path.exists():
        raise typer.Exit(code=1)

    console.print("[yellow]KiCad CLI not found. Launching the setup helper...[/yellow]")
    subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        check=False,
    )
    refreshed = settings.resolve_kicad_cli_path()
    typer.echo(
        json.dumps(
            {
                "kicad_cli": refreshed,
                "status": "found" if (shutil.which(refreshed) or Path(refreshed).exists()) else "missing",
            },
            indent=2,
        )
    )


def main() -> None:
    """Launch the CLI application."""

    app()


if __name__ == "__main__":
    main()
