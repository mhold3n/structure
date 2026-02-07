"""
Loader: Load registry, schemas, and policies from disk.
"""

import json
import yaml
from pathlib import Path
from typing import Optional, Any

# Base paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
REGISTRY_DIR = PROJECT_ROOT / "registry"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
POLICIES_DIR = PROJECT_ROOT / "policies"


def load_registry() -> dict:
    """Load the kernel registry."""
    registry_path = REGISTRY_DIR / "kernels.json"
    if registry_path.exists():
        with open(registry_path) as f:
            return json.load(f)
    return {"kernels": []}


def load_quantities() -> dict:
    """Load the quantities registry."""
    path = REGISTRY_DIR / "quantities.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"quantities": []}


def load_reason_codes() -> dict:
    """Load reason codes registry."""
    path = REGISTRY_DIR / "reason_codes.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"reason_codes": {}}


def load_schema(schema_id: str) -> Optional[dict]:
    """
    Load a schema by ID.

    schema_id can be:
    - Full filename: "problem_spec.schema.json"
    - Basename: "problem_spec"
    """
    # Normalize schema_id
    if not schema_id.endswith(".schema.json"):
        schema_id = f"{schema_id}.schema.json"

    schema_path = SCHEMAS_DIR / schema_id
    if schema_path.exists():
        with open(schema_path) as f:
            return json.load(f)
    return None


def load_policy(policy_id: str) -> Optional[dict]:
    """
    Load a policy by ID.

    policy_id can be:
    - Full filename: "determinism.yaml"
    - Basename: "determinism"
    """
    # Normalize policy_id
    if not policy_id.endswith(".yaml"):
        policy_id = f"{policy_id}.yaml"

    policy_path = POLICIES_DIR / policy_id
    if policy_path.exists():
        with open(policy_path) as f:
            return yaml.safe_load(f)
    return None


def load_all_schemas() -> dict[str, dict]:
    """Load all schemas into a dictionary keyed by $id."""
    schemas = {}
    for schema_file in SCHEMAS_DIR.glob("*.schema.json"):
        with open(schema_file) as f:
            schema = json.load(f)
            schema_id = schema.get("$id", schema_file.stem)
            schemas[schema_id] = schema
    return schemas


def load_all_policies() -> dict[str, dict]:
    """Load all policies into a dictionary keyed by filename."""
    policies = {}
    for policy_file in POLICIES_DIR.glob("*.yaml"):
        with open(policy_file) as f:
            policies[policy_file.stem] = yaml.safe_load(f)
    return policies
