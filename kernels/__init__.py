# Kernels module - Deterministic compute units

from .statistics import StatisticsKernel
from .project import ProjectKernel
from .summary import SummaryKernel
from .base import get_kernel, list_kernels, KERNEL_REGISTRY

# Re-export available kernels
__all__ = [
    "StatisticsKernel",
    "ProjectKernel",
    "SummaryKernel",
    "get_kernel",
    "list_kernels",
    "KERNEL_REGISTRY",
]
