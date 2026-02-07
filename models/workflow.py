"""
Workflow: Multi-step task execution model.

Supports sequential and parallel execution of task specifications.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from models.task_spec import TaskSpec


class WorkflowStatus(str, Enum):
    """Status of a workflow or step."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkflowStep(BaseModel):
    """
    A single step in a workflow.

    Wraps a TaskSpec with execution context and dependencies.
    """

    step_id: str = Field(..., description="Unique ID for this step")
    description: str = Field(..., description="Human-readable description")
    spec: Optional[TaskSpec] = Field(None, description="The executable task specification")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    depends_on: list[str] = Field(
        default_factory=list, description="IDs of steps that must complete first"
    )
    output: Optional[Any] = Field(None, description="Result of the step execution")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def mark_active(self):
        """Mark step as active."""
        self.status = WorkflowStatus.ACTIVE
        self.started_at = datetime.utcnow()

    def mark_completed(self, output: Any):
        """Mark step as completed with output."""
        self.status = WorkflowStatus.COMPLETED
        self.output = output
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str):
        """Mark step as failed."""
        self.status = WorkflowStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()


class Workflow(BaseModel):
    """
    A collection of steps with dependencies.

    Represents a full multi-step task execution plan.
    """

    workflow_id: str = Field(..., description="Unique workflow ID")
    name: str = Field(..., description="Workflow name or objective")
    steps: list[WorkflowStep] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict, description="Shared workflow context")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        if any(s.step_id == step.step_id for s in self.steps):
            raise ValueError(f"Step ID {step.step_id} already exists")
        self.steps.append(step)
        self.updated_at = datetime.utcnow()

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_ready_steps(self) -> list[WorkflowStep]:
        """Get steps that are pending and have all dependencies met."""
        completed_ids = {s.step_id for s in self.steps if s.status == WorkflowStatus.COMPLETED}
        ready = []
        for step in self.steps:
            if step.status == WorkflowStatus.PENDING:
                if all(dep in completed_ids for dep in step.depends_on):
                    ready.append(step)
        return ready

    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return all(s.status == WorkflowStatus.COMPLETED for s in self.steps)
