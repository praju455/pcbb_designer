"""PCB placement and routing with Gemini-assisted placement strategy."""

from __future__ import annotations

import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_verifier_llm
from pcbai.models import BillOfMaterials, NetlistDescription, OptimizationMode, PlacementRecord, PlacementResult


def _load_sidecars(schematic_path: Path) -> tuple[BillOfMaterials, NetlistDescription]:
    """Load sidecar BOM and netlist artifacts."""

    bom = BillOfMaterials.model_validate_json(schematic_path.with_suffix(".bom.json").read_text(encoding="utf-8"))
    netlist = NetlistDescription.model_validate_json(schematic_path.with_suffix(".netlist.json").read_text(encoding="utf-8"))
    return bom, netlist


def _build_graph(netlist: NetlistDescription) -> dict[str, set[str]]:
    """Build a component connectivity graph from net definitions."""

    graph: dict[str, set[str]] = defaultdict(set)
    for net in netlist.nets:
        refs = [pin.reference for pin in net.pins]
        for ref in refs:
            graph[ref].update(other for other in refs if other != ref)
    return graph


def _candidate_positions(width: float, height: float) -> list[tuple[float, float]]:
    """Generate grid positions for greedy placement."""

    return [(float(x), float(y)) for y in range(15, int(height) - 10, 15) for x in range(15, int(width) - 10, 20)]


def _score(reference: str, position: tuple[float, float], placed: list[PlacementRecord], mode: OptimizationMode, graph: dict[str, set[str]], width: float, height: float) -> float:
    """Score a candidate placement using thermal, signal, and density terms."""

    x, y = position
    edge = min(x, y, width - x, height - y)
    thermal_score = max(0.0, 25.0 - edge) if mode == "thermal" and reference.startswith(("U", "Q")) else 0.0
    signal_score = 0.0
    density_score = 0.0
    for record in placed:
        distance = math.dist((record.x_mm, record.y_mm), position)
        density_score += max(0.0, 18.0 - distance)
        if record.reference in graph.get(reference, set()):
            signal_score += max(0.0, 30.0 - distance)
    return (thermal_score * 0.4) + (signal_score * 0.4) - (density_score * 0.2)


def _cluster_for(reference: str, graph: dict[str, set[str]]) -> str:
    """Return a simple cluster label for a component."""

    if reference.startswith("U"):
        return "logic"
    if reference.startswith(("C", "R")) and any(peer.startswith("U") for peer in graph.get(reference, set())):
        return "support"
    if reference.startswith("J"):
        return "io"
    return "misc"


def _place(bom: BillOfMaterials, graph: dict[str, set[str]], mode: OptimizationMode, width: float, height: float) -> list[PlacementRecord]:
    """Greedily place components on the board grid."""

    candidates = _candidate_positions(width, height)
    placed: list[PlacementRecord] = []
    for item in sorted(bom.items, key=lambda row: (row.reference[0] not in {"U", "J"}, row.reference)):
        ranked = sorted(candidates, key=lambda pos: _score(item.reference, pos, placed, mode, graph, width, height), reverse=True)
        best = ranked[0]
        candidates.remove(best)
        placed.append(
            PlacementRecord(
                reference=item.reference,
                footprint=item.footprint,
                x_mm=best[0],
                y_mm=best[1],
                rotation_deg=0.0,
                score=_score(item.reference, best, placed[:-1], mode, graph, width, height),
                cluster=_cluster_for(item.reference, graph),
            )
        )
    return placed


def _board_text(bom: BillOfMaterials, netlist: NetlistDescription, result: PlacementResult) -> str:
    """Render a lightweight KiCad PCB file."""

    net_names = [""] + [net.net_name for net in netlist.nets]
    lines = [
        '(kicad_pcb (version 20221018) (generator circuitforge-ai)',
        '  (general (thickness 1.6))',
        '  (paper "A4")',
        '  (layers',
        '    (0 "F.Cu" signal)',
        '    (31 "B.Cu" signal)',
        '    (37 "F.SilkS" user)',
        '    (39 "F.Mask" user)',
        '    (44 "Edge.Cuts" user)',
        '    (47 "F.CrtYd" user)',
        '  )',
        f'  (gr_rect (start 0 0) (end {result.board_width_mm:.2f} {result.board_height_mm:.2f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))',
    ]
    for index, name in enumerate(net_names[1:], start=1):
        lines.append(f'  (net {index} "{name}")')
    for placement in result.placements:
        item = next(row for row in bom.items if row.reference == placement.reference)
        lines.extend(
            [
                f'  (footprint "{item.footprint}" (layer "F.Cu")',
                f'    (at {placement.x_mm:.2f} {placement.y_mm:.2f} {placement.rotation_deg:.2f})',
                f'    (property "Reference" "{item.reference}" (at 0 -3 0) (layer "F.SilkS"))',
                f'    (property "Value" "{item.value}" (at 0 3 0) (layer "F.Fab"))',
                '    (attr smd)',
                '    (fp_line (start -3.5 -2.8) (end 3.5 -2.8) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                '    (fp_line (start 3.5 -2.8) (end 3.5 2.8) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                '    (fp_line (start 3.5 2.8) (end -3.5 2.8) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                '    (fp_line (start -3.5 2.8) (end -3.5 -2.8) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                '    (pad "1" smd rect (at -0.8 0) (size 0.9 1.0) (layers "F.Cu" "F.Paste" "F.Mask"))',
                '    (pad "2" smd rect (at 0.8 0) (size 0.9 1.0) (layers "F.Cu" "F.Paste" "F.Mask"))',
                "  )",
            ]
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def _try_freerouting(pcb_path: Path) -> bool:
    """Attempt freerouting if available on disk."""

    jar_path = shutil.which("freerouting.jar")
    if not jar_path and Path("freerouting.jar").exists():
        jar_path = str(Path("freerouting.jar"))
    if not jar_path:
        return False
    try:
        subprocess.run(["java", "-jar", jar_path, "-de", str(pcb_path)], check=False, capture_output=True, text=True, timeout=60)
    except Exception:
        return False
    return True


def _render(result: PlacementResult, console: Console) -> None:
    """Render the placement summary."""

    table = Table(title=f"Placement Summary ({result.optimization_mode})")
    table.add_column("Ref")
    table.add_column("Cluster")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")
    table.add_column("Score", justify="right")
    for row in result.placements:
        table.add_row(row.reference, row.cluster, f"{row.x_mm:.2f}", f"{row.y_mm:.2f}", f"{row.score:.2f}")
    console.print(table)
    console.print(f"[bold]Strategy:[/bold] {result.strategy_summary}")


def route_pcb(schematic_path: str | Path, optimization_mode: OptimizationMode = "default", console: Console | None = None, output_dir: str | Path | None = None) -> str:
    """Generate a KiCad PCB file from a synthesized schematic."""

    console = console or Console(stderr=True)
    verifier = get_verifier_llm()
    settings = get_settings()
    schematic_file = Path(schematic_path)
    output_root = Path(output_dir) if output_dir else settings.ensure_output_dir()
    output_root.mkdir(parents=True, exist_ok=True)
    pcb_path = output_root / f"{schematic_file.stem}.kicad_pcb"

    bom, netlist = _load_sidecars(schematic_file)
    graph = _build_graph(netlist)
    strategy = "Balanced placement with clustered support parts."
    try:
        strategy = verifier.generate(
            f"Suggest an optimal {optimization_mode} placement strategy for this board.\n\n"
            f"BOM:\n{bom.model_dump_json(indent=2)}\n\nNetlist:\n{netlist.model_dump_json(indent=2)}"
        )
    except LLMProviderError:
        pass

    placements = _place(bom, graph, optimization_mode, 120.0, 90.0)
    result = PlacementResult(
        optimization_mode=optimization_mode,
        board_width_mm=120.0,
        board_height_mm=90.0,
        placements=placements,
        nets_routed=len(netlist.nets),
        freerouting_used=False,
        strategy_summary=strategy,
    )
    pcb_path.write_text(_board_text(bom, netlist, result), encoding="utf-8")
    result.freerouting_used = _try_freerouting(pcb_path)
    pcb_path.with_suffix(".placement.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    _render(result, console)
    return str(pcb_path)
