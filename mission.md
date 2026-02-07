# Mission & Scope

## In-Scope Tasks

The AI Lab Framework (Hybrid Stack) is designed to orchestrate:

1. **R&D Workflows**: Generating hypotheses, designing experiments, and analyzing results within the defined domains (Experiment, Analysis, Survey, Project, Operations).
2. **Deterministic Calculations**: Performing statistical analysis, power calculations, and other mathematical operations using validated kernels.
3. **Governance & Compliance**: Enforcing safety gates, audit logging, and determinism policies for all operations.
4. **Structured Information Extraction**: Converting unstructured text into structured, schema-validated task specifications without hallucinations.

## Out-of-Scope

1. **Creative Fiction**: The system is not for open-ended creative writing or storytelling.
2. **Unverified Medical Advice**: While it supports experiment design, it does not provide direct clinical diagnosis or treatment recommendations without human oversight.
3. **Arbitrary Code Execution**: Code execution is strictly limited to pre-defined, sandboxed kernels.

## Required Response Properties

1. **Citations**: All assertions must be backed by citations to authoritative sources (where applicable).
2. **Determinism**:
    - **D1 (Strict)**: Same input + same config -> exact same output (e.g., calculations).
    - **D2 (Seeded)**: Same input + same seed -> same output (e.g., simulation, controlled generation).
3. **Latency/Cost**: Operations must fall within defined resource envelopes (e.g., < 2s for classification, < $0.05 per step).

## Tooling Permissions

- **Allowed**: Reading authorized data sources, executing registered kernels, logging to audit trails.
- **Disallowed**: Writing to arbitrary file paths, accessing network endpoints not in the allowlist, modifying system configuration at runtime.
