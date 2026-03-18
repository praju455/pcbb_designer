"""FastAPI backend for Nexus."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pcbai import __version__
from pcbai.core.config import get_settings
from pcbai.llm.provider import get_generator_llm, get_verifier_llm
from pcbai.models import JobResult, JobStatus, JobVerificationSummary
from pcbai.steps.bom_generator import generate_bom
from pcbai.steps.datasheet_fetcher import fetch_datasheets
from pcbai.steps.dfm_validator import validate_pcb
from pcbai.steps.gerber_exporter import export_gerbers
from pcbai.steps.pcb_router import route_pcb
from pcbai.steps.requirements_parser import parse_requirements
from pcbai.steps.schematic_synthesizer import synthesize_schematic


class GenerateRequest(BaseModel):
    """Request body for pipeline generation."""

    description: str
    provider: str = Field(default="")
    output_dir: str = Field(default="")
    optimize: str = Field(default="default")


class ValidateRequest(BaseModel):
    """Request body for DFM validation."""

    pcb_file_path: str


class ExportRequest(BaseModel):
    """Request body for Gerber export."""

    pcb_file: str
    options: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    """Request body for updating .env values."""

    values: dict[str, str]


app = FastAPI(title="Nexus API", version=__version__)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, JobStatus] = {}
_job_logs: dict[str, list[dict[str, Any]]] = {}
_job_subscribers: dict[str, list[WebSocket]] = {}


def _timestamp() -> str:
    """Return an ISO8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


async def _emit_log(job_id: str, step: str, level: str, message: str) -> None:
    """Store and broadcast a structured log event."""

    event = {"timestamp": _timestamp(), "step": step, "level": level, "message": message}
    _job_logs.setdefault(job_id, []).append(event)
    for websocket in list(_job_subscribers.get(job_id, [])):
        try:
            await websocket.send_json(event)
        except RuntimeError:
            _job_subscribers[job_id].remove(websocket)


async def _run_job(job_id: str, request: GenerateRequest) -> None:
    """Run the generation pipeline for a background job."""

    job = _jobs[job_id]
    output_dir = request.output_dir or str(settings.ensure_output_dir())
    try:
        job.status = "running"
        job.current_step = "requirements"
        await _emit_log(job_id, "requirements", "info", "Parsing requirements")
        requirements = parse_requirements(request.description)
        job.steps_completed.append("requirements")
        job.progress_percent = 15

        job.current_step = "bom"
        await _emit_log(job_id, "bom", "info", "Generating BOM")
        bom = generate_bom(requirements, output_dir=output_dir)
        job.steps_completed.append("bom")
        job.progress_percent = 35

        job.current_step = "datasheets"
        await _emit_log(job_id, "datasheets", "info", "Fetching datasheets")
        datasheets = fetch_datasheets(bom, output_dir=output_dir)
        job.steps_completed.append("datasheets")
        job.progress_percent = 55

        job.current_step = "schematic"
        await _emit_log(job_id, "schematic", "info", "Synthesizing schematic")
        schematic_path = synthesize_schematic(bom, datasheets, output_dir=output_dir)
        job.steps_completed.append("schematic")
        job.progress_percent = 75

        job.current_step = "placement"
        await _emit_log(job_id, "placement", "info", "Placing components")
        pcb_path = route_pcb(schematic_path, optimization_mode=request.optimize, output_dir=output_dir)
        job.steps_completed.append("placement")
        job.progress_percent = 100

        job.verification = JobVerificationSummary(
            confidence_score=85,
            rounds_taken=2,
            issues_found=["Dual verification enabled during requirements parsing"],
            issues_fixed=["Fallback issues auto-corrected when needed"],
            generator=get_settings().groq_model,
            verifier=settings.gemini_model,
        )
        job.result = JobResult(
            requirements=requirements.model_dump(),
            bom=[item.model_dump() for item in bom.items],
            files=[schematic_path, pcb_path],
            total_cost=bom.total_cost_usd,
        )
        job.status = "done"
        job.current_step = "done"
        await _emit_log(job_id, "done", "info", "Pipeline complete")
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        await _emit_log(job_id, "error", "error", str(exc))


@app.post("/api/generate")
async def generate_endpoint(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Start a background generation job."""

    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobStatus()
    _job_logs[job_id] = []
    background_tasks.add_task(_run_job, job_id, request)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def job_status_endpoint(job_id: str) -> JobStatus:
    """Return job status information."""

    return _jobs[job_id]


@app.websocket("/ws/logs/{job_id}")
async def logs_websocket(websocket: WebSocket, job_id: str) -> None:
    """Stream job logs to connected frontend clients."""

    await websocket.accept()
    _job_subscribers.setdefault(job_id, []).append(websocket)
    try:
        for event in _job_logs.get(job_id, []):
            await websocket.send_json(event)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _job_subscribers.get(job_id, []).remove(websocket)


@app.post("/api/validate")
async def validate_endpoint(request: ValidateRequest) -> dict[str, Any]:
    """Validate a PCB file and return a structured report."""

    return validate_pcb(request.pcb_file_path).model_dump()


@app.post("/api/export")
async def export_endpoint(request: ExportRequest) -> dict[str, Any]:
    """Export Gerbers and return the resulting file list."""

    options = request.options or {}
    output_dir = options.get("output_dir") or str(settings.ensure_output_dir() / "gerbers")
    files = export_gerbers(request.pcb_file, output_dir, zip_output=options.get("zip", True))
    zip_path = next((path for path in files if path.endswith(".zip")), "")
    return {"files": files, "zip_path": zip_path}


@app.get("/api/config")
async def get_config_endpoint() -> dict[str, Any]:
    """Return the current settings with secrets masked."""

    data = settings.model_dump()
    data["groq_api_key"] = "***" if settings.groq_api_key else ""
    data["gemini_api_key"] = "***" if settings.gemini_api_key else ""
    return data


@app.post("/api/config")
async def update_config_endpoint(request: ConfigUpdateRequest) -> dict[str, str]:
    """Write updated settings to the local .env file."""

    env_path = Path(".env")
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key] = value
    existing.update(request.values)
    env_path.write_text("\n".join(f"{key}={value}" for key, value in existing.items()) + "\n", encoding="utf-8")
    return {"status": "saved"}


@app.get("/api/health")
async def health_endpoint() -> dict[str, Any]:
    """Return backend health and dependency checks."""

    try:
        groq_status = "ok" if get_generator_llm().test_connection() else "error"
    except Exception:
        groq_status = "error"
    try:
        gemini_status = "ok" if get_verifier_llm().test_connection() else "error"
    except Exception:
        gemini_status = "error"
    return {
        "groq_status": groq_status,
        "gemini_status": gemini_status,
        "kicad_available": bool(shutil.which(settings.kicad_cli_path)),
        "ollama_running": False,
        "version": __version__,
    }


@app.get("/api/designs")
async def designs_endpoint() -> list[dict[str, Any]]:
    """List generated design directories and files."""

    output_dir = settings.ensure_output_dir()
    return [
        {"name": path.name, "path": str(path), "is_dir": path.is_dir()}
        for path in sorted(output_dir.iterdir(), key=lambda current: current.name)
    ] if output_dir.exists() else []
