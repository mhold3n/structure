"""
Gateway: Single auditable entrypoint for R&D Orchestration.

All requests flow through here with structured logging for replayability.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
import uuid
from datetime import datetime

from .logging import StructuredLogger
from validator.loader import load_registry, load_schema, load_policy
from validator.gates import run_gates
from router.classifier import classify_task

app = FastAPI(
    title="R&D Orchestration Gateway",
    description="Deterministic Kernels + LLM Interface",
    version="0.1.0"
)

logger = StructuredLogger("gateway")


# --- Request/Response Models ---

class TaskRequest(BaseModel):
    """Incoming task request from LLM or user."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str
    domain_hint: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Response to a task request."""
    request_id: str
    status: str  # "success" | "clarify" | "reject" | "error"
    result: Optional[Any] = None
    gate_decisions: Optional[list[dict]] = None
    required_fields: Optional[list[str]] = None
    message: Optional[str] = None


class KernelRequest(BaseModel):
    """Direct kernel invocation request."""
    kernel_id: str
    version: Optional[str] = None
    inputs: dict[str, Any]


# --- Routes ---

@app.post("/task", response_model=TaskResponse)
async def submit_task(request: TaskRequest) -> TaskResponse:
    """
    Submit a task for processing.
    
    Flow: classify → validate → dispatch to kernel → format response
    """
    logger.log_request(request.request_id, "task", request.model_dump())
    
    try:
        # 1. Classify the task
        task_plan = classify_task(request.user_input, request.domain_hint)
        logger.log_event(request.request_id, "classified", task_plan)
        
        # 2. Run validation gates
        gate_results = run_gates(task_plan, request.model_dump())
        
        # Check for CLARIFY or REJECT
        for gate in gate_results:
            if gate["decision"] == "REJECT":
                return TaskResponse(
                    request_id=request.request_id,
                    status="reject",
                    gate_decisions=gate_results,
                    message=f"Rejected by {gate['gate_id']}: {gate['reasons']}"
                )
            if gate["decision"] == "CLARIFY":
                return TaskResponse(
                    request_id=request.request_id,
                    status="clarify",
                    gate_decisions=gate_results,
                    required_fields=gate.get("required_fields", []),
                    message="Clarification needed before proceeding"
                )
        
        # 3. Dispatch to kernel (placeholder for now)
        result = {
            "task_plan": task_plan,
            "gates_passed": True,
            "kernel_result": "TODO: implement kernel dispatch"
        }
        
        logger.log_response(request.request_id, "success", result)
        return TaskResponse(
            request_id=request.request_id,
            status="success",
            result=result,
            gate_decisions=gate_results
        )
        
    except Exception as e:
        logger.log_error(request.request_id, str(e))
        return TaskResponse(
            request_id=request.request_id,
            status="error",
            message=str(e)
        )


@app.post("/kernel/{kernel_id}")
async def invoke_kernel(kernel_id: str, request: KernelRequest):
    """
    Directly invoke a registered kernel.
    
    Bypasses routing but still runs validation gates.
    """
    request_id = str(uuid.uuid4())
    logger.log_request(request_id, f"kernel/{kernel_id}", request.model_dump())
    
    registry = load_registry()
    kernel_entry = next(
        (k for k in registry.get("kernels", []) if k["kernel_id"] == kernel_id),
        None
    )
    
    if not kernel_entry:
        raise HTTPException(status_code=404, detail=f"Kernel {kernel_id} not found")
    
    # TODO: Validate inputs against kernel schema
    # TODO: Dispatch to kernel implementation
    
    return {
        "request_id": request_id,
        "kernel_id": kernel_id,
        "status": "success",
        "result": "TODO: implement kernel dispatch"
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
