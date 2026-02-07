"""
Tests for Spec Normalization.

Ensures:
- Deterministic key ordering
- Stable list sorting
- Canonical unit conversion
- Bitwise-stable output
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.normalizer import (
    normalize_dict_keys,
    normalize_list_ordering,
    convert_to_canonical,
    normalize_for_logging,
    normalize_kernel_result,
)


class TestKeyOrdering:
    """Test stable key ordering."""

    def test_simple_dict_sorted(self):
        """Dict keys should be sorted alphabetically."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = normalize_dict_keys(obj)
        assert list(result.keys()) == ["a", "m", "z"]

    def test_nested_dicts_sorted(self):
        """Nested dicts should also have sorted keys."""
        obj = {"z": {"b": 1, "a": 2}, "a": 3}
        result = normalize_dict_keys(obj)
        assert list(result.keys()) == ["a", "z"]
        assert list(result["z"].keys()) == ["a", "b"]

    def test_list_of_dicts_sorted(self):
        """Dicts inside lists should have sorted keys."""
        obj = [{"z": 1, "a": 2}]
        result = normalize_dict_keys(obj)
        assert list(result[0].keys()) == ["a", "z"]


class TestListOrdering:
    """Test stable list ordering."""

    def test_sortable_lists_sorted(self):
        """Lists for specified keys should be sorted."""
        obj = {"reasons": ["z_reason", "a_reason", "m_reason"]}
        result = normalize_list_ordering(obj)
        assert result["reasons"] == ["a_reason", "m_reason", "z_reason"]

    def test_non_sortable_lists_preserved(self):
        """Lists not in sortable_keys should preserve order."""
        obj = {"items": ["z", "a", "m"]}
        result = normalize_list_ordering(obj)
        assert result["items"] == ["z", "a", "m"]

    def test_multiple_sortable_keys(self):
        """Multiple sortable keys should all be sorted."""
        obj = {
            "reasons": ["b", "a"],
            "reason_codes": ["CODE_B", "CODE_A"],
            "required_fields": ["field_z", "field_a"],
        }
        result = normalize_list_ordering(obj)
        assert result["reasons"] == ["a", "b"]
        assert result["reason_codes"] == ["CODE_A", "CODE_B"]
        assert result["required_fields"] == ["field_a", "field_z"]


class TestUnitConversion:
    """Test canonical unit conversion."""

    def test_lb_to_kg(self):
        """Pounds should convert to kg."""
        value, unit = convert_to_canonical(10, "lb")
        assert unit == "kg"
        assert abs(value - 4.53592) < 0.0001

    def test_psi_to_pa(self):
        """PSI should convert to Pa."""
        value, unit = convert_to_canonical(14.7, "psi")
        assert unit == "Pa"
        assert abs(value - 101352.972) < 1.0

    def test_km_h_to_m_s(self):
        """km/h should convert to m/s."""
        value, unit = convert_to_canonical(36, "km/h")
        assert unit == "m/s"
        assert abs(value - 10.0) < 0.01

    def test_unknown_unit_preserved(self):
        """Unknown units should be preserved as-is."""
        value, unit = convert_to_canonical(42, "frobnicators")
        assert unit == "frobnicators"
        assert value == 42


class TestNormalization:
    """Test full normalization functions."""

    def test_logging_produces_deterministic_json(self):
        """Same object should produce identical JSON regardless of input order."""
        obj1 = {"a": 1, "b": 2}
        obj2 = {"b": 2, "a": 1}
        assert normalize_for_logging(obj1) == normalize_for_logging(obj2)

    def test_kernel_result_adds_canonical_values(self):
        """Kernel results with quantities should get canonical values."""
        result = {"output": {"value": 10, "unit": "lb"}}
        normalized = normalize_kernel_result(result)
        assert "value_canonical" in normalized["output"]
        assert "unit_canonical" in normalized["output"]
        assert normalized["output"]["unit_canonical"] == "kg"

    def test_complex_object_normalized(self):
        """Complex objects should be fully normalized."""
        obj = {
            "z_key": 1,
            "a_key": 2,
            "reasons": ["z", "a"],
            "nested": {
                "b": {"value": 100, "unit": "psi"},
                "a": 1,
            },
        }
        normalized = normalize_kernel_result(obj)
        # Keys sorted
        assert list(normalized.keys()) == ["a_key", "nested", "reasons", "z_key"]
        # Lists sorted
        assert normalized["reasons"] == ["a", "z"]
        # Nested keys sorted
        assert list(normalized["nested"].keys()) == ["a", "b"]
        # Quantities canonicalized
        assert "unit_canonical" in normalized["nested"]["b"]


def run_tests():
    """Run all normalization tests."""
    import traceback

    test_classes = [
        TestKeyOrdering,
        TestListOrdering,
        TestUnitConversion,
        TestNormalization,
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
