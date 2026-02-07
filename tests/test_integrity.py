"""
Tests for referential integrity validation.

Ensures that:
- Registry entries point to real kernel implementations
- Schema references exist
- Policy references exist
- Kernel interfaces match registry declarations
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.integrity import (
    validate_kernel_references,
    validate_schema_references,
    validate_policy_references,
    validate_registry_kernel_interface,
    validate_all_references,
)


class TestKernelReferences:
    """Test that registry kernels have implementations."""

    def test_all_kernels_have_implementations(self):
        is_valid, errors = validate_kernel_references()
        assert is_valid, f"Kernel reference errors: {errors}"

    def test_kernels_are_importable(self):
        """All implemented kernels should be importable."""
        from validator.integrity import KERNEL_IMPLEMENTATIONS
        import importlib

        for kernel_id, impl in KERNEL_IMPLEMENTATIONS.items():
            if impl is None:
                continue  # Skip planned kernels
            module_path, class_name = impl
            module = importlib.import_module(module_path)
            kernel_class = getattr(module, class_name, None)
            assert kernel_class is not None, f"Kernel {kernel_id} class not found"


class TestSchemaReferences:
    """Test that schema files exist and are valid."""

    def test_all_schemas_valid(self):
        is_valid, errors = validate_schema_references()
        assert is_valid, f"Schema reference errors: {errors}"

    def test_essential_schemas_exist(self):
        """Essential schemas should exist."""
        from validator.loader import SCHEMAS_DIR

        essential = ["task_request.schema.json", "task_plan.schema.json"]
        for schema in essential:
            path = SCHEMAS_DIR / schema
            assert path.exists(), f"Essential schema missing: {schema}"


class TestPolicyReferences:
    """Test that policy files exist and are valid."""

    def test_all_policies_valid(self):
        is_valid, errors = validate_policy_references()
        assert is_valid, f"Policy reference errors: {errors}"

    def test_essential_policies_exist(self):
        """Essential policies should exist."""
        from validator.loader import POLICIES_DIR

        essential = ["unit_disambiguation.yaml", "determinism.yaml"]
        for policy in essential:
            path = POLICIES_DIR / policy
            assert path.exists(), f"Essential policy missing: {policy}"


class TestKernelInterface:
    """Test that kernel implementations match registry declarations."""

    def test_all_kernels_have_correct_interface(self):
        is_valid, errors = validate_registry_kernel_interface()
        assert is_valid, f"Kernel interface errors: {errors}"

    def test_kernel_ids_match_registry(self):
        """Kernel class kernel_id should match registry entry."""
        from validator.loader import load_registry
        from validator.integrity import KERNEL_IMPLEMENTATIONS
        import importlib

        registry = load_registry()
        for kernel in registry.get("kernels", []):
            kernel_id = kernel.get("kernel_id")
            if kernel_id in KERNEL_IMPLEMENTATIONS:
                impl = KERNEL_IMPLEMENTATIONS[kernel_id]
                if impl is None:
                    continue  # Skip planned kernels
                module_path, class_name = impl
                module = importlib.import_module(module_path)
                kernel_class = getattr(module, class_name)
                assert kernel_class.kernel_id == kernel_id, (
                    f"Kernel {kernel_id} class has wrong kernel_id"
                )


class TestFullIntegrity:
    """Test complete referential integrity."""

    def test_all_references_valid(self):
        is_valid, errors = validate_all_references()
        assert is_valid, f"Integrity errors: {errors}"


def run_tests():
    """Run all integrity tests."""
    import traceback

    test_classes = [
        TestKernelReferences,
        TestSchemaReferences,
        TestPolicyReferences,
        TestKernelInterface,
        TestFullIntegrity,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_class.__name__}")
        print("=" * 60)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
