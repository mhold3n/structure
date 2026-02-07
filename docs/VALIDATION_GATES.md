# Validation Gates

## Gate taxonomy

- **Schema gate** - Validates against JSON Schema
- **Units/dimensions gate** - UCUM parsing + dimensional analysis
- **Completeness gate** - Required fields per domain
- **Ambiguity gate** - Term collisions + disallowed terms
- **Envelope/OOD gate** - Kernel envelope bounds
- **Post-kernel sanity gate** - Output reasonableness checks
- **Citation/groundedness gate** (research) - Source verification

## Reason codes

- Format: `UPPER_SNAKE_CASE`
- Canonical list: `registry/reason_codes.json`

## Decision behavior

| Decision | Meaning | Next Action |
|----------|---------|-------------|
| `ACCEPT` | All gates passed | Proceed to kernel selection |
| `CLARIFY` | Ambiguity detected | Generate clarifying questions from `required_fields[]` |
| `FALLBACK` | Out of envelope | Route to fallback kernel or abstain |
| `ESCALATE` | Sanity check fail | Human review required |
| `REJECT` | Schema/contract violation | Return error, do not proceed |

---

## Ambiguity Gate Algorithm

The ambiguity gate is a **deterministic function** — no LLM, no vibes.

```python
def ambiguity_gate(spec, ontology, policy):
    """
    Deterministic ambiguity detection.
    Returns GateDecision with decision, reasons, required_fields.
    """
    reasons = []
    required_fields = []
    
    for qty in spec.quantities:
        term = qty.get("quantity_id") or qty.get("term")
        unit = qty.get("unit_raw") or qty.get("unit_ucum")
        
        # 1. Check term collision
        candidates = ontology.lookup_by_alias(term)
        if len(candidates) > 1:
            dims = [ontology.get_dimensions(c) for c in candidates]
            if not all_equal(dims):
                reasons.append("TERM_COLLISION")
                required_fields.append(f"{term}_disambiguation")
        
        # 2. Check unit ambiguity
        if unit and unit in policy.ambiguous_units:
            entry = policy.ambiguous_units[unit]
            reasons.append("UNIT_AMBIGUOUS")
            required_fields.append("unit_clarification")
        
        # 3. Check disallowed terms
        if term in policy.disallowed_without_disambiguator:
            reasons.append("DISALLOWED_TERM")
            required_fields.append(f"{term}_clarification")
        
        # 4. UCUM parse check
        if unit and not ucum_parse(unit).success:
            reasons.append("UCUM_PARSE_FAIL")
            required_fields.append("unit_restatement")
    
    if reasons:
        return GateDecision(
            gate_id="ambiguity_gate",
            decision="CLARIFY",
            reasons=reasons,
            required_fields=required_fields
        )
    
    return GateDecision(
        gate_id="ambiguity_gate",
        decision="ACCEPT",
        reasons=[]
    )
```

### Inputs

- `spec`: The ProblemSpec being validated
- `ontology`: Loaded from `registry/quantities.json`
- `policy`: Loaded from `policies/unit_disambiguation.yaml`

### Key behaviors

1. **Term collision**: If a term (e.g., "specific weight") maps to multiple `quantity_id`s with **different dimensions**, emit `CLARIFY`
2. **Unit ambiguity**: If a unit (e.g., "lb") is in `policy.ambiguous_units`, emit `CLARIFY` with the configured question
3. **Disallowed terms**: If a term is in `policy.disallowed_without_disambiguator`, require clarification
4. **UCUM parse failure**: If unit string fails UCUM parse, require restatement

---

## "No hidden constants" rule

### How enforced

- ProblemSpec schema forbids `expression`, `formula`, `equation` fields
- All numeric values must be explicit in `quantities[].value`
- Constants must be declared quantities, not embedded in strings

### Example failure cases

```json
// BAD: Hidden constant in string
{"objective": "calculate force using F = ma where m = 10"}

// GOOD: Explicit quantities
{"quantities": [
    {"quantity_id": "mass", "value": 10, "unit_ucum": "kg"},
    {"quantity_id": "acceleration", "value": 9.81, "unit_ucum": "m/s2"}
]}
```

---

## Gate execution order

1. **Schema gate** (fast fail)
2. **Ambiguity gate** (before LLM spec extraction completes)
3. **Units/dimensions gate**
4. **Completeness gate**
5. **Envelope gate** (after kernel selection)
6. **Post-kernel sanity gate** (after kernel execution)
