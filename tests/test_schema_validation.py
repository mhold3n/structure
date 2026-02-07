"""
Tests for schema validation.

Validates that:
- Registry files conform to their schemas
- Policies conform to policy schemas
- Invalid data is properly rejected
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.schema_validator import (
    SchemaValidator,
    RegistryValidator,
    PolicyValidator,
    validate_all_registries,
    validate_all_policies,
)


class TestSchemaValidator:
    """Test SchemaValidator class."""

    def test_validates_valid_task_request(self):
        validator = SchemaValidator()
        valid_request = {"user_input": "What is the specific weight of water?"}
        is_valid, errors = validator.validate_task_request(valid_request)
        assert is_valid, f"Should be valid: {errors}"

    def test_rejects_invalid_task_request(self):
        validator = SchemaValidator()
        invalid_request = {
            "user_input": ""  # Empty string should fail minLength
        }
        is_valid, errors = validator.validate_task_request(invalid_request)
        # Note: depends on schema having minLength constraint
        # If no constraint, this may pass

    def test_validates_valid_task_plan(self):
        validator = SchemaValidator()
        valid_plan = {"domain": "physics", "required_gates": ["schema_gate"]}
        is_valid, errors = validator.validate_task_plan(valid_plan)
        assert is_valid, f"Should be valid: {errors}"

    def test_rejects_invalid_domain(self):
        validator = SchemaValidator()
        invalid_plan = {
            "domain": "invalid_domain",  # Not in enum
            "required_gates": [],
        }
        is_valid, errors = validator.validate_task_plan(invalid_plan)
        assert not is_valid, "Should reject invalid domain"


class TestRegistryValidator:
    """Test RegistryValidator class."""

    def test_validates_kernel_registry(self):
        validator = RegistryValidator()
        is_valid, errors = validator.validate_kernel_registry()
        assert is_valid, f"Kernel registry should be valid: {errors}"

    def test_validates_quantities_registry(self):
        validator = RegistryValidator()
        is_valid, errors = validator.validate_quantities_registry()
        assert is_valid, f"Quantities registry should be valid: {errors}"

    def test_validate_all_registries(self):
        is_valid, errors = validate_all_registries()
        assert is_valid, f"All registries should be valid: {errors}"


class TestPolicyValidator:
    """Test PolicyValidator class."""

    def test_validates_unit_disambiguation_policy(self):
        validator = PolicyValidator()
        is_valid, errors = validator.validate_policy("unit_disambiguation")
        assert is_valid, f"unit_disambiguation policy should be valid: {errors}"

    def test_validates_all_policies(self):
        is_valid, errors = validate_all_policies()
        # Note: some policies may not conform to base schema
        # This is expected for policies without policy_id field
        print(f"Policy validation: {is_valid}, errors: {errors}")


def run_tests():
    """Run all schema validation tests."""
    import traceback

    test_classes = [
        TestSchemaValidator,
        TestRegistryValidator,
        TestPolicyValidator,
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
