# Validation Gates

Validation Gates are the core mechanism for ensuring safety, compliance, and quality in the R&D Orchestration framework.

## Overview

Every task submission and workflow step is evaluated against a set of **Gates**.

- **Soft Gates**: Provide warnings or require additional context/clarification.
- **Hard Gates**: Block execution immediately involved if violated.

## Core Gates

| Gate ID | Type | Description |
| :--- | :--- | :--- |
| `policy.safety` | Hard | Checks for harmful content, PII, and jailbreak attempts. |
| `policy.determinism` | Hard | Enforces deterministic execution rules based on system mode. |
| `quality.clarity` | Soft | Checks if the request is ambiguous or lacks necessary detail. |
| `quality.schema` | Hard | Validates that inputs match the required schema for the selected kernel. |
| `resource.budget` | Hard | Checks if the task exceeds compute/cost budgets. |

## Configuration

Gates are configured via `policies/*.yaml`.

Example `determinism.yaml`:

```yaml
mode: deterministic
allowed_kernels:
  - "stats_v1"
  - "project_v1"
prohibited_terms:
  - "approximate"
  - "guess"
```

## Adding New Gates

To add a new gate:

1. Implement the gate function in `validator/gates.py`.
2. Register it in `validator/loader.py` (or Plugin Registry).
3. Update relevant policies to include the new gate.
