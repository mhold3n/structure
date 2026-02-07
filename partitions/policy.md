# Data Partitioning Policy

To ensure rigorous evaluation and prevent data leakage, all data must be strictly partitioned.

## 1. Partitions

### Train (`indexes/train`)

- **Content**: Data allowed for updating model weights, tuning prompts, or few-shot examples.
- **Access**: Training pipelines, RAG during "Research Mode" (if explicitly allowed).
- **Prohibition**: Never used for evaluation.

### Dev (`indexes/dev`)

- **Content**: Data used for hyperparameter tuning, prompt engineering, and qualitative analysis.
- **Access**: Evaluation pipelines during development.
- **Prohibition**: Never used for final reported metrics.

### Test (`indexes/test`)

- **Content**: Held-out data for final benchmarking.
- **Access**: **Read-only** for final evaluation scripts.
- **Prohibition**:
  - NEVER returned in "Research Mode" retrieval or RAG.
  - NEVER used in prompts during development.
  - NEVER used to select best kernels/models.

## 2. Contamination Control

### Ingestion Gate

All new data ingestion must pass through the `ContaminationDetector`:

1. **Exact Hash**: Check MD5 of document against Test set.
2. **Near-Dedup**: Check MinHash LSH against Test set.
3. **Problem Overlap**: Check for similar problem structures (for math/logic).

If a match is found in `Test`, the data is **rejected** from `Train` and `Dev`.

### Retrieval Gate

Runtime retrieval must explicitly specify the allowed partition.

- `UserQuery` -> defaults to `Train` index.
- `EvalQuery` -> specifies `Dev` or `Test` index.

Querying `Test` index without the `EVAL_MODE=True` flag will raise a `SecurityViolation`.
