"""Design-for-manufacturing validation for generated KiCad boards."""

from __future__ import annotations

import math
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.models import DFMCheck, DFMReport


def _extract_segments(text: str) -> list[tuple[float, float, float, float, float]]:
    """Parse segment start/end coordinates and widths."""

    pattern = re.compile(
        r'\(segment \(start ([\d\.-]+) ([\d\.-]+)\) \(end ([\d\.-]+) ([\d\.-]+)\) \(width ([\d\.-]+)\) .*?\)'
    )
    return [tuple(float(group) for group in match) for match in pattern.findall(text)]


def _extract_vias(text: str) -> list[float]:
    """Parse via diameters from the PCB file."""

    pattern = re.compile(r'\(via .*?\(size ([\d\.-]+)\)')
    return [float(value) for value in pattern.findall(text)]


def _extract_board_rect(text: str) -> tuple[float, float]:
    """Parse the board size from the edge-cuts rectangle."""

    match = re.search(r'\(gr_rect \(start [\d\.-]+ [\d\.-]+\) \(end ([\d\.-]+) ([\d\.-]+)\)', text)
    if not match:
        return 100.0, 80.0
    return float(match.group(1)), float(match.group(2))


def _extract_footprints(text: str) -> list[tuple[str, float, float, bool]]:
    """Parse footprint references, positions, and courtyard presence."""

    pattern = re.compile(
        r'\(footprint ".*?" \(layer "F\.Cu"\)\s+\(at ([\d\.-]+) ([\d\.-]+) [\d\.-]+\)(.*?)\n  \)',
        re.DOTALL,
    )
    footprints: list[tuple[str, float, float, bool]] = []
    for x_text, y_text, body in pattern.findall(text):
        reference_match = re.search(r'\(property "Reference" "([^"]+)"', body)
        reference = reference_match.group(1) if reference_match else "U?"
        has_courtyard = 'layer "F.CrtYd"' in body
        footprints.append((reference, float(x_text), float(y_text), has_courtyard))
    return footprints


def _extract_silk_and_pads(text: str) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
    """Parse simple silkscreen lines and pad rectangles."""

    silk_pattern = re.compile(
        r'\(fp_line \(start ([\d\.-]+) ([\d\.-]+)\) \(end ([\d\.-]+) ([\d\.-]+)\).*?layer "F\.SilkS"\)'
    )
    pad_pattern = re.compile(r'\(pad ".*?" .*?\(at ([\d\.-]+) ([\d\.-]+)\) \(size ([\d\.-]+) ([\d\.-]+)\)')
    silk = [tuple(float(group) for group in match) for match in silk_pattern.findall(text)]
    pads = [tuple(float(group) for group in match) for match in pad_pattern.findall(text)]
    return silk, pads


def _segment_distance(segment_a: tuple[float, float, float, float, float], segment_b: tuple[float, float, float, float, float]) -> float:
    """Approximate the spacing between two segments using endpoints."""

    ax1, ay1, ax2, ay2, _ = segment_a
    bx1, by1, bx2, by2, _ = segment_b
    points_a = [(ax1, ay1), (ax2, ay2)]
    points_b = [(bx1, by1), (bx2, by2)]
    return min(math.dist(point_a, point_b) for point_a in points_a for point_b in points_b)


def _make_check(name: str, passed: bool, severity: str, message: str, recommendation: str) -> DFMCheck:
    """Create a validated DFM check."""

    return DFMCheck(name=name, passed=passed, severity=severity, message=message, recommendation=recommendation)


def _render_report(report: DFMReport, console: Console) -> None:
    """Print the report as a Rich table."""

    table = Table(title=f"DFM Report (Score: {report.score:.1f})")
    table.add_column("Status")
    table.add_column("Check")
    table.add_column("Severity")
    table.add_column("Message")
    table.add_column("Recommendation")

    for check in report.checks:
        status = "[green]✅[/green]" if check.passed else "[red]❌[/red]" if check.severity == "error" else "[yellow]⚠️[/yellow]"
        color = "green" if check.passed else "red" if check.severity == "error" else "yellow"
        table.add_row(status, check.name, f"[{color}]{check.severity}[/{color}]", check.message, check.recommendation)

    console.print(table)


def validate_pcb(pcb_file: str | Path, console: Console | None = None) -> DFMReport:
    """Validate a KiCad PCB against manufacturing-focused checks."""

    console = console or Console()
    settings = get_settings()
    text = Path(pcb_file).read_text(encoding="utf-8")
    segments = _extract_segments(text)
    vias = _extract_vias(text)
    board_width, board_height = _extract_board_rect(text)
    footprints = _extract_footprints(text)
    silk, pads = _extract_silk_and_pads(text)

    min_trace = min((segment[4] for segment in segments), default=1.0)
    min_clearance = min(
        (_segment_distance(segments[index], segments[other]) for index in range(len(segments)) for other in range(index + 1, len(segments))),
        default=1.0,
    )
    min_via = min(vias, default=1.0)
    min_edge_clearance = min((min(x, y, board_width - x, board_height - y) for _, x, y, _ in footprints), default=10.0)
    silk_overlap = any(
        abs((x1 + x2) / 2 - pad_x) <= pad_w / 2 and abs((y1 + y2) / 2 - pad_y) <= pad_h / 2
        for x1, y1, x2, y2 in silk
        for pad_x, pad_y, pad_w, pad_h in pads
    )
    missing_courtyard = any(not has_courtyard for _, _, _, has_courtyard in footprints)

    checks = [
        _make_check(
            "Minimum trace width",
            min_trace >= settings.dfm_min_trace_width_mm,
            "error",
            f"Minimum trace width is {min_trace:.3f} mm; target is {settings.dfm_min_trace_width_mm:.3f} mm.",
            "Increase narrow traces or relax the configured rule if the fab allows it.",
        ),
        _make_check(
            "Minimum clearance",
            min_clearance >= settings.dfm_min_clearance_mm,
            "error",
            f"Minimum segment clearance is {min_clearance:.3f} mm; target is {settings.dfm_min_clearance_mm:.3f} mm.",
            "Spread dense routes or use additional layers to improve spacing.",
        ),
        _make_check(
            "Minimum via diameter",
            min_via >= settings.dfm_min_via_diameter_mm,
            "error",
            f"Minimum via diameter is {min_via:.3f} mm; target is {settings.dfm_min_via_diameter_mm:.3f} mm.",
            "Increase via diameter in the routing strategy or board rules.",
        ),
        _make_check(
            "Board edge clearance",
            min_edge_clearance >= 2.0,
            "warning",
            f"Closest component center is {min_edge_clearance:.3f} mm from the board edge.",
            "Move sensitive parts inward by at least 2 mm for assembly margin.",
        ),
        _make_check(
            "Silkscreen overlap",
            not silk_overlap,
            "warning",
            "Silkscreen elements overlap pad areas." if silk_overlap else "No silkscreen overlap detected.",
            "Trim silkscreen lines away from solderable pads.",
        ),
        _make_check(
            "Courtyard presence",
            not missing_courtyard,
            "warning",
            "One or more footprints are missing courtyard outlines." if missing_courtyard else "All footprints include a courtyard.",
            "Add F.CrtYd outlines to every footprint used for assembly.",
        ),
        _make_check(
            "JLCPCB trace width",
            min_trace >= settings.jlcpcb_min_trace_width_mm,
            "info",
            f"Minimum trace width is {min_trace:.3f} mm; JLCPCB baseline is {settings.jlcpcb_min_trace_width_mm:.3f} mm.",
            "Keep traces above the JLCPCB minimum to avoid fab rule violations.",
        ),
    ]

    penalties = sum(20 if not check.passed and check.severity == "error" else 8 if not check.passed else 0 for check in checks)
    report = DFMReport(passed=all(check.passed or check.severity != "error" for check in checks), score=max(0.0, 100.0 - penalties), checks=checks)
    _render_report(report, console)
    return report
