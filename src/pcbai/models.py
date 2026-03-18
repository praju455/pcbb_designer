"""Shared Pydantic models for the PCB AI backend and API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ComponentType = Literal["resistor", "capacitor", "ic", "led", "transistor", "connector"]
SeverityLevel = Literal["error", "warning", "info"]
OptimizationMode = Literal["thermal", "signal", "default"]
FabTarget = Literal["jlcpcb", "pcbway", "generic"]
JobState = Literal["queued", "running", "done", "error"]


class ComponentRequirement(BaseModel):
    """Structured description of a component requested by the user."""

    name: str = Field(default="Generic Component")
    type: ComponentType = Field(default="ic")
    value: str = Field(default="TBD")
    quantity: int = Field(default=1, ge=1)
    package: str = Field(default="TBD")
    notes: str = Field(default="")


class CircuitRequirements(BaseModel):
    """Validated circuit requirements extracted from natural language."""

    circuit_name: str = Field(default="AI Generated Circuit")
    description: str = Field(default="")
    components: list[ComponentRequirement] = Field(default_factory=list)
    power_supply: str = Field(default="5V DC")
    frequency: str = Field(default="")
    special_requirements: list[str] = Field(default_factory=list)


class BOMItem(BaseModel):
    """One line item in the bill of materials."""

    reference: str
    value: str
    footprint: str
    datasheet_url: str = Field(default="")
    manufacturer: str = Field(default="Generic")
    part_number: str = Field(default="GENERIC-PART")
    lcsc_part: str = Field(default="")
    quantity: int = Field(default=1, ge=1)
    unit_price_usd: float = Field(default=0.0, ge=0.0)


class BillOfMaterials(BaseModel):
    """Validated bill of materials for a generated circuit."""

    items: list[BOMItem] = Field(default_factory=list)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_components: int = Field(default=0, ge=0)


class DatasheetKeySpecs(BaseModel):
    """Structured specs extracted from a datasheet."""

    package: str = Field(default="Unknown")
    pin_count: int = Field(default=0, ge=0)
    voltage_range: str = Field(default="Unknown")
    pinout: dict[str, str] = Field(default_factory=dict)


class DatasheetInfo(BaseModel):
    """Cached datasheet metadata and extracted information."""

    url: str = Field(default="")
    local_path: str = Field(default="")
    key_specs: DatasheetKeySpecs = Field(default_factory=DatasheetKeySpecs)


class NetPin(BaseModel):
    """Pin participating in a named net."""

    reference: str
    pin_number: str
    pin_name: str = Field(default="")


class NetDescription(BaseModel):
    """Named connection between multiple pins."""

    net_name: str
    pins: list[NetPin] = Field(default_factory=list)
    notes: str = Field(default="")


class NetlistDescription(BaseModel):
    """Generated netlist description used for schematic synthesis."""

    nets: list[NetDescription] = Field(default_factory=list)
    signal_flow: list[str] = Field(default_factory=list)
    power_symbols: list[str] = Field(default_factory=list)


class PlacementRecord(BaseModel):
    """Component placement on the board."""

    reference: str
    footprint: str
    x_mm: float
    y_mm: float
    rotation_deg: float = Field(default=0.0)
    score: float = Field(default=0.0)
    cluster: str = Field(default="")


class PlacementResult(BaseModel):
    """Placement summary used by the router and API."""

    optimization_mode: OptimizationMode = Field(default="default")
    board_width_mm: float = Field(default=100.0, gt=0.0)
    board_height_mm: float = Field(default=80.0, gt=0.0)
    placements: list[PlacementRecord] = Field(default_factory=list)
    nets_routed: int = Field(default=0, ge=0)
    freerouting_used: bool = Field(default=False)
    strategy_summary: str = Field(default="")


class VerificationIssue(BaseModel):
    """One issue found during dual-LLM verification."""

    title: str
    severity: SeverityLevel = Field(default="warning")
    detail: str
    recommendation: str = Field(default="")


class VerificationResult(BaseModel):
    """Result returned by the dual-LLM verifier."""

    netlist: dict[str, Any]
    confidence_score: int = Field(default=0, ge=0, le=100)
    rounds_taken: int = Field(default=1, ge=1)
    issues_found: list[VerificationIssue] = Field(default_factory=list)
    issues_fixed: list[str] = Field(default_factory=list)
    generator_model: str = Field(default="")
    verifier_model: str = Field(default="")
    passed: bool = Field(default=False)
    warnings: list[str] = Field(default_factory=list)


class DFMCheck(BaseModel):
    """One DFM rule check."""

    name: str
    passed: bool
    severity: SeverityLevel
    message: str
    recommendation: str
    value_found: str = Field(default="")
    value_required: str = Field(default="")


class DFMReport(BaseModel):
    """Full DFM validation report."""

    passed: bool
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    fab_target: FabTarget = Field(default="generic")
    checks: list[DFMCheck] = Field(default_factory=list)
    ai_summary: str = Field(default="")
    fabrication_success_probability: int = Field(default=0, ge=0, le=100)
    suggested_fixes: list[str] = Field(default_factory=list)


class JobVerificationSummary(BaseModel):
    """Verification data surfaced through the API."""

    confidence_score: int = Field(default=0, ge=0, le=100)
    rounds_taken: int = Field(default=0, ge=0)
    issues_found: list[str] = Field(default_factory=list)
    issues_fixed: list[str] = Field(default_factory=list)
    generator: str = Field(default="")
    verifier: str = Field(default="")


class JobResult(BaseModel):
    """Job result payload returned by the API."""

    requirements: dict[str, Any] = Field(default_factory=dict)
    bom: list[dict[str, Any]] = Field(default_factory=list)
    netlist: dict[str, Any] = Field(default_factory=dict)
    files: list[str] = Field(default_factory=list)
    total_cost: float = Field(default=0.0, ge=0.0)


class JobStatus(BaseModel):
    """Background job state for the FastAPI backend."""

    status: JobState = Field(default="queued")
    current_step: str = Field(default="")
    steps_completed: list[str] = Field(default_factory=list)
    progress_percent: int = Field(default=0, ge=0, le=100)
    verification: JobVerificationSummary = Field(default_factory=JobVerificationSummary)
    result: JobResult = Field(default_factory=JobResult)
    error: str = Field(default="")


class LogEvent(BaseModel):
    """Structured log message streamed over WebSocket."""

    timestamp: str
    step: str
    level: str
    message: str
