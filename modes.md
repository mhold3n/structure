# Operating Modes

The system operates in distinct modes to balance flexibility with reliability.

## 1. Deterministic Mode (Default)

- **Goal**: High reliability, exact reproducibility.
- **Components**: Pre-defined Kernels, Hard Logic Gates, Regex Policies.
- **Behavior**:
  - Inputs are matched against strict schemas.
  - Calculations are performed by Python kernels (e.g., `scipy`, `numpy`).
  - Failure to match schema results in immediate rejection or clarification request.
  - **No LLM generation** is used for the core result; LLMs may only be used for parsing/formatting under strict constraints.

## 2. Research Mode (Grounded)

- **Goal**: Exploration, hypothesis generation, synthesis of information.
- **Components**: LLM Spec Extractor, Retrieval Augmented Generation (RAG), Soft Gates.
- **Behavior**:
  - Inputs are natural language queries.
  - System retrieves data from authoritative `train` or `dev` indices (never `test`).
  - Responses must be grounded in retrieved context with citations.
  - LLM temperature is low (e.g., 0.2) to minimize hallucination.
  - Output is audited for citations and relevance.

## 3. Creative/Drafting Mode (Restricted)

- **Goal**: Drafting content, formatting reports, paraphrasing.
- **Components**: LLM, Templates.
- **Behavior**:
  - Only allowed for specific "Drafting" or "Formatting" tasks.
  - Higher LLM temperature allowed (e.g., 0.7).
  - Must be clearly labeled as "Generated Content".
  - Gates check for safety and policy violations but are more permissive on structure.

## Switching Modes

Mode selection is determined by the `Router` based on user intent and task type.

- **Explicit**: User can request a specific mode via API (e.g., `mode="deterministic"`).
- **Implicit**: Router classifies intent (e.g., "Calculate..." -> Deterministic, "What is..." -> Research).
