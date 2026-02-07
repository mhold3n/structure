"""
GateDecision: Validated gate output model.

All gates return this - typed decisions, not dicts.
"""

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


class Decision(str, Enum):
    """Gate decision outcomes."""

    ACCEPT = "ACCEPT"
    CLARIFY = "CLARIFY"
    REJECT = "REJECT"
    FALLBACK = "FALLBACK"
    ESCALATE = "ESCALATE"
    WARN = "WARN"


class GateDecision(BaseModel):
    """
    Structured gate decision output.

    All validation gates return this model.
    """

    gate_id: str = Field(..., description="ID of the gate")
    decision: Decision = Field(..., description="Gate decision")
    reasons: list[str] = Field(default_factory=list, description="Reason codes")
    required_fields: list[str] = Field(
        default_factory=list, description="Fields needed for CLARIFY"
    )
    clarifying_questions: list[str] = Field(
        default_factory=list, description="Human-readable questions for CLARIFY"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    def is_blocking(self) -> bool:
        """Return True if this decision blocks execution."""
        return self.decision in (Decision.CLARIFY, Decision.REJECT, Decision.ESCALATE)
