"""
Data Summary Kernel: Data summarization utilities.

Provides deterministic data summarization:
- Pivot table / group-by aggregation
- Summary statistics
- Missing data analysis
- Distribution analysis
"""

import math
from typing import Optional

from models.kernel_io import KernelInput, KernelOutput
from .base import KernelInterface, register_kernel


@register_kernel
class DataSummaryKernel(KernelInterface):
    """
    Data summarization kernel.

    Determinism level: D1 (pure calculation)

    Operations:
    - pivot: Group-by aggregation (pivot table)
    - summary: Column-wise summary statistics
    - missing: Missing data analysis
    - distribution: Distribution analysis
    """

    kernel_id = "data_summary_v1"
    version = "1.0.0"
    determinism_level = "D1"

    SUPPORTED_OPERATIONS = ["pivot", "summary", "missing", "distribution"]

    def execute(self, input: KernelInput) -> KernelOutput:
        """Execute with typed KernelInput."""
        operation = input.args.get("operation", "")

        if operation == "pivot":
            return self._pivot(input.args, input.request_id)
        elif operation == "summary":
            return self._summary(input.args, input.request_id)
        elif operation == "missing":
            return self._missing(input.args, input.request_id)
        elif operation == "distribution":
            return self._distribution(input.args, input.request_id)
        else:
            return self._make_output(
                request_id=input.request_id,
                success=False,
                error=f"Unknown operation: {operation}. Supported: {self.SUPPORTED_OPERATIONS}",
            )

    def _pivot(self, args: dict, request_id: str) -> KernelOutput:
        """
        Pivot table / group-by aggregation.

        Args:
            data: List of dicts (rows)
            group_by: Column to group by
            value_column: Column to aggregate
            agg_func: Aggregation function (sum, mean, count, min, max)

        Returns:
            Grouped aggregation results
        """
        data = args.get("data", [])
        group_by = args.get("group_by", "")
        value_column = args.get("value_column", "")
        agg_func = args.get("agg_func", "sum")

        if not data:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Data cannot be empty",
            )

        if not group_by or not value_column:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="group_by and value_column are required",
            )

        # Group data
        groups = {}
        for row in data:
            key = row.get(group_by)
            value = row.get(value_column)
            if key is not None and value is not None:
                if key not in groups:
                    groups[key] = []
                groups[key].append(value)

        # Aggregate
        result = {}
        for key, values in groups.items():
            if agg_func == "sum":
                result[key] = sum(values)
            elif agg_func == "mean":
                result[key] = round(sum(values) / len(values), 4)
            elif agg_func == "count":
                result[key] = len(values)
            elif agg_func == "min":
                result[key] = min(values)
            elif agg_func == "max":
                result[key] = max(values)
            else:
                result[key] = sum(values)

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "pivot": result,
                "group_by": group_by,
                "value_column": value_column,
                "agg_func": agg_func,
                "num_groups": len(result),
            },
        )

    def _summary(self, args: dict, request_id: str) -> KernelOutput:
        """
        Column-wise summary statistics.

        Args:
            data: List of dicts (rows)
            columns: List of columns to summarize (optional, defaults to all numeric)

        Returns:
            Summary stats for each column
        """
        data = args.get("data", [])
        columns = args.get("columns", None)

        if not data:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Data cannot be empty",
            )

        # Detect columns if not specified
        if columns is None:
            columns = list(data[0].keys()) if data else []

        summaries = {}
        for col in columns:
            values = [row.get(col) for row in data if row.get(col) is not None]

            # Check if numeric
            numeric_values = [v for v in values if isinstance(v, (int, float))]

            if numeric_values:
                n = len(numeric_values)
                mean = sum(numeric_values) / n
                sorted_vals = sorted(numeric_values)

                if n % 2 == 0:
                    median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
                else:
                    median = sorted_vals[n // 2]

                variance = sum((x - mean) ** 2 for x in numeric_values) / (n - 1) if n > 1 else 0
                std = math.sqrt(variance)

                summaries[col] = {
                    "type": "numeric",
                    "count": n,
                    "mean": round(mean, 4),
                    "median": round(median, 4),
                    "std": round(std, 4),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                }
            else:
                # Categorical summary
                value_counts = {}
                for v in values:
                    value_counts[str(v)] = value_counts.get(str(v), 0) + 1

                summaries[col] = {
                    "type": "categorical",
                    "count": len(values),
                    "unique": len(value_counts),
                    "top_values": dict(sorted(value_counts.items(), key=lambda x: -x[1])[:5]),
                }

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "summaries": summaries,
                "total_rows": len(data),
                "columns_analyzed": len(summaries),
            },
        )

    def _missing(self, args: dict, request_id: str) -> KernelOutput:
        """
        Missing data analysis.

        Args:
            data: List of dicts (rows)

        Returns:
            Missing data counts and percentages
        """
        data = args.get("data", [])

        if not data:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Data cannot be empty",
            )

        # Get all columns
        all_columns = set()
        for row in data:
            all_columns.update(row.keys())

        n_rows = len(data)
        missing_report = {}

        for col in all_columns:
            missing_count = sum(1 for row in data if row.get(col) is None)
            missing_pct = round(missing_count / n_rows * 100, 2)

            missing_report[col] = {
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "present_count": n_rows - missing_count,
            }

        # Overall completeness
        total_cells = n_rows * len(all_columns)
        total_missing = sum(r["missing_count"] for r in missing_report.values())

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "missing_by_column": missing_report,
                "total_rows": n_rows,
                "total_columns": len(all_columns),
                "total_missing": total_missing,
                "completeness_pct": (
                    round((1 - total_missing / total_cells) * 100, 2) if total_cells > 0 else 100
                ),
            },
        )

    def _distribution(self, args: dict, request_id: str) -> KernelOutput:
        """
        Distribution analysis for numeric column.

        Args:
            values: List of numeric values
            bins: Number of histogram bins (default 10)

        Returns:
            Distribution metrics and histogram
        """
        values = args.get("values", [])
        bins = args.get("bins", 10)

        if not values:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Values cannot be empty",
            )

        # Filter to numeric
        numeric = [v for v in values if isinstance(v, (int, float))]
        if not numeric:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="No numeric values found",
            )

        n = len(numeric)
        mean = sum(numeric) / n
        sorted_vals = sorted(numeric)

        # Median
        if n % 2 == 0:
            median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            median = sorted_vals[n // 2]

        # Variance, skewness, kurtosis
        variance = sum((x - mean) ** 2 for x in numeric) / (n - 1) if n > 1 else 0
        std = math.sqrt(variance)

        # Skewness
        if std > 0 and n > 2:
            skewness = sum((x - mean) ** 3 for x in numeric) / (n * std**3)
        else:
            skewness = 0

        # Kurtosis (excess)
        if std > 0 and n > 3:
            kurtosis = sum((x - mean) ** 4 for x in numeric) / (n * std**4) - 3
        else:
            kurtosis = 0

        # Histogram
        min_val, max_val = min(numeric), max(numeric)
        if min_val == max_val:
            histogram = [{"bin_start": min_val, "bin_end": max_val, "count": n}]
        else:
            bin_width = (max_val - min_val) / bins
            histogram = []
            for i in range(bins):
                bin_start = min_val + i * bin_width
                bin_end = min_val + (i + 1) * bin_width
                is_last = i == bins - 1
                count = sum(
                    1 for v in numeric if (bin_start <= v < bin_end) or (is_last and v == max_val)
                )
                histogram.append(
                    {
                        "bin_start": round(bin_start, 4),
                        "bin_end": round(bin_end, 4),
                        "count": count,
                    }
                )

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "n": n,
                "mean": round(mean, 4),
                "median": round(median, 4),
                "std": round(std, 4),
                "min": min_val,
                "max": max_val,
                "skewness": round(skewness, 4),
                "kurtosis": round(kurtosis, 4),
                "histogram": histogram,
            },
        )

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """Validate inputs for data summary operations."""
        errors = []

        operation = args.get("operation")
        if not operation:
            errors.append("Missing required field: operation")
        elif operation not in self.SUPPORTED_OPERATIONS:
            errors.append(f"Unknown operation: {operation}")

        return (len(errors) == 0, errors)

    def get_envelope(self) -> dict:
        """Return valid input envelope."""
        return {
            "supported_operations": self.SUPPORTED_OPERATIONS,
            "pivot_params": ["data", "group_by", "value_column", "agg_func"],
            "summary_params": ["data", "columns"],
            "missing_params": ["data"],
            "distribution_params": ["values", "bins"],
        }
