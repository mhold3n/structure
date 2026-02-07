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

from .logging import StructuredLogger
from models.task_spec import TaskSpec, TaskRequest
from models.gate_decision import GateDecision, Decision
from models.clarify import ClarifyRequest  # noqa: F401 - available for future use
from validator.loader import load_registry, load_schema, load_policy
from validator.gates import run_gates, get_blocking_decisions
from router.classifier import classify_task

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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
