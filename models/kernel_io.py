"""
KernelIO: Typed kernel input/output models.

Kernels ONLY accept KernelInput and ONLY return KernelOutput.
No untyped dicts crossing the boundary.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from datetime import datetime


class KernelInput(BaseModel):
    """
    Validated input to a kernel.
    
    Every kernel invocation must receive this - no raw dicts.
    """
    kernel_id: str = Field(..., description="Target kernel ID")
    version: Optional[str] = Field(None, description="Specific version requested")
    
    # The actual arguments (kernel-specific)
    args: dict[str, Any] = Field(default_factory=dict)
    
    # Provenance
    request_id: str = Field(..., description="Originating request ID")
    spec_version: str = Field(default="1.0")
    
    # Execution constraints
    timeout_ms: Optional[int] = Field(None, description="Max execution time")
    determinism_required: Literal["D1", "D2", "NONE"] = Field(
        default="D1",
        description="Required determinism level"
    )


class UnitMetadata(BaseModel):
    """Unit conversion/validation metadata."""
    input_units: Optional[dict[str, str]] = None
    output_units: Optional[dict[str, str]] = None
    conversions_applied: list[str] = Field(default_factory=list)
    dimensional_signature: Optional[dict[str, int]] = None


class Provenance(BaseModel):
    """Provenance information for audit trail."""
    kernel_id: str
    kernel_version: str
    determinism: Literal["D1", "D2", "NONE"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_hash: Optional[str] = None
    source: Optional[str] = None


class KernelOutput(BaseModel):
    """
    Validated output from a kernel.
    
    Every kernel returns this - no raw dicts escaping.
    """
    # Identification
    kernel_id: str = Field(..., description="Kernel that produced this")
    version: str = Field(..., description="Kernel version")
    request_id: str = Field(..., description="Originating request ID")
    
    # Result
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Any] = Field(None, description="The actual output")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Metadata
    units_metadata: Optional[UnitMetadata] = None
    provenance: Provenance
    
    # Confidence/uncertainty
    uncertainty: Optional[float] = Field(None, ge=0)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    
    # Warnings (non-fatal issues)
    warnings: list[str] = Field(default_factory=list)
