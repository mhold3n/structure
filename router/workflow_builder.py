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
from router.classifier import classify_task


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

            # 1. Classify step to get domain and kernels (Deterministic)
            step_request = TaskRequest(
                request_id=step_id,
                user_input=step_text,
                context=request.context,
            )
            try:
                classified_spec = classify_task(step_request)
                spec_data = classified_spec.model_dump()
            except Exception:
                # Fallback if classification fails
                spec_data = {}

            # 2. Extract parameters using LLM (D2 Determinism)
            # This fills in 'args' and other metadata
            extract_result = extract_spec(step_text)

            if extract_result.success and extract_result.spec:
                extracted_data = extract_result.spec
                # Merge parameters into args
                if "parameters" in extracted_data:
                    spec_data["args"] = extracted_data["parameters"]

                # Merge other fields if missing in classification
                if "intent" in extracted_data and "intent" not in spec_data:
                    # TaskSpec doesn't have intent field yet, but might in future
                    pass

            # 3. Create final merged TaskSpec
            # Ensure required fields are present
            if "request_id" not in spec_data:
                spec_data["request_id"] = step_id
            if "user_input" not in spec_data:
                spec_data["user_input"] = step_text

            try:
                task_spec = TaskSpec(**spec_data)
            except Exception:
                task_spec = None

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
