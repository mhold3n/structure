"""
Referential Integrity Validator.

Validates that all references in the registry resolve to real implementations:
- Registry kernel entries → importable kernel classes
- Schema references → existing schema files
- Policy references → existing policy files
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.loader import load_registry, SCHEMAS_DIR, POLICIES_DIR

# Known kernel implementations
# Value of None means the kernel is planned but not yet implemented
KERNEL_IMPLEMENTATIONS = {
    # Implemented
    "unit_converter_v1": ("kernels.units", "UnitsKernel"),
    "constants_v1": ("kernels.constants", "ConstantsKernel"),
    # Planned - Physics
    "dimensional_check_v1": None,
    "fluids_statics_v1": None,
    "thermo_ideal_gas_v1": None,
    "mechanics_kinematics_v1": None,
    # Planned - AI Lab
    "statistics_v1": ("kernels.statistics", "StatisticsKernel"),
    "experiment_design_v1": ("kernels.experiment", "ExperimentKernel"),
    "project_mgmt_v1": ("kernels.project", "ProjectKernel"),
    "data_summary_v1": ("kernels.data_summary", "DataSummaryKernel"),
}


def validate_kernel_references() -> tuple[bool, list[str]]:
    """
    Validate that all kernel_ids in registry have implementations or are planned.

    Returns:
        (is_valid, error_messages)
    """
    registry = load_registry()
    errors = []
    warnings = []

    for kernel in registry.get("kernels", []):
        kernel_id = kernel.get("kernel_id")
        if not kernel_id:
            errors.append("Kernel entry missing kernel_id")
            continue

        if kernel_id not in KERNEL_IMPLEMENTATIONS:
            errors.append(f"Kernel {kernel_id} not in KERNEL_IMPLEMENTATIONS registry")
            continue

        impl = KERNEL_IMPLEMENTATIONS[kernel_id]
        if impl is None:
            # Planned but not implemented - this is OK
            warnings.append(f"Kernel {kernel_id} is planned but not yet implemented")
            continue

        # Try to import the kernel class
        module_path, class_name = impl
        try:
            import importlib

            module = importlib.import_module(module_path)
            kernel_class = getattr(module, class_name, None)
            if kernel_class is None:
                errors.append(f"Kernel {kernel_id}: class {class_name} not found in {module_path}")
        except ImportError as e:
            errors.append(f"Kernel {kernel_id}: failed to import {module_path}: {e}")

    return (len(errors) == 0, errors)


def validate_schema_references() -> tuple[bool, list[str]]:
    """
    Validate that all referenced schemas exist.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check that essential schemas exist
    essential_schemas = [
        "task_request.schema.json",
        "task_plan.schema.json",
        "kernel_result.schema.json",
        "gate_decision.schema.json",
    ]

    for schema_file in essential_schemas:
        schema_path = SCHEMAS_DIR / schema_file
        if not schema_path.exists():
            errors.append(f"Essential schema missing: {schema_file}")

    # Check all schemas are valid JSON
    for schema_file in SCHEMAS_DIR.glob("*.schema.json"):
        try:
            import json

            with open(schema_file) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {schema_file.name}: {e}")

    return (len(errors) == 0, errors)


def validate_policy_references() -> tuple[bool, list[str]]:
    """
    Validate that all referenced policies exist and are valid YAML.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check that essential policies exist
    essential_policies = [
        "unit_disambiguation.yaml",
        "determinism.yaml",
    ]

    for policy_file in essential_policies:
        policy_path = POLICIES_DIR / policy_file
        if not policy_path.exists():
            errors.append(f"Essential policy missing: {policy_file}")

    # Check all policies are valid YAML
    for policy_file in POLICIES_DIR.glob("*.yaml"):
        try:
            import yaml

            with open(policy_file) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in {policy_file.name}: {e}")

    return (len(errors) == 0, errors)


def validate_registry_kernel_interface() -> tuple[bool, list[str]]:
    """
    Validate that kernel implementations match registry declarations.

    Checks:
    - Kernel class has required attributes (kernel_id, version, determinism_level)
    - Kernel has execute and validate_args methods
    """
    registry = load_registry()
    errors = []

    for kernel in registry.get("kernels", []):
        kernel_id = kernel.get("kernel_id")
        if kernel_id not in KERNEL_IMPLEMENTATIONS:
            continue  # Already reported in validate_kernel_references

        impl = KERNEL_IMPLEMENTATIONS[kernel_id]
        if impl is None:
            continue  # Planned kernel, skip interface check

        module_path, class_name = impl
        try:
            import importlib

            module = importlib.import_module(module_path)
            kernel_class = getattr(module, class_name)

            # Check required class attributes
            if not hasattr(kernel_class, "kernel_id"):
                errors.append(f"Kernel {kernel_id}: missing kernel_id attribute")
            if not hasattr(kernel_class, "version"):
                errors.append(f"Kernel {kernel_id}: missing version attribute")
            if not hasattr(kernel_class, "determinism_level"):
                errors.append(f"Kernel {kernel_id}: missing determinism_level attribute")

            # Check required methods
            if not hasattr(kernel_class, "execute"):
                errors.append(f"Kernel {kernel_id}: missing execute method")
            if not hasattr(kernel_class, "validate_args"):
                errors.append(f"Kernel {kernel_id}: missing validate_args method")

            # Validate kernel_id matches registry
            if hasattr(kernel_class, "kernel_id") and kernel_class.kernel_id != kernel_id:
                errors.append(
                    f"Kernel {kernel_id}: class kernel_id '{kernel_class.kernel_id}' "
                    f"does not match registry '{kernel_id}'"
                )

        except Exception as e:
            errors.append(f"Kernel {kernel_id}: validation failed: {e}")

    return (len(errors) == 0, errors)


def validate_all_references() -> tuple[bool, list[str]]:
    """
    Run all referential integrity checks.

    Returns:
        (is_valid, all_error_messages)
    """
    all_errors = []

    kernel_valid, kernel_errors = validate_kernel_references()
    all_errors.extend(kernel_errors)

    schema_valid, schema_errors = validate_schema_references()
    all_errors.extend(schema_errors)

    policy_valid, policy_errors = validate_policy_references()
    all_errors.extend(policy_errors)

    interface_valid, interface_errors = validate_registry_kernel_interface()
    all_errors.extend(interface_errors)

    return (len(all_errors) == 0, all_errors)


if __name__ == "__main__":
    print("Validating referential integrity...")
    is_valid, errors = validate_all_references()

    if is_valid:
        print("✓ All references valid")
        sys.exit(0)
    else:
        print("✗ Referential integrity errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
