"""
Schema Validator: JSON Schema validation for registry, specs, and policies.

Validates that:
- Registry entries conform to their schemas
- TaskSpecs conform to task_request.schema.json
- Policies conform to policy schemas
"""

import json
from pathlib import Path
from typing import Optional
from jsonschema import validate, ValidationError, Draft202012Validator

from .loader import PROJECT_ROOT, SCHEMAS_DIR, REGISTRY_DIR, POLICIES_DIR


class SchemaValidator:
    """
    Validates data against JSON Schema definitions.

    Caches loaded schemas for performance.
    """

    def __init__(self):
        self._schema_cache: dict[str, dict] = {}

    def _load_schema(self, schema_id: str) -> Optional[dict]:
        """Load and cache a schema by ID."""
        if schema_id in self._schema_cache:
            return self._schema_cache[schema_id]

        # Normalize schema_id
        if not schema_id.endswith(".schema.json"):
            schema_id = f"{schema_id}.schema.json"

        schema_path = SCHEMAS_DIR / schema_id
        if schema_path.exists():
            with open(schema_path) as f:
                schema = json.load(f)
                self._schema_cache[schema_id] = schema
                return schema
        return None

    def validate_against_schema(self, data: dict, schema_id: str) -> tuple[bool, list[str]]:
        """
        Validate data against a schema.

        Returns:
            (is_valid, error_messages)
        """
        schema = self._load_schema(schema_id)
        if not schema:
            return (False, [f"Schema not found: {schema_id}"])

        try:
            validate(instance=data, schema=schema)
            return (True, [])
        except ValidationError as e:
            errors = [f"{e.json_path}: {e.message}"]
            return (False, errors)

    def validate_task_request(self, data: dict) -> tuple[bool, list[str]]:
        """Validate a TaskRequest against its schema."""
        return self.validate_against_schema(data, "task_request")

    def validate_task_plan(self, data: dict) -> tuple[bool, list[str]]:
        """Validate a TaskPlan against its schema."""
        return self.validate_against_schema(data, "task_plan")

    def validate_kernel_result(self, data: dict) -> tuple[bool, list[str]]:
        """Validate a KernelResult against its schema."""
        return self.validate_against_schema(data, "kernel_result")


class RegistryValidator:
    """
    Validates registry files have required structure.
    """

    # Minimal schema for kernel registry entries
    KERNEL_ENTRY_SCHEMA = {
        "type": "object",
        "required": ["kernel_id", "version", "type"],
        "properties": {
            "kernel_id": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "type": {"type": "string", "enum": ["classical", "surrogate", "hybrid"]},
            "determinism_guarantee": {"type": "string", "enum": ["D1", "D2", "NONE"]},
            "compatible_domains": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "string"},
        },
    }

    # Minimal schema for quantity registry entries
    QUANTITY_ENTRY_SCHEMA = {
        "type": "object",
        "required": ["quantity_id", "dimensions"],
        "properties": {
            "quantity_id": {"type": "string", "minLength": 1},
            "dimensions": {"type": "object"},
            "preferred_unit": {"type": "string"},
            "admissible_units": {"type": "array", "items": {"type": "string"}},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "collides_with": {"type": "array", "items": {"type": "string"}},
        },
    }

    def validate_kernel_registry(self) -> tuple[bool, list[str]]:
        """Validate all entries in kernels.json."""
        registry_path = REGISTRY_DIR / "kernels.json"
        if not registry_path.exists():
            return (False, ["kernels.json not found"])

        with open(registry_path) as f:
            registry = json.load(f)

        kernels = registry.get("kernels", [])
        errors = []

        for i, kernel in enumerate(kernels):
            try:
                validate(instance=kernel, schema=self.KERNEL_ENTRY_SCHEMA)
            except ValidationError as e:
                errors.append(f"kernels[{i}] ({kernel.get('kernel_id', 'unknown')}): {e.message}")

        return (len(errors) == 0, errors)

    def validate_quantities_registry(self) -> tuple[bool, list[str]]:
        """Validate all entries in quantities.json."""
        registry_path = REGISTRY_DIR / "quantities.json"
        if not registry_path.exists():
            return (False, ["quantities.json not found"])

        with open(registry_path) as f:
            registry = json.load(f)

        quantities = registry.get("quantities", [])
        errors = []

        for i, qty in enumerate(quantities):
            try:
                validate(instance=qty, schema=self.QUANTITY_ENTRY_SCHEMA)
            except ValidationError as e:
                errors.append(f"quantities[{i}] ({qty.get('quantity_id', 'unknown')}): {e.message}")

        return (len(errors) == 0, errors)


class PolicyValidator:
    """
    Validates policy files have required structure.
    """

    # Base schema for all policies
    POLICY_BASE_SCHEMA = {
        "type": "object",
        "required": ["policy_id", "version"],
        "properties": {
            "policy_id": {"type": "string", "minLength": 1},
            "version": {"type": "string"},
            "description": {"type": "string"},
            "applies_to": {"type": "array", "items": {"type": "string"}},
        },
    }

    # Schema for unit_disambiguation policy
    UNIT_DISAMBIGUATION_SCHEMA = {
        "type": "object",
        "required": ["policy_id", "version"],
        "properties": {
            "policy_id": {"type": "string"},
            "version": {"type": "string"},
            "ucum_required": {"type": "boolean"},
            "ambiguous_units": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["ACCEPT", "CLARIFY", "DEFAULT", "REJECT"],
                        },
                        "candidates": {"type": "array", "items": {"type": "string"}},
                        "question": {"type": "string"},
                    },
                },
            },
            "disallowed_without_disambiguator": {"type": "array", "items": {"type": "string"}},
        },
    }

    def validate_policy(self, policy_name: str) -> tuple[bool, list[str]]:
        """Validate a specific policy file."""
        import yaml

        policy_path = POLICIES_DIR / f"{policy_name}.yaml"
        if not policy_path.exists():
            return (False, [f"Policy not found: {policy_name}"])

        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        if policy is None:
            return (False, [f"Policy {policy_name} is empty or invalid YAML"])

        # Infer policy_id from filename if not present (common in existing policies)
        if "policy_id" not in policy:
            policy["policy_id"] = policy_name
        if "version" not in policy:
            policy["version"] = "1.0"

        # Choose schema based on policy type
        if policy_name == "unit_disambiguation":
            schema = self.UNIT_DISAMBIGUATION_SCHEMA
        else:
            schema = self.POLICY_BASE_SCHEMA

        try:
            validate(instance=policy, schema=schema)
            return (True, [])
        except ValidationError as e:
            return (False, [f"{policy_name}: {e.message}"])

    def validate_all_policies(self) -> tuple[bool, list[str]]:
        """Validate all policy files."""
        all_errors = []

        for policy_file in POLICIES_DIR.glob("*.yaml"):
            policy_name = policy_file.stem
            is_valid, errors = self.validate_policy(policy_name)
            all_errors.extend(errors)

        return (len(all_errors) == 0, all_errors)


# Convenience functions


def validate_all_registries() -> tuple[bool, list[str]]:
    """Validate all registry files."""
    validator = RegistryValidator()
    all_errors = []

    is_valid, errors = validator.validate_kernel_registry()
    all_errors.extend(errors)

    is_valid, errors = validator.validate_quantities_registry()
    all_errors.extend(errors)

    return (len(all_errors) == 0, all_errors)


def validate_all_policies() -> tuple[bool, list[str]]:
    """Validate all policy files."""
    validator = PolicyValidator()
    return validator.validate_all_policies()
