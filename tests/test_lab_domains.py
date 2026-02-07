"""
Tests for AI Lab Domain Routing.

Verifies that lab-specific requests are routed to the correct domains
and trigger appropriate gates and kernels.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from router.classifier import classify_task, extract_features
from models.task_spec import TaskRequest, Domain


class TestLabDomainRouting:
    """Test routing to lab domains."""

    def test_experiment_design_keywords(self):
        """Experiment design keywords should route to experiment domain."""
        prompts = [
            "Design a randomized control group experiment",
            "What is the best protocol for my hypothesis test?",
            "Create a double-blind study with treatment arms",
            "IRB approval for cohort study",
        ]
        for prompt in prompts:
            request = TaskRequest(request_id="test", user_input=prompt)
            spec = classify_task(request)
            assert spec.domain == Domain.EXPERIMENT, f"'{prompt}' should route to experiment"

    def test_survey_keywords(self):
        """Survey research keywords should route to survey domain."""
        prompts = [
            "Design a questionnaire with likert scale questions",
            "Calculate sample size for margin of error 5%",
            "Analyze demographics of respondents",
            "Reduce non-response in stratified sampling",
        ]
        for prompt in prompts:
            request = TaskRequest(request_id="test", user_input=prompt)
            spec = classify_task(request)
            assert spec.domain == Domain.SURVEY, f"'{prompt}' should route to survey"

    def test_project_keywords(self):
        """Project management keywords should route to project domain."""
        prompts = [
            "Create a gantt chart for the project",
            "Calculate critical path for dependencies",
            "Assign resources to sprint deliverables",
            "Track milestones and deadlines",
        ]
        for prompt in prompts:
            request = TaskRequest(request_id="test", user_input=prompt)
            spec = classify_task(request)
            assert spec.domain == Domain.PROJECT, f"'{prompt}' should route to project"

    def test_operations_keywords(self):
        """Operations keywords should route to operations domain."""
        prompts = [
            "Design a workflow for inventory management",
            "Write an SOP for escalation procedures",
            "Improve throughput by reducing bottlenecks",
            "Schedule shifts for capacity planning",
        ]
        for prompt in prompts:
            request = TaskRequest(request_id="test", user_input=prompt)
            spec = classify_task(request)
            assert spec.domain == Domain.OPERATIONS, f"'{prompt}' should route to operations"

    def test_analysis_keywords(self):
        """Data analysis keywords should route to analysis domain."""
        prompts = [
            "Run a regression on this dataset",
            "Calculate p-value and confidence interval",
            "Create a pivot table with aggregations",
            "Check for outliers in the distribution",
        ]
        for prompt in prompts:
            request = TaskRequest(request_id="test", user_input=prompt)
            spec = classify_task(request)
            assert spec.domain == Domain.ANALYSIS, f"'{prompt}' should route to analysis"


class TestLabAmbiguousTerms:
    """Test that lab ambiguous terms trigger clarification."""

    def test_response_rate_ambiguous(self):
        """'response rate' should be detected as ambiguous."""
        features = extract_features("What is the response rate?")
        assert "response rate" in features["ambiguous_terms"]

    def test_sample_ambiguous(self):
        """'sample' should be detected as ambiguous."""
        features = extract_features("Analyze the sample data")
        assert "sample" in features["ambiguous_terms"]

    def test_power_ambiguous(self):
        """'power' should be detected as ambiguous."""
        features = extract_features("Calculate the power requirement")
        assert "power" in features["ambiguous_terms"]

    def test_unambiguous_lab_term_passes(self):
        """Lab terms without ambiguity should not require clarification."""
        features = extract_features("Create a gantt chart")
        # "gantt chart" is not ambiguous
        assert len(features["ambiguous_terms"]) == 0


class TestLabKernelSelection:
    """Test kernel selection for lab domains."""

    def test_experiment_selects_experiment_kernel(self):
        """Experiment domain should select experiment_design_v1."""
        request = TaskRequest(
            request_id="test",
            user_input="Design a randomized control trial protocol",
        )
        spec = classify_task(request)
        assert "experiment_design_v1" in spec.selected_kernels

    def test_survey_selects_statistics_kernel(self):
        """Survey domain should select statistics_v1."""
        request = TaskRequest(
            request_id="test",
            user_input="Calculate sample size for questionnaire",
        )
        spec = classify_task(request)
        assert "statistics_v1" in spec.selected_kernels

    def test_analysis_selects_multiple_kernels(self):
        """Analysis domain should select statistics and data_summary kernels."""
        request = TaskRequest(
            request_id="test",
            user_input="Run regression and create pivot tables",
        )
        spec = classify_task(request)
        assert "statistics_v1" in spec.selected_kernels
        assert "data_summary_v1" in spec.selected_kernels


def run_tests():
    """Run all lab domain tests."""
    import traceback

    test_classes = [
        TestLabDomainRouting,
        TestLabAmbiguousTerms,
        TestLabKernelSelection,
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
