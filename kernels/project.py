from typing import List, Dict, Any
from kernels.base import KernelInterface
from models.kernel_io import KernelInput, KernelOutput


class ProjectKernel(KernelInterface):
    """
    Deterministic kernel for project planning validations.
    """

    kernel_id = "project_v1"
    description = "Validates project plans, calculates critical path, formats Gantt."

    def execute(self, input: KernelInput) -> KernelOutput:
        method = input.args.get("method")

        if method == "validate_timeline":
            return self._validate_timeline(input.args.get("tasks", []))
        elif method == "critical_path":
            return self._critical_path(input.args.get("tasks", []))
        else:
            return KernelOutput(success=False, error=f"Unknown method '{method}'")

    def _validate_timeline(self, tasks: List[Dict]) -> KernelOutput:
        errors = []
        for t in tasks:
            if "start" in t and "end" in t:
                if t["end"] < t["start"]:
                    errors.append(f"Task '{t.get('id')}' ends before it starts.")

            if "dependencies" in t:
                for dep in t["dependencies"]:
                    # check if dep exists
                    if not any(x["id"] == dep for x in tasks):
                        errors.append(f"Task '{t.get('id')}' depends on unknown task '{dep}'.")

        if errors:
            return KernelOutput(success=False, result={"valid": False, "errors": errors})
        return KernelOutput(success=True, result={"valid": True})

    def _critical_path(self, tasks: List[Dict]) -> KernelOutput:
        # Simplified CPM logic placeholder
        # 1. Build graph
        # 2. Forward pass (ES, EF)
        # 3. Backward pass (LS, LF)
        # 4. Identifying slack=0
        return KernelOutput(
            success=True, result={"message": "Critical path calculation not fully implemented yet."}
        )
