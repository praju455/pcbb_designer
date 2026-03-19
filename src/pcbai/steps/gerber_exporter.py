"""Gerber export helpers using kicad-cli."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings


def export_gerbers(pcb_file: str | Path, output_dir: str | Path, console: Console | None = None, zip_output: bool = True) -> list[str]:
    """Export Gerber and drill files and optionally zip them."""

    console = console or Console(stderr=True)
    settings = get_settings()
    pcb_path = Path(pcb_file)
    export_dir = Path(output_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    cli_path = shutil.which(settings.resolve_kicad_cli_path()) or shutil.which("kicad-cli") or settings.resolve_kicad_cli_path()
    if not cli_path:
        console.print("[red]kicad-cli not found in PATH.[/red]")
        console.print("[yellow]Install KiCad 7+ and ensure kicad-cli is available.[/yellow]")
        return []
    if not Path(cli_path).exists() and shutil.which(cli_path) is None:
        console.print("[red]kicad-cli not found in PATH.[/red]")
        console.print("[yellow]Install KiCad 7+ and ensure kicad-cli is available.[/yellow]")
        return []

    subprocess.run([cli_path, "pcb", "export", "gerbers", "--output", str(export_dir), str(pcb_path)], check=True, capture_output=True, text=True)
    subprocess.run([cli_path, "pcb", "export", "drill", "--output", str(export_dir), str(pcb_path)], check=True, capture_output=True, text=True)

    files = sorted(str(path) for path in export_dir.iterdir() if path.is_file())
    if zip_output and files:
        files.append(shutil.make_archive(str(export_dir / "fab-package"), "zip", root_dir=export_dir))

    table = Table(title="Fabrication Files")
    table.add_column("File")
    for path in files:
        table.add_row(path)
    console.print(table)
    console.print("[bold]JLCPCB upload checklist:[/bold] Verify board outline, drill map, BOM/CPL, and copper layer polarity.")
    return files
