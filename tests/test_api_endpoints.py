import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from gateway.main import app, sessions, active_workflows
from models.workflow import Workflow, WorkflowStep, WorkflowStatus
from models.session import Session
from models.task_spec import TaskSpec, Domain

client = TestClient(app)


@pytest.fixture
def mock_orchestrator():
    with patch("gateway.main.orchestrator") as mock_orch:
        # Async mock for run_workflow
        mock_orch.run_workflow = AsyncMock()
        yield mock_orch


def test_experiment_endpoint(mock_orchestrator):
    """Test POST /experiment routes with correct domain hint."""
    # Mock submit_task behavior by mocking what it calls: classify_task, etc.
    # OR better, mock submit_task internals?
    # submit_task calls classify_task, run_gates, then returns TaskResponse.
    # To avoid mocking all that, let's mock the `submit_task` function itself?
    # But `submit_task` is an endpoint function.
    # We can patch `gateway.main.submit_task`? No, because it's imported/defined in module.

    # We'll use the real pipeline but mock `classify_task` to return a valid spec
    with (
        patch("gateway.main.classify_task") as mock_classify,
        patch("gateway.main.run_gates") as mock_gates,
    ):
        mock_classify.return_value = TaskSpec(
            request_id="123", user_input="test", domain=Domain.EXPERIMENT
        )
        mock_gates.return_value = []  # No gates blocking

        response = client.post("/experiment", json={"user_input": "Design a study"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Since classify_task was mocked, we can't check if domain_hint was passed to it
        # unless we check call_args on classify_task

        # Verify domain_hint was in the request passed to classify_task
        # classify_task takes TaskRequest.
        call_arg = mock_classify.call_args[0][0]
        assert call_arg.domain_hint == "experiment"


def test_project_plan_endpoint(mock_orchestrator):
    with (
        patch("gateway.main.classify_task") as mock_classify,
        patch("gateway.main.run_gates") as mock_gates,
    ):
        mock_classify.return_value = TaskSpec(
            request_id="124", user_input="test", domain=Domain.PROJECT
        )
        mock_gates.return_value = []

        response = client.post("/project-plan", json={"user_input": "Plan X"})
        assert response.status_code == 200

        call_arg = mock_classify.call_args[0][0]
        assert call_arg.domain_hint == "project"


def test_session_endpoints(mock_orchestrator):
    """Test GET /session and POST /session/answer."""
    # 1. Setup Session and Active Workflow
    sess_id = "sess_test_1"
    session = Session(session_id=sess_id, user_id="u1")
    sessions[sess_id] = session

    spec = TaskSpec(request_id="r1", user_input="test", domain=Domain.EXPERIMENT)
    workflow = Workflow(
        workflow_id="wf_1",
        name="Test Workflow",
        steps=[
            WorkflowStep(
                step_id="s1", description="Test step", status=WorkflowStatus.BLOCKED, spec=spec
            )
        ],
    )
    session.active_workflow_id = workflow.workflow_id
    active_workflows[workflow.workflow_id] = workflow

    # 2. Test GET session
    resp = client.get(f"/session/{sess_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sess_id

    # 3. Test POST answer
    # Mock orchestrator to return updated workflow
    mock_orchestrator.run_workflow.return_value = Workflow(
        workflow_id="wf_1",
        name="Test Workflow",
        steps=[
            WorkflowStep(
                step_id="s1", description="Test step", status=WorkflowStatus.COMPLETED, spec=spec
            )
        ],
        status=WorkflowStatus.COMPLETED,
    )

    answers = [{"question_id": "q1", "answer": "42"}]
    resp_ans = client.post(f"/session/{sess_id}/answer", json=answers)

    assert resp_ans.status_code == 200
    assert resp_ans.json()["status"] == "completed"

    # Verify context updated
    assert session.context.get("answer_q1") == "42"
    # Verify step unblocked (reset to pending/active before run)
    # The test verified that run_workflow was called.
    mock_orchestrator.run_workflow.assert_called_once()

    # Verify workflow passed to orchestrator has updated context
    called_workflow = mock_orchestrator.run_workflow.call_args[0][0]
    assert called_workflow.context.get("answer_q1") == "42"
