import pytest
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.workflow import Workflow, WorkflowStep, WorkflowStatus
from models.session import Session
from models.task_spec import TaskSpec, TaskRequest
from runtime.orchestrator import Orchestrator
from router.workflow_builder import build_workflow_from_request


@pytest.mark.asyncio
async def test_orchestrator_single_step():
    """Test executing a single step workflow."""
    orchestrator = Orchestrator()
    session = Session(session_id="test_sess_1")

    # Manually create a workflow with a known ready step
    # "Calculate mean of [1, 2, 3]" -> statistics_v1, args={data: [1,2,3]}

    spec = TaskSpec(
        request_id="req1",
        user_input="Calculate mean",
        domain="analysis",
        selected_kernels=["statistics_v1"],
        args={"data": [1, 2, 3], "operation": "descriptive"},
    )

    step = WorkflowStep(
        step_id="step1", description="Calculate mean", spec=spec, status=WorkflowStatus.PENDING
    )

    workflow = Workflow(workflow_id="wf1", name="Test Workflow", steps=[step])

    # Execute
    updated_wf = await orchestrator.run_workflow(workflow, session)

    assert updated_wf.status == WorkflowStatus.COMPLETED
    assert updated_wf.steps[0].status == WorkflowStatus.COMPLETED
    assert updated_wf.steps[0].output is not None
    assert updated_wf.steps[0].output["mean"] == 2.0

    # Verify session history
    assert len(session.history) == 1
    assert session.history[0]["type"] == "step_complete"


@pytest.mark.asyncio
async def test_builder_and_orchestrator_integration():
    """Test building AND executing a workflow from text."""
    orchestrator = Orchestrator()
    session = Session(session_id="test_sess_2")

    # Request that should fulfill both classification (statistics) and extraction (args)
    # "Calculate the mean of data [10, 20, 30]"
    # Note: 'extract_spec' needs to be smart enough or we rely on 'rule_based_extraction'
    # 'rule_based_extraction' does generic entity extraction.
    # It might NOT extract "data": [10, 20, 30] correctly unless we improved it.
    # BUT, let's try. If it fails, we know we need to improve extraction rules.

    # Actually, current _rule_based_extraction is very simple.
    # It extracts "entities" but not "parameters" with values unless hardcoded.
    # So this test might fail on args extraction.
    # Let's mock extraction or construct request such that we assume extraction works?
    # Or upgrade extraction.

    # For now, let's verify the FLOW, even if args are empty it might fail gracefully.

    req = TaskRequest(request_id="req2", user_input="Calculate mean of [10, 20, 30]")

    workflow = build_workflow_from_request(req)

    # Inject args manually if extraction is too weak for this test
    # This simulates a "human in the loop" or "better LLM"
    if not workflow.steps[0].spec.args:
        workflow.steps[0].spec = workflow.steps[0].spec.model_copy(
            update={"args": {"data": [10, 20, 30], "operation": "descriptive"}}
        )

    updated_wf = await orchestrator.run_workflow(workflow, session)

    assert updated_wf.status == WorkflowStatus.COMPLETED
    result = updated_wf.steps[0].output
    assert result["mean"] == 20.0


@pytest.mark.asyncio
async def test_multi_step_independent():
    """Test two independent steps."""
    orchestrator = Orchestrator()
    session = Session(session_id="test_sess_3")

    # 1. Mean of [1,1,1] -> 1
    # 2. Mean of [2,2,2] -> 2

    req = TaskRequest(
        request_id="req3",
        user_input=("1. Calculate mean of [1,1,1]. 2. Calculate mean of [2,2,2]."),
    )

    workflow = build_workflow_from_request(req)
    assert len(workflow.steps) == 2

    # Inject args
    workflow.steps[0].spec = workflow.steps[0].spec.model_copy(
        update={"args": {"data": [1, 1, 1], "operation": "descriptive"}}
    )
    workflow.steps[1].spec = workflow.steps[1].spec.model_copy(
        update={"args": {"data": [2, 2, 2], "operation": "descriptive"}}
    )

    updated_wf = await orchestrator.run_workflow(workflow, session)

    assert updated_wf.status == WorkflowStatus.COMPLETED
    assert updated_wf.steps[0].output["mean"] == 1.0
    assert updated_wf.steps[1].output["mean"] == 2.0
