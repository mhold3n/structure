"""
Gateway: Single auditable entrypoint for R&D Orchestration.

All requests flow through here with structured logging for replayability.
Uses typed Pydantic models - no untyped dicts crossing boundaries.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
import uuid
from datetime import datetime

from .logging import StructuredLogger, AuditRecord
from models.task_spec import TaskSpec, TaskRequest
from models.gate_decision import GateDecision, Decision
from models.clarify import ClarifyRequest  # noqa: F401 - available for future use
from validator.loader import load_registry, load_schema, load_policy
from validator.gates import run_gates, get_blocking_decisions
from router.classifier import classify_task
from models.workflow import Workflow
from models.session import Session
from runtime.orchestrator import Orchestrator
from router.workflow_builder import build_workflow_from_request

app = FastAPI(
    title="R&D Orchestration Gateway",
    description="Deterministic Kernels + LLM Interface",
    version="0.3.0",
)

logger = StructuredLogger("gateway")


# --- Request/Response Models ---


class TaskRequestInput(BaseModel):
    """Incoming task request from API."""

    user_input: str = Field(..., min_length=1)
    domain_hint: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class ClarifyPayload(BaseModel):
    """Structured clarification payload for CLARIFY responses."""

    reason_codes: list[str] = Field(default_factory=list)
    questions: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    """Response to a task request."""

    request_id: str
    status: str  # "success" | "clarify" | "reject" | "error"
    spec: Optional[dict] = None
    result: Optional[Any] = None
    gate_decisions: Optional[list[dict]] = None
    clarify: Optional[ClarifyPayload] = None  # Structured clarify payload
    message: Optional[str] = None


class KernelRequestInput(BaseModel):
    """Direct kernel invocation request."""

    kernel_id: str
    version: Optional[str] = None
    args: dict[str, Any] = Field(default_factory=dict)


# --- Routes ---


@app.post("/task", response_model=TaskResponse)
async def submit_task(input: TaskRequestInput) -> TaskResponse:
    """
    Submit a task for processing.

    Flow: TaskRequest → classify → TaskSpec → validate → dispatch
    """
    request_id = str(uuid.uuid4())

    # Create typed TaskRequest
    request = TaskRequest(
        request_id=request_id,
        user_input=input.user_input,
        domain_hint=input.domain_hint,
        context=input.context or {},
    )

    logger.log_request(request_id, "task", request.model_dump())

    try:
        # 1. Classify into validated TaskSpec
        spec: TaskSpec = classify_task(request)
        logger.log_event(request_id, "classified", spec.model_dump())

        # 2. Run validation gates
        gate_results: list[GateDecision] = run_gates(spec)
        blocking = get_blocking_decisions(gate_results)

        # Check for blocking decisions
        if blocking:
            first_block = blocking[0]

            # Build structured clarify payload
            all_reasons = []
            all_questions = []
            all_required = []

            for g in blocking:
                all_reasons.extend(g.reasons)
                all_required.extend(g.required_fields)
                for i, q in enumerate(g.clarifying_questions):
                    all_questions.append(
                        {
                            "id": f"{g.gate_id}_{i}",
                            "prompt": q,
                            "type": "choice" if g.required_fields else "text",
                            "required": True,
                        }
                    )

            status = "clarify" if first_block.decision == Decision.CLARIFY else "reject"

            # Audit Log for Blocked Task
            logger.log_audit(
                AuditRecord(
                    event_id=str(uuid.uuid4()),
                    actor_id="api_user", # TODO: extract from auth
                    action="task_submission",
                    resource_id=request_id,
                    status="BLOCKED",
                    details={"reason": f"Blocked by {first_block.gate_id}"},
                    gates_passed=[g.gate_id for g in gate_results if not g.is_blocking()],
                    policy_violations=[g.gate_id for g in blocking]
                )
            )

            clarify_payload = ClarifyPayload(
                reason_codes=list(set(all_reasons)),
                questions=all_questions,
                context={
                    "domain": spec.domain.value,
                    "subdomain": spec.subdomain,
                    "detected_terms": spec.quantities,
                    "blocking_gates": [g.gate_id for g in blocking],
                },
                required_fields=list(set(all_required)),
            )

            return TaskResponse(
                request_id=request_id,
                status=status,
                spec=spec.model_dump(),
                gate_decisions=[g.model_dump() for g in gate_results],
                clarify=clarify_payload,
                message=f"Blocked by {first_block.gate_id}: {first_block.reasons}",
            )

        # 3. All gates passed - dispatch to kernel (placeholder)
        result = {
            "gates_passed": True,
            "selected_kernels": spec.selected_kernels,
            "kernel_result": "TODO: implement kernel dispatch",
        }

        logger.log_response(request_id, "success", result)
        return TaskResponse(
            request_id=request_id,
            status="success",
            spec=spec.model_dump(),
            result=result,
            gate_decisions=[g.model_dump() for g in gate_results],
        )

    except Exception as e:
        logger.log_error(request_id, str(e))
        return TaskResponse(request_id=request_id, status="error", message=str(e))


@app.post("/kernel/{kernel_id}")
async def invoke_kernel(kernel_id: str, input: KernelRequestInput):
    """
    Directly invoke a registered kernel.

    Bypasses routing but still runs validation gates.
    """
    request_id = str(uuid.uuid4())
    logger.log_request(request_id, f"kernel/{kernel_id}", input.model_dump())

    registry = load_registry()
    kernel_entry = next(
        (k for k in registry.get("kernels", []) if k["kernel_id"] == kernel_id), None
    )

    if not kernel_entry:
        raise HTTPException(status_code=404, detail=f"Kernel {kernel_id} not found")

    # TODO: Create KernelInput, validate, dispatch

    return {
        "request_id": request_id,
        "kernel_id": kernel_id,
        "status": "success",
        "result": "TODO: implement kernel dispatch with KernelInput model",
    }


@app.get("/registry")
async def get_registry():
    """List all registered kernels and their metadata."""
    return load_registry()


@app.get("/schemas/{schema_id}")
async def get_schema(schema_id: str):
    """Retrieve a specific schema by ID."""
    schema = load_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    return schema


@app.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """Retrieve a specific policy by ID."""
    policy = load_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
    return policy




# Global runtime state
orchestrator = Orchestrator()
sessions: dict[str, Session] = {}
active_workflows: dict[str, Workflow] = {}


@app.post("/workflow", response_model=Workflow)
async def submit_workflow(input: TaskRequestInput) -> Workflow:
    """
    Submit a task request to be executed as a multi-step workflow.
    
    Decomposes input -> Workflow -> Executes via Orchestrator.
    """
    request_id = str(uuid.uuid4())
    
    # 1. Create Request
    request = TaskRequest(
        request_id=request_id,
        user_input=input.user_input,
        domain_hint=input.domain_hint,
        context=input.context or {},
    )
    
    logger.log_request(request_id, "workflow", request.model_dump())
    
    # 2. Build Workflow
    workflow = build_workflow_from_request(request)
    
    # 3. Create/Get Session 
    # For now, create a new session for each workflow request
    # In future, we'd extract session_id from headers/auth
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    session = Session(session_id=session_id)
    sessions[session_id] = session
    
    # Store workflow for resumption
    active_workflows[workflow.workflow_id] = workflow
    
    # 4. Execute Workflow
    try:
        updated_workflow = await orchestrator.run_workflow(workflow, session)
        
        logger.log_response(request_id, "success", updated_workflow.model_dump())
        return updated_workflow
        
    except Exception as e:
        logger.log_error(request_id, str(e))
        # Return workflow in failed state if possible, else raise
        workflow.status = "failed" # Should be WorkflowStatus.FAILED but utilizing string for simplicity/safety
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experiment", response_model=TaskResponse)
async def submit_experiment(input: TaskRequestInput) -> TaskResponse:
    """Submit an experiment design request (Shortcut for /task with domain='experiment')."""
    input.domain_hint = "experiment"
    return await submit_task(input)


@app.post("/analysis", response_model=TaskResponse)
async def submit_analysis(input: TaskRequestInput) -> TaskResponse:
    """Submit a data analysis request (Shortcut for /task with domain='analysis')."""
    input.domain_hint = "analysis"
    return await submit_task(input)


@app.post("/project-plan", response_model=TaskResponse)
async def submit_project_plan(input: TaskRequestInput) -> TaskResponse:
    """Submit a project planning request (Shortcut for /task with domain='project')."""
    input.domain_hint = "project"
    return await submit_task(input)


@app.get("/session/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    """Retrieve the current state of a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return sessions[session_id]


class ClarificationAnswer(BaseModel):
    """User answer to a clarification question."""
    question_id: str
    answer: str


@app.post("/session/{session_id}/answer", response_model=Workflow)
async def answer_clarification(session_id: str, answers: list[ClarificationAnswer]) -> Workflow:
    """
    Submit answers to clarifying questions for a blocked step/workflow.
    
    This resumes the workflow:
    1. Updates context with answers
    2. Re-runs the blocked step
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = sessions[session_id]
    
    # 1. Update Session Context
    # Map answers to context variables? Or just store them?
    # For now, store in a special 'user_answers' dict in context
    for ans in answers:
         session.context[f"answer_{ans.question_id}"] = ans.answer
         # Also log to history
         session.add_history("user_clarification", {"question": ans.question_id, "answer": ans.answer})

    # 2. Resume Workflow
    if not session.active_workflow_id:
         raise HTTPException(status_code=400, detail="No active workflow in this session")

    # In a real app we'd load workflow from DB. Here we don't have global workflow storage 
    # except explicitly returned, but `orchestrator.run_workflow` takes a workflow object.
    # We need to retrieve the workflow object. 
    # LIMITATION: In this in-memory prototype, we don't have a lookup for Workflow objects by ID 
    # outside of the `result`... wait.
    # The `sessions` dict stores `Session`, but `Workflow` state is lost if not persisted.
    # 
    # For this prototype, I will rely on the client re-submitting OR (better) I'll add a 
    # `workflows` in-memory store to `main.py` to support this pattern.
    
    workflow = active_workflows.get(session.active_workflow_id)
    if not workflow:
         raise HTTPException(status_code=404, detail="Active workflow not found (memory reset?)")
         
    # Update workflow context too
    workflow.context.update(session.context)
    
    # Reset blocked steps to PENDING or ACTIVE to retry
    for step in workflow.steps:
        if step.status == "blocked": # WorkflowStatus.BLOCKED
             step.status = "pending" # WorkflowStatus.PENDING
    
    # Re-run
    try:
        updated_workflow = await orchestrator.run_workflow(workflow, session)
        return updated_workflow
    except Exception as e:
        logger.log_error(session_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(sessions),
        "active_workflows": len(active_workflows)
    }

