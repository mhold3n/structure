"""
Project Management Kernel: Project planning utilities.

Provides deterministic project management calculations:
- Gantt chart/schedule generation
- Critical path analysis
- Risk matrix generation
- Resource allocation
"""

from datetime import datetime, timedelta
from typing import Optional

from models.kernel_io import KernelInput, KernelOutput
from .base import KernelInterface, register_kernel


@register_kernel
class ProjectKernel(KernelInterface):
    """
    Project management kernel.

    Determinism level: D1 (pure calculation)

    Operations:
    - schedule: Generate task schedule (Gantt)
    - critical_path: Identify critical path
    - risk_matrix: Generate risk assessment
    - resource_allocation: Allocate resources to tasks
    """

    kernel_id = "project_mgmt_v1"
    version = "1.0.0"
    determinism_level = "D1"

    SUPPORTED_OPERATIONS = ["schedule", "critical_path", "risk_matrix", "resource_allocation"]

    def execute(self, input: KernelInput) -> KernelOutput:
        """Execute with typed KernelInput."""
        operation = input.args.get("operation", "")

        if operation == "schedule":
            return self._schedule(input.args, input.request_id)
        elif operation == "critical_path":
            return self._critical_path(input.args, input.request_id)
        elif operation == "risk_matrix":
            return self._risk_matrix(input.args, input.request_id)
        elif operation == "resource_allocation":
            return self._resource_allocation(input.args, input.request_id)
        else:
            return self._make_output(
                request_id=input.request_id,
                success=False,
                error=f"Unknown operation: {operation}. Supported: {self.SUPPORTED_OPERATIONS}",
            )

    def _schedule(self, args: dict, request_id: str) -> KernelOutput:
        """
        Generate task schedule.

        Args:
            tasks: List of {name, duration_days, dependencies (optional)}
            start_date: Project start date (YYYY-MM-DD)

        Returns:
            Schedule with start/end dates for each task
        """
        tasks = args.get("tasks", [])
        start_date_str = args.get("start_date", datetime.now().strftime("%Y-%m-%d"))

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return self._make_output(
                request_id=request_id,
                success=False,
                error=f"Invalid start_date format: {start_date_str}. Use YYYY-MM-DD.",
            )

        if not tasks:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Tasks list cannot be empty",
            )

        # Build task index
        task_index = {t["name"]: i for i, t in enumerate(tasks)}
        schedule = []

        # Calculate earliest start for each task
        for task in tasks:
            name = task["name"]
            duration = task.get("duration_days", 1)
            dependencies = task.get("dependencies", [])

            # Find latest end of dependencies
            if dependencies:
                dep_ends = []
                for dep in dependencies:
                    if dep in task_index:
                        dep_idx = task_index[dep]
                        if dep_idx < len(schedule):
                            dep_ends.append(datetime.strptime(schedule[dep_idx]["end"], "%Y-%m-%d"))
                if dep_ends:
                    task_start = max(dep_ends)
                else:
                    task_start = start_date
            else:
                task_start = start_date

            task_end = task_start + timedelta(days=duration)

            schedule.append(
                {
                    "name": name,
                    "duration_days": duration,
                    "start": task_start.strftime("%Y-%m-%d"),
                    "end": task_end.strftime("%Y-%m-%d"),
                    "dependencies": dependencies,
                }
            )

        # Calculate project end
        project_end = max(datetime.strptime(t["end"], "%Y-%m-%d") for t in schedule)
        total_duration = (project_end - start_date).days

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "schedule": schedule,
                "project_start": start_date_str,
                "project_end": project_end.strftime("%Y-%m-%d"),
                "total_duration_days": total_duration,
            },
        )

    def _critical_path(self, args: dict, request_id: str) -> KernelOutput:
        """
        Identify critical path through project.

        Args:
            tasks: List of {name, duration_days, dependencies}

        Returns:
            Critical path and total duration
        """
        tasks = args.get("tasks", [])

        if not tasks:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Tasks list cannot be empty",
            )

        # Build adjacency list and calculate early start/finish
        task_index = {t["name"]: i for i, t in enumerate(tasks)}
        n = len(tasks)

        # Early start/finish (forward pass)
        early_start = [0] * n
        early_finish = [0] * n

        for i, task in enumerate(tasks):
            duration = task.get("duration_days", 1)
            dependencies = task.get("dependencies", [])

            if dependencies:
                early_start[i] = max(
                    early_finish[task_index[dep]] for dep in dependencies if dep in task_index
                )
            else:
                early_start[i] = 0

            early_finish[i] = early_start[i] + duration

        project_duration = max(early_finish)

        # Late start/finish (backward pass)
        late_finish = [project_duration] * n
        late_start = [0] * n

        for i in range(n - 1, -1, -1):
            task = tasks[i]
            duration = task.get("duration_days", 1)

            # Find successors
            successors = [
                j for j, t in enumerate(tasks) if task["name"] in t.get("dependencies", [])
            ]

            if successors:
                late_finish[i] = min(late_start[j] for j in successors)
            else:
                late_finish[i] = project_duration

            late_start[i] = late_finish[i] - duration

        # Slack = late_start - early_start
        # Critical path has zero slack
        critical_path = []
        for i, task in enumerate(tasks):
            slack = late_start[i] - early_start[i]
            if slack == 0:
                critical_path.append(task["name"])

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "critical_path": critical_path,
                "project_duration_days": project_duration,
                "task_details": [
                    {
                        "name": tasks[i]["name"],
                        "early_start": early_start[i],
                        "early_finish": early_finish[i],
                        "late_start": late_start[i],
                        "late_finish": late_finish[i],
                        "slack": late_start[i] - early_start[i],
                        "critical": late_start[i] == early_start[i],
                    }
                    for i in range(n)
                ],
            },
        )

    def _risk_matrix(self, args: dict, request_id: str) -> KernelOutput:
        """
        Generate risk assessment matrix.

        Args:
            risks: List of {name, probability (1-5), impact (1-5), description}

        Returns:
            Risk matrix with scores and priorities
        """
        risks = args.get("risks", [])

        if not risks:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Risks list cannot be empty",
            )

        risk_matrix = []
        for risk in risks:
            name = risk.get("name", "Unnamed")
            probability = risk.get("probability", 3)
            impact = risk.get("impact", 3)
            description = risk.get("description", "")

            # Validate ranges
            probability = max(1, min(5, probability))
            impact = max(1, min(5, impact))

            score = probability * impact

            # Priority levels
            if score >= 15:
                priority = "Critical"
            elif score >= 10:
                priority = "High"
            elif score >= 5:
                priority = "Medium"
            else:
                priority = "Low"

            risk_matrix.append(
                {
                    "name": name,
                    "probability": probability,
                    "impact": impact,
                    "score": score,
                    "priority": priority,
                    "description": description,
                }
            )

        # Sort by score descending
        risk_matrix.sort(key=lambda x: -x["score"])

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "risk_matrix": risk_matrix,
                "total_risks": len(risk_matrix),
                "critical_count": sum(1 for r in risk_matrix if r["priority"] == "Critical"),
                "high_count": sum(1 for r in risk_matrix if r["priority"] == "High"),
            },
        )

    def _resource_allocation(self, args: dict, request_id: str) -> KernelOutput:
        """
        Allocate resources to tasks.

        Args:
            tasks: List of {name, resource_hours}
            resources: List of {name, available_hours}

        Returns:
            Allocation matrix and utilization
        """
        tasks = args.get("tasks", [])
        resources = args.get("resources", [])

        if not tasks or not resources:
            return self._make_output(
                request_id=request_id,
                success=False,
                error="Both tasks and resources must be provided",
            )

        # Simple greedy allocation
        allocation = []
        resource_remaining = {r["name"]: r.get("available_hours", 40) for r in resources}

        for task in tasks:
            task_name = task["name"]
            required_hours = task.get("resource_hours", 8)

            # Find resource with most available hours
            available_resources = [
                (r, resource_remaining[r])
                for r in resource_remaining
                if resource_remaining[r] >= required_hours
            ]

            if available_resources:
                # Assign to first available
                assigned = available_resources[0][0]
                resource_remaining[assigned] -= required_hours
                allocation.append(
                    {
                        "task": task_name,
                        "assigned_to": assigned,
                        "hours": required_hours,
                    }
                )
            else:
                allocation.append(
                    {
                        "task": task_name,
                        "assigned_to": None,
                        "hours": required_hours,
                        "warning": "No resource with sufficient capacity",
                    }
                )

        # Calculate utilization
        utilization = {}
        for r in resources:
            name = r["name"]
            total = r.get("available_hours", 40)
            used = total - resource_remaining[name]
            utilization[name] = round(used / total * 100, 1) if total > 0 else 0

        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "allocation": allocation,
                "utilization": utilization,
                "unassigned_tasks": [a["task"] for a in allocation if a["assigned_to"] is None],
            },
        )

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """Validate inputs for project operations."""
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
            "schedule_params": ["tasks", "start_date"],
            "critical_path_params": ["tasks"],
            "risk_matrix_params": ["risks"],
            "resource_allocation_params": ["tasks", "resources"],
        }
