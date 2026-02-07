# Plugin Architecture

This directory contains domain-specific plugins for the AI Lab framework.
Plugins allow extending the framework with new domains, kernels, gates, and policies without modifying the core codebase.

## Plugin Structure

Each plugin should be a Python package (directory with `__init__.py`) containing the following:

- **Domain ID**: A unique string identifier.
- **Keywords**: List of keywords for routing.
- **Kernels**: List of `KernelInterface` classes.
- **Gates**: Dictionary of `gate_id` -> `gate_function`.
- **Policies**: List of paths to policy YAML files.

## Example `__init__.py`

```python
from kernels.base import KernelInterface
from models.task_spec import TaskSpec
from models.gate_decision import GateDecision

# 1. Define Domain ID
DOMAIN_ID = "my_domain"

# 2. Define Routing Keywords
KEYWORDS = ["custom keyword", "domain term"]

# 3. Register Kernels
KERNELS = [
    MyCustomKernel
]

# 4. Register Gates
def my_gate(spec: TaskSpec) -> GateDecision:
    ...

GATES = {
    "my_domain_gate": my_gate
}

# 5. Register Policies
POLICIES = [
    # Path("policies/my_policy.yaml")
]
```

## Discovery

The `PluginRegistry` in `plugins/__init__.py` automatically scans this directory and registers valid plugins at runtime.
