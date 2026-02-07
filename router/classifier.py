"""
Router: Deterministic task classification.

Rule-based routing with LLM as tie-breaker only.
Output is a typed TaskPlan, not freeform text.
"""

import re
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class TaskPlan:
    """Typed output from router - deterministic classification."""
    domain: str  # physics, chemistry, math, code, general
    subdomain: Optional[str] = None  # fluids, mechanics, thermo, etc.
    needs_units: bool = False
    has_equations: bool = False
    risk_level: str = "low"  # low, medium, high
    required_gates: list[str] = None
    selected_kernels: list[str] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.required_gates is None:
            self.required_gates = []
        if self.selected_kernels is None:
            self.selected_kernels = []
    
    def to_dict(self) -> dict:
        return asdict(self)


# --- Feature Extraction (Deterministic) ---

# Unit patterns (common physics/engineering units)
UNIT_PATTERNS = [
    r'\b(kg|g|mg|lb|lbs|lbm|lbf|slug|oz)\b',  # mass/force
    r'\b(m|cm|mm|km|ft|in|inch|mile|mi)\b',    # length
    r'\b(s|sec|second|min|minute|hour|hr|h)\b', # time
    r'\b(N|newton|dyn|kN)\b',                   # force
    r'\b(Pa|kPa|MPa|bar|atm|psi)\b',            # pressure
    r'\b(J|kJ|MJ|cal|kcal|BTU|eV)\b',           # energy
    r'\b(W|kW|MW|hp|horsepower)\b',             # power
    r'\b(K|°C|°F|Celsius|Fahrenheit|Kelvin)\b', # temperature
    r'\b(m/s|km/h|mph|ft/s)\b',                 # velocity
    r'\b(m/s²|ft/s²|g)\b',                      # acceleration
    r'\b(kg/m³|g/cm³|lb/ft³)\b',                # density
    r'\b(N/m³|lbf/ft³)\b',                      # specific weight
    r'\b(N/m|dyn/cm)\b',                        # surface tension
]

# Equation indicators
EQUATION_PATTERNS = [
    r'=',                # equals sign
    r'\$.*\$',           # LaTeX inline
    r'\\\[.*\\\]',       # LaTeX display
    r'\b[a-zA-Z]\s*=',   # variable assignment
    r'∫|∑|∏|∂|∇',        # calculus symbols
]

# Domain keywords
DOMAIN_KEYWORDS = {
    "physics.fluids": [
        "fluid", "water", "liquid", "gas", "flow", "pressure", "viscosity",
        "buoyancy", "hydrostatic", "bernoulli", "reynolds", "density",
        "specific weight", "surface tension", "pipe", "channel"
    ],
    "physics.mechanics": [
        "force", "mass", "acceleration", "velocity", "momentum", "torque",
        "friction", "gravity", "newton", "kinematics", "dynamics",
        "projectile", "motion", "collision", "energy", "work"
    ],
    "physics.thermodynamics": [
        "heat", "temperature", "entropy", "enthalpy", "thermal",
        "ideal gas", "adiabatic", "isothermal", "carnot", "efficiency",
        "specific heat", "conduction", "convection", "radiation"
    ],
    "chemistry": [
        "reaction", "molecule", "atom", "bond", "equilibrium", "pH",
        "acid", "base", "oxidation", "reduction", "stoichiometry",
        "molar", "concentration", "solution"
    ],
    "math": [
        "integral", "derivative", "equation", "solve", "proof",
        "matrix", "vector", "polynomial", "limit", "series",
        "differential", "algebra", "calculus", "trigonometry"
    ],
    "code": [
        "function", "class", "code", "program", "algorithm", "debug",
        "error", "exception", "refactor", "test", "implement"
    ],
}

# Ambiguous/high-risk terms that require clarification
AMBIGUOUS_TERMS = [
    "specific weight", "weight", "pound", "lb", "gamma",
    "unit weight", "density"  # can be confused
]


def extract_features(text: str) -> dict:
    """Extract deterministic features from input text."""
    text_lower = text.lower()
    
    # Check for units
    units_found = []
    for pattern in UNIT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        units_found.extend(matches)
    
    # Check for equations
    has_equations = any(
        re.search(pattern, text) for pattern in EQUATION_PATTERNS
    )
    
    # Count numeric values
    numbers = re.findall(r'\b\d+\.?\d*\b', text)
    numeric_density = len(numbers) / max(len(text.split()), 1)
    
    # Check for ambiguous terms
    ambiguous_found = [
        term for term in AMBIGUOUS_TERMS if term in text_lower
    ]
    
    # Domain keyword matches
    domain_scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            domain_scores[domain] = score
    
    return {
        "units_found": units_found,
        "has_equations": has_equations,
        "numeric_density": numeric_density,
        "ambiguous_terms": ambiguous_found,
        "domain_scores": domain_scores
    }


def classify_task(user_input: str, domain_hint: Optional[str] = None) -> dict:
    """
    Classify a task into a typed TaskPlan.
    
    This is deterministic - same input produces same output.
    """
    features = extract_features(user_input)
    
    # Determine domain
    if domain_hint:
        domain = domain_hint
    elif features["domain_scores"]:
        # Pick highest scoring domain
        domain = max(features["domain_scores"], key=features["domain_scores"].get)
    else:
        domain = "general"
    
    # Split domain into domain/subdomain
    if "." in domain:
        main_domain, subdomain = domain.split(".", 1)
    else:
        main_domain = domain
        subdomain = None
    
    # Determine risk level
    risk_level = "low"
    if features["ambiguous_terms"]:
        risk_level = "medium"
    if len(features["ambiguous_terms"]) > 1:
        risk_level = "high"
    
    # Determine required gates
    required_gates = ["schema_gate"]  # Always
    
    if features["units_found"]:
        required_gates.append("unit_consistency_gate")
    
    if features["ambiguous_terms"]:
        required_gates.append("ambiguity_gate")
    
    # Select kernels based on domain
    selected_kernels = []
    if features["units_found"]:
        selected_kernels.append("unit_converter_v1")
    
    if main_domain == "physics":
        if subdomain == "fluids":
            selected_kernels.append("fluids_statics_v1")
        elif subdomain == "mechanics":
            selected_kernels.append("mechanics_kinematics_v1")
        elif subdomain == "thermodynamics":
            selected_kernels.append("thermo_ideal_gas_v1")
    
    # Build task plan
    plan = TaskPlan(
        domain=main_domain,
        subdomain=subdomain,
        needs_units=bool(features["units_found"]),
        has_equations=features["has_equations"],
        risk_level=risk_level,
        required_gates=required_gates,
        selected_kernels=selected_kernels,
        confidence=1.0 if domain_hint else 0.8
    )
    
    return plan.to_dict()
