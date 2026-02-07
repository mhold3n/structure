import logging
import uuid
import traceback
from typing import Optional, Dict, Any, List

from models.workflow import Workflow, WorkflowStep, WorkflowStatus
from models.task_spec import TaskSpec
from models.kernel_io import KernelInput, KernelOutput
from models.session import Session
from kernels import get_kernel
from router.classifier import classify_task  # To deduce kernels if not set
from validator.gates import run_gates, get_blocking_decisions
from gateway.logging import StructuredLogger, AuditRecord
from gateway.compliance import ComplianceChecker

logger_struct = StructuredLogger("orchestrator")
logger = logging.getLogger("orchestrator")

class Orchestrator:
    """
    Runtime engine for executing workflows.
    """
    
    def __init__(self):
        self.compliance = ComplianceChecker()

    async def run_step(self, step: WorkflowStep, session: Session) -> WorkflowStep:
        """
        Execute a single workflow step.
        """
        logger.info(f"Executing step {step.step_id}: {step.description}")
        step.status = WorkflowStatus.ACTIVE
        
        try:
            # 0. Compliance Check (Phase 6)
            user_id = session.user_id if hasattr(session, "user_id") else "unknown"
            if not self.compliance.check_access(user_id, step.step_id, "execute"):
                # Log violation
                audit = AuditRecord(
                    event_id=str(uuid.uuid4()),
                    actor_id=user_id,
                    action="step_execution_attempt",
                    resource_id=step.step_id,
                    status="BLOCKED",
                    details={"reason": "Access Denied"},
                    policy_violations=["access_control"]
                )
                logger_struct.log_audit(audit)
                
                step.status = WorkflowStatus.BLOCKED
                step.error = "Compliance violation: Access Denied"
                return step

            # 1. Resolve TaskSpec
            if not step.spec:
                # If spec is missing, this is a failure in the build phase
                raise ValueError(f"Step {step.step_id} has no TaskSpec")
            
            spec = step.spec
            
            # 1b. Run Gates (New Phase 5 Requirement)
            gate_decisions = run_gates(spec)
            blocking = get_blocking_decisions(gate_decisions)
            
            if blocking:
                # Log blocking reasons
                reasons = [f"{d.gate_id}: {', '.join(d.reasons)}" for d in blocking]
                
                # Audit Block
                audit = AuditRecord(
                    event_id=str(uuid.uuid4()),
                    actor_id=user_id,
                    action="step_execution_attempt",
                    resource_id=step.step_id,
                    status="BLOCKED",
                    details={"reason": "Gate Failure", "gates": reasons},
                    gates_passed=[g.gate_id for g in gate_decisions if not g.is_blocking()]
                )
                logger_struct.log_audit(audit)

                step.status = WorkflowStatus.BLOCKED
                step.error = f"Blocked by gates: {'; '.join(reasons)}"
                # Retrieve clarifying questions if any
                questions = [q for d in blocking for q in d.clarifying_questions]
                if questions:
                    # In a real system, we'd trigger a clarification workflow
                    step.output = {"clarification_needed": questions}
                return step

            # 2. Identify Kernel
            # If selected_kernels is empty, we might need to route it now
            if not spec.selected_kernels:
                # TODO: re-run classifier? For now assume builder did its job
                # Or maybe spec extraction didn't pick a kernel?
                # We can try to deduce it from domain
                pass
                
            if not spec.selected_kernels:
                raise ValueError(f"No kernel selected for step {step.step_id}")
            
            kernel_id = spec.selected_kernels[0]  # Pick first for now
            kernel_class = get_kernel(kernel_id)
            
            if not kernel_class:
                raise ValueError(f"Kernel {kernel_id} not found in registry")
            
            # 3. Prepare Input
            # Merge session context with spec args
            # Context takes precedence? Or args? 
            # Usually args from spec are explicit user intent. 
            # Context provides global state (e.g. dataframes).
            
            # Combine args: start with spec.args
            kernel_args = spec.args.copy() if spec.args else {}
            
            # Inject context variables if needed?
            # Simple approach: pass session context variables that match expected kernel args
            # But we don't know expected args easily without envelope.
            # For now, just pass explicit args.
            
            # 4. Instantiate and Execute Kernel
            kernel = kernel_class()
            
            kernel_input = KernelInput(
                kernel_id=kernel_id,
                request_id=f"exec_{uuid.uuid4()}",
                args=kernel_args,
                determinism_required="D1"
            )
            
            # Validate input? Kernel.execute checks args but `KernelInterface` has `validate_args`.
            # We trust kernel to validate inside execute (it takes KernelInput).
            
            output: KernelOutput = kernel.execute(kernel_input)
            
            # 5. Handle Output
            if output.success:
                step.status = WorkflowStatus.COMPLETED
                step.output = output.result
                
                # Update session
                session.add_history("step_complete", {
                    "step_id": step.step_id, 
                    "kernel": kernel_id,
                    "result_summary": str(output.result)[:100]
                })

                # Audit Log
                audit = AuditRecord(
                    event_id=str(uuid.uuid4()),
                    actor_id=session.user_id if hasattr(session, "user_id") else "unknown",
                    action="step_execution",
                    resource_id=step.step_id,
                    status="SUCCESS",
                    details={
                        "kernel": kernel_id, 
                        "workflow_id": session.active_workflow_id
                    },
                    gates_passed=[g.gate_id for g in gate_decisions] if gate_decisions else []
                )
                logger_struct.log_audit(audit)
                
                # If result is a dict, merge into context?
                # Be careful not to pollute.
                if isinstance(output.result, dict):
                    session.update_context(output.result)
                    
            else:
                step.status = WorkflowStatus.FAILED
                step.output = {"error": output.error}
                session.add_history("step_failed", {
                    "step_id": step.step_id,
                    "error": output.error
                })
                
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            step.status = WorkflowStatus.FAILED
            step.output = {"error": str(e), "traceback": traceback.format_exc()}
            
        return step

    async def run_workflow(self, workflow: Workflow, session: Session) -> Workflow:
        """
        Run workflow loop until blocked or finished.
        """
        # Set session active workflow
        session.active_workflow_id = workflow.workflow_id
        session.update_context(workflow.context)
        
        while True:
            # 1. Get ready steps
            ready_steps = workflow.get_ready_steps()
            
            if not ready_steps:
                # No ready steps. Are we done?
                pending = [s for s in workflow.steps if s.status in [WorkflowStatus.PENDING, WorkflowStatus.ACTIVE]]
                if not pending:
                    workflow.status = WorkflowStatus.COMPLETED
                else:
                    # Steps pending but not ready -> Blocked?
                    # Or maybe waiting for dependencies that failed?
                     failed = [s for s in workflow.steps if s.status == WorkflowStatus.FAILED]
                     if failed:
                         workflow.status = WorkflowStatus.FAILED
                     else:
                         # Blocked on something else?
                         workflow.status = WorkflowStatus.BLOCKED
                break
            
            # 2. Execute ready steps (sequential for now)
            progress_made = False
            for step in ready_steps:
                await self.run_step(step, session)
                if step.status == WorkflowStatus.COMPLETED:
                    progress_made = True
                elif step.status == WorkflowStatus.FAILED:
                    # Build stop on failure
                    workflow.status = WorkflowStatus.FAILED
                    return workflow
            
            if not progress_made:
                # Avoid infinite loop if step stays PENDING (shouldn't happen with logic above)
                break
                
        return workflow
