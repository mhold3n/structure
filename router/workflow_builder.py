"""
Workflow Builder: Decomposes tasks into executable workflows.

Parses natural language requests into multi-step workflows with dependencies.
"""

import re
import uuid
from typing import List

from models.task_spec import TaskRequest, TaskSpec
from models.workflow import Workflow, WorkflowStep, WorkflowStatus
from router.llm_extractor import extract_spec, ExtractionConfig, ExtractionMode


class WorkflowBuilder:
    """Builds workflows from task requests."""

    def build_workflow(self, request: TaskRequest) -> Workflow:
        """
        Convert a task request into a workflow.

        Detects if the request is single-step or multi-step.
        """
        steps = self._decompose_request(request.user_input)

        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Workflow for: {request.user_input[:50]}...",
            steps=[],
            context=request.context or {},
        )

        previous_step_id = None

        for i, step_text in enumerate(steps):
            step_id = f"step_{i + 1}_{uuid.uuid4().hex[:6]}"

            # Extract spec for this step
            # We treat each step as a sub-request
            # Note: This is synchronous and sequential for now
            spec_result = extract_spec(step_text)

            # Ensure spec dict is valid for TaskSpec if possible
            spec_data = spec_result.spec
            task_spec = None

            if spec_data:
                # Inject necessary fields for TaskSpec validation
                if "request_id" not in spec_data:
                    spec_data["request_id"] = step_id
                if "user_input" not in spec_data:
                    spec_data["user_input"] = step_text

                try:
                    task_spec = TaskSpec(**spec_data)
                except Exception:
                    # If validation fails, leave spec as None or handle gracefully
                    # For now we just don't attach the invalid spec
                    pass

            step = WorkflowStep(
                step_id=step_id,
                description=step_text,
                spec=task_spec,
                status=WorkflowStatus.PENDING,
                depends_on=[previous_step_id] if previous_step_id else [],
            )

            workflow.add_step(step)
            previous_step_id = step_id

        return workflow

    def _decompose_request(self, text: str) -> List[str]:
        """
        Decompose text into steps.

        Heuristics:
        1. Numbered lists (1. Do X, 2. Do Y)
        2. Sequence keywords (First X, then Y, finally Z)
        3. Transition keywords (..., then ...)
        """
        text = text.strip()

        # 1. Check for numbered list pattern "1. ... 2. ..."
        # Split by "N. "
        numbered_steps = re.split(r"\s*\d+\.\s+", text)
        # Filter out empty strings (often the first if text starts with "1.")
        numbered_steps = [s.strip() for s in numbered_steps if s.strip()]

        if len(numbered_steps) > 1:
            return numbered_steps

        # 2. Check for "then", "next", "after that"
        # Be careful not to split inside sentences needlessly
        # Matches ", then " or "; then " or ". Then "
        split_pattern = r"[,;.]\s+(?:then|next|after that|finally)\s+"
        sequence_steps = re.split(split_pattern, text, flags=re.IGNORECASE)

        if len(sequence_steps) > 1:
            return [s.strip() for s in sequence_steps]

        # 3. Default: Single step
        return [text]


# Convenience function
def build_workflow_from_request(request: TaskRequest) -> Workflow:
    """Build a workflow from a TaskRequest."""
    builder = WorkflowBuilder()
    return builder.build_workflow(request)
