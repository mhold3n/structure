"""
Spec Normalizer.

Ensures deterministic, stable outputs by normalizing:
1. Stable key ordering - sort dict keys for consistent serialization
2. Canonical units - convert all quantities to SI base units
3. Stable list ordering - sort lists where order is not semantic

This enables "bitwise-stable" outputs: same inputs → identical JSON.
"""

import json
from typing import Any
from decimal import Decimal

# Canonical SI units for each quantity type
CANONICAL_UNITS = {
    "mass": "kg",
    "length": "m",
    "time": "s",
    "temperature": "K",
    "force": "N",
    "pressure": "Pa",
    "energy": "J",
    "power": "W",
    "velocity": "m/s",
    "acceleration": "m/s2",
    "density": "kg/m3",
    "volume": "m3",
    "area": "m2",
}

# Conversion factors TO canonical SI units
# Format: (from_unit, to_SI_multiplier)
CONVERSION_TO_SI = {
    # Mass
    "g": ("mass", 0.001),
    "mg": ("mass", 1e-6),
    "lb": ("mass", 0.453592),
    "lbm": ("mass", 0.453592),
    "oz": ("mass", 0.0283495),
    "kg": ("mass", 1.0),
    # Length
    "mm": ("length", 0.001),
    "cm": ("length", 0.01),
    "m": ("length", 1.0),
    "km": ("length", 1000.0),
    "in": ("length", 0.0254),
    "ft": ("length", 0.3048),
    "mi": ("length", 1609.34),
    # Force
    "N": ("force", 1.0),
    "kN": ("force", 1000.0),
    "lbf": ("force", 4.44822),
    # Pressure
    "Pa": ("pressure", 1.0),
    "kPa": ("pressure", 1000.0),
    "MPa": ("pressure", 1e6),
    "bar": ("pressure", 1e5),
    "psi": ("pressure", 6894.76),
    "atm": ("pressure", 101325.0),
    # Temperature (special handling)
    "K": ("temperature", 1.0),  # Base
    # Velocity
    "m/s": ("velocity", 1.0),
    "km/h": ("velocity", 0.277778),
    "mph": ("velocity", 0.44704),
    "ft/s": ("velocity", 0.3048),
}


def normalize_dict_keys(obj: Any) -> Any:
    """
    Recursively sort dictionary keys for stable serialization.

    Args:
        obj: Any Python object

    Returns:
        The same object with all dicts having sorted keys
    """
    if isinstance(obj, dict):
        return {k: normalize_dict_keys(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [normalize_dict_keys(item) for item in obj]
    else:
        return obj


def normalize_list_ordering(obj: Any, sortable_keys: set[str] = None) -> Any:
    """
    Sort lists where order is not semantically meaningful.

    Args:
        obj: Any Python object
        sortable_keys: Set of dict keys whose list values should be sorted

    Returns:
        Object with specified lists sorted
    """
    if sortable_keys is None:
        sortable_keys = {"required_fields", "reasons", "reason_codes", "blocking_gates"}

    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in sortable_keys and isinstance(v, list):
                # Sort if all items are strings
                if all(isinstance(x, str) for x in v):
                    result[k] = sorted(v)
                else:
                    result[k] = [normalize_list_ordering(x, sortable_keys) for x in v]
            else:
                result[k] = normalize_list_ordering(v, sortable_keys)
        return result
    elif isinstance(obj, list):
        return [normalize_list_ordering(item, sortable_keys) for item in obj]
    else:
        return obj


def convert_to_canonical(value: float, from_unit: str) -> tuple[float, str]:
    """
    Convert a value to its canonical SI unit.

    Args:
        value: Numeric value
        from_unit: Source unit string

    Returns:
        (canonical_value, canonical_unit)
    """
    if from_unit not in CONVERSION_TO_SI:
        # Unknown unit, return as-is
        return (value, from_unit)

    quantity_type, multiplier = CONVERSION_TO_SI[from_unit]
    canonical_unit = CANONICAL_UNITS[quantity_type]
    canonical_value = value * multiplier

    return (canonical_value, canonical_unit)


def normalize_quantities(obj: Any) -> Any:
    """
    Convert all quantities to canonical form.

    Looks for dicts with 'value' and 'unit' keys and normalizes them.

    Args:
        obj: Any Python object

    Returns:
        Object with quantities normalized to SI
    """
    if isinstance(obj, dict):
        # Check if this is a quantity (has value + unit)
        if "value" in obj and "unit" in obj:
            value = obj["value"]
            unit = obj["unit"]
            if isinstance(value, (int, float)) and isinstance(unit, str):
                can_value, can_unit = convert_to_canonical(value, unit)
                result = obj.copy()
                result["value_canonical"] = can_value
                result["unit_canonical"] = can_unit
                # Keep original as display values
                result["value_display"] = value
                result["unit_display"] = unit
                return {k: normalize_quantities(v) for k, v in sorted(result.items())}

        return {k: normalize_quantities(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [normalize_quantities(item) for item in obj]
    else:
        return obj


def normalize_for_logging(obj: Any) -> str:
    """
    Normalize an object and serialize to JSON for logging/audit.

    Returns a deterministic JSON string suitable for diff comparison.

    Args:
        obj: Any Python object

    Returns:
        Deterministic JSON string
    """
    normalized = normalize_dict_keys(obj)
    normalized = normalize_list_ordering(normalized)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def normalize_for_response(obj: Any) -> dict:
    """
    Normalize an object for API response.

    Applies key ordering and list sorting for consistency.

    Args:
        obj: Any Python object (usually a dict)

    Returns:
        Normalized dict
    """
    normalized = normalize_dict_keys(obj)
    normalized = normalize_list_ordering(normalized)
    return normalized


def normalize_kernel_result(result: dict) -> dict:
    """
    Normalize a kernel result for storage/comparison.

    Applies full normalization including quantity conversion.

    Args:
        result: Kernel result dict

    Returns:
        Fully normalized result
    """
    normalized = normalize_dict_keys(result)
    normalized = normalize_list_ordering(normalized)
    normalized = normalize_quantities(normalized)
    return normalized


if __name__ == "__main__":
    # Demo
    test_obj = {
        "reasons": ["reason_b", "reason_a"],
        "z_key": 1,
        "a_key": 2,
        "quantity": {"value": 10, "unit": "lb"},
    }

    print("Original:", json.dumps(test_obj))
    print("Normalized:", normalize_for_logging(test_obj))
    print("With quantities:", json.dumps(normalize_kernel_result(test_obj), indent=2))
