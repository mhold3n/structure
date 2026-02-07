# Evaluation Benchmarks

## 1. Grounded QA (`grounded_qa.jsonl`)

- **Metric**: Citation Exact Match, ROUGE-L vs Ground Truth.
- **Source**: `indexes/test`.

## 2. Deterministic Math (`math_ops.jsonl`)

- **Metric**: Numeric Equality (within tolerance).
- **Source**: Synthetic generated problems.

## 3. Tool Usage (`tool_calls.jsonl`)

- **Metric**: Correct Kernel Selection, Valid Argument Types.
- **Source**: Hand-crafted scenarios.
