"""Bootstrap mode for incremental spec creation.

Stub module — implemented in task group 11.
"""
from __future__ import annotations

import pathlib
from typing import Any

from afspec.models import Spec


class BootstrapSpec:
    """Context manager for incremental spec creation.

    STUB: implemented in task group 11.

    Note: write_* methods accept Any so that both raw strings (used in tests)
    and typed dataclasses (used by real consumers) satisfy mypy until the real
    implementation is wired up in task group 11.
    """

    def __init__(
        self, spec_root: pathlib.Path, spec_id: str, spec_name: str
    ) -> None:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def __enter__(self) -> BootstrapSpec:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def __exit__(self, *args: Any) -> None:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def write_prd(self, prd: Any) -> None:
        raise NotImplementedError("BootstrapSpec.write_prd not yet implemented (task group 11)")

    def write_requirements(self, requirements: Any) -> None:
        raise NotImplementedError(
            "BootstrapSpec.write_requirements not yet implemented (task group 11)"
        )

    def write_test_spec(self, test_spec: Any) -> None:
        raise NotImplementedError(
            "BootstrapSpec.write_test_spec not yet implemented (task group 11)"
        )

    def write_tasks(self, tasks: Any) -> None:
        raise NotImplementedError(
            "BootstrapSpec.write_tasks not yet implemented (task group 11)"
        )

    @property
    def result(self) -> Spec:
        raise NotImplementedError(
            "BootstrapSpec.result not yet implemented (task group 11)"
        )
