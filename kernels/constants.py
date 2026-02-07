"""
Constants Kernel: Authoritative physical constants table.

Provides definitive values with provenance to prevent
confusion (e.g., specific weight vs density).
"""

from typing import Optional
from .base import KernelInterface, KernelResult, register_kernel


# Authoritative physical constants with provenance
# Values from CODATA 2018 and standard references
PHYSICAL_CONSTANTS = {
    # Fundamental constants
    "speed_of_light": {
        "value": 299792458.0,
        "unit": "m/s",
        "uncertainty": 0.0,
        "source": "CODATA 2018 (exact)",
        "symbol": "c"
    },
    "gravitational_constant": {
        "value": 6.67430e-11,
        "unit": "m3/(kg·s2)",
        "uncertainty": 0.00015e-11,
        "source": "CODATA 2018",
        "symbol": "G"
    },
    "planck_constant": {
        "value": 6.62607015e-34,
        "unit": "J·s",
        "uncertainty": 0.0,
        "source": "CODATA 2018 (exact)",
        "symbol": "h"
    },
    "boltzmann_constant": {
        "value": 1.380649e-23,
        "unit": "J/K",
        "uncertainty": 0.0,
        "source": "CODATA 2018 (exact)",
        "symbol": "k"
    },
    "avogadro_number": {
        "value": 6.02214076e23,
        "unit": "1/mol",
        "uncertainty": 0.0,
        "source": "CODATA 2018 (exact)",
        "symbol": "N_A"
    },
    
    # Standard Earth conditions
    "standard_gravity": {
        "value": 9.80665,
        "unit": "m/s2",
        "uncertainty": 0.0,
        "source": "ISO 80000-3 (exact by definition)",
        "symbol": "g_n",
        "aliases": ["g", "gravity", "gravitational acceleration"]
    },
    "standard_atmosphere": {
        "value": 101325.0,
        "unit": "Pa",
        "uncertainty": 0.0,
        "source": "ISO 2533 (exact by definition)",
        "symbol": "atm",
        "aliases": ["atmospheric pressure", "1 atm"]
    },
    
    # Water properties at standard conditions (20°C, 1 atm)
    "water_density_20C": {
        "value": 998.2,
        "unit": "kg/m3",
        "uncertainty": 0.1,
        "source": "CRC Handbook",
        "symbol": "ρ_water",
        "aliases": ["density of water", "water density"],
        "note": "At 20°C and 1 atm"
    },
    "water_specific_weight_20C": {
        "value": 9789.0,
        "unit": "N/m3",
        "uncertainty": 1.0,
        "source": "Derived: ρ × g",
        "symbol": "γ_water",
        "aliases": ["specific weight of water"],
        "note": "At 20°C and 1 atm. γ = ρg",
        "disambiguation": "This is WEIGHT DENSITY (N/m³), not surface tension"
    },
    "water_surface_tension_20C": {
        "value": 0.0728,
        "unit": "N/m",
        "uncertainty": 0.0001,
        "source": "CRC Handbook",
        "symbol": "σ_water",
        "aliases": ["surface tension of water"],
        "note": "At 20°C against air",
        "disambiguation": "This is SURFACE TENSION (N/m), not weight density"
    },
    
    # Air properties at standard conditions (20°C, 1 atm)  
    "air_density_20C": {
        "value": 1.204,
        "unit": "kg/m3",
        "uncertainty": 0.001,
        "source": "Ideal gas law at STP",
        "symbol": "ρ_air",
        "aliases": ["density of air", "air density"],
        "note": "At 20°C and 1 atm, dry air"
    },
    
    # Gas constants
    "universal_gas_constant": {
        "value": 8.314462618,
        "unit": "J/(mol·K)",
        "uncertainty": 0.0,
        "source": "CODATA 2018 (exact)",
        "symbol": "R",
        "aliases": ["gas constant", "ideal gas constant"]
    },
    "specific_gas_constant_air": {
        "value": 287.05,
        "unit": "J/(kg·K)",
        "uncertainty": 0.01,
        "source": "R/M_air",
        "symbol": "R_air",
        "note": "For dry air"
    },
}


@register_kernel
class ConstantsKernel(KernelInterface):
    """
    Physical constants lookup kernel.
    
    Provides authoritative values with provenance.
    Determinism level: D2 (full output determinism)
    """
    
    kernel_id = "constants_v1"
    version = "1.0.0"
    determinism_level = "D2"
    
    def execute(self, inputs: dict) -> KernelResult:
        """
        Look up a physical constant.
        
        Inputs:
            constant_id: ID of the constant to look up
            or
            search: Alias or description to search for
            
        Outputs:
            constant data with provenance
        """
        constant_id = inputs.get("constant_id")
        search_term = inputs.get("search", "").lower()
        
        if constant_id:
            # Direct lookup
            constant = PHYSICAL_CONSTANTS.get(constant_id)
            if constant:
                return KernelResult(
                    kernel_id=self.kernel_id,
                    version=self.version,
                    success=True,
                    result={
                        "constant_id": constant_id,
                        **constant
                    },
                    provenance={
                        "source": constant.get("source"),
                        "determinism": "D2"
                    }
                )
            else:
                return KernelResult(
                    kernel_id=self.kernel_id,
                    version=self.version,
                    success=False,
                    result=None,
                    warnings=[f"Unknown constant: {constant_id}"]
                )
        
        elif search_term:
            # Search by alias
            matches = []
            for cid, cdata in PHYSICAL_CONSTANTS.items():
                aliases = cdata.get("aliases", [])
                if (search_term in cid.lower() or 
                    any(search_term in a.lower() for a in aliases)):
                    matches.append({
                        "constant_id": cid,
                        **cdata
                    })
            
            if len(matches) == 1:
                return KernelResult(
                    kernel_id=self.kernel_id,
                    version=self.version,
                    success=True,
                    result=matches[0],
                    provenance={"determinism": "D2"}
                )
            elif len(matches) > 1:
                # Multiple matches - disambiguation needed
                return KernelResult(
                    kernel_id=self.kernel_id,
                    version=self.version,
                    success=False,
                    result={"candidates": matches},
                    warnings=["Multiple constants match. Disambiguation required."]
                )
            else:
                return KernelResult(
                    kernel_id=self.kernel_id,
                    version=self.version,
                    success=False,
                    result=None,
                    warnings=[f"No constants found matching: {search_term}"]
                )
        
        else:
            return KernelResult(
                kernel_id=self.kernel_id,
                version=self.version,
                success=False,
                result=None,
                warnings=["Either constant_id or search must be provided"]
            )
    
    def validate_inputs(self, inputs: dict) -> tuple[bool, list[str]]:
        """Validate inputs for constants lookup."""
        if "constant_id" not in inputs and "search" not in inputs:
            return (False, ["Either constant_id or search must be provided"])
        return (True, [])
    
    def get_envelope(self) -> dict:
        """Return list of available constants."""
        return {
            "available_constants": list(PHYSICAL_CONSTANTS.keys())
        }
