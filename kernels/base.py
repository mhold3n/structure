"""
Base: Kernel interface and registry.

All kernels must implement the KernelInterface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class KernelResult:
    """Standardized kernel output."""
    kernel_id: str
    version: str
    success: bool
    result: Any
    units_metadata: Optional[dict] = None
    provenance: Optional[dict] = None
    uncertainty: Optional[float] = None
    warnings: Optional[list[str]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class KernelInterface(ABC):
    """
    Abstract base class for all kernels.
    
    Kernels are deterministic compute units that:
    - Accept validated, canonical inputs
    - Produce typed outputs with provenance
    - Are stateless (same input → same output)
    """
    
    kernel_id: str
    version: str
    determinism_level: str  # D1, D2, NONE
    
    @abstractmethod
    def execute(self, inputs: dict) -> KernelResult:
        """
        Execute the kernel with validated inputs.
        
        Args:
            inputs: Validated input dictionary matching kernel schema
            
        Returns:
            KernelResult with output and metadata
        """
        pass
    
    @abstractmethod
    def validate_inputs(self, inputs: dict) -> tuple[bool, list[str]]:
        """
        Validate inputs before execution.
        
        Returns:
            (is_valid, error_messages)
        """
        pass
    
    def get_envelope(self) -> dict:
        """Return the valid input envelope for this kernel."""
        return {}


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
