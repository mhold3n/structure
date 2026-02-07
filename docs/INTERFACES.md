# Interfaces (Authoritative Contracts)

## SessionEnvelope (API boundary)

- Fields:
- Allowed values:
- Examples:
- Error model:

## ProblemSpec (LLM output contract)

- Allowed fields only
- Forbidden fields (e.g., dimensions)
- QuantityRef rules (ontology-bound)

## Constraint AST

- Node allowlist
- Domain-specific operator allowlists

## GateDecision

- decision enum
- reasons[] (machine codes)
- required_fields[] for clarify
- fallback routing

## Kernel interface

### Input

- canonical_spec
- feature_vector

### Output

- result_bundle
- uncertainty / validity_flags
- kernel_provenance
