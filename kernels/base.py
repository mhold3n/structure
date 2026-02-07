"""
Base: Kernel interface and registry.

All kernels must implement KernelInterface.
All kernels accept KernelInput and return KernelOutput.
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from models.kernel_io import KernelInput, KernelOutput, Provenance, UnitMetadata


class KernelInterface(ABC):
    """
    Abstract base class for all kernels.
    
    Kernels are deterministic compute units that:
    - Accept validated KernelInput (not raw dicts)
    - Produce typed KernelOutput with provenance
    - Are stateless (same input → same output)
    """
    
    kernel_id: str
    version: str
    determinism_level: str  # D1, D2, NONE
    
    @abstractmethod
    def execute(self, input: KernelInput) -> KernelOutput:
        """
        Execute the kernel with validated input.
        
        Args:
            input: Validated KernelInput (not raw dict)
            
        Returns:
            KernelOutput with typed result and metadata
        """
        pass
    
    @abstractmethod
    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """
        Validate the args dict before execution.
        
        Returns:
            (is_valid, error_messages)
        """
        pass
    
    def get_envelope(self) -> dict:
        """Return the valid input envelope for this kernel."""
        return {}
    
    def _make_output(
        self,
        request_id: str,
        success: bool,
        result=None,
        error: str = None,
        units_metadata: UnitMetadata = None,
        warnings: list[str] = None
    ) -> KernelOutput:
        """Helper to create properly-formed KernelOutput."""
        return KernelOutput(
            kernel_id=self.kernel_id,
            version=self.version,
            request_id=request_id,
            success=success,
            result=result,
            error=error,
            units_metadata=units_metadata,
            provenance=Provenance(
                kernel_id=self.kernel_id,
                kernel_version=self.version,
                determinism=self.determinism_level,
                timestamp=datetime.utcnow()
            ),
            warnings=warnings or []
        )


# Kernel registry (populated by kernel modules)
KERNEL_REGISTRY: dict[str, type[KernelInterface]] = {}


def register_kernel(kernel_class: type[KernelInterface]) -> type[KernelInterface]:
    """Decorator to register a kernel class."""
    KERNEL_REGISTRY[kernel_class.kernel_id] = kernel_class
    return kernel_class


def get_kernel(kernel_id: str) -> Optional[type[KernelInterface]]:
    """Get a kernel class by ID."""
    return KERNEL_REGISTRY.get(kernel_id)


def list_kernels() -> list[str]:
    """List all registered kernel IDs."""
    return list(KERNEL_REGISTRY.keys())
