"""
Clarify Protocol Models.

Defines the contract for disambiguation flows:
- ClarifyRequest: What we need from the user
- ClarifyAnswer: User's disambiguation response
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClarifyType(str, Enum):
    """Types of clarification needed."""

    TERM_DISAMBIGUATION = "term_disambiguation"
    UNIT_SPECIFICATION = "unit_specification"
    MISSING_PARAMETER = "missing_parameter"
    DOMAIN_SELECTION = "domain_selection"
    CONSTRAINT_CLARIFICATION = "constraint_clarification"


class ClarifyOption(BaseModel):
    """A single option in a disambiguation choice."""

    option_id: str = Field(..., description="Unique ID for this option")
    label: str = Field(..., description="Human-readable label")
    description: Optional[str] = Field(None, description="Extended description")
    canonical_value: str = Field(..., description="Canonical value if selected")
    unit_ucum: Optional[str] = Field(None, description="UCUM unit if applicable")


class ClarifyRequest(BaseModel):
    """
    Structured clarification request.

    This is returned when gates detect ambiguity that cannot be
    resolved deterministically. The user must provide a ClarifyAnswer.
    """

    request_id: str = Field(..., description="Original request ID")
    clarify_type: ClarifyType = Field(..., description="Type of clarification")
    ambiguous_term: str = Field(..., description="The term needing clarification")
    question: str = Field(..., description="Human-readable question")
    options: list[ClarifyOption] = Field(
        default_factory=list, description="Allowed options (if enumerable)"
    )
    required_fields: list[str] = Field(
        default_factory=list, description="Fields that must be provided"
    )
    reason_code: str = Field(..., description="Reason code from registry")
    context: Optional[dict] = Field(None, description="Additional context")

    def has_options(self) -> bool:
        """Return True if this is a multiple-choice clarification."""
        return len(self.options) > 0


class ClarifyAnswer(BaseModel):
    """
    User's response to a ClarifyRequest.

    This gets merged back into the TaskSpec to resolve ambiguity.
    """

    request_id: str = Field(..., description="Original request ID")
    clarify_request_id: Optional[str] = Field(None, description="ID of ClarifyRequest answered")
    selected_option_id: Optional[str] = Field(None, description="Selected option ID")
    provided_values: dict[str, str] = Field(
        default_factory=dict, description="Values for required_fields"
    )
    freeform_response: Optional[str] = Field(None, description="Freeform text if no options")


class ClarifyChain(BaseModel):
    """
    Tracks the full disambiguation chain for a request.

    Enables audit of all clarifications needed to reach a resolved spec.
    """

    request_id: str
    clarifications: list[tuple[ClarifyRequest, ClarifyAnswer]] = Field(default_factory=list)
    resolved: bool = Field(default=False)

    def add_exchange(self, request: ClarifyRequest, answer: ClarifyAnswer) -> None:
        """Add a clarification exchange to the chain."""
        self.clarifications.append((request, answer))


# Pre-defined clarify requests for common ambiguities


def make_specific_weight_clarify(request_id: str) -> ClarifyRequest:
    """Create ClarifyRequest for 'specific weight' ambiguity."""
    return ClarifyRequest(
        request_id=request_id,
        clarify_type=ClarifyType.TERM_DISAMBIGUATION,
        ambiguous_term="specific weight",
        question="'Specific weight' can mean different things. Which do you mean?",
        options=[
            ClarifyOption(
                option_id="weight_density",
                label="Weight Density (γ)",
                description="Force per unit volume, γ = ρg (N/m³)",
                canonical_value="weight_density",
                unit_ucum="N/m3",
            ),
            ClarifyOption(
                option_id="specific_gravity",
                label="Specific Gravity",
                description="Ratio of density to water density (dimensionless)",
                canonical_value="specific_gravity",
                unit_ucum="1",
            ),
        ],
        required_fields=["quantity_type"],
        reason_code="TERM_COLLISION",
    )


def make_lb_unit_clarify(request_id: str) -> ClarifyRequest:
    """Create ClarifyRequest for 'lb' unit ambiguity."""
    return ClarifyRequest(
        request_id=request_id,
        clarify_type=ClarifyType.UNIT_SPECIFICATION,
        ambiguous_term="lb",
        question="'lb' can mean mass or force. Which do you mean?",
        options=[
            ClarifyOption(
                option_id="lbm",
                label="Pound-mass (lbm)",
                description="Unit of mass",
                canonical_value="[lb_av]",
                unit_ucum="[lb_av]",
            ),
            ClarifyOption(
                option_id="lbf",
                label="Pound-force (lbf)",
                description="Unit of force",
                canonical_value="[lbf_av]",
                unit_ucum="[lbf_av]",
            ),
        ],
        required_fields=["unit_type"],
        reason_code="UNIT_AMBIGUOUS",
    )


def make_weight_clarify(request_id: str) -> ClarifyRequest:
    """Create ClarifyRequest for 'weight' term ambiguity."""
    return ClarifyRequest(
        request_id=request_id,
        clarify_type=ClarifyType.TERM_DISAMBIGUATION,
        ambiguous_term="weight",
        question="'Weight' is ambiguous. Do you mean force (W=mg) or mass?",
        options=[
            ClarifyOption(
                option_id="force",
                label="Weight as Force",
                description="W = mg, measured in Newtons or lbf",
                canonical_value="weight_force",
                unit_ucum="N",
            ),
            ClarifyOption(
                option_id="mass",
                label="Mass",
                description="Amount of matter, measured in kg or lbm",
                canonical_value="mass",
                unit_ucum="kg",
            ),
        ],
        required_fields=["quantity_meaning"],
        reason_code="TERM_COLLISION",
    )
