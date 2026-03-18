"""Shared Pydantic models for the PCB AI pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


ComponentType = Literal["resistor", "capacitor", "ic", "led", "transistor", "connector"]
SeverityLevel = Literal["error", "warning", "info"]
OptimizationMode = Literal["thermal", "signal", "default"]


class ComponentRequirement(BaseModel):
    """Structured description of a required component."""

    name: str = Field(default="Generic Component")
    type: ComponentType = Field(default="ic")
    value: str = Field(default="TBD")
    quantity: int = Field(default=1, ge=1)
    package: str = Field(default="TBD")
    notes: str = Field(default="")


class CircuitRequirements(BaseModel):
    """Validated requirements extracted from natural language."""

    circuit_name: str = Field(default="AI Generated Circuit")
    description: str = Field(default="")
    components: list[ComponentRequirement] = Field(default_factory=list)
    power_supply: str = Field(default="5V DC")
    special_requirements: list[str] = Field(default_factory=list)


class BOMItem(BaseModel):
    """A line item in a bill of materials."""

    reference: str = Field(default="U1")
    value: str = Field(default="TBD")
    footprint: str = Field(default="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    datasheet_url: str = Field(default="")
    manufacturer: str = Field(default="Generic")
    part_number: str = Field(default="GENERIC-PART")
    lcsc_part: str = Field(default="")
    quantity: int = Field(default=1, ge=1)
    unit_price_usd: float = Field(default=0.0, ge=0.0)


class BillOfMaterials(BaseModel):
    """Validated bill of materials for a design."""

    items: list[BOMItem] = Field(default_factory=list)


class DatasheetKeySpecs(BaseModel):
    """Key package and electrical information extracted from a datasheet."""

    package: str = Field(default="Unknown")
    pin_count: int = Field(default=0, ge=0)
    voltage_range: str = Field(default="Unknown")
    pinout: dict[str, str] = Field(default_factory=dict)


class DatasheetInfo(BaseModel):
    """Cached datasheet metadata for a BOM item."""

    url: str = Field(default="")
    local_path: str = Field(default="")
    key_specs: DatasheetKeySpecs = Field(default_factory=DatasheetKeySpecs)


class NetPin(BaseModel):
    """One reference-designator pin participating in a net."""

    reference: str = Field(default="U1")
    pin_number: str = Field(default="1")
    pin_name: str = Field(default="")


class NetDescription(BaseModel):
    """Named electrical net with participating pins."""

    net_name: str = Field(default="NET_1")
    pins: list[NetPin] = Field(default_factory=list)
    notes: str = Field(default="")


class NetlistDescription(BaseModel):
    """LLM-produced netlist guidance used for schematic generation."""

    nets: list[NetDescription] = Field(default_factory=list)
    signal_flow: list[str] = Field(default_factory=list)


class PlacementRecord(BaseModel):
    """Component placement chosen by the board placer."""

    reference: str
    footprint: str
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    score: float = 0.0


class PlacementResult(BaseModel):
    """Placement summary written by the router."""

    optimization_mode: OptimizationMode = Field(default="default")
    board_width_mm: float = Field(default=100.0, gt=0.0)
    board_height_mm: float = Field(default=80.0, gt=0.0)
    placements: list[PlacementRecord] = Field(default_factory=list)
    nets_routed: int = Field(default=0, ge=0)
    freerouting_used: bool = Field(default=False)


class DFMCheck(BaseModel):
    """One design-for-manufacturing rule check."""

    name: str
    passed: bool
    severity: SeverityLevel
    message: str
    recommendation: str


class DFMReport(BaseModel):
    """Aggregate DFM result for a PCB file."""

    passed: bool
    score: float = Field(ge=0.0, le=100.0)
    checks: list[DFMCheck] = Field(default_factory=list)
