# Determinism

## Determinism levels

- D1 (Numeric determinism):
- D2 (Full-output determinism):
- NONE:

## Deterministic invariants

- Same canonical_spec_hash -> same kernel_id/version -> same numeric outputs (within policy)

## Prohibited under D1/D2

- Approximate cache matches
- Speculative execution
- Automatic re-running LLM proposal steps
- Non-idempotent retries

## Caching rules

- Cache key definition:
- What is cacheable:
- What is never cacheable:

## CPU/GPU policy

- Allowed modes:
- "Deterministic within tolerance" policy:
- Rounding/canonical formatting rules:
