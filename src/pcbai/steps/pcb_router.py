"""PCB placement and lightweight routing with package-aware footprints."""

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


PadSpec = tuple[str, str, float, float, float, float]


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

    return [(float(x), float(y)) for y in range(15, int(height) - 10, 15) for x in range(18, int(width) - 10, 18)]


def _score(reference: str, position: tuple[float, float], placed: list[PlacementRecord], mode: OptimizationMode, graph: dict[str, set[str]], width: float, height: float) -> float:
    """Score a candidate placement using thermal, signal, and density terms."""

    x, y = position
    edge = min(x, y, width - x, height - y)
    thermal_score = max(0.0, 25.0 - edge) if mode == "thermal" and reference.startswith(("U", "Q")) else 0.0
    signal_score = 0.0
    density_penalty = 0.0
    for record in placed:
        distance = math.dist((record.x_mm, record.y_mm), position)
        density_penalty += max(0.0, 16.0 - distance)
        if record.reference in graph.get(reference, set()):
            signal_score += max(0.0, 32.0 - distance)
    return (thermal_score * 0.4) + (signal_score * 0.4) - (density_penalty * 0.2)


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
                score=_score(item.reference, best, placed, mode, graph, width, height),
                cluster=_cluster_for(item.reference, graph),
            )
        )
    return placed


def _pad_specs(item_footprint: str, reference: str) -> list[PadSpec]:
    """Return pad definitions for common package families."""

    footprint = item_footprint.upper()
    if "DIP-8" in footprint:
        return [
            ("1", "thru_hole rect", -3.81, -3.81, 1.6, 1.6),
            ("2", "thru_hole oval", -3.81, -1.27, 1.6, 1.6),
            ("3", "thru_hole oval", -3.81, 1.27, 1.6, 1.6),
            ("4", "thru_hole oval", -3.81, 3.81, 1.6, 1.6),
            ("5", "thru_hole oval", 3.81, 3.81, 1.6, 1.6),
            ("6", "thru_hole oval", 3.81, 1.27, 1.6, 1.6),
            ("7", "thru_hole oval", 3.81, -1.27, 1.6, 1.6),
            ("8", "thru_hole oval", 3.81, -3.81, 1.6, 1.6),
        ]
    if "SOIC-8" in footprint:
        return [
            ("1", "smd roundrect", -2.7, -1.905, 1.5, 0.6),
            ("2", "smd roundrect", -2.7, -0.635, 1.5, 0.6),
            ("3", "smd roundrect", -2.7, 0.635, 1.5, 0.6),
            ("4", "smd roundrect", -2.7, 1.905, 1.5, 0.6),
            ("5", "smd roundrect", 2.7, 1.905, 1.5, 0.6),
            ("6", "smd roundrect", 2.7, 0.635, 1.5, 0.6),
            ("7", "smd roundrect", 2.7, -0.635, 1.5, 0.6),
            ("8", "smd roundrect", 2.7, -1.905, 1.5, 0.6),
        ]
    if reference.startswith("J"):
        return [
            ("1", "thru_hole oval", 0.0, -1.27, 1.7, 1.7),
            ("2", "thru_hole oval", 0.0, 1.27, 1.7, 1.7),
        ]
    return [
        ("1", "smd roundrect", -0.95, 0.0, 0.9, 1.1),
        ("2", "smd roundrect", 0.95, 0.0, 0.9, 1.1),
    ]


def _net_lookup(netlist: NetlistDescription) -> tuple[dict[tuple[str, str], str], dict[str, int]]:
    """Return pin-to-net and net-to-index lookup tables."""

    pin_to_net: dict[tuple[str, str], str] = {}
    net_to_index: dict[str, int] = {}
    for index, net in enumerate(netlist.nets, start=1):
        net_to_index[net.net_name] = index
        for pin in net.pins:
            pin_to_net[(pin.reference, pin.pin_number)] = net.net_name
    return pin_to_net, net_to_index


def _outline_size(placement: PlacementRecord) -> tuple[float, float]:
    """Return a simple footprint outline size for courtyard generation."""

    if placement.reference.startswith("U"):
        return 10.0, 12.0
    if placement.reference.startswith("J"):
        return 5.0, 7.0
    return 5.0, 3.6


def _pad_line(pad: PadSpec, net_name: str | None, net_to_index: dict[str, int]) -> str:
    """Render a pad definition with optional net assignment."""

    number, pad_kind, x, y, width, height = pad
    net_clause = ""
    if net_name and net_name in net_to_index:
        net_clause = f' (net {net_to_index[net_name]} "{net_name}")'
    if pad_kind.startswith("thru_hole"):
        return (
            f'    (pad "{number}" {pad_kind} (at {x:.2f} {y:.2f}) (size {width:.2f} {height:.2f}) '
            f'(drill 0.80) (layers "*.Cu" "*.Mask"){net_clause})'
        )
    return (
        f'    (pad "{number}" {pad_kind} (at {x:.2f} {y:.2f}) (size {width:.2f} {height:.2f}) '
        f'(layers "F.Cu" "F.Paste" "F.Mask"){net_clause})'
    )


def _anchor_positions(result: PlacementResult, bom: BillOfMaterials) -> dict[tuple[str, str], tuple[float, float]]:
    """Return board coordinates for each pad anchor."""

    placements = {placement.reference: placement for placement in result.placements}
    anchors: dict[tuple[str, str], tuple[float, float]] = {}
    for item in bom.items:
        placement = placements[item.reference]
        for number, _kind, dx, dy, _w, _h in _pad_specs(item.footprint, item.reference):
            anchors[(item.reference, number)] = (placement.x_mm + dx, placement.y_mm + dy)
    return anchors


def _segment_width(net_name: str) -> float:
    """Return a routing width for a named net."""

    upper = net_name.upper()
    if upper in {"VCC", "GND"}:
        return 0.6
    if "LED" in upper or "OUTPUT" in upper:
        return 0.35
    return 0.25


def _route_segments(
    netlist: NetlistDescription,
    anchors: dict[tuple[str, str], tuple[float, float]],
    net_to_index: dict[str, int],
) -> list[str]:
    """Create simple Manhattan routes for each named net."""

    segments: list[str] = []
    for net in netlist.nets:
        points = [anchors[(pin.reference, pin.pin_number)] for pin in net.pins if (pin.reference, pin.pin_number) in anchors]
        if len(points) < 2:
            continue
        hub_x = sum(point[0] for point in points) / len(points)
        hub_y = sum(point[1] for point in points) / len(points)
        width = _segment_width(net.net_name)
        net_index = net_to_index.get(net.net_name, 1)
        for point_x, point_y in points:
            if abs(point_x - hub_x) > 0.05:
                segments.append(
                    f'  (segment (start {point_x:.2f} {point_y:.2f}) (end {hub_x:.2f} {point_y:.2f}) '
                    f'(width {width:.2f}) (layer "F.Cu") (net {net_index}))'
                )
            if abs(point_y - hub_y) > 0.05:
                segments.append(
                    f'  (segment (start {hub_x:.2f} {point_y:.2f}) (end {hub_x:.2f} {hub_y:.2f}) '
                    f'(width {width:.2f}) (layer "F.Cu") (net {net_index}))'
                )
    return segments


def _board_text(bom: BillOfMaterials, netlist: NetlistDescription, result: PlacementResult) -> str:
    """Render a more realistic KiCad PCB file with package-aware pads and copper."""

    pin_to_net, net_to_index = _net_lookup(netlist)
    lines = [
        '(kicad_pcb (version 20221018) (generator nexus-backend)',
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
    for index, net in enumerate(netlist.nets, start=1):
        lines.append(f'  (net {index} "{net.net_name}")')
    for placement in result.placements:
        item = next(row for row in bom.items if row.reference == placement.reference)
        outline_w, outline_h = _outline_size(placement)
        lines.extend(
            [
                f'  (footprint "{item.footprint}" (layer "F.Cu")',
                f'    (at {placement.x_mm:.2f} {placement.y_mm:.2f} {placement.rotation_deg:.2f})',
                f'    (property "Reference" "{item.reference}" (at 0 {-outline_h / 2 - 1.4:.2f} 0) (layer "F.SilkS"))',
                f'    (property "Value" "{item.value}" (at 0 {outline_h / 2 + 1.4:.2f} 0) (layer "F.Fab"))',
                '    (attr smd)',
                f'    (fp_line (start {-outline_w / 2:.2f} {-outline_h / 2:.2f}) (end {outline_w / 2:.2f} {-outline_h / 2:.2f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                f'    (fp_line (start {outline_w / 2:.2f} {-outline_h / 2:.2f}) (end {outline_w / 2:.2f} {outline_h / 2:.2f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                f'    (fp_line (start {outline_w / 2:.2f} {outline_h / 2:.2f}) (end {-outline_w / 2:.2f} {outline_h / 2:.2f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
                f'    (fp_line (start {-outline_w / 2:.2f} {outline_h / 2:.2f}) (end {-outline_w / 2:.2f} {-outline_h / 2:.2f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
            ]
        )
        for pad in _pad_specs(item.footprint, item.reference):
            pad_number = pad[0]
            net_name = pin_to_net.get((item.reference, pad_number))
            lines.append(_pad_line(pad, net_name, net_to_index))
        lines.append("  )")
    anchors = _anchor_positions(result, bom)
    lines.extend(_route_segments(netlist, anchors, net_to_index))
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
        nets_routed=len([net for net in netlist.nets if len(net.pins) >= 2]),
        freerouting_used=False,
        strategy_summary=strategy,
    )
    pcb_path.write_text(_board_text(bom, netlist, result), encoding="utf-8")
    result.freerouting_used = _try_freerouting(pcb_path)
    pcb_path.with_suffix(".placement.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    _render(result, console)
    return str(pcb_path)
