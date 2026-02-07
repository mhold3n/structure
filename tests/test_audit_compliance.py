import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch
from models.task_spec import TaskSpec, Domain
from models.workflow import WorkflowStep, WorkflowStatus
from models.session import Session
from runtime.orchestrator import Orchestrator
from gateway.logging import AuditRecord

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.mark.asyncio
async def test_audit_logging_success():
    """Test that successful steps generate audit logs."""
    # Patch get_kernel to return a mock kernel class
    with patch("gateway.logging.StructuredLogger.log_audit") as mock_log, \
         patch("runtime.orchestrator.get_kernel") as mock_get_kernel:
        
        # Setup mock kernel
        mock_kernel_instance = MagicMock()
        mock_kernel_instance.execute.return_value = MagicMock(success=True, result={"status": "ok"})
        mock_kernel_class = MagicMock(return_value=mock_kernel_instance)
        mock_get_kernel.return_value = mock_kernel_class
        
        orchestrator = Orchestrator()
        orchestrator.compliance.check_access = MagicMock(return_value=True)
        
        session = Session(session_id="audit_sess", user_id="test_user")
        
        spec = TaskSpec(
            request_id="audit1", 
            user_input="Test", 
            domain=Domain.CODE,
            selected_kernels=["mock_kernel"]
        )
        step = WorkflowStep(step_id="step1", description="Test", spec=spec)
        
        await orchestrator.run_step(step, session)
        
        assert mock_log.called
        call_args = mock_log.call_args[0][0]
        assert isinstance(call_args, AuditRecord)
        assert call_args.action == "step_execution"
        assert call_args.status == "SUCCESS"
        assert call_args.actor_id == "test_user"

@pytest.mark.asyncio
async def test_compliance_blocking():
    """Test that compliance checker blocks execution."""
    with patch("gateway.logging.StructuredLogger.log_audit") as mock_log:
        orchestrator = Orchestrator()
        # Mock compliance to DENY
        orchestrator.compliance.check_access = MagicMock(return_value=False)
        
        session = Session(session_id="comp_sess", user_id="bad_actor")
        
        spec = TaskSpec(
            request_id="comp1", 
            user_input="Sensitive Op", 
            domain=Domain.CODE,
            selected_kernels=["project_mgmt_v1"]
        )
        step = WorkflowStep(step_id="step_sensitive", description="Sensitive", spec=spec)
        
        result = await orchestrator.run_step(step, session)
        
        assert result.status == WorkflowStatus.BLOCKED
        assert "Compliance violation" in result.error
        
        # Verify audit log for BLOCK
        assert mock_log.called
        call_args = mock_log.call_args[0][0]
        assert call_args.status == "BLOCKED"
        assert "access_control" in call_args.policy_violations

@pytest.mark.asyncio
async def test_gate_blocking_audit():
    """Test that gate failures generate audit logs."""
    with patch("gateway.logging.StructuredLogger.log_audit") as mock_log:
        orchestrator = Orchestrator()
        orchestrator.compliance.check_access = MagicMock(return_value=True)
        session = Session(session_id="gate_audit_sess", user_id="user")
        
        # Spec that fails a gate
        spec = TaskSpec(
            request_id="block2",
            user_input="Write secret_key now",
            domain=Domain.CODE,
            required_gates=["file_write_gate"]
        )
        step = WorkflowStep(step_id="step_gate_fail", description="Fail Gate", spec=spec)
        
        await orchestrator.run_step(step, session)
        
        # Should call log_audit for the BLOCK
        assert mock_log.called
        call_args = mock_log.call_args[0][0]
        assert call_args.status == "BLOCKED"
        assert "Gate Failure" in call_args.details["reason"]
