# R&D Orchestration Topology - Complete System Architecture

## LEGEND

```
  [ ]  module/service (deterministic logic)
  ( )  model (stochastic inference)
  {*}  compute kernel registry
  { }  datastore/cache
  < >  artifact/output
  ===  synchronous control flow
  ---  data payload
  ...  async telemetry/logs
  !!   hard gate (validation/rejection point)
  >>>  side effect boundary (I/O, external calls, persistence)
  ^^^  feedback loop
  |||  parallel execution
  🔒  determinism enforced
  ⚠️   abstention/uncertainty signal
```

---

## ENHANCED R&D ORCHESTRATION TOPOLOGY

```
                              +--------------------------------------+
                              |         USER / CLIENT LAYER          |
                              | chat | CLI | IDE | notebook | API    |
                              +------------------+-------------------+
                                                 |
                                                 |--- request + context + files + metadata
                                                 v
+------------------------------------------------------------------------------------------------------+
| [INGESTION & SESSION LAYER]                                                                          |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [AUTH & RATE LIMITER]  →  [SESSION MANAGER]  →  [REQUEST NORMALIZER]                            │ |
| │ - token validation       - conversation state    - protocol translation                          │ |
| │ - quota enforcement      - context window mgmt   - multimodal parsing                            │ |
| │ - user permissions       - run/session IDs       - attachment extraction                         │ |
| │                                                                                                  │ |
| │ 🔒 DETERMINISM LEVELS (attached to request envelope):                                            │ |
| │                                                                                                  │ |
| │ D1: NUMERIC-DETERMINISTIC (default for R&D)                                                      │ |
| │   - Same validated spec → same kernel_id → same numeric result bundle                            │ |
| │   - LLM prose can vary (spec extraction, formatting)                                             │ |
| │   - Numbers CANNOT vary                                                                          │ |
| │   - Enforce: exact cache, no approx matching, no speculative exec                                │ |
| │                                                                                                  │ |
| │ D2: FULL-OUTPUT-DETERMINISTIC (optional/harder)                                                  │ |
| │   - Same request → identical spec JSON + identical prose output                                  │ |
| │   - Greedy decode (temp=0, top_p=1) for all LLM calls                                            │ |
| │   - Disable all "retry" or "regenerate" loops                                                    │ |
| │   - Frozen random seeds for any sampling                                                         │ |
| │                                                                                                  │ |
| │ Implementation:                                                                                  │ |
| │   - determinism_level: "D1" | "D2" (extracted from request or policy)                            │ |
| │   - if D1: disable stochastic fallbacks in gates, freeze kernel selection                        │ |
| │   - if D2: additionally freeze LLM decode params, disable retries                                │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+---------------------------+------------------------------+------------------------------+--------------+
                            |                              |                              |
                            |... audit trail               |... usage metrics             |... distributed traces
                            v                              v                              v
                    {AUDIT LOG}                    {METRICS STORE}                  {TRACE BACKEND}
                    - who/what/when                - latency/cost                   - Jaeger/OTEL
                    - PII redacted                 - success rates                  - span context
                            |
                            |--- normalized request envelope
                            v
+------------------------------------------------------------------------------------------------------+
| [INTENT ROUTER] 🔒 (DETERMINISTIC RULES-ONLY for v1)                                                 |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [RULE MATCHER] (deterministic)                                                                   │ |
| │ - regex patterns for explicit keywords (calculate, solve, debug, research)                       │ |
| │ - file extension detection (.py, .ipynb, .pdf)                                                   │ |
| │ - schema inference (JSON structure, API specs)                                                   │ |
| │ - domain vocabulary matching from {DOMAIN ONTOLOGY}                                              │ |
| │                                                                                                  │ |
| │ [POLICY SELECTOR] (deterministic)                                                                │ |
| │ - maps domain → pipeline template + tool allowlist + kernel registry access                      │ |
| │ - sets budgets (max tokens, max tool calls, timeout)                                             │ |
| │ - enables/disables features based on determinism_level in {D1,D2}                                │ |
| │ - if determinism_level in {D1,D2}: disable stochastic fallbacks, classifier models               │ |
| │                                                                                                  │ |
| │ FUTURE (v2+): Optional (CLASSIFIER MODEL) for proposal-only mode                                 │ |
| │ - outputs: domain + confidence + secondary domains                                               │ |
| │ - NEVER decides alone; only proposes for deterministic validation                                │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+---------------------------+------------------------------+------------------------------+--------------+
                            |                              |                              |
                numeric/analytical                   research/synthesis            code/infrastructure
                            |                              |                              |
                            v                              v                              v
```

---

## PIPELINE 1: NUMERIC / ANALYTICAL COMPUTATION

```
+------------------------------------------------------------------------------------------------------+
| [PRE-PROCESSING LAYER] 🔒                                                                            |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [CONTENT FILTER] → [SPAN EXTRACTOR] → [CONTEXT ENRICHER]                                        │ |
| │ - unsafe pattern removal  - regex: numbers+units  - {DOMAIN ONTOLOGY} (always)                  │ |
| │ - PII masking             - NER: quantities        - unit definitions (UCUM standard)            │ |
| │ - jailbreak detection     - equation detection     - required-parameter checklist                │ |
| │                                                    - canonical sign conventions                  │ |
| │                                                    - similar problems (toggle-only, didactic)    │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- sanitized text + annotated spans + context
                             v
+------------------------------------------------------------------------------------------------------+
| (LLM: PROBLEM SPECIFICATION EXTRACTOR) - "PROPOSE ONLY, NEVER COMPUTE"                              |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ System Prompt:                                                                                   │ |
| │ "Extract ONLY structured problem specification. Output valid JSON conforming to ProblemSpec     │ |
| │  schema v2. Do NOT solve. Do NOT write equations or code. Do NOT guess missing values.          │ |
| │  Use quantity_ids from provided ontology. Mark unknowns explicitly. Do NOT emit dimensions."    │ |
| │                                                                                                  │ |
| │ Output Schema v2 (TYPED, NO STRING MATH, NO LLM-AUTHORED DIMENSIONS): {                         │ |
| │   "domain_id": "thermo.steady_state | mechanics.rigid_body | ...",  // from ontology             │ |
| │   "problem_type_id": "thermo.heat_transfer.conduction | ...",                                    │ |
| │   "given": [                                                                                     │ |
| │     {                                                                                            │ |
| │       "quantity_id": "thermo.temperature.T1",  // must exist in ontology                         │ |
| │       "value": {"magnitude": 298.15, "uncertainty": null},                                       │ |
| │       "unit": "K"  // UCUM standard, dimension derived by validator                              │ |
| │     }                                                                                            │ |
| │   ],                                                                                             │ |
| │   "unknown": [                                                                                   │ |
| │     {"quantity_id": "thermo.temperature.T2", "constraints_id": ["bounds.physical_temp"]}         │ |
| │   ],                                                                                             │ |
| │   "constraints": [  // TYPED AST, all vars must be QuantityRef                                   │ |
| │     {                                                                                            │ |
| │       "constraint_id": "energy_balance_1",                                                       │ |
| │       "type": "equality | inequality | bound",                                                   │ |
| │       "lhs": {"qref": {"qid": "thermo.heat_flux.q"}},                                            │ |
| │       "op": "eq | lt | gt | le | ge",                                                            │ |
| │       "rhs": {                                                                                   │ |
| │         "mul": [                                                                                 │ |
| │           {"qref": {"qid": "thermo.conductivity.k"}},                                            │ |
| │           {"qref": {"qid": "thermo.grad_T"}}                                                     │ |
| │         ]                                                                                        │ |
| │       },                                                                                         │ |
| │       "expression_human": "q = k * ∇T"  // non-authoritative display only                       │ |
| │     }                                                                                            │ |
| │   ],                                                                                             │ |
| │   "assumptions": [                                                                               │ |
| │     {                                                                                            │ |
| │       "assumption_id": "steady_state",  // from domain enum in ontology                          │ |
| │       "source": "user | system | model",  // explicit provenance                                 │ |
| │       "justification": "User stated 'equilibrium conditions'"                                    │ |
| │     }                                                                                            │ |
| │   ],                                                                                             │ |
| │   "missing_required": ["thermo.conductivity.k"]  // explicit gaps, NO DEFAULTS                  │ |
| │ }                                                                                                │ |
| │                                                                                                  │ |
| │ NOTE: LLM "confidence" is NOT emitted; acceptance is purely deterministic validation             │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- ProblemSpec JSON
                             v
+------------------------------------------------------------------------------------------------------+
| !! [SPECIFICATION VALIDATOR] 🔒 (FULLY DETERMINISTIC GATEKEEPER)                                     |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ STAGE 1: Schema Conformance                                                                      │ |
| │ - JSON validates against ProblemSpec v2 schema                                                   │ |
| │ - all required fields present, correct types                                                     │ |
| │ - quantity_ids exist in {DOMAIN ONTOLOGY}                                                        │ |
| │ - assumption_ids from domain-specific enum in ontology                                           │ |
| │ - ALL constraint AST nodes with qref must reference existing quantity_ids                        │ |
| │                                                                                                  │ |
| │ STAGE 2: Dimension Derivation & Validation (deterministic via Pint/UCUM + ontology)              │ |
| │ - Parse units: UCUM standard only                                                                │ |
| │ - Derive dimension vectors [M,L,T,Θ,N,I,J] from (quantity_id + unit + ontology)                 │ |
| │ - Attach dimensions to canonical spec (NOT from LLM output)                                      │ |
| │ - Validate dimensional consistency in typed constraints                                          │ |
| │ - Check unit compatibility with quantity_id definitions in ontology                              │ |
| │                                                                                                  │ |
| │ STAGE 2.5: AST Operator Allowlist Validation                                                     │ |
| │ - Per-domain allowlist: allowed_ast_nodes: ["add","mul","div","pow","qref","const",...]         │ |
| │ - Reject any unrecognized node type (no silent acceptance)                                       │ |
| │ - Prevents LLM from inventing operators that validator treats as opaque                          │ |
| │                                                                                                  │ |
| │ STAGE 3: Envelope & Range Validation                                                             │ |
| │ - Values within domain envelope (from {KERNEL REGISTRY})                                         │ |
| │ - Detect out-of-distribution: flag ⚠️ extrapolation risk                                         │ |
| │ - Cross-check against {GOLDEN TEST CATALOG}                                                      │ |
| │                                                                                                  │ |
| │ STAGE 4: Completeness & Constraint Validity                                                      │ |
| │ - Degree-of-freedom analysis: #equations vs #unknowns                                            │ |
| │ - Parse typed constraints (no string eval, only AST traversal)                                   │ |
| │ - Check for contradictions (deterministic SAT check if simple)                                   │ |
| │ - Flag missing_required parameters                                                               │ |
| │                                                                                                  │ |
| │ DECISION MATRIX (PURELY DETERMINISTIC - NO LLM CONFIDENCE):                                      │ |
| │ ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │ |
| │ │ ACCEPT        → All stages pass + in-envelope + complete                                  │   │ |
| │ │ CLARIFY       → missing_required params (deterministic error, not retry)                  │   │ |
| │ │ FALLBACK      → Valid + simple + classical kernel exists in registry                      │   │ |
| │ │ REJECT        → Invalid schema OR impossible constraints OR dimension mismatch            │   │ |
| │ │ ABSTAIN       → Out-of-envelope OR contradictions detected                                │   │ |
| │ │ ESCALATE      → Safety-critical domain OR manual assumption approval required             │   │ |
| │ └──────────────────────────────────────────────────────────────────────────────────────────┘   │ |
| │                                                                                                  │ |
| │ CRITICAL: Decision based ONLY on deterministic checks. LLM confidence treated as metadata only.  │ |
| │ NO automatic retry of spec extraction with "stricter prompt" - return deterministic error.       │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------+-------------------+----------------------+-------------------+----------------------------+
           |                   |                      |                   |
       ACCEPT               CLARIFY               FALLBACK           ABSTAIN/ESCALATE
           |                   |                      |                   |
           v                   v                      v                   v
+---------------------+ +-------------------+ +--------------------+ +--------------------------+
| [CANONICALIZER] 🔒  | | (LLM: CLARIFIER)  | | [CLASSICAL SOLVER] | | [HUMAN REVIEW QUEUE]     |
| - convert to SI base| | - generate Qs ONLY| | 🔒 SymPy/SciPy     | | - show spec + flags      |
| - apply conventions | | - NO guesses      | | - exact solutions  | | - approval workflow      |
| - normalize tensor  | | - NO defaults     | | - constraint solver| | - assumption override    |
| - dimension vectors | +-------------------+ | - cite kernel_id   | | - risk assessment        |
| - generate spec_id: |         |              +--------------------+ +--------------------------+
|   canonical_hash =  |         |
|   sha256(spec_json) |         |
|   spec_id = "spec_" |         |
|   + hash[0:12]      |         |
+----------+----------+         |
           |                    |                      |                           |
           |                    v                      |                           |
           |         ^^^ [CLARIFICATION COLLECTOR] 🔒  |                           |
           |             - await user response OR      |                           |
           |             - authoritative tool lookup   |                           |
           |             - NEVER auto-fill defaults    |                           |
           |             - explicit citation required  |                           |
           |                    |                      |                           |
           |                    v                      |                           |
           |         (retry spec extraction with       |                           |
           |          user-provided or tool-sourced    |                           |
           |          values, cite provenance)         |                           |
           |                                           v                           v
           |                                     to [REPORTER] ──────────────> to [REPORTER]
           |                                    (cite: kernel_id + version)
           |
           |--- canonical spec + feature vector
           v
+------------------------------------------------------------------------------------------------------+
| {*} [KERNEL SELECTOR] 🔒 (DETERMINISTIC)                                                             |
| - Query {COMPUTE KERNEL REGISTRY} by domain_id + envelope                                            |
| - Select kernel: classical | nn_surrogate | hybrid                                                   |
| - Verify: determinism_guarantee + golden_tests passed                                                |
| - Compatibility checks (deterministic):                                                              |
|   • schema_version_compat matches spec schema version                                                |
|   • ontology_version_compat matches loaded ontology                                                  |
|   • kernel_interface_hash validates I/O contract                                                     |
| - If multiple compatible candidates: deterministic tiebreak                                          |
|   • Prefer: oldest stable version (proven reliability)                                               |
|   • Fallback: lexicographic kernel_id sort                                                           |
| - Attach: kernel_id + version + interface_hash to result provenance                                  |
+----------------------------+-------------------------------+-------------------------------------------+
           |
           |--- selected kernel_id + metadata
           v
+------------------------------------------------------------------------------------------------------+
| (SOLVER: DOMAIN-SPECIFIC COMPUTE KERNEL) 🔒                                                          |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ Kernel Types:                                                                                    │ |
| │                                                                                                  │ |
| │ A) CLASSICAL (preferred for v1):                                                                 │ |
| │    - SymPy, SciPy, NumPy (deterministic)                                                         │ |
| │    - Closed-form solutions where possible                                                        │ |
| │    - Numerical ODE/PDE solvers with fixed tolerances                                             │ |
| │                                                                                                  │ |
| │ B) NN_SURROGATE (only when envelope + tests exist):                                              │ |
| │    - Frozen ensemble of N models (N=3-5) trained on domain envelope                              │ |
| │    - DETERMINISTIC inference: NO MC-dropout, fixed seeds                                        │ |
| │    - Compute policy (D1 numeric determinism):                                                    │ |
| │      • DEFAULT: CPU-only execution for deterministic reproducibility                             │ |
| │      • GPU allowed only if: deterministic_ops enabled, fixed kernels/algorithms,                 │ |
| │        fp32 precision policy, hardware+driver pinned in provenance                               │ |
| │    - Numeric tolerance: results numerically identical within documented tolerance                │ |
| │      (deterministic rounding rules specified per kernel)                                         │ |
| │    - Quantile regression heads (P10/P50/P90) trained supervised                                  │ |
| │    - OR: ensemble disagreement for epistemic uncertainty                                         │ |
| │                                                                                                  │ |
| │ C) HYBRID:                                                                                       │ |
| │    - Classical + NN correction term                                                              │ |
| │    - Physics-informed architecture with hard constraints                                         │ |
| │                                                                                                  │ |
| │ Inference Contract (deterministic):                                                              │ |
| │ - Input: canonical_spec (typed, validated)                                                       │ |
| │ - Output: {                                                                                      │ |
| │     "y_pred": primary_solution,                                                                  │ |
| │     "uncertainty": {                                                                             │ |
| │       "type": "quantile | ensemble_std | none",                                                  │ |
| │       "p10": value, "p50": value, "p90": value  // if quantile regression                       │ |
| │       "ensemble_disagreement": value  // if ensemble                                             │ |
| │     },                                                                                           │ |
| │     "validity_flags": {                                                                          │ |
| │       "in_training_envelope": bool,                                                              │ |
| │       "extrapolation_risk": "none | low | medium | high",                                        │ |
| │       "convergence_status": "ok | warning | fail"                                                │ |
| │     },                                                                                           │ |
| │     "kernel_id": "thermo.heat_transfer.v1.2.3",                                                  │ |
| │     "compute_trace": {...}  // for reproducibility                                               │ |
| │   }                                                                                              │ |
| │                                                                                                  │ |
| │ ⚠️ ABSTENTION POLICY (hard gate):                                                                │ |
| │ - out-of-envelope → abstain                                                                      │ |
| │ - uncertainty > domain threshold → abstain                                                       │ |
| │ - validity_flags indicate failure → abstain                                                      │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- solution bundle + uncertainty + validity_flags
                             v
+------------------------------------------------------------------------------------------------------+
| !! [SOLUTION VALIDATOR] 🔒 (POST-COMPUTATION HARD GATE)                                              |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ STAGE 1: Physics Invariant Checks (deterministic)                                                │ |
| │ - Domain-specific sanity: no negative absolute temps, pressures, etc.                            │ |
| │ - Conservation laws: energy, mass, momentum balance (where applicable)                           │ |
| │ - Monotonicity: entropy must increase, etc. (domain-dependent)                                   │ |
| │ - Order-of-magnitude: result within expected physical range                                      │ |
| │                                                                                                  │ |
| │ STAGE 2: Uncertainty Threshold Gate                                                              │ |
| │ - Reject if uncertainty > domain-specific tolerance                                              │ |
| │ - Reject if extrapolation_risk = "high"                                                          │ |
| │ - Reject if ensemble_disagreement > threshold (if applicable)                                    │ |
| │                                                                                                  │ |
| │ STAGE 3: Cross-Validation (optional, deterministic only)                                         │ |
| │ - Spot-check against classical solver (if available)                                             │ |
| │ - Compare to {GOLDEN TEST CATALOG} (if input matches known case)                                 │ |
| │ - Ensemble consistency check (if multiple kernels used)                                          │ |
| │ - NO stochastic retries—if failed, reject or escalate                                            │ |
| │                                                                                                  │ |
| │ DECISION (hard gate):                                                                            │ |
| │ - ACCEPT → package result + full metadata + kernel_id + provenance                               │ |
| │ - ABSTAIN → uncertainty too high OR out-of-envelope OR invariant violation                       │ |
| │             return "unable to solve confidently" with reason                                     │ |
| │ - ESCALATE → safety-critical failure OR golden test mismatch                                     │ |
| │                                                                                                  │ |
| │ NO RETRIES with different random seeds or stochastic sampling                                    │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- validated result bundle
                             v
+------------------------------------------------------------------------------------------------------+
| (LLM: RESULT FORMATTER / REPORTER)                                                                   |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ System Prompt:                                                                                   │ |
| │ "You are a technical writer formatting numerical results. You MUST NOT alter any numbers.       │ |
| │  Present the result, uncertainty, assumptions, and methodology. Use LaTeX for equations.         │ |
| │  Cite run_id and spec_id. Explain limitations clearly."                                         │ |
| │                                                                                                  │ |
| │ Inputs:                                                                                          │ |
| │ - validated result bundle (read-only)                                                            │ |
| │ - original problem spec                                                                          │ |
| │ - solver metadata                                                                                │ |
| │                                                                                                  │ |
| │ Output Format:                                                                                   │ |
| │ - Executive summary                                                                              │ |
| │ - Solution with uncertainty bounds                                                               │ |
| │ - Assumptions made                                                                               │ |
| │ - Methodology summary                                                                            │ |
| │ - Limitations & caveats                                                                          │ |
| │ - Provenance (run_id, model version, timestamp)                                                  │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- formatted response
                             v
+------------------------------------------------------------------------------------------------------+
| >>> [ARTIFACT GENERATOR]                                                                             |
| - Create <RESULT.md> with prose explanation                                                          |
| - Create <RESULT.json> with structured data                                                          |
| - Create <RESULT.tex> with equations (optional)                                                      |
| - Attach provenance metadata                                                                          |
| - Store in {ARTIFACT CACHE} keyed by run_id                                                          |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             v
                    <RESULT ARTIFACTS> ──────────────────────────────> to USER
```

---

## PIPELINE 2: RESEARCH / KNOWLEDGE SYNTHESIS

```
+------------------------------------------------------------------------------------------------------+
| [RESEARCH ORCHESTRATOR] (DETERMINISTIC CONTROL)                                                      |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [CORPUS SELECTOR]                                                                                │ |
| │ - Choose sources based on query domain:                                                          │ |
| │   • {LOCAL KNOWLEDGE BASE} - internal docs, papers                                               │ |
| │   • {VECTOR STORE} - embedded technical literature                                               │ |
| │   • {WEB SEARCH} - current information via API                                                   │ |
| │   • {CODE REPOS} - reference implementations                                                     │ |
| │                                                                                                  │ |
| │ [RETRIEVAL STRATEGY]                                                                             │ |
| │ - Hybrid search: dense (embeddings) + sparse (BM25)                                              │ |
| │ - Re-ranking via cross-encoder                                                                   │ |
| │ - Diversity filtering (MMR)                                                                      │ |
| │ - Recency weighting (optional)                                                                   │ |
| │                                                                                                  │ |
| │ [CITATION POLICY]                                                                                │ |
| │ - Every factual claim MUST map to source                                                         │ |
| │ - Track provenance throughout pipeline                                                           │ |
| │ - Enable source link-back                                                                        │ |
| │                                                                                                  │ |
| │ [DETERMINISM SCOPE FOR RESEARCH/WEB]                                                             │ |
| │ - Web search is inherently time-varying (non-deterministic source)                               │ |
| │ - If determinism_level in {D1,D2} and pipeline=research:                                         │ |
| │   • OPTION A (local-only): Disable web search, use only {LOCAL KNOWLEDGE BASE}                  │ |
| │   • OPTION B (snapshot): Snapshot retrieval results with:                                        │ |
| │     - source_payload_hashes (content fingerprint)                                                │ |
| │     - passage_ids (stable identifiers)                                                           │ |
| │     - retrieval_timestamp (ISO 8601)                                                             │ |
| │   • Treat snapshot as canonical corpus for that run                                              │ |
| │ - Without this policy, "deterministic" may incorrectly imply stable research outputs             │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- retrieval queries
                             v
         ┌───────────────────────────────────────────────────────────────────────────┐
         │                    PARALLEL RETRIEVAL EXECUTION                            │
         │                                                                            │
         │  |||  {VECTOR STORE}      |||  {WEB SEARCH API}     |||  {LOCAL CORPUS}   │
         │      - semantic search        - current info            - curated docs     │
         │      - top-k by similarity    - fact verification       - high authority   │
         │                                                                            │
         │       |                           |                          |             │
         │       └───────────────────────────┴──────────────────────────┘             │
         └───────────────────────────────────────┬───────────────────────────────────┘
                                                 |
                                                 |--- retrieved passages + metadata
                                                 v
+------------------------------------------------------------------------------------------------------+
| [PASSAGE PROCESSOR]                                                                                  |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [DOCUMENT PARSER]                                                                                │ |
| │ - PDF → Markdown/JSON (preserve structure)                                                       │ |
| │ - Extract figures, tables, equations                                                             │ |
| │ - OCR for scanned docs                                                                           │ |
| │ - Code extraction with syntax preservation                                                       │ |
| │                                                                                                  │ |
| │ [CHUNKING STRATEGY]                                                                              │ |
| │ - Semantic chunking (not fixed tokens)                                                           │ |
| │ - Preserve section boundaries                                                                    │ |
| │ - Overlap for context continuity                                                                 │ |
| │                                                                                                  │ |
| │ [METADATA ATTACHMENT]                                                                            │ |
| │ - Source URL/DOI                                                                                 │ |
| │ - Author, date, venue                                                                            │ |
| │ - Retrieval score, rank                                                                          │ |
| │ - Document type, section                                                                         │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- structured passages + provenance
                             v
+------------------------------------------------------------------------------------------------------+
| (LLM: RESEARCH SYNTHESIZER) - SINGLE-PASS for v1, MULTI-PHASE optional for deep investigation       |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ DEFAULT MODE (v1): Single Synthesis Pass                                                         │ |
| │                                                                                                  │ |
| │ System Prompt:                                                                                   │ |
| │ "Synthesize findings from provided passages. Every factual claim MUST cite source_id.           │ |
| │  Output structured response with summary, key findings, citation map.                            │ |
| │  Mark any inferences beyond sources as [INFERENCE]. No hallucinated sources."                   │ |
| │                                                                                                  │ |
| │ Output Schema: {                                                                                 │ |
| │   "summary": "2-3 sentence high-level takeaway",                                                 │ |
| │   "key_findings": [                                                                              │ |
| │     {                                                                                            │ |
| │       "claim": "brief statement",                                                                │ |
| │       "source_ids": ["src_1", "src_3"],  // required                                             │ |
| │       "claim_type": "empirical | definition | opinion | synthesis",                              │ |
| │       "confidence": "high | medium | low"  // based on source authority + consensus              │ |
| │     }                                                                                            │ |
| │   ],                                                                                             │ |
| │   "controversies": [  // optional, if conflicting sources exist                                  │ |
| │     {"topic": str, "positions": [str], "sources_per_position": {...}}                           │ |
| │   ],                                                                                             │ |
| │   "knowledge_gaps": [str],  // explicit unknowns                                                 │ |
| │   "citation_map": {"claim_text_hash": ["source_ids"]}  // for validation                        │ |
| │ }                                                                                                │ |
| │                                                                                                  │ |
| │ OPTIONAL: MULTI-STAGE MODE (deep investigation toggle)                                          │ |
| │ - Stage 1: Extract claims with source_ids                                                        │ |
| │ - Stage 2: Reconcile conflicts, assess consensus                                                 │ |
| │ - Stage 3: Build narrative with citation preservation                                            │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- synthesis + citation map
                             v
+------------------------------------------------------------------------------------------------------+
| !! [GROUNDEDNESS & CITATION VALIDATOR] 🔒 (DETERMINISTIC CHECKS)                                     |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ STAGE 1: Citation Completeness (deterministic)                                                   │ |
| │ - Every factual claim in key_findings has source_ids (non-empty)                                 │ |
| │ - No orphaned claims                                                                             │ |
| │ - Citation map complete and valid                                                                │ |
| │                                                                                                  │ |
| │ STAGE 2: Citation Existence (deterministic)                                                      │ |
| │ - All source_ids exist in retrieved passages                                                     │ |
| │ - No hallucinated source references                                                              │ |
| │                                                                                                  │ |
| │ STAGE 3: Inference Labeling (deterministic check)                                                │ |
| │ - Claims marked [INFERENCE] are not counted as grounded facts                                    │ |
| │ - Reasoning steps explicitly documented                                                          │ |
| │                                                                                                  │ |
| │ STAGE 4: NLI Grounding Check (OPTIONAL, can defer to v2)                                         │ |
| │ - Use deterministic NLI model to check claim↔source entailment                                   │ |
| │ - Flag misalignment for human review                                                             │ |
| │ - v1: skip this, rely on citation completeness only                                              │ |
| │                                                                                                  │ |
| │ DECISION:                                                                                        │ |
| │ - ACCEPT → all required citations present, no hallucinated sources                               │ |
| │ - REJECT → missing citations OR fake sources → return error, do NOT revise automatically        │ |
| │ - ESCALATE → suspicious pattern (too many inferences, controversial topic)                       │ |
| │                                                                                                  │ |
| │ NO automatic re-synthesis with "stricter requirements"—that's nondeterministic                   │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- validated synthesis
                             v
+------------------------------------------------------------------------------------------------------+
| >>> [REPORT GENERATOR]                                                                               |
| - Format as Markdown with inline citations                                                           |
| - Generate bibliography                                                                               |
| - Add "Confidence" and "Gaps" sections                                                                |
| - Create optional interactive artifact (if complex)                                                   |
| - Store in {ARTIFACT CACHE}                                                                          |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             v
                    <RESEARCH_REPORT.md> + <BIBLIOGRAPHY.bib> ────────────> to USER
```

---

## PIPELINE 3: CODE / INFRASTRUCTURE MODIFICATION

```
+------------------------------------------------------------------------------------------------------+
| [CODE TASK PLANNER] (DETERMINISTIC SCAFFOLDING)                                                      |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [REPO ANALYZER]                                                                                  │ |
| │ - Scan repository structure                                                                      │ |
| │ - Identify language(s), framework(s)                                                             │ |
| │ - Detect test framework, linter config                                                           │ |
| │ - Build dependency graph                                                                         │ |
| │                                                                                                  │ |
| │ [PERMISSION MAPPER]                                                                              │ |
| │ - Allowlist: editable directories/files                                                          │ |
| │ - Denylist: system files, secrets, .git/                                                         │ |
| │ - Max diff size limits                                                                           │ |
| │ - Require approval for: production code, config files, migrations                                │ |
| │                                                                                                  │ |
| │ [TOOL SELECTOR]                                                                                  │ |
| │ - Choose linters (pylint, eslint, etc.)                                                          │ |
| │ - Select test runner (pytest, jest, etc.)                                                        │ |
| │ - Enable static analyzers (mypy, TypeScript, etc.)                                               │ |
| │ - Configure security scanners (bandit, semgrep)                                                  │ |
| │                                                                                                  │ |
| │ [WORKSPACE SETUP]                                                                                │ |
| │ - Create isolated sandbox (container/VM)                                                         │ |
| │ - Clone repository to sandbox                                                                    │ |
| │ - Install dependencies                                                                           │ |
| │ - Never touch production/main branch directly                                                    │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- task spec + repo context + constraints
                             v
+------------------------------------------------------------------------------------------------------+
| (LLM: CODE UNDERSTANDING & PLANNING)                                                                 |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ STAGE 1: Context Building                                                                        │ |
| │ - Read relevant files (smart file selection)                                                     │ |
| │ - Understand existing patterns, conventions                                                      │ |
| │ - Identify dependencies & side effects                                                           │ |
| │                                                                                                  │ |
| │ STAGE 2: Change Planning                                                                         │ |
| │ - Decompose task into atomic changes                                                             │ |
| │ - Identify files to modify/create                                                                │ |
| │ - Plan test additions/modifications                                                              │ |
| │ - Consider backward compatibility                                                                │ |
| │                                                                                                  │ |
| │ Output: {                                                                                        │ |
| │   "plan": [{"file": str, "operation": "modify|create|delete", "rationale": str}],               │ |
| │   "dependencies": [str],  // other files that might be affected                                  │ |
| │   "tests_needed": [str],                                                                         │ |
| │   "risk_assessment": str                                                                         │ |
| │ }                                                                                                │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- change plan
                             v
+------------------------------------------------------------------------------------------------------+
| (LLM: PATCH GENERATOR)                                                                               |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ System Prompt:                                                                                   │ |
| │ "Generate ONLY unified diff format patches. Do not directly write files.                        │ |
| │  Follow existing code style. Add comments for complex logic.                                     │ |
| │  Include test cases for new functionality."                                                      │ |
| │                                                                                                  │ |
| │ Constraints:                                                                                     │ |
| │ - One logical change per patch                                                                   │ |
| │ - Preserve existing formatting where unchanged                                                   │ |
| │ - No credentials or secrets in code                                                              │ |
| │ - Include docstrings/comments                                                                    │ |
| │                                                                                                  │ |
| │ Output: <PATCH.diff> in unified diff format                                                      │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- <PATCH.diff> + metadata
                             v
+------------------------------------------------------------------------------------------------------+
| !! [PATCH VALIDATOR] 🔒 (PRE-APPLICATION GATEKEEPER)                                                 |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ STAGE 1: Path Security                                                                           │ |
| │ - All paths in allowlist                                                                         │ |
| │ - No path traversal (../, symlinks)                                                              │ |
| │ - No system/config file modifications without approval                                           │ |
| │                                                                                                  │ |
| │ STAGE 2: Content Security                                                                        │ |
| │ - Secret scanner (detect API keys, passwords, tokens)                                            │ |
| │ - Dangerous pattern detection (eval, exec, SQL injection vectors)                                │ |
| │ - License compliance (no proprietary code injection)                                             │ |
| │                                                                                                  │ |
| │ STAGE 3: Size & Scope Limits                                                                     │ |
| │ - Diff size within limits                                                                        │ |
| │ - Number of files within limits                                                                  │ |
| │ - Complexity metrics (cyclomatic, nesting depth)                                                 │ |
| │                                                                                                  │ |
| │ STAGE 4: Syntax & Schema Validation                                                              │ |
| │ - Parse as valid diff format                                                                     │ |
| │ - For config files: validate against schema (JSON Schema, etc.)                                  │ |
| │ - For structured files: check well-formedness                                                    │ |
| │                                                                                                  │ |
| │ DECISION:                                                                                        │ |
| │ - ACCEPT → proceed to sandbox                                                                    │ |
| │ - REJECT → explain violation, request revision                                                   │ |
| │ - ESCALATE → requires human approval (sensitive paths, large changes)                            │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             | ACCEPT
                             v
+------------------------------------------------------------------------------------------------------+
| >>> [SANDBOX EXECUTOR]                                                                               |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ - Apply patch in isolated environment (Docker/VM)                                                │ |
| │ - No network access (or heavily restricted)                                                      │ |
| │ - Filesystem isolation                                                                           │ |
| │ - Resource limits (CPU, memory, time)                                                            │ |
| │ - Capture all outputs (stdout, stderr, file changes)                                             │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- modified codebase in sandbox
                             v
         ┌───────────────────────────────────────────────────────────────────────────┐
         │                    PARALLEL VALIDATION PIPELINE                            │
         │                                                                            │
         │  |||                    |||                    |||                         │
         │  [LINTER]            [TEST RUNNER]         [STATIC ANALYZER]               │
         │  - style check       - unit tests          - type checker                  │
         │  - code smell        - integration tests   - dataflow analysis             │
         │  - complexity        - coverage report     - unused code                   │
         │                                                                            │
         │  |||                                                                       │
         │  [SECURITY SCANNER]                                                        │
         │  - dependency vulnerabilities (Snyk, Safety)                               │
         │  - SAST (Semgrep, Bandit)                                                  │
         │  - secret leakage check                                                    │
         │                                                                            │
         │       |                    |                    |             |            │
         │       └────────────────────┴────────────────────┴─────────────┘            │
         └───────────────────────────────────┬───────────────────────────────────────┘
                                             |
                                             |... all results
                                             v
+------------------------------------------------------------------------------------------------------+
| [RESULT AGGREGATOR]                                                                                  |
| - Collect outputs from all validators                                                                |
| - Categorize issues (error, warning, info)                                                           |
| - Generate diff summary                                                                              |
| - Compute quality metrics (coverage delta, complexity delta)                                         |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             |--- validation report
                             v
+------------------------------------------------------------------------------------------------------+
| !! [RELEASE GATE] (PRE-MERGE GATEKEEPER)                                                             |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ CRITERIA FOR AUTO-APPROVAL:                                                                      │ |
| │ - All tests pass (no regressions)                                                                │ |
| │ - No linter errors                                                                               │ |
| │ - No security vulnerabilities introduced                                                         │ |
| │ - Coverage not decreased (or within tolerance)                                                   │ |
| │ - Static analysis clean (or only warnings)                                                       │ |
| │ - Change size below auto-approve threshold                                                       │ |
| │                                                                                                  │ |
| │ REQUIRE HUMAN REVIEW IF:                                                                         │ |
| │ - Test failures                                                                                  │ |
| │ - Security issues detected                                                                       │ |
| │ - Large/complex changes                                                                          │ |
| │ - Touching critical paths (auth, payments, etc.)                                                 │ |
| │ - Breaking API changes                                                                           │ |
| │                                                                                                  │ |
| │ OPTIONAL: (LLM: CODE REVIEWER)                                                                   │ |
| │ - Generate risk assessment summary                                                               │ |
| │ - Identify potential edge cases                                                                  │ |
| │ - Suggest improvements                                                                           │ |
| │ - Explain changes in natural language                                                            │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             | APPROVE (or HUMAN APPROVES)
                             v
+------------------------------------------------------------------------------------------------------+
| >>> [COMMIT & INTEGRATION]                                                                           |
| ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ |
| │ [PR CREATOR]                                                                                     │ |
| │ - Create pull request with:                                                                      │ |
| │   • Descriptive title & summary                                                                  │ |
| │   • Link to original task/ticket                                                                 │ |
| │   • Validation results attached                                                                  │ |
| │   • Auto-generated changelog entry                                                               │ |
| │                                                                                                  │ |
| │ [COMMIT WRITER]                                                                                  │ |
| │ - Conventional commit format                                                                     │ |
| │ - Sign commits (GPG)                                                                             │ |
| │ - Reference issue/ticket numbers                                                                 │ |
| │                                                                                                  │ |
| │ AUDIT TRAIL:                                                                                     │ |
| │ - Who approved (human or auto)                                                                   │ |
| │ - Validation reports                                                                             │ |
| │ - Model versions used                                                                            │ |
| │ - Timestamp, run_id                                                                              │ |
| └─────────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------+-------------------------------+-------------------------------------------+
                             |
                             v
                    <PR / COMMIT> + <CHANGELOG> + <VALIDATION_REPORT> ──────> to USER / VCS
```

---

## CROSS-CUTTING INFRASTRUCTURE

### {*} [COMPUTE KERNEL REGISTRY] 🔒 (DETERMINISTIC CATALOG)

**Purpose**: Bridge between LLM specification and deterministic compute. The LLM never sees implementation details, only kernel interfaces.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {KERNEL CATALOG SCHEMA}                                                                          │
│                                                                                                  │
│ kernel_id: "thermo.heat_transfer.conduction.v1.2.3"                                              │
│ domain_id: "thermo.heat_transfer"                                                                │
│ problem_type_id: "steady_state.conduction"                                                       │
│ schema_version: "2.0"                                                                            │
│ schema_version_compat: ["2.0", "2.1"]  // which ProblemSpec versions supported                   │
│ ontology_version: "thermo_v3.1.0"                                                                │
│ ontology_version_compat: ["3.0.0", "3.1.x"]                                                      │
│ kernel_interface_hash: "sha256:abc123..."  // deterministic I/O contract validation              │
│ envelope: {                                                                                      │
│   "temperature": {"min": 0, "max": 5000, "unit": "K"},                                           │
│   "conductivity": {"min": 0.01, "max": 1000, "unit": "W/(m*K)"},                                 │
│   ...                                                                                            │
│ }                                                                                                │
│ implementation_type: "classical | nn_surrogate | hybrid"                                         │
│ implementation_path: "kernels/thermo/heat_transfer_v1_2_3.py"                                    │
│ determinism_guarantee: true | false                                                              │
│ uncertainty_type: "none | quantile | ensemble"                                                   │
│ golden_tests: {                                                                                  │
│   "test_suite_id": "thermo_golden_v1",                                                           │
│   "num_tests": 47,                                                                               │
│   "pass_rate": 1.0,                                                                              │
│   "last_validated": "2026-02-06T21:30:00Z"                                                       │
│ }                                                                                                │
│ created_at: "2025-11-15T10:30:00Z"                                                               │
│ deprecated: false                                                                                │
│ successor_id: null | "kernel_id"  // if deprecated                                               │
│                                                                                                  │
│ INTERFACE CONTRACT:                                                                              │
│ - input_schema: ProblemSpec v2 (typed, no string math, ontology-bound QuantityRef)               │
│ - output_schema: SolutionBundle (y_pred, uncertainty, validity_flags, provenance)                │
│ - guarantees: determinism, envelope coverage, golden test passage                                │
│                                                                                                  │
│ VERSIONING:                                                                                      │
│ - Semantic versioning: MAJOR.MINOR.PATCH                                                         │
│ - Breaking changes (interface/schema) → new MAJOR version                                        │
│ - Envelope expansion → MINOR version                                                             │
│ - Bug fixes → PATCH version                                                                      │
│ - All versions immutable once deployed                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Operations**:

- `query_kernel(domain_id, envelope) → kernel_id + metadata`
- `validate_input(kernel_id, spec) → in_envelope: bool`
- `get_kernel_interface(kernel_id) → input/output schemas`
- `register_kernel(metadata, tests) → kernel_id` (admin only)
- `deprecate_kernel(kernel_id, successor_id)` (admin only)

**Governance**:

- New kernels require: golden tests passed + human approval + envelope documentation
- Classical kernels preferred for v1 (SymPy, SciPy, NumPy)
- NN surrogates only when: envelope defined + tests exist + determinism verified

---

### [POLICY ENGINE] (CENTRALIZED GOVERNANCE)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {POLICY DEFINITIONS}                                                                             │
│ - user_id → role → permissions mapping                                                           │
│ - resource budgets (tokens, API calls, compute time)                                             │
│ - rate limits per user/team/org                                                                  │
│ - allowed tools per pipeline                                                                     │
│ - data retention policies                                                                        │
│ - geographic restrictions                                                                        │
│                                                                                                  │
│ ENFORCEMENT:                                                                                     │
│ - Checked at every gate                                                                          │
│ - Circuit breaker for quota exhaustion                                                           │
│ - Kill switches per tool/model                                                                   │
│ - Escalation workflows                                                                           │
│                                                                                                  │
│ AUDIT:                                                                                           │
│ - Log all policy checks                                                                          │
│ - Alert on violations                                                                            │
│ - Generate compliance reports                                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### [OBSERVABILITY & MONITORING]

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {STRUCTURED LOGGING}                                                                             │
│ - All prompts (PII-redacted)                                                                     │
│ - Tool calls with parameters                                                                     │
│ - Gate decisions + rationale                                                                     │
│ - Model outputs (truncated if large)                                                             │
│ - Timing breakdowns per stage                                                                    │
│                                                                                                  │
│ {METRICS COLLECTION}                                                                             │
│ - Latency (p50, p95, p99) per pipeline stage                                                     │
│ - Token usage & cost attribution                                                                 │
│ - Success/failure rates                                                                          │
│ - Gate rejection rates + reasons                                                                 │
│ - User satisfaction (thumbs up/down)                                                             │
│                                                                                                  │
│ {DISTRIBUTED TRACING}                                                                            │
│ - OpenTelemetry integration                                                                      │
│ - Trace context propagation                                                                      │
│ - Span annotations for gates, models, tools                                                      │
│ - Dependency mapping                                                                             │
│                                                                                                  │
│ DASHBOARDS:                                                                                      │
│ - Real-time pipeline health                                                                      │
│ - Cost tracking                                                                                  │
│ - Error rate trends                                                                              │
│ - Model performance over time                                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### [MODEL REGISTRY & VERSIONING]

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {MODEL CATALOG}                                                                                  │
│ - model_id → weights, config, metadata                                                           │
│ - version tags (production, staging, experimental)                                               │
│ - performance benchmarks                                                                         │
│ - training data provenance                                                                       │
│                                                                                                  │
│ DEPLOYMENT:                                                                                      │
│ - A/B testing framework                                                                          │
│ - Canary deployments                                                                             │
│ - Rollback capability                                                                            │
│ - Blue-green model swaps                                                                         │
│                                                                                                  │
│ REPRODUCIBILITY:                                                                                 │
│ - Every result tagged with model_version                                                         │
│ - Immutable model artifacts                                                                      │
│ - Environment snapshots                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### [FEEDBACK & CONTINUOUS IMPROVEMENT]

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {FEEDBACK STORE}                                                                                 │
│ - Explicit: thumbs up/down, ratings, comments                                                    │
│ - Implicit: edits to outputs, re-runs, abandonment                                               │
│ - Expert corrections (for supervised fine-tuning)                                                │
│                                                                                                  │
│ ANALYSIS:                                                                                        │
│ - Identify failure patterns                                                                      │
│ - Detect model drift                                                                             │
│ - Find edge cases for training data augmentation                                                 │
│ - Measure inter-annotator agreement for ambiguous cases                                          │
│                                                                                                  │
│ IMPROVEMENT LOOPS:                                                                               │
│ ^^^ Gate threshold tuning based on precision/recall                                              │
│ ^^^ Prompt refinement based on failure analysis                                                  │
│ ^^^ Model retraining pipeline triggered by performance degradation                               │
│ ^^^ Policy updates based on abuse patterns                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### [CACHING & PERFORMANCE OPTIMIZATION]

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ {RESULT CACHE}                                                                                   │
│                                                                                                  │
│ DETERMINISM-AWARE CACHING:                                                                       │
│                                                                                                  │
│ IF determinism_level = D1 (numeric-deterministic):                                              │
│   - Exact hash keying: hash(canonical_spec + kernel_id + kernel_version + pipeline_config)      │
│   - NO approximate/probabilistic cache matching                                                  │
│   - TTL: long (results are reproducible)                                                         │
│   - Cache hit → return with provenance metadata                                                  │
│                                                                                                  │
│ IF determinism_level = D2 (full-output-deterministic):                                          │
│   - Additionally hash: LLM model version + decode params (temp, top_p, seed)                     │
│   - Exact match required for prose outputs                                                       │
│                                                                                                  │
│ IF determinism_level = NONE (not R&D default):                                                   │
│   - Probabilistic cache allowed (approximate matching for similar queries)                       │
│   - Shorter TTL for time-sensitive domains                                                       │
│                                                                                                  │
│ {EMBEDDING CACHE}                                                                                │
│ - Reuse vector embeddings for identical text (deterministic lookup)                              │
│                                                                                                  │
│ OPTIMIZATION STRATEGIES (DETERMINISM-GATED):                                                     │
│                                                                                                  │
│ Always allowed:                                                                                  │
│ - Batching for vector operations                                                                 │
│ - Early termination for impossible specs (deterministic rejection)                               │
│ - Model distillation for frequent simple queries (if deterministic)                              │
│                                                                                                  │
│ Disabled when determinism_level = D1 or D2:                                                      │
│ - ❌ Speculative execution (can change outcomes)                                                 │
│ - ❌ Approximate cache matching (can return wrong result)                                        │
│ - ❌ Stochastic query expansion                                                                  │
│                                                                                                  │
│ CRITICAL: Cache invalidation on kernel version update or ontology change                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### [SECURITY & PRIVACY]

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DATA PROTECTION:                                                                                 │
│ - PII detection & redaction in logs                                                              │
│ - Encryption at rest (artifacts, logs)                                                           │
│ - Encryption in transit (TLS)                                                                    │
│ - Data retention limits                                                                          │
│                                                                                                  │
│ ACCESS CONTROL:                                                                                  │
│ - RBAC for all resources                                                                         │
│ - API key rotation                                                                               │
│ - Session timeout enforcement                                                                    │
│                                                                                                  │
│ THREAT MITIGATION:                                                                               │
│ - Prompt injection detection                                                                     │
│ - Rate limiting (per user/IP)                                                                    │
│ - DDoS protection                                                                                │
│ - Sandboxing for code execution                                                                  │
│ - Input sanitization                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## FAILURE & RECOVERY STRATEGIES

### [GRACEFUL DEGRADATION]

- Model unavailable → fallback to simpler model or deterministic solver
- External API down → use cached results or internal alternatives
- Quota exceeded → queue request or suggest optimization
- Ambiguous input → clarify rather than guess

### [ERROR HANDLING HIERARCHY]

1. **RETRY** with backoff (transient network errors)
2. **FALLBACK** to alternative (model failure)
3. **CLARIFY** with user (ambiguous input)
4. **REJECT** with explanation (impossible request)
5. **ESCALATE** to human (safety concern, out-of-scope)

### [CIRCUIT BREAKER PATTERN]

- Monitor failure rates per component
- Open circuit after threshold failures (stop sending traffic)
- Half-open state for recovery testing
- Auto-recovery when success rate restored

---

## RECOMMENDED PROJECT-DEFAULT TOPOLOGY (R&D v1)

For R&D scope with deterministic gates and LLM-as-proposer architecture:

### Control Plane

- **Type**: Hybrid Deterministic Pipeline (C3)
- **Router**: Rules-only (deterministic)
- **Gates**: All validation stages deterministic
- **Kernels**: Classical first (SymPy/SciPy), NN per-domain only when envelope + tests exist

### Agent Architecture

- **Type**: Specialist Split (A2) with optional Evaluator (A4)
- **LLM Role**: Propose specifications, synthesize findings, generate code diffs
- **Deterministic Role**: Validate, execute, gate all side effects

### Governance

- **Type**: Authority Ladder (G3) with Write Gates
- **LLM Authority**: Propose only, never execute
- **Gate Authority**: Hard validation, rejection, escalation to human
- **Write Boundary**: All file/state modifications behind explicit approval gates

### Memory & Context

- **Type**: Vector + Governed Memory (M3 + M4)
- **Domain Ontology**: Required for spec extraction (with quantity_ids, dimension definitions)
- **Kernel Registry**: Required for deterministic compute (with compatibility metadata)
- **Citation Tracking**: Required for research synthesis

### Deployment Scale

- **v1 Start**: Single-node (D1)
  - Single API gateway
  - Single router instance
  - 1 GPU worker (or CPU-only for classical kernels)
  - Optional tool sandbox container
- **Scale to v2**: Two-tier (D2) only when:
  - Schemas are stable
  - Eval harness exists and passes
  - Repeat workloads justify optimization
- **Avoid**: Enterprise topology (load balancers, pools, sharding) until apparatus is stable

### Determinism Enforcement

- **Default Level**: D1 (Numeric-Deterministic)
  - Same validated spec → same kernel → same numeric result
  - LLM prose variation allowed (spec extraction, formatting)
  - Exact cache keying (no approximate matching)
  - No speculative execution
- **Optional Level**: D2 (Full-Output-Deterministic)
  - Additionally: greedy decode (temp=0), frozen LLM outputs
  - Use only when reproducible prose is required
- **Seed Freezing**: All random operations frozen
- **No Stochastic Retries**: No re-sampling on failure
- **Abstention Policy**: Explicit "unable to solve confidently" preferred over low-confidence guesses

---

## DEPLOYMENT TOPOLOGY

### v1: Single-Node (R&D Start)

```
                    [API GATEWAY]
                         |
            +------------+------------+
            |            |            |
      [ROUTER 🔒]  [COMPUTE]    [STORAGE]
      rules-only    - Classical      - {KERNEL REGISTRY}
                    - Optional GPU    - {DOMAIN ONTOLOGY}
                    - Sandbox         - {ARTIFACT CACHE}
                                      - Audit/Metrics
```

### v2: Two-Tier (Stable Workloads)

```
              [LOAD BALANCER]
                    |
        +-----------+-----------+
        |                       |
   [Gateway 1]            [Gateway 2]
        |                       |
    +-------+---------------+-------+
    |       |               |       |
[Router] [Compute]      [Storage] [Tools]
  Pool    Workers        Layer     Sandbox
```

### Future: Multi-Tier (Only After Eval Harness Stable)

```
                              [LOAD BALANCER]
                                    |
                +-------------------+-------------------+
                |                   |                   |
          [API Gateway 1]     [API Gateway 2]     [API Gateway 3]
                |                   |                   |
        +-----------------+-----------------+-----------------+
        |                 |                 |                 |
  [Router Pool]    [Model Inference]  [Tool Execution]  [Storage Layer]
  - stateless      - GPU workers      - sandboxes        - distributed
  - horizontal     - batching         - isolated         - replicated
    scaling        - kernel cache     - resource limits  - sharded
                              |
                +-------------+-------------+
                |             |             |
          [Vector DB]   [Relational]   [Object Store]
          - ANN index   - metadata     - artifacts
          - embeddings  - audit log    - large files
```

**Scaling Decision Criteria**:

- ✅ Scale when: schemas stable, eval harness passing, repeat workloads, performance bottlenecks identified
- ❌ Don't scale: to optimize before apparatus is proven, for hypothetical future load

---

## KEY DESIGN PRINCIPLES

### 1. DETERMINISM AS FIRST-CLASS CONCERN 🔒

- **Two levels defined**:
  - **D1 (Numeric-Deterministic)**: Same validated spec → same kernel_id → same numeric result bundle. LLM prose can vary. **DEFAULT for R&D.**
  - **D2 (Full-Output-Deterministic)**: Same request → identical spec JSON + identical prose. Greedy decode (temp=0), no retries.
- Enforcement: frozen seeds, fixed ensembles
- GPU determinism (D1 numeric):
  - Default to CPU-only execution for numeric kernels
  - GPU allowed only if: deterministic_ops enabled, fixed kernels, fp32 precision, hardware+driver pinned
  - Define tolerance: numerically identical within documented tolerance, deterministic rounding
- Exact cache only (no approximate matching under D1/D2)
- No speculative execution under determinism mode
- Abstention preferred over nondeterministic "best guess"

### 2. LLM PROPOSES, GATES DISPOSE

- **LLMs**: Extract specs, synthesize findings, generate code, format results
- **Deterministic Gates**: Validate, reject, execute, enforce physics
- **LLM confidence is metadata only** — never used in gate decisions
- **Never**: Allow LLM to perform math, compute dimensions, execute code, or make final decisions
- Clear separation: stochastic proposal vs deterministic execution

### 3. NO STRINGLY-TYPED MATH

- Constraints as typed AST with QuantityRef nodes (ontology-bound)
- All `qid` references must exist in {DOMAIN ONTOLOGY}
- Dimension vectors derived deterministically by validator (not from LLM)
- UCUM standard for units, parsed deterministically via Pint
- Human-readable expressions for display only (non-authoritative)

### 4. DEFENSE IN DEPTH

- Multiple validation stages (pre-spec, post-spec, post-solution)
- Principle of least privilege (minimal tool access)
- Fail-safe defaults (reject when uncertain, abstain when out-of-envelope)
- Explicit provenance for everything:
  - Values: value_source + source_ref (user | tool, with message_id/doc_id/tool_call_id)
  - Results: kernel_id + version + interface_hash + run_id
  - Citations: source_ids for every factual claim

### 5. OBSERVABILITY & REPRODUCIBILITY

- Every result tagged with: kernel_id + version + determinism_level + run_id + timestamp
- Full audit trail: who approved, what was validated, which gates triggered
- Golden test catalog for regression detection
- Immutable kernel versions with compatibility metadata (schema_version_compat, ontology_version_compat, kernel_interface_hash)

### 6. HUMAN IN THE LOOP (WHEN NEEDED)

- Escalation paths for: uncertainty, out-of-envelope, safety-critical, assumption approval
- Override mechanisms with explicit justification + audit trail
- Explicit approval gates for: file writes, production changes, high-stakes compute
- No automatic retry with "stricter prompts"—return deterministic errors

### 7. RIGHT-SIZED FOR R&D

- Start simple: rules-only router, single-node deployment, classical kernels
- Add complexity only when: schemas stable, tests passing, workloads proven
- Avoid premature optimization: no load balancers before load exists
- Prefer classical deterministic solvers over NN surrogates until envelope proven

### 8. GRACEFUL FAILURE & ABSTENTION

- Never crash, always explain why (with provenance)
- Abstention is a valid output: "unable to solve confidently because..."
- Fallbacks only if deterministic (no stochastic retry loops)
- User agency preserved: suggest, don't dictate; show uncertainty, don't hide it

---

## APPENDIX: COMPONENT REFERENCE

### Models (Stochastic Components - PROPOSE ONLY)

- **Spec Extractor**: Converts natural language → structured ProblemSpec (typed, no string math)
- **Clarifier**: Generates questions for missing parameters (no auto-fill defaults)
- **Research Synthesizer**: Extracts claims + synthesizes with mandatory citations
- **Code Planner**: Analyzes repositories and plans atomic changes
- **Patch Generator**: Creates unified diffs (no direct file writes)
- **Result Formatter**: Converts validated results to human-readable prose (no number modification)

**LLM Contract**: Propose, extract, synthesize, explain — NEVER compute, execute, or decide

### Gates (Deterministic Validators - DISPOSE/ENFORCE)

- **Specification Validator**: Schema conformance + dimensional analysis + envelope check + DOF analysis
- **Solution Validator**: Physics invariants + uncertainty threshold + cross-validation against golden tests
- **Citation Validator**: Completeness + existence + (optional) NLI grounding
- **Patch Validator**: Security scan + path allowlist + size limits + schema validation
- **Release Gate**: Test passage + lint clean + security clear + approval workflow

**Gate Contract**: Validate, reject, abstain, escalate — NEVER modify or "heal" inputs

### Deterministic Tools & Kernels 🔒

- **Kernel Selector**: Queries {KERNEL REGISTRY} by domain_id + envelope, returns kernel_id
- **Classical Solvers**: SymPy (symbolic), SciPy (numerical), NumPy (linear algebra)
- **NN Surrogates**: Frozen ensembles with quantile heads OR ensemble disagreement (NO MC-dropout)
- **Canonicalizer**: SI unit conversion + sign convention + dimension vector computation
- **Linter/Tester/Analyzer**: Code quality gates (deterministic checks only)

**Tool Contract**: Deterministic execution, explicit provenance, abstention on failure

### Datastores & Registries

- **{KERNEL REGISTRY}**: Catalog of compute kernels with envelope + tests + determinism guarantee + compatibility metadata
- **{DOMAIN ONTOLOGY}**: Quantity IDs, assumption enums, canonical units, dimension definitions
- **{GOLDEN TEST CATALOG}**: Reference solutions for regression detection
- **{AUDIT LOG}**: Compliance tracking (PII-redacted, immutable)
- **{METRICS STORE}**: Performance analytics, gate rejection rates
- **{ARTIFACT CACHE}**: Results + intermediate outputs with full provenance

### Key Data Structures

- **ProblemSpec v2**: Typed schema with quantity_ids, QuantityRef constraints (ontology-bound), NO LLM-authored dimensions
- **SolutionBundle**: y_pred + uncertainty + validity_flags + kernel_id + compute_trace
- **CitationMap**: claim_hash → [source_ids] for research groundedness
- **Provenance**: run_id + kernel_id + version + interface_hash + determinism_level + value_source + source_ref + timestamp

---

## V2 REVIEW CHANGE SUMMARY

All required changes from v2 review have been implemented:

| Area | Previous v2 Behavior | Updated v2.1 Behavior | Rationale |
|------|---------------------|----------------------|-----------|
| **Determinism** | Single "determinism_mode" concept | Split into D1 (numeric) vs D2 (full-output), D1 is default | Prevent over-claiming determinism; LLM prose can vary in D1 |
| **Acceptance Gating** | Used LLM confidence in decision matrix | Confidence is metadata only, gates use only deterministic checks | Avoid stochastic acceptance decisions |
| **Dimensions** | LLM emitted dimension vectors in spec | Validator derives dimensions from (quantity_id + unit + ontology) | Remove misalignment backdoor |
| **Caching** | Approximate cache + speculative exec mentioned | Disabled under determinism_level=D1/D2, exact hash only | Preserve D1 determinism guarantee |
| **Typed Constraints** | Good direction, var refs not fully bound | All AST vars must be QuantityRef with ontology-bound qid | Prevent "free variable" drift |
| **Provenance** | Clarification required citation | Machine-enforceable: value_source + source_ref for every filled gap | Ensure no auto-healing |
| **Kernel Selection** | Oldest stable tiebreak only | Added compatibility checks: schema_version_compat, ontology_version_compat, interface_hash | Prevent mismatched kernel interpretations |
| **Auto-Retry** | Implied possible retry on rejection | Explicit: NO auto-retry with "stricter prompt", return deterministic error | Avoid nondeterministic loops |
| **Terminology** | "Phase" in research pipeline | Changed to "Stage" throughout | Consistency with execution semantics |
| **Metadata** | Informal "February 2025" | ISO timestamp: 2026-02-06T21:45:00-08:00 + commit ref | Professional hygiene |

**Bottom Line**: Architecture now fully enforces: **LLMs propose structured specs and format prose; determinism lives in gates + kernel selection + kernel execution. Same validated spec → same numeric results (D1).**

---

**Document Version**: 3.0 (Determinism-First Revision + v2/v3 Review Changes)  
**Last Updated**: 2026-02-06T22:30:00-08:00  
**Source Commit**: [to be tagged on commit]  
**Architecture**: LLM-as-Proposer + Deterministic Gates  
**Target Scope**: R&D orchestration with typed specifications, no string math  
**Default Mode**: D1 Numeric-Deterministic (same spec → same numbers)  
**Key Principles**: Determinism 🔒 | LLM proposes, gates dispose | Abstention > guessing  
**License**: Internal Use Only

**Revision Notes**:

- v3.0: Applied v3 review changes—removed confidence score from spec extractor output, unified determinism_mode→determinism_level terminology, added determinism scope for research/web (local-only or snapshot), explicit GPU determinism policy (CPU-only default under D1), AST operator allowlist per domain, spec_id + canonical_spec_hash for cache keys and provenance
- v2.1: Applied v2 review changes—D1/D2 determinism levels, removed LLM confidence from gates, dimensions derived deterministically, compatibility checks in kernel selector, disabled approx cache under determinism mode, provenance requirements for clarification, proper ISO timestamps
- v2.0: Added determinism mode enforcement, typed constraints (no string math), kernel registry, simplified for R&D scope
- v1.0: Initial enterprise-grade topology (pre-determinism refactor)
