"""
Experiment Design Kernel: Experiment planning utilities.

Provides deterministic experiment design calculations:
- Randomization sequence generation (seeded)
- Power calculation
- Block randomization
- Covariate balance check
"""

import random
import math
from typing import Optional

from models.kernel_io import KernelInput, KernelOutput
from .base import KernelInterface, register_kernel


@register_kernel
class ExperimentKernel(KernelInterface):
    """
    Experiment design kernel.

    Determinism level: D1 (seeded randomization)

    Operations:
    - randomize: Generate treatment assignment sequence
    - power_calc: Statistical power calculation
    - block_randomize: Block randomization
    - balance_check: Check covariate balance
    """

    kernel_id = "experiment_design_v1"
    version = "1.0.0"
    determinism_level = "D1"

    SUPPORTED_OPERATIONS = ["randomize", "power_calc", "block_randomize", "balance_check"]

    def execute(self, input: KernelInput) -> KernelOutput:
        """Execute with typed KernelInput."""
        operation = input.args.get("operation", "")

        if operation == "randomize":
            return self._randomize(input.args, input.request_id)
        elif operation == "power_calc":
            return self._power_calc(input.args, input.request_id)
        elif operation == "block_randomize":
            return self._block_randomize(input.args, input.request_id)
        elif operation == "balance_check":
            return self._balance_check(input.args, input.request_id)
        else:
            return self._make_output(
                request_id=input.request_id,
                success=False,
                error=f"Unknown operation: {operation}. Supported: {self.SUPPORTED_OPERATIONS}",
            )

    def _randomize(self, args: dict, request_id: str) -> KernelOutput:
        """
        Generate randomized treatment assignments.

        Args:
            n: Number of subjects
            groups: Number of treatment groups (default 2)
            group_names: Names for groups (default ["Control", "Treatment"])
            seed: Random seed for reproducibility

        Returns:
            List of treatment assignments
        """
        n = args.get("n", 10)
        groups = args.get("groups", 2)
        group_names = args.get("group_names", ["Control", "Treatment"])
        seed = args.get("seed", 42)

        # Ensure we have enough group names
        while len(group_names) < groups:
            group_names.append(f"Group_{len(group_names) + 1}")

        # Seeded randomization for D1 determinism
        rng = random.Random(seed)
        assignments = [group_names[rng.randint(0, groups - 1)] for _ in range(n)]

        # Calculate group sizes
        group_counts = {name: assignments.count(name) for name in group_names[:groups]}

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "assignments": assignments,
                "n": n,
                "groups": groups,
                "group_counts": group_counts,
                "seed": seed,
            },
        )

    def _power_calc(self, args: dict, request_id: str) -> KernelOutput:
        """
        Calculate statistical power or required sample size.

        Args:
            effect_size: Expected effect size (Cohen's d)
            alpha: Significance level (default 0.05)
            n: Sample size per group (if calculating power)
            power: Desired power (if calculating sample size)

        Returns:
            Power or required sample size
        """
        effect_size = args.get("effect_size", 0.5)
        alpha = args.get("alpha", 0.05)
        n = args.get("n")
        target_power = args.get("power")

        # Z-scores for common values
        z_alpha = {0.01: 2.576, 0.05: 1.96, 0.10: 1.645}.get(alpha, 1.96)

        if n is not None:
            # Calculate power given sample size
            # Power ≈ Φ(effect_size * sqrt(n/2) - z_alpha/2)
            ncp = effect_size * math.sqrt(n / 2)
            # Approximate power using normal approximation
            z_power = ncp - z_alpha / 2
            # Convert z to power (using approximation)
            power = 0.5 * (1 + math.erf(z_power / math.sqrt(2)))
            power = max(0, min(1, power))

            return self._make_output(
                request_id=request_id,
                success=True,
                result={
                    "power": round(power, 4),
                    "n_per_group": n,
                    "total_n": n * 2,
                    "effect_size": effect_size,
                    "alpha": alpha,
                },
            )
        elif target_power is not None:
            # Calculate sample size given target power
            z_beta = {
                0.80: 0.84,
                0.85: 1.04,
                0.90: 1.28,
                0.95: 1.645,
            }.get(target_power, 0.84)

            n_per_group = math.ceil(2 * ((z_alpha + z_beta) / effect_size) ** 2)

            return self._make_output(
                request_id=request_id,
                success=True,
                result={
                    "n_per_group": n_per_group,
                    "total_n": n_per_group * 2,
                    "power": target_power,
                    "effect_size": effect_size,
                    "alpha": alpha,
                },
            )
        else:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Must provide either 'n' (to calculate power) or 'power' (to calculate n)",
            )

    def _block_randomize(self, args: dict, request_id: str) -> KernelOutput:
        """
        Block randomization for balanced groups.

        Args:
            n: Total number of subjects
            block_size: Size of each block (must be multiple of groups)
            groups: Number of treatment groups (default 2)
            seed: Random seed

        Returns:
            Balanced treatment assignments
        """
        n = args.get("n", 20)
        groups = args.get("groups", 2)
        block_size = args.get("block_size", groups * 2)
        seed = args.get("seed", 42)

        if block_size % groups != 0:
            return self._make_output(
                request_id=request_id,
                success=False,
                error=f"Block size ({block_size}) must be multiple of groups ({groups})",
            )

        per_group_in_block = block_size // groups
        rng = random.Random(seed)

        assignments = []
        num_blocks = math.ceil(n / block_size)

        for _ in range(num_blocks):
            # Create balanced block
            block = []
            for g in range(groups):
                block.extend([g] * per_group_in_block)
            rng.shuffle(block)
            assignments.extend(block)

        # Trim to exact n
        assignments = assignments[:n]

        # Calculate group counts
        group_counts = {f"Group_{i}": assignments.count(i) for i in range(groups)}

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "assignments": assignments,
                "n": n,
                "block_size": block_size,
                "groups": groups,
                "group_counts": group_counts,
                "num_blocks": num_blocks,
                "seed": seed,
            },
        )

    def _balance_check(self, args: dict, request_id: str) -> KernelOutput:
        """
        Check covariate balance between groups.

        Args:
            covariate: List of covariate values
            assignments: List of group assignments (0/1)

        Returns:
            Balance metrics (means, difference, normalized difference)
        """
        covariate = args.get("covariate", [])
        assignments = args.get("assignments", [])

        if len(covariate) != len(assignments):
            err_msg = (
                f"Covariate and assignments must have same length "
                f"({len(covariate)} vs {len(assignments)})"
            )
            return self._make_output(
                request_id=request_id,
                success=False,
                error=err_msg,
            )

        # Split by group
        group0 = [covariate[i] for i in range(len(covariate)) if assignments[i] == 0]
        group1 = [covariate[i] for i in range(len(covariate)) if assignments[i] == 1]

        if not group0 or not group1:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Each group must have at least one observation",
            )

        mean0 = sum(group0) / len(group0)
        mean1 = sum(group1) / len(group1)

        # Pooled standard deviation
        var0 = sum((x - mean0) ** 2 for x in group0) / len(group0)
        var1 = sum((x - mean1) ** 2 for x in group1) / len(group1)
        pooled_sd = math.sqrt((var0 + var1) / 2)

        # Normalized difference (Rubin, 2001)
        if pooled_sd > 0:
            normalized_diff = (mean1 - mean0) / pooled_sd
        else:
            normalized_diff = 0 if mean0 == mean1 else float("inf")

        # Balance is typically acceptable if |normalized_diff| < 0.25
        balanced = abs(normalized_diff) < 0.25

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "mean_group0": round(mean0, 4),
                "mean_group1": round(mean1, 4),
                "difference": round(mean1 - mean0, 4),
                "normalized_difference": round(normalized_diff, 4),
                "balanced": balanced,
                "n_group0": len(group0),
                "n_group1": len(group1),
            },
        )

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """Validate inputs for experiment operations."""
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
            "randomize_params": ["n", "groups", "group_names", "seed"],
            "power_calc_params": ["effect_size", "alpha", "n", "power"],
            "block_randomize_params": ["n", "block_size", "groups", "seed"],
            "balance_check_params": ["covariate", "assignments"],
        }
