"""
Gates: Model-agnostic validation gates.

Hard gates: Must pass (schema, units, bounds)
Soft gates: Attach warnings (ambiguity detection)

All gates accept TaskSpec and return GateDecision.
"""

import re
from typing import Any

from models.task_spec import TaskSpec
from models.gate_decision import GateDecision, Decision
from .loader import load_quantities, load_policy


# --- Gate Implementations ---


def schema_gate(spec: TaskSpec) -> GateDecision:
    """
    Validate TaskSpec structure.

    Since we're using Pydantic, if we get here the spec is valid.
    This gate is a pass-through but can add domain-specific checks.
    """
    # TaskSpec is already validated by Pydantic
    # Add any domain-specific structural requirements here

    if not spec.user_input.strip():
        return GateDecision(
            gate_id="schema_gate",
            decision=Decision.REJECT,
            reasons=["SCHEMA_INVALID"],
            required_fields=["user_input"],
            clarifying_questions=["Please provide a valid input."],
        )

    return GateDecision(gate_id="schema_gate", decision=Decision.ACCEPT, reasons=[])


def unit_consistency_gate(spec: TaskSpec) -> GateDecision:
    """
    Check for unit consistency and UCUM compliance.

    This is a soft gate - may CLARIFY but not REJECT.
    """
    # Load unit disambiguation policy
    policy = load_policy("unit_disambiguation") or {}
    ambiguous_units = policy.get("ambiguous_units", {})

    reasons = []
    required_fields = []
    questions = []

    # Check for ambiguous unit strings in original input
    for unit, config in ambiguous_units.items():
        if re.search(rf"\b{unit}\b", spec.user_input, re.IGNORECASE):
            if config.get("action") == "CLARIFY":
                reasons.append("UNIT_AMBIGUOUS")
                required_fields.append("unit_clarification")
                question = config.get("question", f"Please clarify the unit '{unit}'")
                questions.append(question)

    if reasons:
        return GateDecision(
            gate_id="unit_consistency_gate",
            decision=Decision.CLARIFY,
            reasons=reasons,
            required_fields=required_fields,
            clarifying_questions=questions,
        )

    return GateDecision(gate_id="unit_consistency_gate", decision=Decision.ACCEPT, reasons=[])


def ambiguity_gate(spec: TaskSpec) -> GateDecision:
    """
    Detect term collisions and disallowed terms.

    This is the main ambiguity detection gate.
    """
    user_input_lower = spec.user_input.lower()

    # Load quantities registry
    quantities = load_quantities()
    quantities_list = quantities.get("quantities", [])

    # Load unit disambiguation policy
    policy = load_policy("unit_disambiguation") or {}
    disallowed = policy.get("disallowed_without_disambiguator", [])

    reasons = []
    required_fields = []
    questions = []

    # Check for disallowed terms
    for term in disallowed:
        if term.lower() in user_input_lower:
            reasons.append("DISALLOWED_TERM")
            field_name = term.replace(" ", "_").lower()
            required_fields.append(f"{field_name}_clarification")
            questions.append(f"The term '{term}' is ambiguous. Please clarify what you mean.")

    # Check for term collisions
    for qty in quantities_list:
        for alias in qty.get("aliases", []):
            if alias.lower() in user_input_lower:
                collides_with = qty.get("collides_with", [])
                if collides_with:
                    reasons.append("TERM_COLLISION")
                    field_name = alias.replace(" ", "_").lower()
                    required_fields.append(f"{field_name}_disambiguation")
                    hint = qty.get("disambiguation_hint", "")
                    questions.append(
                        f"'{alias}' could mean multiple things. {hint} "
                        f"Please specify which you mean."
                    )

    if reasons:
        return GateDecision(
            gate_id="ambiguity_gate",
            decision=Decision.CLARIFY,
            reasons=list(set(reasons)),  # dedupe
            required_fields=list(set(required_fields)),
            clarifying_questions=questions,
        )

    return GateDecision(gate_id="ambiguity_gate", decision=Decision.ACCEPT, reasons=[])


def bounds_gate(spec: TaskSpec) -> GateDecision:
    """
    Check if request is within kernel envelope bounds.

    This is a soft gate - may FALLBACK to different kernel.
    """
    # Placeholder - would check against kernel envelope in registry
    return GateDecision(gate_id="bounds_gate", decision=Decision.ACCEPT, reasons=[])


# --- Gate Runner ---

GATES = {
    "schema_gate": schema_gate,
    "unit_consistency_gate": unit_consistency_gate,
    "ambiguity_gate": ambiguity_gate,
    "bounds_gate": bounds_gate,
}


def run_gates(spec: TaskSpec) -> list[GateDecision]:
    """
    Run all required gates for a TaskSpec.

    Returns list of GateDecision models.
    """
    results = []
    for gate_id in spec.required_gates:
        gate_fn = GATES.get(gate_id)
        if gate_fn:
            decision = gate_fn(spec)
            results.append(decision)

    return results


def get_blocking_decisions(decisions: list[GateDecision]) -> list[GateDecision]:
    """Return only the decisions that block execution."""
    return [d for d in decisions if d.is_blocking()]
