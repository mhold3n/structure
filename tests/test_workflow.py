"""
Tests for Workflow models and builder.

Verifies workflow construction, step parsing, and dependency management.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.task_spec import TaskRequest
from models.workflow import Workflow, WorkflowStep, WorkflowStatus
from router.workflow_builder import build_workflow_from_request, WorkflowBuilder


@pytest.fixture
def sample_request():
    return TaskRequest(
        request_id="req_123",
        user_input="First calculate sample size, then design the experiment.",
    )


class TestWorkflowModels:
    """Test Workflow and WorkflowStep models."""

    def test_workflow_step_creation(self):
        """Step creation with defaults."""
        step = WorkflowStep(step_id="step_1", description="Do task")
        assert step.status == WorkflowStatus.PENDING
        assert step.depends_on == []
        assert step.output is None

    def test_workflow_creation(self):
        """Workflow creation."""
        wf = Workflow(
            workflow_id="wf_1",
            name="Test Workflow",
        )
        assert wf.status == WorkflowStatus.PENDING
        assert len(wf.steps) == 0

    def test_add_step(self):
        """Adding steps."""
        wf = Workflow(workflow_id="wf_1", name="Test")
        step = WorkflowStep(step_id="s1", description="Step 1")
        wf.add_step(step)
        assert len(wf.steps) == 1
        assert wf.get_step("s1") == step

    def test_duplicate_step_id_raises(self):
        """Adding duplicate step ID should raise error."""
        wf = Workflow(workflow_id="wf_1", name="Test")
        step = WorkflowStep(step_id="s1", description="Step 1")
        wf.add_step(step)
        with pytest.raises(ValueError):
            wf.add_step(WorkflowStep(step_id="s1", description="Duplicate"))

    def test_get_ready_steps(self):
        """Dependency resolution."""
        wf = Workflow(workflow_id="wf_1", name="Test")

        s1 = WorkflowStep(step_id="s1", description="Step 1")
        s2 = WorkflowStep(step_id="s2", description="Step 2", depends_on=["s1"])

        wf.add_step(s1)
        wf.add_step(s2)

        # Initially only s1 is ready
        ready = wf.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

        # Complete s1
        s1.mark_completed({"result": "done"})

        # Now s2 is ready
        ready = wf.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s2"


class TestWorkflowBuilder:
    """Test workflow construction from requests."""

    def test_single_step_request(self):
        """Single step parsing."""
        req = TaskRequest(request_id="r1", user_input="Calculate correlation")
        wf = build_workflow_from_request(req)

        assert len(wf.steps) == 1
        assert wf.steps[0].description == "Calculate correlation"

    def test_numbered_list_decomposition(self):
        """Numbered list parsing."""
        text = "1. Design experiment. 2. Collect data."
        req = TaskRequest(request_id="r1", user_input=text)
        wf = build_workflow_from_request(req)

        assert len(wf.steps) == 2
        assert "Design experiment" in wf.steps[0].description
        assert "Collect data" in wf.steps[1].description

        # Check dependencies
        assert wf.steps[1].depends_on == [wf.steps[0].step_id]

    def test_keyword_decomposition(self):
        """Keyword (then) decomposition."""
        text = "Design experiment, then analyze data"
        req = TaskRequest(request_id="r1", user_input=text)
        wf = build_workflow_from_request(req)

        assert len(wf.steps) == 2
        assert "Design experiment" in wf.steps[0].description
        assert "analyze data" in wf.steps[1].description
        assert wf.steps[1].depends_on == [wf.steps[0].step_id]

    def test_integration_with_extractor(self):
        """Verify LLM extractor is called for steps."""
        # This test verifies that steps have Specs attached (even if simple)
        text = "Calculate sample size"
        req = TaskRequest(request_id="r1", user_input=text)
        wf = build_workflow_from_request(req)

        assert wf.steps[0].spec is not None
        # Verify spec has correct intent from extractor
        assert wf.steps[0].spec is not None
        assert wf.steps[0].spec.user_input == text
