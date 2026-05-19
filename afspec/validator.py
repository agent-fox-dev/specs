"""Validation logic for afspec.

Implements schema loading (task group 3) and validation entry points.
Cross-file integrity and full validate() are stubs for task group 7.
"""
from __future__ import annotations

import importlib.resources
import json
from typing import Any

import jsonschema
import jsonschema.exceptions

from afspec.models import Spec, ValidationError

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = 1

# Mapping from file name to bundled schema file name
_SCHEMA_FILE_MAP: dict[str, str] = {
    "requirements.json": "requirements.v1.json",
    "test_spec.json": "test_spec.v1.json",
    "tasks.json": "tasks.v1.json",
    "prd.md": "prd-frontmatter.v1.json",
    "prd-frontmatter": "prd-frontmatter.v1.json",
    # Also allow direct schema file names
    "requirements.v1.json": "requirements.v1.json",
    "test_spec.v1.json": "test_spec.v1.json",
    "tasks.v1.json": "tasks.v1.json",
    "prd-frontmatter.v1.json": "prd-frontmatter.v1.json",
}


def _load_schema(schema_name: str) -> dict[str, Any]:
    """Load a bundled JSON Schema file by name.

    Args:
        schema_name: The schema file name (e.g., 'requirements.v1.json').

    Returns:
        Parsed JSON Schema dict.
    """
    package = importlib.resources.files("afspec.schemas")
    schema_file = package.joinpath(schema_name)
    text = schema_file.read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def _get_schema_for_file(file_name: str) -> dict[str, Any] | None:
    """Return the bundled schema for the given file name, or None if unknown."""
    schema_file = _SCHEMA_FILE_MAP.get(file_name)
    if schema_file is None:
        return None
    return _load_schema(schema_file)


def _jsonschema_errors_to_validation_errors(
    file_name: str,
    js_errors: list[jsonschema.exceptions.ValidationError],
) -> list[ValidationError]:
    """Convert jsonschema ValidationError instances to afspec ValidationError instances."""
    result = []
    for err in js_errors:
        # Build a JSON path string from the error path
        path_parts = []
        for part in err.absolute_path:
            if isinstance(part, int):
                path_parts.append(f"[{part}]")
            else:
                path_parts.append(str(part))
        path = "/" + "/".join(path_parts) if path_parts else ""

        # Build a human-readable message
        message = err.message

        result.append(
            ValidationError(
                file=file_name,
                path=path,
                rule="schema",
                message=message,
                severity="error",
            )
        )
    return result


def validate_dict_against_schema(
    file_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate a dict against the bundled JSON Schema for the given file.

    Args:
        file_name: The artifact file name (e.g., 'requirements.json').
        data: The dict to validate.

    Returns:
        List of ValidationError instances (empty if valid).
    """
    schema = _get_schema_for_file(file_name)
    if schema is None:
        return []

    validator = jsonschema.Draft7Validator(schema)
    js_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return _jsonschema_errors_to_validation_errors(file_name, list(js_errors))


def _validate_cross_file(spec: Spec) -> list[ValidationError]:
    """Run cross-file integrity validation (seven rules).

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError("_validate_cross_file not yet implemented (task group 7)")


def _validate_schemas(spec: Spec) -> list[ValidationError]:
    """Run per-file JSON Schema validation against bundled schemas.

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError("_validate_schemas not yet implemented (task group 7)")


def validate(spec: Spec) -> list[ValidationError]:
    """Run full validation: schema, ID format, and cross-file checks.

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError("validate not yet implemented (task group 7)")
