"""DFM validation with stronger realism checks and Gemini analysis."""

from __future__ import annotations

import math
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_verifier_llm
from pcbai.models import DFMCheck, DFMReport, FabTarget


def _segments(text: str) -> list[tuple[float, float, float, float, float, int]]:
    """Extract PCB segments and widths."""

    pattern = re.compile(
        r'\(segment \(start ([\d\.-]+) ([\d\.-]+)\) \(end ([\d\.-]+) ([\d\.-]+)\) \(width ([\d\.-]+)\) \(layer ".*?"\) \(net (\d+)\)\)'
    )
    return [(float(a), float(b), float(c), float(d), float(width), int(net)) for a, b, c, d, width, net in pattern.findall(text)]


def _vias(text: str) -> list[tuple[float, float]]:
    """Extract via sizes and drills."""

    pattern = re.compile(r'\(via .*?\(size ([\d\.-]+)\) \(drill ([\d\.-]+)\)')
    return [tuple(float(value) for value in match) for match in pattern.findall(text)]


def _footprints(text: str) -> list[tuple[str, float, float, bool]]:
    """Extract footprint reference, position, and courtyard presence."""

    pattern = re.compile(r'\(footprint ".*?" \(layer "F\.Cu"\)\s+\(at ([\d\.-]+) ([\d\.-]+) [\d\.-]+\)(.*?)\n  \)', re.DOTALL)
    footprints: list[tuple[str, float, float, bool]] = []
    for x_text, y_text, block in pattern.findall(text):
        ref_match = re.search(r'\(property "Reference" "([^"]+)"', block)
        footprints.append((ref_match.group(1) if ref_match else "U?", float(x_text), float(y_text), 'layer "F.CrtYd"' in block))
    return footprints


def _pads_and_silk(text: str) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
    """Extract pads and silk lines."""

    pad_pattern = re.compile(r'\(pad ".*?" .*?\(at ([\d\.-]+) ([\d\.-]+)\) \(size ([\d\.-]+) ([\d\.-]+)\)')
    silk_pattern = re.compile(r'\(fp_line \(start ([\d\.-]+) ([\d\.-]+)\) \(end ([\d\.-]+) ([\d\.-]+)\).*?F\.SilkS')
    pads = [tuple(float(value) for value in match) for match in pad_pattern.findall(text)]
    silk = [tuple(float(value) for value in match) for match in silk_pattern.findall(text)]
    return pads, silk


def _edge_size(text: str) -> tuple[float, float]:
    """Extract board outline size."""

    match = re.search(r'\(gr_rect \(start [\d\.-]+ [\d\.-]+\) \(end ([\d\.-]+) ([\d\.-]+)\)', text)
    if not match:
        return 100.0, 80.0
    return float(match.group(1)), float(match.group(2))


def _distance(a: tuple[float, float, float, float, float, int], b: tuple[float, float, float, float, float, int]) -> float:
    """Approximate segment-to-segment distance using endpoints."""

    a_points = [(a[0], a[1]), (a[2], a[3])]
    b_points = [(b[0], b[1]), (b[2], b[3])]
    return min(math.dist(pa, pb) for pa in a_points for pb in b_points)


def _check(name: str, passed: bool, severity: str, recommendation: str, value_found: str, value_required: str) -> DFMCheck:
    """Construct a DFM check record."""

    return DFMCheck(
        name=name,
        passed=passed,
        severity=severity,
        message=f"{name} validation",
        recommendation=recommendation,
        value_found=value_found,
        value_required=value_required,
    )


def _render(report: DFMReport, console: Console) -> None:
    """Render the DFM report."""

    table = Table(title=f"DFM Report ({report.fab_target})")
    table.add_column("Status")
    table.add_column("Check")
    table.add_column("Value")
    table.add_column("Required")
    table.add_column("Fix")
    for check in report.checks:
        if check.passed:
            icon = "[green]PASS[/green]"
        elif check.severity == "error":
            icon = "[red]FAIL[/red]"
        else:
            icon = "[yellow]WARN[/yellow]"
        table.add_row(icon, check.name, check.value_found, check.value_required, check.recommendation)
    console.print(table)
    if report.ai_summary:
        console.print(f"[bold]Gemini assessment:[/bold] {report.ai_summary}")
        console.print(f"[bold]Fab success probability:[/bold] {report.fabrication_success_probability}%")


def validate_pcb(pcb_file: str | Path, fab_target: FabTarget = "generic", console: Console | None = None) -> DFMReport:
    """Validate a PCB file against DFM and fab-specific rules."""

    console = console or Console(stderr=True)
    settings = get_settings()
    verifier = get_verifier_llm()
    text = Path(pcb_file).read_text(encoding="utf-8")
    segments = _segments(text)
    vias = _vias(text)
    footprints = _footprints(text)
    pads, silk = _pads_and_silk(text)
    width, height = _edge_size(text)
    net_count = len(re.findall(r'\(net \d+ "', text))

    min_trace = min((segment[4] for segment in segments), default=0.0)
    min_clearance = min(
        (
            _distance(segments[index], segments[other])
            for index in range(len(segments))
            for other in range(index + 1, len(segments))
            if segments[index][5] != segments[other][5]
        ),
        default=1.0 if segments else 0.0,
    )
    min_via = min((size for size, _ in vias), default=0.0)
    min_drill = min((drill for _, drill in vias), default=0.0)
    min_edge = min((min(x, y, width - x, height - y) for _, x, y, _ in footprints), default=0.0)
    silk_overlap = any(abs((x1 + x2) / 2 - pad_x) <= pad_w / 2 and abs((y1 + y2) / 2 - pad_y) <= pad_h / 2 for x1, y1, x2, y2 in silk for pad_x, pad_y, pad_w, pad_h in pads)
    missing_courtyard = any(not has_courtyard for _, _, _, has_courtyard in footprints) or not footprints
    overlap = any(math.dist((footprints[index][1], footprints[index][2]), (footprints[other][1], footprints[other][2])) < 5.0 for index in range(len(footprints)) for other in range(index + 1, len(footprints)))
    enough_copper = len(segments) >= max(3, net_count)
    realistic_vias = min_via >= settings.dfm_min_via_diameter_mm if vias else True
    has_meaningful_board = bool(footprints) and net_count >= 3 and len(pads) >= 2 * max(1, len(footprints) // 2)

    checks = [
        _check("Min trace width", min_trace >= settings.dfm_min_trace_width_mm, "error", "Increase narrow traces.", f"{min_trace:.3f} mm", f">= {settings.dfm_min_trace_width_mm:.3f} mm"),
        _check("Min clearance", min_clearance >= settings.dfm_min_clearance_mm, "error", "Increase spacing between tracks and avoid stacked Manhattan routes.", f"{min_clearance:.3f} mm", f">= {settings.dfm_min_clearance_mm:.3f} mm"),
        _check(
            "Min via diameter",
            realistic_vias,
            "error",
            "Add production-size vias or keep the board single-sided until routing is improved.",
            f"{min_via:.3f} mm" if vias else "not used",
            f">= {settings.dfm_min_via_diameter_mm:.3f} mm",
        ),
        _check("Board edge clearance", min_edge >= 2.0, "warning", "Move parts inward.", f"{min_edge:.3f} mm", ">= 2.000 mm"),
        _check("Silkscreen overlap", not silk_overlap, "warning", "Trim silkscreen away from pads.", "overlap" if silk_overlap else "clear", "clear"),
        _check("Missing courtyard", not missing_courtyard, "warning", "Add F.CrtYd outlines to every footprint.", "missing" if missing_courtyard else "present", "present"),
        _check("JLCPCB trace width", min_trace >= settings.jlcpcb_min_trace_width_mm, "info", "Keep traces above the fab minimum.", f"{min_trace:.3f} mm", f">= {settings.jlcpcb_min_trace_width_mm:.3f} mm"),
        _check("Drill sizes", min_drill >= 0.2 if vias else True, "warning", "Add drillable vias or review fab drill limits.", f"{min_drill:.3f} mm" if vias else "not used", ">= 0.200 mm"),
        _check("Copper connectivity", enough_copper, "error", "Route every declared net with real copper segments before export.", f"{len(segments)} segments", f">= {max(3, net_count)} segments"),
        _check("Component overlap detection", not overlap and has_meaningful_board, "error", "Spread footprints farther apart and ensure the board contains real package geometry.", "overlap" if overlap else "clear", "clear"),
    ]

    score = max(0.0, 100.0 - sum(18 if not check.passed and check.severity == "error" else 7 if not check.passed else 0 for check in checks))
    summary = ""
    suggested_fixes = [check.recommendation for check in checks if not check.passed]
    fabrication_success_probability = int(score)
    try:
        summary = verifier.generate(
            "Analyze this DFM report and respond in 3 short paragraphs maximum. "
            "Focus on the main fabrication blocker, the next best fix, and a brief confidence estimate. "
            "Do not include JSON, markdown lists, or code fences.\n\n"
            f"{DFMReport(passed=False, score=score, fab_target=fab_target, checks=checks).model_dump_json(indent=2)}"
        )
    except LLMProviderError:
        summary = "Gemini analysis unavailable. Review the failing checks manually."

    report = DFMReport(
        passed=all(check.passed or check.severity != "error" for check in checks),
        score=score,
        fab_target=fab_target,
        checks=checks,
        ai_summary=summary,
        fabrication_success_probability=fabrication_success_probability,
        suggested_fixes=suggested_fixes,
    )
    _render(report, console)
    return report
