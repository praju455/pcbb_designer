"""Gerber export helpers using kicad-cli."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings


def export_gerbers(
    pcb_file: str | Path,
    output_dir: str | Path,
    zip_output: bool = True,
    console: Console | None = None,
) -> list[str]:
    """Export Gerber and drill files using kicad-cli."""

    console = console or Console()
    settings = get_settings()
    pcb_path = Path(pcb_file)
    gerber_dir = Path(output_dir)
    gerber_dir.mkdir(parents=True, exist_ok=True)

    cli_path = shutil.which(settings.kicad_cli_path) or shutil.which("kicad-cli")
    if not cli_path:
        console.print("[red]kicad-cli not found in PATH.[/red]")
        console.print("[yellow]Install KiCad 7+ and ensure 'kicad-cli' is available in your shell PATH.[/yellow]")
        return []

    commands = [
        [cli_path, "pcb", "export", "gerbers", "--output", str(gerber_dir), str(pcb_path)],
        [cli_path, "pcb", "export", "drill", "--output", str(gerber_dir), str(pcb_path)],
    ]

    for command in commands:
        subprocess.run(command, check=True, capture_output=True, text=True)

    exported_files = sorted(str(path) for path in gerber_dir.iterdir() if path.is_file())
    if zip_output and exported_files:
        archive = shutil.make_archive(str(gerber_dir / "gerbers"), "zip", root_dir=gerber_dir)
        exported_files.append(archive)

    table = Table(title="Exported Manufacturing Files")
    table.add_column("Path")
    for path in exported_files:
        table.add_row(path)
    console.print(table)
    return exported_files
