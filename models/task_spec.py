"""
TaskSpec: Canonical validated task specification.

This is THE contract between router/validator and kernels.
Kernels ONLY accept TaskSpec - no raw dicts allowed.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class Domain(str, Enum):
    """Valid domain classifications."""

    # Scientific domains
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    MATH = "math"
    CODE = "code"
    GENERAL = "general"
    # AI Lab domains
    EXPERIMENT = "experiment"  # experiment design
    SURVEY = "survey"  # survey research
    PROJECT = "project"  # project management
    OPERATIONS = "operations"  # operations planning
    ANALYSIS = "analysis"  # data analysis


class RiskLevel(str, Enum):
    """Risk level for ambiguity/error."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuantityRef(BaseModel):
    """
    Reference to a physical quantity with validated units.

    This replaces freeform dicts - all quantities must be typed.
    """

    quantity_id: str = Field(..., description="Canonical quantity ID from registry")
    value: Optional[float] = Field(None, description="Numeric value if known")
    unit_ucum: Optional[str] = Field(None, description="UCUM unit string")
    unit_raw: Optional[str] = Field(None, description="Original user-provided unit")
    uncertainty: Optional[float] = Field(None, description="Measurement uncertainty")

    # Validator-derived (read-only in practice)
    dimensions: Optional[dict[str, int]] = Field(
        None, description="Dimensional signature derived by validator"
    )


class TaskRequest(BaseModel):
    """
    Incoming request before validation.

    This is what the gateway receives - not yet validated.
    """

    request_id: str = Field(..., description="Unique request ID")
    user_input: str = Field(..., min_length=1, description="Raw user input")
    domain_hint: Optional[str] = Field(None, description="Optional domain hint")
    context: Optional[dict] = Field(default_factory=dict, description="Session context")


class TaskSpec(BaseModel):
    """
    Validated task specification.

    This is the ONLY input kernels accept.
    Produced by: router → validator pipeline.
    Consumed by: kernels.

    Immutable after validation - same spec → same output.
    """

    # Identification
    request_id: str = Field(..., description="Original request ID")
    spec_version: str = Field(default="1.0", description="Spec schema version")

    # Classification (from router)
    domain: Domain = Field(..., description="Primary domain")
    subdomain: Optional[str] = Field(None, description="Subdomain (e.g., fluids)")

    # Risk assessment
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    needs_units: bool = Field(default=False)
    has_equations: bool = Field(default=False)

    # Quantities (validated)
    quantities: list[QuantityRef] = Field(default_factory=list)

    # Execution plan
    required_gates: list[str] = Field(default_factory=list)
    selected_kernels: list[str] = Field(default_factory=list)
    # Generic arguments for kernels (e.g., alpha, parameters)
    args: dict = Field(default_factory=dict)

    # Original input (for reference only)
    user_input: str = Field(..., description="Original user input")

    # Confidence
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        frozen = True  # Immutable after creation
