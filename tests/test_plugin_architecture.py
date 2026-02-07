import pytest
from plugins import PluginRegistry

def test_plugin_discovery():
    registry = PluginRegistry(plugins_dir="plugins")
    registry.discover_plugins()
    
    # Check if experiment domain was found
    assert "experiment" in registry.domains
    
    # Check if keywords were loaded
    keywords = registry.keywords.get("experiment")
    assert keywords is not None
    assert "hypothesis" in keywords
    
    # Check if kernel was loaded
    # Note: ExperimentKernel ID is "experiment_design_v1"
    assert "experiment_design_v1" in registry.kernels

def test_missing_plugin_dir():
    registry = PluginRegistry(plugins_dir="non_existent")
    registry.discover_plugins()
    assert len(registry.domains) == 0
