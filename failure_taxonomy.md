# Failure Taxonomy & Mitigation

This document enumerates potential failure modes, their detection mechanisms, and mitigation strategies.

## 1. Retrieval Failures

- **Description**: The system fails to find relevant information in the index.
- **Detector**: `RetrievalScoreGate` (low similarity scores).
- **Mitigation**:
  - **Fallback**: Search broader keywords or fallback to `Research Mode` (if allowed).
  - **Clarification**: Ask user for more specific terms.
  - **Abstain**: "I cannot find information about [Topic] in the authoritative sources."

## 2. Hallucination

- **Description**: The system generates plausible but incorrect information not found in the source.
- **Detector**: `CitationCheckGate` (unsupported claims), `NLI` (Natural Language Inference) check.
- **Mitigation**:
  - **Strict Mode**: Reject response if any claim is unsupported.
  - **Regenerate**: Attempt generation with lower temperature or different prompt.
  - **Flag**: Mark response as "Unverified" (if allowed in mode).

## 3. Schema Violation / Parse Failure

- **Description**: LLM output does not match the required JSON schema.
- **Detector**: `SchemaValidator` (Pydantic validation error).
- **Mitigation**:
  - **Retry**: Pass error message back to LLM for self-correction (up to N retries).
  - **Fallback**: Return partial result or raw text if schema is too strict for flexible input.
  - **Fail**: Hard failure for critical deterministic workflows.

## 4. Policy/Safety Violation

- **Description**: Request violates safety guidelines (e.g., PII, hazardous content).
- **Detector**: `SafetyGate` (keyword match, classifier).
- **Mitigation**:
  - **Block**: Immediate refusal with explanation.
  - **Redact**: Strip sensitive information (if minor).
  - **Escalate**: Log incident for audit.

## 5. Ambiguity

- **Description**: User intent is unclear or maps to multiple domains.
- **Detector**: `AmbiguityGate` (multiple high-confidence domain classifications).
- **Mitigation**:
  - **Clarify**: Ask user to disambiguate (e.g., "Did you mean X or Y?").
  - **Default**: Proceed with most likely intent but flag assumption.

## 6. Latency/Timeout

- **Description**: Operation takes longer than allowed budget.
- **Detector**: `TimeoutGate`.
- **Mitigation**:
  - **Abort**: Cancel operation to free resources.
  - **Async**: Switch to background processing and notify user later.
