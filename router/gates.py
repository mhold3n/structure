"""
Gates: Decision points that control task flow.

Gates evaluate task specs and decide:
- PASS: Continue to next step
- CLARIFY: Request more information
- BLOCK: Reject the task

Provides lab-specific gates for AI Lab workflows.
"""

from typing import Optional
from enum import Enum
from dataclasses import dataclass


class GateDecision(str, Enum):
    """Possible gate outcomes."""

    PASS = "pass"  # Continue processing
    CLARIFY = "clarify"  # Need more information
    BLOCK = "block"  # Reject the task


@dataclass
class GateResult:
    """Result from gate evaluation."""

    decision: GateDecision
    gate_id: str
    reason: Optional[str] = None
    clarify_questions: Optional[list[str]] = None
    metadata: Optional[dict] = None


class Gate:
    """Base class for gates."""

    gate_id: str = "base_gate"
    description: str = "Base gate"

    def evaluate(self, task_spec: dict) -> GateResult:
        """Evaluate the task spec. Override in subclasses."""
        return GateResult(
            decision=GateDecision.PASS,
            gate_id=self.gate_id,
        )


# =============================================================================
# Lab Ambiguity Gate
# =============================================================================


class LabAmbiguityGate(Gate):
    """
    Gate for lab-specific ambiguous terms.

    Detects terms that have different meanings in lab vs general contexts
    and requests clarification when context is unclear.
    """

    gate_id = "lab_ambiguity_v1"
    description = "Detects lab-specific ambiguous terminology"

    # Terms with multiple meanings in lab context
    AMBIGUOUS_TERMS = {
        "sample": {
            "meanings": ["statistical sample", "biological sample", "data sample"],
            "clarify": "What type of sample are you referring to?",
        },
        "power": {
            "meanings": ["statistical power", "electrical power", "computational power"],
            "clarify": "Are you referring to statistical power or another type?",
        },
        "response rate": {
            "meanings": ["survey completion rate", "API response latency"],
            "clarify": "Is this survey response rate or system response time?",
        },
        "significance": {
            "meanings": ["statistical significance", "practical importance"],
            "clarify": "Do you mean statistical significance (p-value) or practical significance?",
        },
        "control": {
            "meanings": ["control group", "control variable", "access control"],
            "clarify": "Are you referring to a control group or a control variable?",
        },
        "effect": {
            "meanings": ["effect size", "side effect", "treatment effect"],
            "clarify": "What type of effect are you measuring?",
        },
        "bias": {
            "meanings": ["sampling bias", "cognitive bias", "model bias"],
            "clarify": "What type of bias are you concerned about?",
        },
        "error": {
            "meanings": ["Type I/II error", "measurement error", "software error"],
            "clarify": "Are you referring to statistical error or measurement error?",
        },
        "rate": {
            "meanings": ["rate of change", "response rate", "success rate"],
            "clarify": "What rate are you measuring?",
        },
        "distribution": {
            "meanings": ["probability distribution", "data distribution", "resource distribution"],
            "clarify": "Are you asking about statistical distribution or resource allocation?",
        },
    }

    # Context keywords that disambiguate terms
    DISAMBIGUATORS = {
        "sample": {
            "statistical sample": ["sample size", "random sample", "sampling"],
            "biological sample": ["blood", "tissue", "specimen", "lab", "collect"],
            "data sample": ["dataset", "dataframe", "subset"],
        },
        "power": {
            "statistical power": [
                "effect size",
                "sample size",
                "hypothesis",
                "detect",
                "0.5",
                "0.8",
                "statistical",
            ],
            "electrical power": ["watt", "voltage", "circuit", "outlet"],
        },
        "effect": {
            "effect size": ["effect size", "cohen", "d=", "treatment effect"],
            "side effect": ["adverse", "side", "reaction"],
        },
    }

    def evaluate(self, task_spec: dict) -> GateResult:
        """Check for ambiguous lab terminology."""
        text = self._get_text(task_spec).lower()

        ambiguities = []
        questions = []

        for term, info in self.AMBIGUOUS_TERMS.items():
            if term in text and not self._is_disambiguated(term, text):
                ambiguities.append(term)
                questions.append(info["clarify"])

        if ambiguities:
            return GateResult(
                decision=GateDecision.CLARIFY,
                gate_id=self.gate_id,
                reason=f"Ambiguous terms detected: {', '.join(ambiguities)}",
                clarify_questions=questions,
                metadata={"ambiguous_terms": ambiguities},
            )

        return GateResult(
            decision=GateDecision.PASS,
            gate_id=self.gate_id,
            reason="No ambiguous lab terminology detected",
        )

    def _get_text(self, task_spec: dict) -> str:
        """Extract text content from task spec."""
        if isinstance(task_spec, str):
            return task_spec
        return task_spec.get("raw_input", "") or task_spec.get("intent", "")

    def _is_disambiguated(self, term: str, text: str) -> bool:
        """Check if term is already disambiguated by context."""
        if term not in self.DISAMBIGUATORS:
            return False

        for meaning, keywords in self.DISAMBIGUATORS[term].items():
            if any(kw in text for kw in keywords):
                return True

        return False


# =============================================================================
# Experiment Safety Gate
# =============================================================================


class ExperimentSafetyGate(Gate):
    """
    Gate for experiment design safety.

    Checks that experiments have proper:
    - Control groups
    - Sample size justification
    - IRB/ethics considerations for human subjects
    """

    gate_id = "experiment_safety_v1"
    description = "Validates experiment design safety"

    # Required elements for human subjects research
    HUMAN_SUBJECTS_KEYWORDS = [
        "participant",
        "subject",
        "volunteer",
        "patient",
        "respondent",
        "human",
        "people",
        "interview",
        "survey",
        "questionnaire",
    ]

    # Ethics-related keywords
    ETHICS_KEYWORDS = [
        "irb",
        "ethics",
        "consent",
        "informed consent",
        "privacy",
        "confidential",
    ]

    # Risk indicators (specifically medical/clinical contexts)
    RISK_INDICATORS = [
        "invasive",
        "medical",
        "drug",
        "intervention",
        "clinical trial",
        "therapeutic",
        "diagnosis",
    ]

    def evaluate(self, task_spec: dict) -> GateResult:
        """Evaluate experiment safety requirements."""
        text = self._get_text(task_spec).lower()
        domain = task_spec.get("domain", "")

        # Only apply to experiment domain
        if domain not in ["experiment", "survey"]:
            return GateResult(
                decision=GateDecision.PASS,
                gate_id=self.gate_id,
                reason="Not an experiment/survey domain task",
            )

        issues = []
        questions = []

        # Check for human subjects
        has_human_subjects = any(kw in text for kw in self.HUMAN_SUBJECTS_KEYWORDS)
        has_ethics = any(kw in text for kw in self.ETHICS_KEYWORDS)
        has_risk = any(kw in text for kw in self.RISK_INDICATORS)

        if has_human_subjects and not has_ethics:
            issues.append("human_subjects_no_ethics")
            questions.append("This involves human subjects. Has IRB approval been obtained?")

        if has_risk:
            issues.append("high_risk_indicators")
            questions.append(
                "This appears to be a high-risk study. What safety protocols are in place?"
            )

        # Check for control group in experiments
        if domain == "experiment":
            has_control = any(
                kw in text for kw in ["control group", "control condition", "placebo", "baseline"]
            )
            if not has_control:
                issues.append("no_control_group")
                questions.append("No control group mentioned. Is this a controlled experiment?")

        if issues:
            # High-risk studies should block, others clarify
            if has_risk and not has_ethics:
                return GateResult(
                    decision=GateDecision.BLOCK,
                    gate_id=self.gate_id,
                    reason="High-risk study without ethics approval",
                    clarify_questions=questions,
                    metadata={"issues": issues},
                )

            return GateResult(
                decision=GateDecision.CLARIFY,
                gate_id=self.gate_id,
                reason="Experiment safety review needed",
                clarify_questions=questions,
                metadata={"issues": issues},
            )

        return GateResult(
            decision=GateDecision.PASS,
            gate_id=self.gate_id,
            reason="Experiment safety requirements met",
        )

    def _get_text(self, task_spec: dict) -> str:
        """Extract text content from task spec."""
        if isinstance(task_spec, str):
            return task_spec
        return task_spec.get("raw_input", "") or task_spec.get("intent", "")


# =============================================================================
# Data Quality Gate
# =============================================================================


class DataQualityGate(Gate):
    """
    Gate for data quality requirements.

    Ensures data-related tasks specify:
    - Data source
    - Data format
    - Quality expectations
    """

    gate_id = "data_quality_v1"
    description = "Validates data quality specifications"

    DATA_KEYWORDS = [
        "data",
        "dataset",
        "dataframe",
        "csv",
        "excel",
        "database",
        "table",
        "records",
    ]

    def evaluate(self, task_spec: dict) -> GateResult:
        """Check data quality specifications."""
        text = self._get_text(task_spec).lower()
        domain = task_spec.get("domain", "")

        # Only apply to analysis domain
        if domain not in ["analysis", "survey"]:
            return GateResult(
                decision=GateDecision.PASS,
                gate_id=self.gate_id,
                reason="Not a data domain task",
            )

        has_data_mention = any(kw in text for kw in self.DATA_KEYWORDS)
        if not has_data_mention:
            return GateResult(
                decision=GateDecision.PASS,
                gate_id=self.gate_id,
                reason="No data operations detected",
            )

        questions = []

        # Check for data source specification
        has_source = any(
            kw in text for kw in ["from", "source", "file", "path", "query", "fetch", "load"]
        )
        if not has_source:
            questions.append("Where is the data coming from?")

        # Check for format specification
        has_format = any(kw in text for kw in ["csv", "json", "excel", "parquet", "sql", "format"])
        if not has_format:
            questions.append("What format is the data in?")

        if questions:
            return GateResult(
                decision=GateDecision.CLARIFY,
                gate_id=self.gate_id,
                reason="Missing data specifications",
                clarify_questions=questions,
            )

        return GateResult(
            decision=GateDecision.PASS,
            gate_id=self.gate_id,
            reason="Data specifications adequate",
        )

    def _get_text(self, task_spec: dict) -> str:
        if isinstance(task_spec, str):
            return task_spec
        return task_spec.get("raw_input", "") or task_spec.get("intent", "")


# =============================================================================
# Gate Registry
# =============================================================================


# Registry of all available gates
GATE_REGISTRY: dict[str, type[Gate]] = {
    "lab_ambiguity_v1": LabAmbiguityGate,
    "experiment_safety_v1": ExperimentSafetyGate,
    "data_quality_v1": DataQualityGate,
}


def get_gate(gate_id: str) -> Optional[Gate]:
    """Get a gate instance by ID."""
    gate_class = GATE_REGISTRY.get(gate_id)
    if gate_class:
        return gate_class()
    return None


def get_all_gates() -> list[Gate]:
    """Get instances of all registered gates."""
    return [gate_class() for gate_class in GATE_REGISTRY.values()]


class GatePipeline:
    """
    Run multiple gates in sequence.

    Stops on first BLOCK or CLARIFY decision.
    """

    def __init__(self, gates: Optional[list[Gate]] = None):
        self.gates = gates or get_all_gates()

    def evaluate(self, task_spec: dict) -> GateResult:
        """Run all gates and return first non-PASS result."""
        for gate in self.gates:
            result = gate.evaluate(task_spec)
            if result.decision != GateDecision.PASS:
                return result

        return GateResult(
            decision=GateDecision.PASS,
            gate_id="pipeline",
            reason="All gates passed",
        )

    def evaluate_all(self, task_spec: dict) -> list[GateResult]:
        """Run all gates and return all results."""
        return [gate.evaluate(task_spec) for gate in self.gates]
