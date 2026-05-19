"""Validation logic for afspec.

STUB — real implementation in task group 7.
"""
from __future__ import annotations

from typing import Any

from afspec.models import Spec, ValidationError


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


def _load_schema(schema_name: str) -> dict[str, Any]:
    """Load a bundled JSON Schema file by name.

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError("_load_schema not yet implemented (task group 7)")


def validate(spec: Spec) -> list[ValidationError]:
    """Run full validation: schema, ID format, and cross-file checks.

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError("validate not yet implemented (task group 7)")


def validate_dict_against_schema(
    file_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate a dict against the bundled JSON Schema for the given file.

    STUB: raises NotImplementedError. Implemented in task group 7.
    """
    raise NotImplementedError(
        "validate_dict_against_schema not yet implemented (task group 7)"
    )
