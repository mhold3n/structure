"""
Units Kernel: UCUM-based unit conversion and dimensional analysis.

Uses KernelInput/KernelOutput models.
"""

from typing import Optional
from datetime import datetime

from models.kernel_io import KernelInput, KernelOutput, Provenance, UnitMetadata
from .base import KernelInterface, register_kernel


# Simplified UCUM conversion factors to SI base units
UNIT_CONVERSIONS = {
    # Mass (to kg)
    "kg": 1.0,
    "g": 1e-3,
    "mg": 1e-6,
    "[lb_av]": 0.45359237,
    "lbm": 0.45359237,
    "[oz_av]": 0.028349523125,
    "[slug]": 14.593903,
    
    # Length (to m)
    "m": 1.0,
    "cm": 1e-2,
    "mm": 1e-3,
    "km": 1e3,
    "[ft_i]": 0.3048,
    "ft": 0.3048,
    "[in_i]": 0.0254,
    "in": 0.0254,
    "[mi_i]": 1609.344,
    
    # Time (to s)
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    
    # Force (to N)
    "N": 1.0,
    "kN": 1e3,
    "[lbf_av]": 4.4482216152605,
    "lbf": 4.4482216152605,
    "dyn": 1e-5,
    
    # Pressure (to Pa)
    "Pa": 1.0,
    "kPa": 1e3,
    "MPa": 1e6,
    "bar": 1e5,
    "atm": 101325.0,
    "[psi]": 6894.757293168,
    "psi": 6894.757293168,
    
    # Energy (to J)
    "J": 1.0,
    "kJ": 1e3,
    "MJ": 1e6,
    "cal": 4.184,
    "kcal": 4184.0,
    "BTU": 1055.06,
    "eV": 1.602176634e-19,
    
    # Power (to W)
    "W": 1.0,
    "kW": 1e3,
    "MW": 1e6,
    "hp": 745.7,
    
    # Temperature (special handling needed)
    "K": 1.0,
    "Cel": 1.0,
    "[degF]": 5/9,
    
    # Density (to kg/m³)
    "kg/m3": 1.0,
    "g/cm3": 1000.0,
    "g/L": 1.0,
    
    # Specific weight (to N/m³)
    "N/m3": 1.0,
    
    # Surface tension (to N/m)
    "N/m": 1.0,
    "mN/m": 1e-3,
    "dyn/cm": 1e-3,
}


@register_kernel
class UnitsKernel(KernelInterface):
    """
    Unit conversion and dimensional analysis kernel.
    
    Determinism level: D1 (numeric determinism)
    """
    
    kernel_id = "unit_converter_v1"
    version = "1.0.0"
    determinism_level = "D1"
    
    def execute(self, input: KernelInput) -> KernelOutput:
        """Execute with typed KernelInput."""
        return self._convert(input.args, input.request_id)
    
    def execute_legacy(self, args: dict) -> KernelOutput:
        """Legacy interface for backward compatibility."""
        return self._convert(args, "legacy")
    
    def _convert(self, args: dict, request_id: str) -> KernelOutput:
        """Core conversion logic."""
        value = args.get("value")
        from_unit = args.get("from_unit", "").strip()
        to_unit = args.get("to_unit", "").strip()
        
        # Get conversion factors
        from_factor = UNIT_CONVERSIONS.get(from_unit)
        to_factor = UNIT_CONVERSIONS.get(to_unit)
        
        if from_factor is None:
            return self._make_output(
                request_id=request_id,
                success=False,
                error=f"Unknown source unit: {from_unit}",
                warnings=[f"Unknown source unit: {from_unit}"]
            )
        
        # Convert to SI
        si_value = value * from_factor
        
        # Convert to target if specified
        if to_unit and to_factor:
            converted_value = si_value / to_factor
        else:
            converted_value = si_value
            to_unit = self._get_si_unit(from_unit)
        
        return self._make_output(
            request_id=request_id,
            success=True,
            result={
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": converted_value,
                "converted_unit": to_unit,
                "si_value": si_value,
            },
            units_metadata=UnitMetadata(
                input_units={"value": from_unit},
                output_units={"value": to_unit},
                conversions_applied=[f"{from_unit} → {to_unit}"]
            )
        )
    
    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        """Validate inputs for unit conversion."""
        errors = []
        
        if "value" not in args:
            errors.append("Missing required field: value")
        elif not isinstance(args["value"], (int, float)):
            errors.append("value must be numeric")
        
        if "from_unit" not in args:
            errors.append("Missing required field: from_unit")
        
        return (len(errors) == 0, errors)
    
    def _get_si_unit(self, unit: str) -> str:
        """Get the SI base unit for a given unit."""
        si_units = {
            "kg": "kg", "g": "kg", "mg": "kg", "[lb_av]": "kg", "lbm": "kg",
            "m": "m", "cm": "m", "mm": "m", "km": "m", "ft": "m", "[ft_i]": "m",
            "s": "s", "min": "s", "h": "s",
            "N": "N", "kN": "N", "lbf": "N", "[lbf_av]": "N",
            "Pa": "Pa", "kPa": "Pa", "MPa": "Pa", "bar": "Pa", "atm": "Pa", "psi": "Pa",
            "J": "J", "kJ": "J", "MJ": "J", "cal": "J", "kcal": "J",
            "W": "W", "kW": "W", "MW": "W", "hp": "W",
            "K": "K", "Cel": "K", "[degF]": "K",
        }
        return si_units.get(unit, unit)
    
    def get_envelope(self) -> dict:
        """Return valid input envelope."""
        return {
            "supported_units": list(UNIT_CONVERSIONS.keys()),
            "value_range": {"min": float("-inf"), "max": float("inf")}
        }
