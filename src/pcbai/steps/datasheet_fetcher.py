"""Datasheet discovery, caching, and first-pass spec extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError, get_llm_provider
from pcbai.models import BillOfMaterials, DatasheetInfo, DatasheetKeySpecs


def _datasheet_search_urls(part_number: str) -> list[str]:
    """Return search URLs to probe for a part number."""

    encoded = quote(part_number)
    return [
        f"https://www.alldatasheet.com/view.jsp?Searchword={encoded}",
        f"https://www.alldatasheet.com/datasheet-pdf/pdf/{encoded}.html",
        f"https://datasheetspdf.com/search/{encoded}",
        f"https://datasheetspdf.com/pdf-file/{encoded}",
    ]


def _candidate_pdf_links(page_text: str) -> list[str]:
    """Extract candidate PDF links from an HTML response."""

    matches = re.findall(r'https?://[^"\']+?\.pdf', page_text, flags=re.IGNORECASE)
    return list(dict.fromkeys(matches))


def _download_pdf(url: str, target_path: Path) -> bool:
    """Download a PDF if the remote resource looks valid."""

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return False

    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not url.lower().endswith(".pdf"):
        return False

    target_path.write_bytes(response.content)
    return True


def _find_and_cache_datasheet(part_number: str, datasheet_url: str, cache_dir: Path) -> tuple[str, str]:
    """Resolve a datasheet URL and cache the PDF locally if possible."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = cache_dir / f"{part_number}.pdf"
    if target_path.exists():
        return datasheet_url, str(target_path)

    urls = [datasheet_url] if datasheet_url else []
    urls.extend(_datasheet_search_urls(part_number))

    for url in filter(None, urls):
        if url.lower().endswith(".pdf") and _download_pdf(url, target_path):
            return url, str(target_path)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            continue
        for link in _candidate_pdf_links(response.text):
            if _download_pdf(link, target_path):
                return link, str(target_path)
        if "pdf" in response.headers.get("content-type", "").lower():
            target_path.write_bytes(response.content)
            return url, str(target_path)

    return datasheet_url, ""


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Read the first three pages of a PDF with PyMuPDF."""

    if not pdf_path:
        return ""
    try:
        import fitz
    except ImportError:  # pragma: no cover - optional dependency
        return ""

    document = fitz.open(pdf_path)
    excerpts: list[str] = []
    try:
        for page_index in range(min(3, len(document))):
            excerpts.append(document[page_index].get_text())
    finally:
        document.close()
    return "\n".join(excerpts)


def _schema() -> dict[str, Any]:
    """Return the expected JSON schema for datasheet key specs."""

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
    """Infer baseline key specs from the chosen footprint."""

    pin_count_match = re.search(r"(\d+)", footprint)
    return DatasheetKeySpecs(
        package=footprint.split(":")[-1] if footprint else "Unknown",
        pin_count=int(pin_count_match.group(1)) if pin_count_match else 0,
        voltage_range="See datasheet",
        pinout={},
    )


def fetch_datasheets(
    bom: BillOfMaterials,
    provider: BaseLLMProvider | None = None,
    output_dir: str | Path | None = None,
    console: Console | None = None,
) -> dict[str, DatasheetInfo]:
    """Download datasheets, parse excerpts, and extract key specs."""

    console = console or Console()
    provider = provider or get_llm_provider()
    root_dir = Path(output_dir) if output_dir else get_settings().ensure_output_dir()
    cache_dir = root_dir / "datasheets"
    report: dict[str, DatasheetInfo] = {}

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task("Fetching datasheets", total=len(bom.items))
        for item in bom.items:
            resolved_url, local_path = _find_and_cache_datasheet(item.part_number, item.datasheet_url, cache_dir)
            excerpt = _extract_text_from_pdf(local_path)
            specs = _fallback_specs(item.footprint)
            if excerpt:
                prompt = (
                    "Extract key PCB-relevant package specs from this datasheet excerpt. "
                    "Focus on package, pin count, supply range, and pin names.\n\n"
                    f"Part number: {item.part_number}\n"
                    f"Excerpt:\n{excerpt[:12000]}"
                )
                try:
                    payload = provider.generate_json(prompt, _schema())
                    specs = DatasheetKeySpecs.model_validate(payload)
                except (LLMProviderError, ValueError, TypeError, json.JSONDecodeError):
                    specs = _fallback_specs(item.footprint)
            report[item.part_number] = DatasheetInfo(url=resolved_url, local_path=local_path, key_specs=specs)
            progress.advance(task_id)

    return report
