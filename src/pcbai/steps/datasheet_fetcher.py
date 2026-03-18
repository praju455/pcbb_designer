"""Datasheet fetching and Gemini-based spec extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from pcbai.core.config import get_settings
from pcbai.llm.provider import LLMProviderError, get_verifier_llm
from pcbai.models import BillOfMaterials, DatasheetInfo, DatasheetKeySpecs


def _search_urls(part_number: str) -> list[str]:
    """Return candidate datasheet URLs."""

    return [
        f"https://www.alldatasheet.com/view.jsp?Searchword={part_number}",
        f"https://datasheetspdf.com/search/{part_number}",
    ]


def _find_pdf_links(html: str) -> list[str]:
    """Extract PDF links from HTML text."""

    return list(dict.fromkeys(re.findall(r'https?://[^"\']+?\.pdf', html, flags=re.IGNORECASE)))


def _download(url: str, target: Path) -> bool:
    """Download a candidate datasheet PDF."""

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return False
    if "pdf" not in response.headers.get("content-type", "").lower() and not url.lower().endswith(".pdf"):
        return False
    target.write_bytes(response.content)
    return True


def _resolve_datasheet(item_part_number: str, direct_url: str, cache_dir: Path) -> tuple[str, str]:
    """Find and cache a datasheet locally."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{item_part_number}.pdf"
    if target.exists():
        return direct_url, str(target)

    candidates = [direct_url] if direct_url else []
    candidates.extend(_search_urls(item_part_number))
    for candidate in filter(None, candidates):
        if candidate.lower().endswith(".pdf") and _download(candidate, target):
            return candidate, str(target)
        try:
            response = requests.get(candidate, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            continue
        for link in _find_pdf_links(response.text):
            if _download(link, target):
                return link, str(target)
    return direct_url, ""


def _extract_pdf_text(path: str) -> str:
    """Extract the first three pages of a PDF using PyMuPDF."""

    if not path:
        return ""
    try:
        import fitz
    except ImportError:  # pragma: no cover - optional dependency
        return ""

    document = fitz.open(path)
    pages: list[str] = []
    try:
        for page_index in range(min(3, len(document))):
            pages.append(document[page_index].get_text())
    finally:
        document.close()
    return "\n".join(pages)


def _spec_schema() -> dict[str, Any]:
    """Return the schema for Gemini spec extraction."""

    return {
        "type": "object",
        "properties": {
            "package": {"type": "string"},
            "pin_count": {"type": "integer", "minimum": 0},
            "voltage_range": {"type": "string"},
            "pinout": {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "required": ["package", "pin_count", "voltage_range", "pinout"],
    }


def _fallback_specs(footprint: str) -> DatasheetKeySpecs:
    """Derive baseline specs from the selected footprint."""

    match = re.search(r"(\d+)", footprint)
    return DatasheetKeySpecs(
        package=footprint.split(":")[-1] if footprint else "Unknown",
        pin_count=int(match.group(1)) if match else 0,
        voltage_range="See datasheet",
        pinout={},
    )


def fetch_datasheets(bom: BillOfMaterials, console: Console | None = None, output_dir: str | Path | None = None) -> dict[str, DatasheetInfo]:
    """Fetch datasheets and extract pinout-related specs."""

    console = console or Console(stderr=True)
    verifier = get_verifier_llm()
    output_root = Path(output_dir) if output_dir else get_settings().ensure_output_dir()
    cache_dir = output_root / "datasheets"
    report: dict[str, DatasheetInfo] = {}

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Fetching datasheets", total=len(bom.items))
        for item in bom.items:
            resolved_url, local_path = _resolve_datasheet(item.part_number, item.datasheet_url, cache_dir)
            text = _extract_pdf_text(local_path)
            specs = _fallback_specs(item.footprint)
            if text:
                prompt = (
                    "Extract package, pin count, voltage range, and pinout from this datasheet excerpt.\n\n"
                    f"Part number: {item.part_number}\n\n{text[:12000]}"
                )
                try:
                    payload = verifier.generate_json(prompt, _spec_schema())
                    specs = DatasheetKeySpecs.model_validate(payload)
                except (LLMProviderError, ValueError, TypeError, json.JSONDecodeError):
                    specs = _fallback_specs(item.footprint)
            report[item.part_number] = DatasheetInfo(url=resolved_url, local_path=local_path, key_specs=specs)
            progress.advance(task)
    return report
