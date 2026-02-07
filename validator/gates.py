"""
Gates: Model-agnostic validation gates.

Hard gates: Must pass (schema, units, bounds)
Soft gates: Attach warnings (ambiguity detection)
"""

import json
import re
from typing import Any
from dataclasses import dataclass, asdict

from .loader import load_quantities, load_policy, load_schema


@dataclass
class GateDecision:
    """Structured gate decision output."""
    gate_id: str
    decision: str  # ACCEPT, CLARIFY, REJECT, FALLBACK, ESCALATE
    reasons: list[str]
    required_fields: list[str] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []
    
    def to_dict(self) -> dict:
        return asdict(self)


# --- Gate Implementations ---

def schema_gate(task_plan: dict, request: dict) -> GateDecision:
    """
    Validate request against TaskRequest schema.
    
    This is a hard gate - failure means REJECT.
    """
    # Basic structural validation (simplified - would use jsonschema in production)
    if "user_input" not in request:
        return GateDecision(
            gate_id="schema_gate",
            decision="REJECT",
            reasons=["SCHEMA_INVALID"],
            required_fields=["user_input"]
        )
    
    if not isinstance(request.get("user_input"), str):
        return GateDecision(
            gate_id="schema_gate",
            decision="REJECT",
            reasons=["SCHEMA_INVALID"],
            required_fields=["user_input must be string"]
        )
    
    return GateDecision(
        gate_id="schema_gate",
        decision="ACCEPT",
        reasons=[]
    )


def unit_consistency_gate(task_plan: dict, request: dict) -> GateDecision:
    """
    Check for unit consistency and UCUM compliance.
    
    This is a soft gate - may CLARIFY but not REJECT.
    """
    user_input = request.get("user_input", "")
    
    # Load unit disambiguation policy
    policy = load_policy("unit_disambiguation") or {}
    ambiguous_units = policy.get("ambiguous_units", {})
    
    reasons = []
    required_fields = []
    
    # Check for ambiguous unit strings
    for unit, config in ambiguous_units.items():
        if re.search(rf'\b{unit}\b', user_input, re.IGNORECASE):
            if config.get("action") == "CLARIFY":
                reasons.append("UNIT_AMBIGUOUS")
                required_fields.append("unit_clarification")
    
    if reasons:
        return GateDecision(
            gate_id="unit_consistency_gate",
            decision="CLARIFY",
            reasons=reasons,
            required_fields=required_fields
        )
    
    return GateDecision(
        gate_id="unit_consistency_gate",
        decision="ACCEPT",
        reasons=[]
    )


def ambiguity_gate(task_plan: dict, request: dict) -> GateDecision:
    """
    Detect term collisions and disallowed terms.
    
    This is the main ambiguity detection gate.
    """
    user_input = request.get("user_input", "").lower()
    
    # Load quantities registry
    quantities = load_quantities()
    quantities_list = quantities.get("quantities", [])
    
    # Load unit disambiguation policy
    policy = load_policy("unit_disambiguation") or {}
    disallowed = policy.get("disallowed_without_disambiguator", [])
    
    reasons = []
    required_fields = []
    
    # Check for disallowed terms
    for term in disallowed:
        if term.lower() in user_input:
            reasons.append("DISALLOWED_TERM")
            required_fields.append(f"{term.replace(' ', '_')}_clarification")
    
    # Check for term collisions
    found_aliases = []
    for qty in quantities_list:
        for alias in qty.get("aliases", []):
            if alias.lower() in user_input:
                found_aliases.append({
                    "term": alias,
                    "quantity_id": qty["quantity_id"],
                    "collides_with": qty.get("collides_with", [])
                })
    
    # If any found alias has collisions, require clarification
    for alias_info in found_aliases:
        if alias_info["collides_with"]:
            reasons.append("TERM_COLLISION")
            term = alias_info["term"].replace(" ", "_")
            required_fields.append(f"{term}_disambiguation")
    
    if reasons:
        return GateDecision(
            gate_id="ambiguity_gate",
            decision="CLARIFY",
            reasons=list(set(reasons)),  # dedupe
            required_fields=list(set(required_fields))
        )
    
    return GateDecision(
        gate_id="ambiguity_gate",
        decision="ACCEPT",
        reasons=[]
    )


def bounds_gate(task_plan: dict, request: dict) -> GateDecision:
    """
    Check if request is within kernel envelope bounds.
    
    This is a soft gate - may FALLBACK to different kernel.
    """
    # Placeholder - would check against kernel envelope in registry
    return GateDecision(
        gate_id="bounds_gate",
        decision="ACCEPT",
        reasons=[]
    )


# --- Gate Runner ---

GATES = {
    "schema_gate": schema_gate,
    "unit_consistency_gate": unit_consistency_gate,
    "ambiguity_gate": ambiguity_gate,
    "bounds_gate": bounds_gate,
}


def run_gates(task_plan: dict, request: dict) -> list[dict]:
    """
    Run all required gates for a task plan.
    
    Returns list of GateDecision dicts.
    """
    required_gates = task_plan.get("required_gates", ["schema_gate"])
    
    results = []
    for gate_id in required_gates:
        gate_fn = GATES.get(gate_id)
        if gate_fn:
            decision = gate_fn(task_plan, request)
            results.append(decision.to_dict())
    
    return results
