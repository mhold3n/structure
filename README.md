# R&D Orchestration Topology (Deterministic Kernels + LLM Interface)

## What this is

A framework for reducing LLM variance on technical/scientific tasks by routing through **deterministic gates and kernels**.

- **Goal**: Ambiguity becomes a first-class outcome (CLARIFY), not a guess
- **Non-goals**: Replacing LLMs; handling arbitrary domains without validation

## Core Principle

- **LLMs**: propose / extract / format
- **Deterministic system**: validates / selects / executes / records

Same validated spec → same numeric outputs (D1 determinism)

## Quickstart

```bash
# Prerequisites
python 3.11+
pip install fastapi uvicorn pyyaml

# Run tests
python tests/test_golden_path.py

# Start gateway
uvicorn gateway.main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"user_input": "specific weight of water"}'
# Expected: {"status": "clarify", ...}
```

## Repository Map

```
gateway/          # FastAPI entrypoint, structured logging
router/           # Deterministic task classification
validator/        # Gates consuming policies (schema, units, ambiguity)
kernels/          # Deterministic compute units (units, constants)
registry/         # Kernel registry, quantities, reason codes
schemas/          # JSON Schema contracts
policies/         # YAML policy files
docs/             # Architecture, pipelines, determinism docs
tests/            # Golden path integration tests
```

## Key Files

| File | Purpose |
|------|---------|
| `gateway/main.py` | FastAPI routes: /task, /kernel, /registry |
| `router/classifier.py` | Rule-based domain classification |
| `validator/gates.py` | Schema, unit, ambiguity gates |
| `kernels/units.py` | UCUM unit conversion |
| `kernels/constants.py` | Authoritative physical constants |
| `tests/test_golden_path.py` | Regression tests |

## Safety and Side Effects

- File writes are patch-only and sandboxed (see `docs/FILE_WRITE_POLICY.md`)
- All requests logged as JSONL for audit
- Gates enforce CLARIFY on ambiguous inputs

## Example: Ambiguity Detection

```python
# Input: "What is the specific weight of water?"

# Router detects:
#   domain: physics.fluids
#   ambiguous_terms: ["specific weight"]

# Ambiguity gate returns:
#   decision: CLARIFY
#   reasons: ["TERM_COLLISION", "DISALLOWED_TERM"]
#   required_fields: ["specific_weight_disambiguation"]

# System asks: "Is 'specific weight' weight density (N/m³) or surface tension (N/m)?"
```

## Status

- **Implemented**: Gateway, router, validator, unit/constants kernels
- **In progress**: Additional domain kernels
- **Next**: LLM integration for spec extraction
