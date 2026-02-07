# Pipelines

## Numeric pipeline (D1/D2 compatible)

### Stages

1) Intake
2) Condition
3) Spec extraction (LLM)
4) Validate + canonicalize (deterministic)
5) Kernel select (deterministic)
6) Kernel execute (deterministic)
7) Post-gate checks
8) Report (LLM formatting)
9) Persist run manifest

### Stage gates

- Gate name -> decision -> reason codes -> next action

## Research pipeline

- Local-only vs snapshot mode rules
- Citation gate requirements

## Code / file-modification pipeline

- Patch-only constraint
- Validation + lint/test/static checks
- Release gate + approval
