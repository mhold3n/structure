from typing import List, Dict, Any
from kernels.base import KernelInterface, register_kernel
from models.kernel_io import KernelInput, KernelOutput


@register_kernel
class ProjectKernel(KernelInterface):
    """
    Deterministic kernel for project planning validations.
    """

    kernel_id = "project_mgmt_v1"
    version = "1.0.0"
    determinism_level = "D1"
    description = "Validates project plans, calculates critical path, formats Gantt."

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        errors = []
        if "method" not in args:
            errors.append("Missing 'method' argument")
        if "tasks" not in args:
            errors.append("Missing 'tasks' argument")
        return len(errors) == 0, errors

    def execute(self, input: KernelInput) -> KernelOutput:
        args = input.args
        valid, errors = self.validate_args(args)
        if not valid:
            return self._make_output(
                input.request_id, success=False, error="Invalid arguments: " + "; ".join(errors)
            )

        method = args.get("method")

        if method == "validate_timeline":
            output = self._validate_timeline(args.get("tasks", []))
            return self._make_output(
                input.request_id, success=output.success, result=output.result, error=output.error
            )
        elif method == "critical_path":
            output = self._critical_path(args.get("tasks", []))
            return self._make_output(
                input.request_id, success=output.success, result=output.result, error=output.error
            )
        else:
            return self._make_output(
                input.request_id, success=False, error=f"Unknown method '{method}'"
            )

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
