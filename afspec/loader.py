"""Spec loading from disk for afspec.

STUB — real implementation in task group 5.
"""
from __future__ import annotations

import pathlib
from typing import TypeVar

from afspec.models import PRD, Spec

T = TypeVar("T")


def _load_prd(path: pathlib.Path) -> PRD:
    """Parse prd.md from disk into a PRD dataclass.

    STUB: raises NotImplementedError. Implemented in task group 5.
    """
    raise NotImplementedError("_load_prd not yet implemented (task group 5)")


def _load_json(path: pathlib.Path, target_type: type[T]) -> T:
    """Deserialize a JSON file from disk into the target dataclass type.

    STUB: raises NotImplementedError. Implemented in task group 5.
    """
    raise NotImplementedError("_load_json not yet implemented (task group 5)")


def _extract_intent(body: str) -> str:
    """Extract the ## Intent section body from a PRD markdown body.

    STUB: raises NotImplementedError. Implemented in task group 5.
    """
    raise NotImplementedError("_extract_intent not yet implemented (task group 5)")


def load_spec(path: pathlib.Path) -> Spec:
    """Load a spec folder from disk into in-memory dataclass instances.

    STUB: raises NotImplementedError. Implemented in task group 5.
    """
    raise NotImplementedError("load_spec not yet implemented (task group 5)")


__all__ = [
    "_load_prd",
    "_load_json",
    "_extract_intent",
    "load_spec",
]
