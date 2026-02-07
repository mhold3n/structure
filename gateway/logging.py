"""
Structured logging for gateway requests.

All logs are JSONL for replayability and audit.
"""

import json
import sys
from datetime import datetime
from typing import Any


class StructuredLogger:
    """JSONL structured logger for gateway operations."""

    def __init__(self, component: str):
        self.component = component

    def _emit(self, record: dict[str, Any]) -> None:
        """Write a log record as JSONL to stdout."""
        record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        record["component"] = self.component
        print(json.dumps(record), file=sys.stdout, flush=True)

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
