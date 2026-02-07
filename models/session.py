from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Session(BaseModel):
    """
    User session for multi-turn interactions.
    
    Persists context across multiple requests and workflow steps.
    """
    session_id: str
    user_id: str = "default_user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Active workflow state
    active_workflow_id: Optional[str] = None
    
    # Context accumulating across the session
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # History of interactions
    history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def update_context(self, new_context: Dict[str, Any]):
        """Update session context with new values."""
        self.context.update(new_context)
        self.updated_at = datetime.utcnow()
    
    def add_history(self, event_type: str, data: Any):
        """Add an event to history."""
        self.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data
        })
        self.updated_at = datetime.utcnow()
