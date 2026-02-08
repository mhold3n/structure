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

    kernel_id = "stats_v1"
    version = "1.0.0"
    determinism_level = "D1"
    description = "Performs basic descriptive statistics and hypothesis testing (t-test)."
    
    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        errors = []
        if "method" not in args:
            errors.append("Missing 'method' argument")
        
        if "data" not in args:
            errors.append("Missing 'data' argument")
        else:
            data = args["data"]
            if not isinstance(data, (list, dict)):
                errors.append("'data' must be a list or dictionary")
        
        return len(errors) == 0, errors

    def execute(self, input: KernelInput) -> KernelOutput:
        args = input.args
        valid, errors = self.validate_args(args)
        if not valid:
            return self._make_output(input.request_id, success=False, error="Invalid arguments: " + "; ".join(errors))

        method = args.get("method")
        data = args.get("data")
        
        try:
            if method == "descriptive":
                return self._make_output(input.request_id, success=True, result=self._descriptive(data).result)
            elif method == "ttest_ind":
                return self._make_output(input.request_id, success=True, result=self._ttest_ind(data).result)
            else:
                return self._make_output(input.request_id, success=False, error=f"Unknown method '{method}'")
        except Exception as e:
             return self._make_output(input.request_id, success=False, error=str(e))

    def _descriptive(self, data: Union[List[float], Dict[str, List[float]]]) -> KernelOutput:
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
                "count": len(values),
            }
        return KernelOutput(success=True, result=results)

    def _ttest_ind(self, data: Dict[str, List[float]]) -> KernelOutput:
        # Expects keys like 'group1', 'group2'
        keys = list(data.keys())
        if len(keys) != 2:
            return KernelOutput(success=False, error="ttest_ind requires exactly 2 groups")

        g1 = data[keys[0]]
        g2 = data[keys[1]]

        n1 = len(g1)
        n2 = len(g2)

        if n1 < 2 or n2 < 2:
            return KernelOutput(success=False, error="Groups must have at least 2 elements")

        m1 = statistics.mean(g1)
        m2 = statistics.mean(g2)
        v1 = statistics.variance(g1)
        v2 = statistics.variance(g2)

        # Welch's t-test (unequal variances)
        vn1 = v1 / n1
        vn2 = v2 / n2
        t_stat = (m1 - m2) / math.sqrt(vn1 + vn2)
        df = (vn1 + vn2) ** 2 / ((vn1**2 / (n1 - 1)) + (vn2**2 / (n2 - 1)))

        # p-value is hard without scipy, return t-stat and df
        return KernelOutput(
            success=True,
            result={
                "t_statistic": t_stat,
                "df": df,
                "method": "Welch's t-test",
                "note": "p-value requires lookup table or scipy",
            },
        )
