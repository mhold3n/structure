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


def experiment_safety_gate(spec: TaskSpec) -> GateDecision:
    """
    Check for experiment safety compliance.
    
    Enforces sample size, IRB requirements, and risk levels.
    """
    policy = load_policy("lab_experiment") or {}
    requirements = policy.get("experiment_requirements", {})
    human_subjects = policy.get("human_subjects", {})
    
    reasons = []
    required_fields = []
    questions = []
    decision = Decision.ACCEPT
    
    # Check sample size
    min_n = requirements.get("sample_size", {}).get("minimum", 10)
    args = spec.args or {} # Check extracted args if available
    
    # Note: args might not be populated yet if this gate runs before extraction?
    # Actually gates run on the initialized TaskSpec. args are usually empty at classification time
    # UNLESS we are re-validating after extraction.
    # We should assume this might run on populated spec too.
    
    # Search for sample size in user_input if not in args
    # Naive extraction for safety check if not already extracted
    n_match = re.search(r"sample size.*?(\d+)", spec.user_input, re.IGNORECASE)
    if n_match:
        n = int(n_match.group(1))
        if n < min_n:
            reasons.append(f"Sample size {n} is below minimum {min_n}")
            decision = Decision.WARN
    
    # Check for human subjects keywords
    hs_keywords = ["human", "patient", "participant", "subject", "interview", "survey"]
    is_human_subjects = any(k in spec.user_input.lower() for k in hs_keywords)
    
    if is_human_subjects:
        if human_subjects.get("irb_approval_required"):
            # Check if IRB mentioned
            if "irb" not in spec.user_input.lower():
                reasons.append("IRB_APPROVAL_REQUIRED")
                required_fields.append("irb_protocol_number")
                questions.append("This appears to involve human subjects. Do you have IRB approval?")
                decision = Decision.CLARIFY

    if reasons:
        return GateDecision(
            gate_id="experiment_safety_gate",
            decision=decision,
            reasons=reasons,
            required_fields=required_fields,
            clarifying_questions=questions,
        )
        
    return GateDecision(gate_id="experiment_safety_gate", decision=Decision.ACCEPT, reasons=[])


def file_write_gate(spec: TaskSpec) -> GateDecision:
    """
    Check for disallowed file operations.
    
    Enforces restricted directories and file types.
    """
    policy = load_policy("file_write_policy") or {}
    denied_patterns = policy.get("denied_patterns", [])
    
    # If operation involves writing (checking keywords for now)
    write_keywords = ["save", "write", "export", "dump", "log to"]
    if not any(k in spec.user_input.lower() for k in write_keywords):
        return GateDecision(gate_id="file_write_gate", decision=Decision.ACCEPT, reasons=[])
        
    # Check for restricted patterns in input
    reasons = []
    for pattern in denied_patterns:
        # Simple string check for now (glob matching would be ideal but complex on text)
        clean_pat = pattern.replace("*", "")
        if clean_pat and clean_pat in spec.user_input:
             reasons.append(f"Potential restricted file pattern: {pattern}")
    
    if "secret" in spec.user_input.lower() or "key" in spec.user_input.lower():
         reasons.append("Potential secret exposure")

    if reasons:
        return GateDecision(
            gate_id="file_write_gate",
            decision=Decision.REJECT, # Reject by default for safety
            reasons=reasons,
            required_fields=[],
            clarifying_questions=[],
        )

    return GateDecision(gate_id="file_write_gate", decision=Decision.ACCEPT, reasons=[])


# --- Gate Runner ---

GATES = {
    "schema_gate": schema_gate,
    "unit_consistency_gate": unit_consistency_gate,
    "ambiguity_gate": ambiguity_gate,
    "bounds_gate": bounds_gate,
    "experiment_safety_gate": experiment_safety_gate,
    "file_write_gate": file_write_gate,
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
