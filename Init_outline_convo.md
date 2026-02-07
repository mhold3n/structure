We have this outline for our inialization. Determine if the repo is alligned with the plan or if we've evolved past it. If its still alligned, determine if the framework would be ready to init, assuming our modules were in place:

# Hybrid AI Stack Initialization Plan (Untuned Baseline → Measured Tuning)

This document is a stepwise, “textbook-style” initialization plan for building a **hybrid AI stack**: adaptive components (LLMs/ML) wrapped in deterministic middleware/orchestration (validators, gates, workflows, tooling). The objective is an **untuned but stable baseline** that is reproducible, auditable, and contamination-resistant—so later tuning is engineering, not guesswork.

---

## 0) Definitions and non-negotiables

### 0.1 Hybrid stack (working definition)

- **Adaptive modules:** LLMs/ML models and any learned routing/scoring that may change with training or data.
- **Deterministic modules:** schema validators, policy gates, tool wrappers, parsers, converters, checks, startup/readiness, and experiment bookkeeping. These should be specified and unit-tested (not “trained”).

Hybrid, tool-augmented patterns are well-established in the literature (e.g., modular neuro-symbolic systems and reasoning+acting loops). :contentReference[oaicite:0]{index=0}

### 0.2 “Untuned baseline” success criteria

A baseline is acceptable only if it satisfies:

- **Reproducibility:** same inputs + same configs + same data partitions → same outputs (within explicitly bounded stochasticity).
- **Isolation:** train/dev/test partitions are impermeable at retrieval + evaluation time (no cross-contamination). :contentReference[oaicite:1]{index=1}
- **Auditability:** every answer/action is traceable to (a) a cited source span, (b) a deterministic computation, or (c) an explicitly labeled model inference with logged inputs/outputs.
- **Observability:** end-to-end traces, metrics, and logs exist for every request. :contentReference[oaicite:2]{index=2}
- **Technical-debt containment:** tests/monitors exist for the ML-specific failure modes that otherwise compound silently. :contentReference[oaicite:3]{index=3}

---

## 1) Mission field and operating modes (before data, before models)

### 1.1 Write the mission field (scope contract)

Produce a single page that states:

- In-scope tasks (and explicit out-of-scope).
- Required response properties (citations, determinism level, latency/cost envelope).
- Tooling permissions and disallowed actions.
- “Modes” (e.g., research-grounded QA vs. deterministic calculation vs. code generation) and the expected behavior in each.

### 1.2 Threat/failure model (practical)

Enumerate failures by class:

- Retrieval failure, hallucination, tool misuse, schema break, leakage, drift, latency blowup, unsafe output, partial output.
Tie each failure class to:
- a detector,
- a gate,
- and a fallback (retry, alternate route, or human escalation).

Risk governance frameworks explicitly recommend monitored plans, override/appeal paths, and change management. :contentReference[oaicite:4]{index=4}

**Deliverables**

- `mission.md`
- `modes.md`
- `failure_taxonomy.md`

---

## 2) Topic-DOE: authoritative sources program (data acquisition as an experiment)

### 2.1 Define source classes (avoid “textbook monoculture”)

Set quotas across classes:

- Reference / encyclopedia
- Standards / procedures / datasheets
- Worked examples
- Problem sets (questions only)
- Primary literature
- Operational docs (APIs, manuals)

### 2.2 Governance + documentation at acquisition time

For every source, require:

- license/usage rights
- provenance (publisher, edition/version, date)
- intended use and known risks

Use dataset documentation practices (“datasheets”) and machine-usable stewardship principles (FAIR) as the baseline standard for dataset provenance and reuse. :contentReference[oaicite:5]{index=5}

**Deliverables**

- `sources/registry.csv`
- `sources/datasheets/<source_id>.md`

---

## 3) Partitioning and contamination control (make leakage hard, not “discouraged”)

### 3.1 Hard partitions at the storage level

Create physically separate namespaces/indices/buckets:

- `train/`
- `dev/`
- `test/`

Do **not** rely on tags alone. Isolation must be enforceable by code + permissions.

### 3.2 Dedup and near-dedup gates

Before anything is admitted to any partition:

- Exact text hash dedup
- Near-duplicate text detection (shingles/MinHash)
- Perceptual hash for figures/images
- Problem overlap detection (including “same problem, numbers changed” patterns)

### 3.3 Retrieval isolation rule

Your runtime retrieval layer must require a partition token:

- user requests during evaluation must only query `test` (or `dev`)
- training/tuning runs must never query `test`

This is the RAG analogue of classic leakage prevention: split first, fit/transform on train only. :contentReference[oaicite:6]{index=6}

**Deliverables**

- `partitions/policy.md`
- `scripts/contamination_audit.*` (runs on every build)

---

## 4) Ingestion pipeline (raw → canonical → derived)

### 4.1 Canonical artifact model (schemas first)

Define schemas *before* mass conversion:

- `Document` (id, provenance, license, version, source path)
- `Chunk` (doc_id, span offsets, section path, page/figure anchors)
- `Figure` (doc_id, page, bbox, caption, pHash)
- `Problem` / `WorkedExample` (question, steps, rubric, difficulty tags)

### 4.2 Conversion + validation (Marker-based extraction)

Pipeline stages:

1. **Raw import** (immutable)
2. **Canonical parse** (structure + metadata)
3. **Derived artifacts**:
   - Markdown
   - JSON (schema-conformant)
   - Image sets (figures/tables)
4. **Validation**:
   - schema validation
   - referential integrity (chunks link to doc + spans)
   - checksum + version stamp

### 4.3 Indexing strategy (hybrid memory)

Adopt a retrieval-augmented architecture (parametric model + non-parametric index) for baseline grounding. :contentReference[oaicite:7]{index=7}  
(Your existing plan to index in a vector DB like :contentReference[oaicite:8]{index=8} aligns with this.)

**Deliverables**

- `schemas/*.json`
- `ingest/manifest.jsonl`
- `indexes/<partition>/*`

---

## 5) Deterministic orchestration skeleton (baseline workflow before “agents”)

### 5.1 Prefer workflows at initialization

Start with a **fixed workflow graph** (deterministic control flow). Add agentic autonomy only after you can measure where it helps and where it hurts (cost, variance, safety).

### 5.2 Bootstrap/init service (your stack-specific must-have)

Because you are using :contentReference[oaicite:9]{index=9} + Compose as the primary orchestrator, implement a dedicated `bootstrap` service that:

- waits for dependencies (DB/vector store/cache) to become healthy
- applies/validates schemas (e.g., Weaviate class schemas)
- runs smoke tests
- sets a single readiness flag (`STACK_READY=1`) for downstream services

Use Compose startup-order + healthcheck gating rather than “sleep loops.” :contentReference[oaicite:10]{index=10}

### 5.3 Healthchecks + disposability

Treat services as disposable: fast startup, graceful shutdown, logs as event streams. This reduces brittle initialization and makes restarts safe. :contentReference[oaicite:11]{index=11}

**Deliverables**

- `compose.yaml` with healthchecks + `depends_on: condition: service_healthy`
- `services/bootstrap/*`

---

## 6) Middleware modules: static gates vs adaptive components

### 6.1 Static (deterministic) modules to implement first

These are “foundation” and should be unit-tested:

- Schema validation (inputs/outputs)
- Citation enforcement + provenance linkage
- Tool wrappers (typed I/O + retries + timeouts)
- Safety/policy gates
- Converters (units, formats)
- Deterministic calculators/checkers where applicable
- Caching + idempotency guards
- Partition gate (prevents test leakage)

This aligns with production-readiness guidance: ML systems accumulate hidden technical debt unless testing/monitoring and strict interfaces exist early. :contentReference[oaicite:12]{index=12}

### 6.2 Adaptive modules (baseline versions)

- LLM reasoning/generation
- Retrieval ranking / reranking (start simple)
- Light routing/classification (only if measurable benefit)

Hybrid modular architectures (LLM + tools + discrete reasoning) are supported by neuro-symbolic designs (MRKL) and interleaved reasoning+acting (ReAct). :contentReference[oaicite:13]{index=13}

**Deliverables**

- `middleware/contracts/*.json`
- `middleware/gates/*`
- `middleware/tools/*`

---

## 7) Observability + experiment bookkeeping (from day zero)

### 7.1 Instrument everything

Adopt an industry-standard observability framework:

- traces (request path across services)
- metrics (latency, error rate, cost, token usage, retrieval hit-rate)
- logs (structured events)

:contentReference[oaicite:14]{index=14} provides specs for traces/metrics/logs and correlation across signals. :contentReference[oaicite:15]{index=15}

### 7.2 Experiment tracking + registries

Even pre-tuning, you need run lineage:

- configs
- datasets/partitions
- model versions
- outputs + evaluation scores

Use a model/experiment registry such as :contentReference[oaicite:16]{index=16} to track lineage and versioning. :contentReference[oaicite:17]{index=17}

**Deliverables**

- `telemetry/otel/*`
- `runs/<run_id>/*` (immutable artifacts)

---

## 8) Evaluation harness (build this before tuning)

### 8.1 Capability matrix

Define capabilities and their tests:

- Grounded QA (must cite)
- Deterministic math/logic correctness
- Tool correctness (typed outputs, retries, timeouts)
- Schema conformance
- Retrieval quality (top-k relevance; abstain when missing)
- Safety/policy compliance
- Robustness to paraphrase/adversarial phrasing
- Cost/latency envelope

### 8.2 Test tiers (minimum viable)

- Unit tests (deterministic modules)
- Contract tests (module interfaces)
- Scenario tests (end-to-end)
- Regression suite (locked)
- Contamination audits (locked)

Use established ML production readiness rubrics to avoid missing the “boring but fatal” tests. :contentReference[oaicite:18]{index=18}  
Follow reproducibility disclosure expectations (code/data/weights/resources). :contentReference[oaicite:19]{index=19}

**Deliverables**

- `eval/benchmarks/*`
- `eval/regression_locked/*`
- `eval/report.md`

---

## 9) Model selection (baseline rules)

### 9.1 Start with one general model

- Minimize routing complexity until measured need exists.
- Use conservative decoding for baseline (reduced variance).

### 9.2 Documentation for models

Create model cards for every model in the stack (even baseline-only), to define intended use, evaluation conditions, and limitations. :contentReference[oaicite:20]{index=20}

**Deliverables**

- `models/registry.yaml`
- `models/model_cards/<model_id>.md`

---

## 10) Baseline assembly and stability sweep (DOE across request types)

### 10.1 Design the “request DOE”

Generate an evaluation set spanning:

- each mode
- each source class
- each tool path
- boundary conditions (missing docs, conflicting sources, ambiguous prompts)

### 10.2 Measure sensitivity correctly

You do **not** want “low sensitivity to request type.” You want:

- correct routing between modes
- stable behavior within a mode
- safe, explainable degradation outside mission field

### 10.3 Acceptance gate

Baseline is accepted only if:

- regression suite passes
- contamination audit passes
- observability coverage meets threshold
- costs/latency within envelope
- variance bounded and explained (where stochasticity remains)

**Deliverables**

- `baseline/acceptance.md`
- `baseline/metrics.json`

---

## 11) Controlled tuning (only after baseline is accepted)

### 11.1 What can be tuned (and what cannot)

- Tunable: retrieval parameters, routing thresholds, prompt templates, model choice, rerankers.
- Not tunable by “learning”: partition gates, schema validators, audit logging, safety rules, init readiness.

### 11.2 Change control

Every change requires:

- experiment entry (run ID)
- diff of configs
- evaluation report
- rollback path

This is consistent with MLOps guidance on CI/CD/CT practices and lifecycle management. :contentReference[oaicite:21]{index=21}

---

# Appendix A: Minimal repository layout

The updated `structure` codebase still follows the high‑level architecture envisioned in your “Hybrid AI Stack Initialization Plan.”  It retains a hybrid design in which adaptive components (the new `LLMSpecExtractor` and its OpenRouter/­local modes) are wrapped by deterministic classification, gating and kernel modules.  These deterministic components enforce reproducibility through D1 or D2 determinism and clarify ambiguous inputs via policy‑driven gates.  The experiment‑design kernel, lab‑specific ambiguity and safety gates, and expanded domain enumeration demonstrate progress toward the plan’s goal of having deterministic calculators, converters and safety checks for core workflows.  Logging all requests and decisions as JSONL (for auditability) and seeding randomization within kernels further support the plan’s baseline success criteria.

However, the initialization plan covers much more than deterministic middleware.  It demands clearly defined mission scopes and modes, a threat/failure taxonomy, hard train/dev/test partitions with dedup gates, a canonical ingestion and indexing pipeline, bootstrap services and health checks, telemetry instrumentation, experiment bookkeeping, and a full evaluation harness.  None of those deliverables (e.g., `mission.md`, `sources/registry.csv`, `partitions/policy.md`, `telemetry/otel/*`) are present in the current repository.  The new integrity validator hints at upcoming kernels for statistics, project management and data summarization, but these are not yet implemented.  There is also no evidence of a Compose bootstrap service, observability hooks or model cards.

In short, the repository remains **aligned** with the initialization plan’s philosophy (hybrid architecture and deterministic foundations) but **does not yet execute** many of its later stages.  To be “ready to init” in the sense of your plan, you would need to add:

- Mission‑field definition, modes and failure taxonomy documents.
- Data ingestion and partitioning pipelines with dedup and contamination gates.
- Bootstrap and healthcheck services for your orchestration stack.
- Telemetry and experiment tracking infrastructure.
- An evaluation harness with tests across modes and safety policies.
- Implemented kernels and policies for all planned domains (survey, project, operations, analysis, statistics).

Assuming those modules and deliverables were in place, the current framework of deterministic kernels, LLM spec extraction and lab‑focused gates would provide a solid foundation for initializing your baseline hybrid stack.
