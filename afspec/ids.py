"""ID format validation for afspec.

STUB — real implementation in task group 3.
"""
from __future__ import annotations

from afspec.models import ValidationError


def validate_id(id_str: str, expected_spec_id: str) -> list[ValidationError]:
    """Validate an ID string against spec-format patterns.

    STUB: raises NotImplementedError. Implemented in task group 3.
    """
    raise NotImplementedError("validate_id not yet implemented (task group 3)")


def check_sequential(ids: list[str]) -> list[ValidationError]:
    """Check that a list of IDs are sequentially numbered; return warnings for gaps.

    STUB: raises NotImplementedError. Implemented in task group 3.
    """
    raise NotImplementedError("check_sequential not yet implemented (task group 3)")
