"""afspec — Python spec-format library for agent-fox specifications.

Public API surface. Modules are implemented incrementally across task groups:
- Task group 2: models, exceptions (THIS GROUP)
- Task group 3: ids, schemas
- Task group 5: loader
- Task group 6: saver
- Task group 7: validator
- Task group 9: renderer
- Task group 10: lifecycle
- Task group 11: bootstrap, discovery
"""
from __future__ import annotations

import pathlib
from typing import Any

# Re-export exception types (using `as` for explicit re-export under mypy strict)
from afspec.exceptions import AfspecError as AfspecError
from afspec.exceptions import IncompleteSpecError as IncompleteSpecError
from afspec.exceptions import LifecycleError as LifecycleError
from afspec.exceptions import SpecValidationError as SpecValidationError

# Re-export all public types from models (explicit re-export)
from afspec.models import PRD as PRD
from afspec.models import ComplexEventCriterion as ComplexEventCriterion
from afspec.models import CorrectnessProperty as CorrectnessProperty
from afspec.models import Coverage as Coverage
from afspec.models import Dependency as Dependency
from afspec.models import EARSCriterion as EARSCriterion
from afspec.models import EdgeCaseTest as EdgeCaseTest
from afspec.models import ErrorHandlingEntry as ErrorHandlingEntry
from afspec.models import EventDrivenCriterion as EventDrivenCriterion
from afspec.models import ExecutionPath as ExecutionPath
from afspec.models import ExecutionPathStep as ExecutionPathStep
from afspec.models import OptionalCriterion as OptionalCriterion
from afspec.models import PRDFrontmatter as PRDFrontmatter
from afspec.models import PropertyTest as PropertyTest
from afspec.models import Requirement as Requirement
from afspec.models import Requirements as Requirements
from afspec.models import SmokeTest as SmokeTest
from afspec.models import Spec as Spec
from afspec.models import StateDrivenCriterion as StateDrivenCriterion
from afspec.models import Subtask as Subtask
from afspec.models import SubtaskState as SubtaskState
from afspec.models import TaskGroup as TaskGroup
from afspec.models import Tasks as Tasks
from afspec.models import TestCase as TestCase
from afspec.models import TestSpec as TestSpec
from afspec.models import TraceabilityEntry as TraceabilityEntry
from afspec.models import UbiquitousCriterion as UbiquitousCriterion
from afspec.models import UnwantedCriterion as UnwantedCriterion
from afspec.models import UserStory as UserStory
from afspec.models import ValidationError as ValidationError
from afspec.models import VerificationSubtask as VerificationSubtask

# ---------------------------------------------------------------------------
# Public API stubs — replaced by real implementations in later task groups
# ---------------------------------------------------------------------------


def load_spec(path: pathlib.Path) -> Spec:
    """Load a spec folder from disk into in-memory dataclass instances."""
    from afspec.loader import load_spec as _load_spec

    return _load_spec(path)


def save_spec(spec: Spec, path: pathlib.Path) -> None:
    """Write in-memory spec structures back to disk with atomic writes.

    STUB: implemented in task group 6.
    """
    raise NotImplementedError("save_spec not yet implemented (task group 6)")


def validate(spec: Spec) -> list[ValidationError]:
    """Validate a spec (schema + ID format + cross-file integrity).

    STUB: implemented in task group 7.
    """
    raise NotImplementedError("validate not yet implemented (task group 7)")


def render_requirements(requirements: Requirements) -> str:
    """Render requirements.json artifact to markdown.

    STUB: implemented in task group 9.
    """
    raise NotImplementedError("render_requirements not yet implemented (task group 9)")


def render_test_spec(test_spec: TestSpec) -> str:
    """Render test_spec.json artifact to markdown.

    STUB: implemented in task group 9.
    """
    raise NotImplementedError("render_test_spec not yet implemented (task group 9)")


def render_tasks(tasks: Tasks) -> str:
    """Render tasks.json artifact to markdown.

    STUB: implemented in task group 9.
    """
    raise NotImplementedError("render_tasks not yet implemented (task group 9)")


def render_combined(spec: Spec) -> str:
    """Render all four spec artifacts into one combined markdown document.

    STUB: implemented in task group 9.
    """
    raise NotImplementedError("render_combined not yet implemented (task group 9)")


def transition(spec: Spec, target_status: str) -> Spec:
    """Apply a lifecycle transition to a spec.

    STUB: implemented in task group 10.
    """
    raise NotImplementedError("transition not yet implemented (task group 10)")


def discover(spec_root: pathlib.Path | None = None) -> Any:
    """Discover spec folders in a root directory.

    STUB: implemented in task group 11.
    """
    raise NotImplementedError("discover not yet implemented (task group 11)")


def schema_version() -> int:
    """Return the bundled schema version."""
    from afspec.validator import _SCHEMA_VERSION

    return _SCHEMA_VERSION


class BootstrapSpec:
    """Context manager for incremental spec creation.

    STUB: implemented in task group 11.
    """

    def __init__(self, spec_root: pathlib.Path, spec_id: str, spec_name: str) -> None:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def __enter__(self) -> BootstrapSpec:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def __exit__(self, *args: Any) -> None:
        raise NotImplementedError("BootstrapSpec not yet implemented (task group 11)")

    def write_prd(self, prd: PRD) -> None:
        """Write prd.md to the bootstrap spec folder.

        STUB: implemented in task group 11.
        """
        raise NotImplementedError("BootstrapSpec.write_prd not yet implemented (task group 11)")

    def write_requirements(self, requirements: Requirements) -> None:
        """Write requirements.json to the bootstrap spec folder.

        STUB: implemented in task group 11.
        """
        raise NotImplementedError(
            "BootstrapSpec.write_requirements not yet implemented (task group 11)"
        )

    def write_test_spec(self, test_spec: TestSpec) -> None:
        """Write test_spec.json to the bootstrap spec folder.

        STUB: implemented in task group 11.
        """
        raise NotImplementedError(
            "BootstrapSpec.write_test_spec not yet implemented (task group 11)"
        )

    def write_tasks(self, tasks: Tasks) -> None:
        """Write tasks.json to the bootstrap spec folder.

        STUB: implemented in task group 11.
        """
        raise NotImplementedError(
            "BootstrapSpec.write_tasks not yet implemented (task group 11)"
        )

    @property
    def result(self) -> Spec:
        """Return the completed Spec after finalization.

        STUB: implemented in task group 11.
        """
        raise NotImplementedError(
            "BootstrapSpec.result not yet implemented (task group 11)"
        )
