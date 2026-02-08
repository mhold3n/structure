import math
import statistics
from typing import List, Dict, Any, Union
from kernels.base import KernelInterface, register_kernel
from models.kernel_io import KernelInput, KernelOutput


@register_kernel
class StatisticsKernel(KernelInterface):
    """
    Deterministic kernel for statistical calculations.
    """

    kernel_id = "statistics_v1"
    version = "1.0.0"
    determinism_level = "D1"
    description = "Performs basic descriptive statistics and hypothesis testing (t-test)."

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        errors = []
        method = args.get("method") or args.get("operation")
        if not method:
            errors.append("Missing 'method' (or 'operation') argument")

        # Check for data or constructible data
        has_data = "data" in args
        has_groups = "group1" in args and "group2" in args
        has_xy = "x" in args and "y" in args

        if not (has_data or has_groups or has_xy):
            if method == "sample_size":
                pass  # sample_size might not need data if just calculating n
            else:
                errors.append("Missing 'data' argument (or flat args like group1/group2, x/y)")

        if has_data:
            data = args["data"]
            if not isinstance(data, (list, dict)):
                errors.append("'data' must be a list or dictionary")

        return len(errors) == 0, errors

    def execute(self, input: KernelInput) -> KernelOutput:
        args = input.args
        valid, errors = self.validate_args(args)
        if not valid:
            return self._make_output(
                input.request_id, success=False, error="Invalid arguments: " + "; ".join(errors)
            )

        method = args.get("method") or args.get("operation")
        data = args.get("data")

        # Construct data from flat args if missing
        if data is None:
            if "group1" in args and "group2" in args:
                data = {"group1": args["group1"], "group2": args["group2"]}
            elif "x" in args and "y" in args:
                data = {"x": args["x"], "y": args["y"]}

        # Alias t_test -> ttest_ind
        if method == "t_test":
            method = "ttest_ind"

        try:
            if method == "descriptive":
                if data is None:
                    return self._make_output(
                        input.request_id, success=False, error="Missing data for descriptive stats"
                    )
                return self._make_output(
                    input.request_id, success=True, result=self._descriptive(data)
                )
            elif method == "ttest_ind":
                if data is None:
                    return self._make_output(
                        input.request_id, success=False, error="Missing data for t-test"
                    )
                return self._make_output(
                    input.request_id, success=True, result=self._ttest_ind(data)
                )
            elif method == "regression":
                if data is None:
                    return self._make_output(
                        input.request_id, success=False, error="Missing data for regression"
                    )
                return self._make_output(
                    input.request_id, success=True, result=self._regression(data)
                )
            elif method == "sample_size":
                return self._make_output(
                    input.request_id, success=True, result=self._sample_size(args)
                )
            else:
                return self._make_output(
                    input.request_id, success=False, error=f"Unknown operation '{method}'"
                )
        except Exception as e:
            return self._make_output(input.request_id, success=False, error=str(e))

    def _descriptive(self, data: Union[List[float], Dict[str, List[float]]]) -> Dict[str, Any]:
        # data can be a list or a dict of lists
        if isinstance(data, list):
            series = {"default": data}
        else:
            series = data

        results = {}
        for name, values in series.items():
            if not values:
                continue
            results[name] = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "n": len(values),
            }

        if isinstance(data, list):
            return results["default"]

        return results

    def _ttest_ind(self, data: Dict[str, List[float]]) -> Dict[str, Any]:
        # Expects keys like 'group1', 'group2'
        keys = list(data.keys())
        # We need validation here or assume validate_args covered it?
        # execute() logic ensures data is present, but content might be wrong?
        if len(keys) != 2:
            raise ValueError("ttest_ind requires exactly 2 groups")

        g1 = data[keys[0]]
        g2 = data[keys[1]]

        n1 = len(g1)
        n2 = len(g2)

        if n1 < 2 or n2 < 2:
            raise ValueError("Groups must have at least 2 elements")

        m1 = statistics.mean(g1)
        m2 = statistics.mean(g2)
        v1 = statistics.variance(g1)
        v2 = statistics.variance(g2)

        # Welch's t-test (unequal variances)
        vn1 = v1 / n1
        vn2 = v2 / n2
        statistic_denominator = math.sqrt(vn1 + vn2)
        if statistic_denominator == 0:
            t_stat = 0.0  # Identical
        else:
            t_stat = (m1 - m2) / statistic_denominator

        return {
            "t_statistic": t_stat,
            "significant": abs(t_stat) > 2.0,  # Mock significance threshold
            "decision": "Reject H0" if abs(t_stat) > 2.0 else "Fail to reject H0",
            "method": "Welch's t-test",
        }

    def _regression(self, data: Dict[str, List[float]]) -> Dict[str, Any]:
        x = data.get("x")
        y = data.get("y")
        if not x or not y:
            raise ValueError("Regression requires 'x' and 'y'")

        if len(x) != len(y):
            raise ValueError("x and y must have same length")

        n = len(x)
        if n < 2:
            raise ValueError("Need at least 2 points")

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        demoninator = sum((xi - mean_x) ** 2 for xi in x)

        if demoninator == 0:
            raise ValueError("Vertical line (no variance in x)")

        slope = numerator / demoninator
        intercept = mean_y - slope * mean_x

        # Calculate R-squared
        ss_tot = sum((yi - mean_y) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 1.0

        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "correlation": math.sqrt(r_squared) if slope >= 0 else -math.sqrt(r_squared),
        }

    def _sample_size(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Mock sample size calculation
        effect_size = args.get("effect_size", 0.5)
        # power = args.get("power", 0.8)
        # alpha = args.get("alpha", 0.05)

        # Simple formula for sample size (Cohen's d)
        z_alpha = 1.96  # for alpha 0.05 two-tailed
        z_beta = 0.84  # for power 0.8

        n_per_group = 2 * ((z_alpha + z_beta) / effect_size) ** 2

        return {
            "n1": math.ceil(n_per_group),
            "n2": math.ceil(n_per_group),
            "total_n": math.ceil(n_per_group * 2),
        }
