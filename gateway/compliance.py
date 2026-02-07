"""
Compliance Checker: Enforce regulatory and policy requirements.

Handles:
- Rate limiting (mocked)
- Access control (mocked)
- Data export controls
"""

from typing import Optional
from models.gate_decision import Decision


class ComplianceChecker:
    """
    Enforces compliance policies for AI Lab operations.
    """

    def __init__(self):
        # In a real system, these would load from external config/DB
        self.rate_limits = {
            "default": 100,  # requests per hour
            "admin": 1000
        }
        self.request_counts = {}  # In-memory mock
        
    def check_rate_limit(self, user_id: str, role: str = "default") -> bool:
        """
        Check if user has exceeded rate limits.
        
        Args:
            user_id: User identifier
            role: User role for limit lookup
            
        Returns:
            True if allowed, False if limit exceeded
        """
        limit = self.rate_limits.get(role, 100)
        current = self.request_counts.get(user_id, 0)
        
        if current >= limit:
            return False
            
        self.request_counts[user_id] = current + 1
        return True

    def check_access(self, user_id: str, resource: str, action: str) -> bool:
        """
        Check if user is allowed to perform action on resource.
        
        Args:
            user_id: User identifier
            resource: Resource identifier
            action: Action (read/write/delete)
            
        Returns:
            True if allowed
        """
        # Mock logic: "admin" can do anything, others read-only on sensitive
        if user_id.startswith("admin"):
            return True
            
        if "sensitive" in resource and action != "read":
            return False
            
        return True

    def check_data_export(self, data_type: str, destination: str) -> Decision:
        """
        Evaluate data export compliance.
        
        Args:
            data_type: Type of data (e.g. 'pii', 'aggregate')
            destination: Target (e.g. 'local', 'public_s3')
            
        Returns:
            Decision: ACCEPT, REJECT, or ESCALATE
        """
        if data_type == "pii" and destination == "public":
            return Decision.REJECT
            
        if data_type == "confidential" and destination == "external":
            return Decision.ESCALATE
            
        return Decision.ACCEPT
