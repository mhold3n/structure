import pytest
import sys
import os
from models.task_spec import TaskSpec, Domain, TaskRequest
from models.workflow import WorkflowStep, WorkflowStatus
from models.session import Session
from validator.gates import experiment_safety_gate, file_write_gate, Decision
from runtime.orchestrator import Orchestrator

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_experiment_safety_gate_sample_size():
    """Test sample size validation."""
    # Too small sample size
    spec = TaskSpec(
        request_id="1",
        user_input="Run an experiment with sample size 5",
        domain=Domain.EXPERIMENT,
        selected_kernels=["experiment_design_v1"],
        args={"sample_size": 5},  # Assuming extracted
    )
    decision = experiment_safety_gate(spec)
    # Should be WARN or REJECT depending on strictness. Policy says WARN for min_n=10?
    # Checking policy via gate logic: min is 10. n=5.
    # Gate logic: if n < min_n: WARN.
    assert decision.decision == Decision.WARN
    assert "below minimum" in decision.reasons[0]

    # Valid sample size
    spec_valid = TaskSpec(
        request_id="2",
        user_input="Run an experiment with sample size 50",
        domain=Domain.EXPERIMENT,
        args={"sample_size": 50},
    )
    decision_valid = experiment_safety_gate(spec_valid)
    assert decision_valid.decision == Decision.ACCEPT


def test_experiment_safety_gate_irb():
    """Test human subjects checks."""
    # Human subjects without IRB
    spec = TaskSpec(
        request_id="3",
        user_input="Interview patients about their symptoms",
        domain=Domain.EXPERIMENT,
    )
    decision = experiment_safety_gate(spec)
    assert decision.decision == Decision.CLARIFY
    assert "IRB_APPROVAL_REQUIRED" in decision.reasons

    # Human subjects WITH IRB
    spec_irb = TaskSpec(
        request_id="4",
        user_input="Interview patients (IRB protocol #12345)",
        domain=Domain.EXPERIMENT,
    )
    decision_irb = experiment_safety_gate(spec_irb)
    # Naive keyword check in gate: if "irb" in input -> ACCEPT
    assert decision_irb.decision == Decision.ACCEPT


def test_file_write_gate_blocks_secrets():
    """Test blocking of potential secrets."""
    spec = TaskSpec(
        request_id="5", user_input="Save this private_key to a file", domain=Domain.CODE
    )
    decision = file_write_gate(spec)
    assert decision.decision == Decision.REJECT
    assert "Potential secret exposure" in decision.reasons


def test_file_write_gate_allows_safe():
    """Test allowing safe writes."""
    spec = TaskSpec(request_id="6", user_input="Save the results to output.txt", domain=Domain.CODE)
    decision = file_write_gate(spec)
    assert decision.decision == Decision.ACCEPT


@pytest.mark.asyncio
async def test_orchestrator_enforces_gates():
    """Test that orchestrator blocks execution if gates fail."""
    orchestrator = Orchestrator()
    session = Session(session_id="test_sess_gates")

    # Create a spec that fails a BLOCKING gate (e.g. file write with secret)
    # Use 'file_write_gate' in required_gates
    spec = TaskSpec(
        request_id="block1",
        user_input="Write my secret_key to logs",
        domain=Domain.CODE,
        required_gates=["file_write_gate"],
        selected_kernels=["project_mgmt_v1"],  # Dummy kernel
    )

    step = WorkflowStep(
        step_id="step_block", description="Write secret", spec=spec, status=WorkflowStatus.PENDING
    )

    # Run step
    result_step = await orchestrator.run_step(step, session)

    assert result_step.status == WorkflowStatus.BLOCKED
    assert "Blocked by gates" in result_step.error
    assert "file_write_gate" in result_step.error
