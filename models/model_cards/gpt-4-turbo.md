# Model Card: GPT-4 Turbo

## Model Details

- **Name**: GPT-4 Turbo
- **Version**: 2024-04-09
- **Date**: April 2024
- **Organization**: OpenAI

## Intended Use

- **Primary Use Case**: Complex reasoning, code generation, and structured data extraction from unstructured text.
- **Supported Languages**: Multilingual.
- **License**: Proprietary (API Access).

## Factors

- **Performance**: High latency compared to local kernels.
- **Cost**: Significant per-token cost; use sparingly for high-value reasoning, not rote transformation.

## Metrics

- **Context Window**: 128k tokens.
- **Training Data cutoff**: Dec 2023.

## Ethical Considerations

- **Bias**: May exhibit biases present in training data.
- **Safety**: Guardrails enforced by OpenAI, but system-level `policy.safety` gate adds a second layer of defense.

## Caveats and Recommendations

- **Determinism**: NOT strictly deterministic even with `seed` parameter. Use ONLY in "Research Mode" or "Creative Mode".
- **Hallucination**: Can hallucinate citations. ALWAYS verify output with `CitationCheckGate` when using for research.
