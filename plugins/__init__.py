import importlib
import pkgutil
from typing import List, Type, Dict, Any, Callable
from pathlib import Path
import logging

from kernels.base import KernelInterface
from models.task_spec import TaskSpec
from models.gate_decision import GateDecision

logger = logging.getLogger(__name__)

class PluginRegistry:
    """
    Registry for auto-discovering and loading domain plugins.
    
    Plugins are expected to be Python packages/modules in the `plugins/` directory.
    Each plugin module should expose a `register()` function or define specific variables:
    - DOMAIN_ID: str
    - KEYWORDS: List[str]
    - KERNELS: List[Type[KernelInterface]]
    - GATES: Dict[str, Callable[[TaskSpec], GateDecision]]
    - POLICIES: List[Path]
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.domains: Dict[str, Any] = {}
        self.kernels: Dict[str, Type[KernelInterface]] = {}
        self.gates: Dict[str, Callable[[TaskSpec], GateDecision]] = {}
        self.policies: List[Path] = []
        self.keywords: Dict[str, List[str]] = {}

    def discover_plugins(self):
        """Scan the plugins directory and load all valid plugins."""
        # Ensure plugins dir exists
        if not Path(self.plugins_dir).exists():
            logger.warning(f"Plugins directory {self.plugins_dir} not found.")
            return

        # Iterate over modules in plugins/
        for _, name, ispkg in pkgutil.iter_modules([self.plugins_dir]):
            full_name = f"{self.plugins_dir}.{name}"
            try:
                module = importlib.import_module(full_name)
                self._register_plugin(module)
                logger.info(f"Loaded plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {name}: {e}")

    def _register_plugin(self, module):
        """Extract components from a plugin module and register them."""
        # 1. Domain ID
        domain_id = getattr(module, "DOMAIN_ID", None)
        if not domain_id:
            return # Skip non-conforming modules
            
        self.domains[domain_id] = module
        
        # 2. Keywords
        keywords = getattr(module, "KEYWORDS", [])
        if keywords:
            self.keywords[domain_id] = keywords
            
        # 3. Kernels
        kernels = getattr(module, "KERNELS", [])
        for k in kernels:
            if issubclass(k, KernelInterface):
                self.kernels[k.kernel_id] = k
                
        # 4. Gates
        gates = getattr(module, "GATES", {})
        if isinstance(gates, dict):
            self.gates.update(gates)
                
        # 5. Policies
        policies = getattr(module, "POLICIES", [])
        self.policies.extend(policies)

# Global registry instance
registry = PluginRegistry()
