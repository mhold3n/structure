"""
Tests for Gates module.

Verifies lab ambiguity gate, experiment safety gate, and gate pipeline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from router.gates import (
    Gate,
    GateDecision,
    GateResult,
    GatePipeline,
    LabAmbiguityGate,
    ExperimentSafetyGate,
    DataQualityGate,
    get_gate,
    get_all_gates,
)


class TestLabAmbiguityGate:
    """Test lab ambiguity detection gate."""

    def test_ambiguous_sample_term(self):
        """'sample' without context should trigger clarification."""
        gate = LabAmbiguityGate()
        result = gate.evaluate({"raw_input": "What is the sample?"})

        assert result.decision == GateDecision.CLARIFY
        assert "sample" in result.metadata["ambiguous_terms"]

    def test_disambiguated_sample_size(self):
        """'sample size' provides context, should pass."""
        gate = LabAmbiguityGate()
        result = gate.evaluate({"raw_input": "Calculate the sample size for my study"})

        assert result.decision == GateDecision.PASS

    def test_ambiguous_power_term(self):
        """'power' without context should trigger clarification."""
        gate = LabAmbiguityGate()
        result = gate.evaluate({"raw_input": "What power do I need?"})

        assert result.decision == GateDecision.CLARIFY
        assert "power" in result.metadata["ambiguous_terms"]

    def test_disambiguated_statistical_power(self):
        """'statistical power' with context should pass."""
        gate = LabAmbiguityGate()
        result = gate.evaluate(
            {"raw_input": "What power do I need to detect an effect size of 0.5?"}
        )

        assert result.decision == GateDecision.PASS

    def test_clear_request_passes(self):
        """Clear, unambiguous request should pass."""
        gate = LabAmbiguityGate()
        result = gate.evaluate({"raw_input": "Calculate the mean and standard deviation"})

        assert result.decision == GateDecision.PASS

    def test_multiple_ambiguities(self):
        """Multiple ambiguous terms should all be detected."""
        gate = LabAmbiguityGate()
        result = gate.evaluate({"raw_input": "Check the power and error of my sample"})

        assert result.decision == GateDecision.CLARIFY
        assert len(result.metadata["ambiguous_terms"]) >= 2


class TestExperimentSafetyGate:
    """Test experiment safety validation gate."""

    def test_non_experiment_passes(self):
        """Non-experiment domains should pass."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "analysis",
                "raw_input": "Analyze the correlation",
            }
        )

        assert result.decision == GateDecision.PASS

    def test_human_subjects_no_ethics_clarifies(self):
        """Human subjects without ethics mention should clarify."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "experiment",
                "raw_input": "Design study with 50 participants",
            }
        )

        assert result.decision == GateDecision.CLARIFY
        assert "human_subjects_no_ethics" in result.metadata["issues"]

    def test_human_subjects_with_irb_passes(self):
        """Human subjects with IRB mention should pass."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "experiment",
                "raw_input": (
                    "Design study with 50 participants, IRB approved, control group included"
                ),
            }
        )

        assert result.decision == GateDecision.PASS

    def test_high_risk_without_ethics_blocks(self):
        """High-risk study without ethics should block."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "experiment",
                "raw_input": "Design clinical drug trial with patients",
            }
        )

        assert result.decision == GateDecision.BLOCK

    def test_no_control_group_clarifies(self):
        """Experiment without control group should clarify."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "experiment",
                "raw_input": "Test the new algorithm on 100 cases",
            }
        )

        assert result.decision == GateDecision.CLARIFY
        assert "no_control_group" in result.metadata["issues"]

    def test_with_control_group_passes(self):
        """Experiment with control group should pass."""
        gate = ExperimentSafetyGate()
        result = gate.evaluate(
            {
                "domain": "experiment",
                "raw_input": "Compare treatment vs control group on algorithm performance",
            }
        )

        assert result.decision == GateDecision.PASS


class TestDataQualityGate:
    """Test data quality validation gate."""

    def test_non_analysis_passes(self):
        """Non-analysis domains should pass."""
        gate = DataQualityGate()
        result = gate.evaluate(
            {
                "domain": "project",
                "raw_input": "Create project schedule",
            }
        )

        assert result.decision == GateDecision.PASS

    def test_missing_data_source_clarifies(self):
        """Data without source specification should clarify."""
        gate = DataQualityGate()
        result = gate.evaluate(
            {
                "domain": "analysis",
                "raw_input": "Analyze the dataset",
            }
        )

        assert result.decision == GateDecision.CLARIFY
        assert any("where" in q.lower() for q in result.clarify_questions)

    def test_with_source_passes(self):
        """Data with source should pass."""
        gate = DataQualityGate()
        result = gate.evaluate(
            {
                "domain": "analysis",
                "raw_input": "Load data from sales.csv file",
            }
        )

        assert result.decision == GateDecision.PASS


class TestGateRegistry:
    """Test gate registry functions."""

    def test_get_gate_returns_instance(self):
        """get_gate should return gate instance."""
        gate = get_gate("lab_ambiguity_v1")

        assert gate is not None
        assert isinstance(gate, LabAmbiguityGate)

    def test_get_gate_invalid_returns_none(self):
        """Invalid gate ID should return None."""
        gate = get_gate("invalid_gate")

        assert gate is None

    def test_get_all_gates_returns_list(self):
        """get_all_gates should return all gates."""
        gates = get_all_gates()

        assert len(gates) >= 3
        assert all(isinstance(g, Gate) for g in gates)


class TestGatePipeline:
    """Test gate pipeline execution."""

    def test_pipeline_all_pass(self):
        """Pipeline with all passing gates should pass."""
        pipeline = GatePipeline()
        result = pipeline.evaluate(
            {
                "domain": "project",
                "raw_input": "Create a Gantt chart for the project schedule",
            }
        )

        assert result.decision == GateDecision.PASS

    def test_pipeline_stops_on_clarify(self):
        """Pipeline should stop on first CLARIFY."""
        pipeline = GatePipeline()
        result = pipeline.evaluate(
            {
                "domain": "experiment",
                "raw_input": "Check the power of my sample",
            }
        )

        assert result.decision == GateDecision.CLARIFY

    def test_pipeline_evaluate_all_returns_all(self):
        """evaluate_all should return all gate results."""
        pipeline = GatePipeline()
        results = pipeline.evaluate_all(
            {
                "domain": "experiment",
                "raw_input": "Compare control vs treatment group performance",
            }
        )

        assert len(results) == len(pipeline.gates)


def run_tests():
    """Run all gate tests."""
    import traceback

    test_classes = [
        TestLabAmbiguityGate,
        TestExperimentSafetyGate,
        TestDataQualityGate,
        TestGateRegistry,
        TestGatePipeline,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_class.__name__}")
        print("=" * 60)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
