"""
Structured logging for gateway requests.

All logs are JSONL for replayability and audit.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    """
    Immutable audit record for compliance.
    """

    event_id: str = Field(..., description="Unique ID for this audit event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str = Field(..., description="User or system ID performing action")
    action: str = Field(..., description="Action performed (e.g., 'submit_workflow')")
    resource_id: Optional[str] = Field(None, description="Target resource ID")
    status: str = Field(..., description="Outcome (SUCCESS, FAILURE, BLOCKED)")
    details: dict[str, Any] = Field(default_factory=dict, description="Contextual details")

    # Compliance fields
    gates_passed: List[str] = Field(default_factory=list)
    policy_violations: List[str] = Field(default_factory=list)


class StructuredLogger:
    """JSONL structured logger for gateway operations."""

    def __init__(self, component: str):
        self.component = component

    def _emit(self, record: dict[str, Any]) -> None:
        """Write a log record as JSONL to stdout."""
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        record["component"] = self.component
        print(json.dumps(record, default=str), file=sys.stdout, flush=True)

    def log_request(self, request_id: str, endpoint: str, payload: dict) -> None:
        """Log an incoming request."""
        self._emit(
            {"event": "request", "request_id": request_id, "endpoint": endpoint, "payload": payload}
        )

    def log_response(self, request_id: str, status: str, result: Any) -> None:
        """Log an outgoing response."""
        self._emit(
            {"event": "response", "request_id": request_id, "status": status, "result": result}
        )

    def log_event(self, request_id: str, event_type: str, data: Any) -> None:
        """Log an intermediate event."""
        self._emit({"event": event_type, "request_id": request_id, "data": data})

    def log_error(self, request_id: str, error: str) -> None:
        """Log an error."""
        self._emit({"event": "error", "request_id": request_id, "error": error})

    def log_audit(self, record: AuditRecord) -> None:
        """Log a formal audit record."""
        self._emit({"event": "audit", "audit_record": record.model_dump()})
