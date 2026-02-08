"""
Tests for Statistics Kernel.

Verifies sample size calculation, t-tests, descriptive stats, and regression.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.kernel_io import KernelInput
from kernels.statistics import StatisticsKernel


class TestSampleSize:
    """Test sample size calculation."""

    def test_default_parameters(self):
        """Default parameters should return reasonable sample size."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "sample_size"},
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["n1"] > 0
        assert result.result["n2"] > 0
        assert result.result["total_n"] > 0

    def test_large_effect_size_smaller_n(self):
        """Larger effect size should require smaller sample."""
        kernel = StatisticsKernel()
        small_effect = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "sample_size", "effect_size": 0.2},
        )
        large_effect = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "sample_size", "effect_size": 0.8},
        )
        small_result = kernel.execute(small_effect)
        large_result = kernel.execute(large_effect)
        assert small_result.result["total_n"] > large_result.result["total_n"]


class TestTTest:
    """Test two-sample t-test."""

    def test_identical_groups_not_significant(self):
        """Identical groups should not be significant."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "t_test",
                "group1": [1, 2, 3, 4, 5],
                "group2": [1, 2, 3, 4, 5],
            },
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["t_statistic"] == 0
        assert result.result["significant"] is False

    def test_different_groups_significant(self):
        """Very different groups should be significant."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "t_test",
                "group1": [1, 2, 3, 4, 5],
                "group2": [10, 11, 12, 13, 14],
            },
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["significant"] is True
        assert result.result["decision"] == "Reject H0"

    def test_too_few_values_fails(self):
        """Groups with less than 2 values should fail."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "t_test",
                "group1": [1],
                "group2": [2],
            },
        )
        result = kernel.execute(input)
        assert not result.success


class TestDescriptive:
    """Test descriptive statistics."""

    def test_basic_stats(self):
        """Should calculate basic descriptive statistics."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "descriptive", "data": [1, 2, 3, 4, 5]},
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["mean"] == 3.0
        assert result.result["median"] == 3.0
        assert result.result["n"] == 5
        assert result.result["min"] == 1
        assert result.result["max"] == 5

    def test_empty_data_fails(self):
        """Empty data should fail."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "descriptive", "data": []},
        )
        result = kernel.execute(input)
        assert not result.success


class TestRegression:
    """Test simple linear regression."""

    def test_perfect_correlation(self):
        """Perfect linear data should have R²=1."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "regression",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],  # y = 2x
            },
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["slope"] == 2.0
        assert result.result["intercept"] == 0.0
        assert result.result["r_squared"] == 1.0

    def test_mismatched_lengths_fails(self):
        """Different length arrays should fail."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "regression",
                "x": [1, 2, 3],
                "y": [1, 2],
            },
        )
        result = kernel.execute(input)
        assert not result.success

    def test_negative_correlation(self):
        """Negative slope should work."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={
                "operation": "regression",
                "x": [1, 2, 3, 4, 5],
                "y": [10, 8, 6, 4, 2],  # y = -2x + 12
            },
        )
        result = kernel.execute(input)
        assert result.success
        assert result.result["slope"] == -2.0
        assert result.result["correlation"] < 0


class TestValidation:
    """Test input validation."""

    def test_unknown_operation_fails(self):
        """Unknown operation should fail gracefully."""
        kernel = StatisticsKernel()
        input = KernelInput(
            request_id="test",
            kernel_id="statistics_v1",
            args={"operation": "unknown", "data": [1, 2, 3]},
        )
        result = kernel.execute(input)
        assert not result.success
        assert "Unknown operation" in result.error


def run_tests():
    """Run all statistics kernel tests."""
    import traceback

    test_classes = [
        TestSampleSize,
        TestTTest,
        TestDescriptive,
        TestRegression,
        TestValidation,
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
