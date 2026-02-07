"""
Statistics Kernel: Statistical analysis operations.

Provides deterministic statistical calculations:
- Sample size calculation
- Two-sample t-test
- Descriptive statistics
- Simple linear regression
"""

import math
from typing import Optional

from models.kernel_io import KernelInput, KernelOutput
from .base import KernelInterface, register_kernel


# Z-scores for common confidence levels
Z_SCORES = {
    0.90: 1.645,
    0.95: 1.96,
    0.99: 2.576,
}

# T-distribution critical values (two-tailed, 0.05)
# Key is degrees of freedom
T_CRITICAL_005 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    15: 2.131,
    20: 2.086,
    25: 2.060,
    30: 2.042,
    40: 2.021,
    50: 2.009,
    60: 2.000,
    80: 1.990,
    100: 1.984,
    120: 1.980,
}


def _get_t_critical(df: int, alpha: float = 0.05) -> float:
    """Get t-critical value for given degrees of freedom."""
    if alpha != 0.05:
        # Only 0.05 table implemented
        return 1.96  # Fallback to z for large samples

    # Find closest df in table
    if df in T_CRITICAL_005:
        return T_CRITICAL_005[df]

    # Linear interpolation for intermediate values
    keys = sorted(T_CRITICAL_005.keys())
    for i, k in enumerate(keys):
        if k > df:
            if i == 0:
                return T_CRITICAL_005[keys[0]]
            k_low = keys[i - 1]
            k_high = k
            t_low = T_CRITICAL_005[k_low]
            t_high = T_CRITICAL_005[k_high]
            return t_low + (t_high - t_low) * (df - k_low) / (k_high - k_low)

    # df > max in table, use z approximation
    return 1.96


@register_kernel
class StatisticsKernel(KernelInterface):
    """
    Statistical analysis kernel.

    Determinism level: D1 (numeric determinism)

    Operations:
    - sample_size: Calculate required sample size for given parameters
    - t_test: Two-sample t-test
    - descriptive: Mean, median, std, quartiles
    - regression: Simple OLS regression
    """

    kernel_id = "statistics_v1"
    version = "1.0.0"
    determinism_level = "D1"

    SUPPORTED_OPERATIONS = ["sample_size", "t_test", "descriptive", "regression"]

    def execute(self, input: KernelInput) -> KernelOutput:
        """Execute with typed KernelInput."""
        operation = input.args.get("operation", "")

        # Infer operation if missing based on arguments
        if not operation:
            if "effect_size" in input.args or "power" in input.args:
                operation = "sample_size"
            elif "group1" in input.args and "group2" in input.args:
                operation = "t_test"
            elif "data" in input.args:
                operation = "descriptive"
            elif "x" in input.args and "y" in input.args:
                operation = "regression"

        if operation == "sample_size":
            return self._sample_size(input.args, input.request_id)
        elif operation == "t_test":
            return self._t_test(input.args, input.request_id)
        elif operation == "descriptive":
            return self._descriptive(input.args, input.request_id)
        elif operation == "regression":
            # Ensure regression checks args too inside
            return self._regression(input.args, input.request_id)
        else:
            return self._make_output(
                request_id=input.request_id,
                success=False,
                error=f"Unknown operation: {operation}. Supported: {self.SUPPORTED_OPERATIONS}",
            )

    def _sample_size(self, args: dict, request_id: str) -> KernelOutput:
        """
        Calculate required sample size.

        Args:
            effect_size: Expected effect size (Cohen's d)
            alpha: Significance level (default 0.05)
            power: Desired power (default 0.80)
            ratio: Sample size ratio n2/n1 (default 1.0 for equal groups)

        Returns:
            Required sample sizes for each group
        """
        effect_size = args.get("effect_size", 0.5)
        alpha = args.get("alpha", 0.05)
        power = args.get("power", 0.80)
        ratio = args.get("ratio", 1.0)

        # Get z-scores
        z_alpha = Z_SCORES.get(1 - alpha, 1.96)
        z_beta = Z_SCORES.get(power, 0.84)  # power 0.80 → z ≈ 0.84

        # Sample size formula for two-sample t-test
        # n = 2 * ((z_alpha + z_beta) / effect_size)^2
        numerator = (z_alpha + z_beta) ** 2
        n_per_group = 2 * numerator / (effect_size**2)

        n1 = math.ceil(n_per_group)
        n2 = math.ceil(n_per_group * ratio)
        total_n = n1 + n2

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "n1": n1,
                "n2": n2,
                "total_n": total_n,
                "effect_size": effect_size,
                "alpha": alpha,
                "power": power,
                "formula": "n = 2 * ((z_alpha + z_beta) / effect_size)^2",
            },
        )

    def _t_test(self, args: dict, request_id: str) -> KernelOutput:
        """
        Two-sample t-test.

        Args:
            group1: List of values for group 1
            group2: List of values for group 2
            alpha: Significance level (default 0.05)

        Returns:
            t-statistic, p-value (approximated), decision
        """
        group1 = args.get("group1", [])
        group2 = args.get("group2", [])
        alpha = args.get("alpha", 0.05)

        if len(group1) < 2 or len(group2) < 2:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Each group must have at least 2 values",
            )

        # Calculate statistics
        n1, n2 = len(group1), len(group2)
        mean1 = sum(group1) / n1
        mean2 = sum(group2) / n2

        var1 = sum((x - mean1) ** 2 for x in group1) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in group2) / (n2 - 1)

        # Pooled standard error
        se = math.sqrt(var1 / n1 + var2 / n2)

        # t-statistic
        if se == 0:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Standard error is zero (no variance in data)",
            )

        t_stat = (mean1 - mean2) / se

        # Degrees of freedom (Welch-Satterthwaite)
        numerator = (var1 / n1 + var2 / n2) ** 2
        denominator = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        df = numerator / denominator if denominator > 0 else n1 + n2 - 2

        # Get critical value and make decision
        t_crit = _get_t_critical(int(df), alpha)
        significant = abs(t_stat) > t_crit

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "t_statistic": round(t_stat, 4),
                "degrees_of_freedom": round(df, 2),
                "t_critical": round(t_crit, 4),
                "alpha": alpha,
                "significant": significant,
                "decision": "Reject H0" if significant else "Fail to reject H0",
                "mean_group1": round(mean1, 4),
                "mean_group2": round(mean2, 4),
                "mean_difference": round(mean1 - mean2, 4),
            },
        )

    def _descriptive(self, args: dict, request_id: str) -> KernelOutput:
        """
        Descriptive statistics.

        Args:
            data: List of numeric values

        Returns:
            Mean, median, std, min, max, quartiles
        """
        data = args.get("data", [])

        if not data:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Data cannot be empty",
            )

        n = len(data)
        sorted_data = sorted(data)

        # Mean
        mean = sum(data) / n

        # Median
        if n % 2 == 0:
            median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            median = sorted_data[n // 2]

        # Standard deviation
        variance = sum((x - mean) ** 2 for x in data) / (n - 1) if n > 1 else 0
        std = math.sqrt(variance)

        # Quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_data[q1_idx] if n > 4 else sorted_data[0]
        q3 = sorted_data[q3_idx] if n > 4 else sorted_data[-1]

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "n": n,
                "mean": round(mean, 4),
                "median": round(median, 4),
                "std": round(std, 4),
                "variance": round(variance, 4),
                "min": min(data),
                "max": max(data),
                "range": max(data) - min(data),
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
            },
        )

    def _regression(self, args: dict, request_id: str) -> KernelOutput:
        """
        Simple linear regression (OLS).

        Args:
            x: Independent variable values
            y: Dependent variable values

        Returns:
            Slope, intercept, R-squared
        """
        x = args.get("x", [])
        y = args.get("y", [])

        if len(x) != len(y):
            return self._make_output(
                request_id=request_id,
                success=False,
                error=f"x and y must have same length ({len(x)} vs {len(y)})",
            )

        if len(x) < 2:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Need at least 2 data points",
            )

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        # Calculate slope and intercept
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="No variance in x (cannot fit line)",
            )

        slope = numerator / denominator
        intercept = mean_y - slope * mean_x

        # R-squared
        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Correlation coefficient
        r = math.sqrt(r_squared) if slope >= 0 else -math.sqrt(r_squared)

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "slope": round(slope, 4),
                "intercept": round(intercept, 4),
                "r_squared": round(r_squared, 4),
                "correlation": round(r, 4),
                "equation": f"y = {round(slope, 4)} * x + {round(intercept, 4)}",
                "n": n,
            },
        )

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """Validate inputs for statistics operations."""
        errors = []

        operation = args.get("operation")
        if not operation:
            # Check if arguments imply a valid operation
            if any(k in args for k in ["effect_size", "group1", "data", "x"]):
                pass # Valid inference possible
            else:
                errors.append("Missing required field: operation (and could not infer from args)")
        elif operation not in self.SUPPORTED_OPERATIONS:
            errors.append(f"Unknown operation: {operation}")

        return (len(errors) == 0, errors)

    def get_envelope(self) -> dict:
        """Return valid input envelope."""
        return {
            "supported_operations": self.SUPPORTED_OPERATIONS,
            "sample_size_params": ["effect_size", "alpha", "power", "ratio"],
            "t_test_params": ["group1", "group2", "alpha"],
            "descriptive_params": ["data"],
            "regression_params": ["x", "y"],
        }
