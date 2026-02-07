# Compute Kernels

## Kernel registry

- kernel_id format
- compatibility keys (schema, ontology, interface hash)
- determinism_guarantee field
- envelope_version field
- golden_tests references

## Kernel selection algorithm (deterministic)

1)
2)
3)

Tie-break rules:

## Kernel types

- classical
- nn_surrogate
- hybrid (if used)

## Adding a kernel (checklist)

- Implement interface
- Add golden tests
- Declare envelope
- Pass CI gates

## Abstention policy

- When to abstain
- How to report abstention to user (structured)
