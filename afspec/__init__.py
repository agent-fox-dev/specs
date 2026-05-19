"""afspec — Python spec-format library for agent-fox specifications.

This package provides the complete Python implementation of the agent-fox
spec-format v1.  It mirrors the Go library (spec 01) in functionality:

- **Data models** — frozen dataclasses for all spec-format entities (PRD,
  Requirements, TestSpec, Tasks) including a discriminated-union for EARS
  criteria and a state-machine enum for subtask states.
- **File I/O** — atomic, deterministic load and save of the four spec
  artifacts (``prd.md``, ``requirements.json``, ``test_spec.json``,
  ``tasks.json``).
- **Validation** — per-file JSON Schema validation against bundled schemas,
  ID-format checks, and seven cross-file integrity rules.
- **Rendering** — deterministic markdown rendering of each JSON artifact
  plus a combined-document renderer.
- **Lifecycle management** — five-state machine (draft → active → sealed →
  superseded / archived) with intent-hash enforcement.
- **Bootstrap mode** — ``BootstrapSpec`` context manager for incremental
  spec creation that defers cross-file validation until all four files are
  written.
- **Discovery** — scan a spec root directory, load metadata, and build a
  dependency graph with cycle detection.

Quick start::

    import pathlib
    import afspec

    # Load a spec from disk
    spec = afspec.load_spec(pathlib.Path("specs/01_my_feature"))

    # Validate it
    errors = afspec.validate(spec)

    # Render to markdown
    doc = afspec.render_combined(spec)

    # Transition draft → active (computes intent hash)
    active = afspec.transition(spec, "active")
    afspec.save_spec(active, pathlib.Path("specs/01_my_feature"))

    # Discover all specs in a root directory
    result = afspec.discover(pathlib.Path("specs"))
    for entry in result.entries:
        print(entry.spec_id, entry.spec_name, entry.status)
"""
from __future__ import annotations

import pathlib

# Re-export bootstrap and discovery types
from afspec.bootstrap import BootstrapSpec as BootstrapSpec
from afspec.discovery import CyclicDependencyError as CyclicDependencyError
from afspec.discovery import DependencyEdge as DependencyEdge
from afspec.discovery import DependencyGraph as DependencyGraph
from afspec.discovery import DiscoveryResult as DiscoveryResult
from afspec.discovery import SpecEntry as SpecEntry

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
# Public API functions
# ---------------------------------------------------------------------------


def load_spec(path: pathlib.Path) -> Spec:
    """Load a spec folder from disk into in-memory dataclass instances.

    Reads all four required artifacts (``prd.md``, ``requirements.json``,
    ``test_spec.json``, ``tasks.json``) from *path* and returns a populated
    :class:`Spec` instance.

    Args:
        path: Directory containing the four spec artifacts.

    Returns:
        A :class:`Spec` with ``prd``, ``requirements``, ``test_spec``, and
        ``tasks`` fields fully populated.

    Raises:
        FileNotFoundError: *path* does not exist or is not a directory.
        IncompleteSpecError: One or more of the four required files are absent;
            the exception's ``missing_files`` attribute lists them.
        SpecValidationError: ``prd.md`` is missing the ``## Intent`` section.
        ValueError: A JSON file contains malformed JSON, or the YAML
            frontmatter in ``prd.md`` cannot be parsed.
    """
    from afspec.loader import load_spec as _load_spec

    return _load_spec(path)


def save_spec(spec: Spec, path: pathlib.Path) -> None:
    """Write in-memory spec structures back to disk with atomic writes.

    Serialises all four artifacts to *path* using write-to-tempfile-then-rename
    so that a failure mid-write leaves the directory in its pre-save state.

    Computed fields are updated automatically before writing:

    - ``updated_at`` in ``prd.md`` frontmatter is set to the current UTC
      timestamp in ISO 8601 format.
    - ``coverage`` in ``test_spec.json`` is recomputed from the current set
      of test cases, property tests, edge-case tests, and smoke tests.

    Serialisation guarantees:
    - JSON: keys sorted alphabetically, 2-space indentation, trailing newline.
    - YAML frontmatter: fixed field order per the spec-format v1 definition.

    Args:
        spec: The in-memory spec to persist.
        path: Target directory; must already exist.

    Raises:
        FileNotFoundError: *path* does not exist.
        OSError: A write failure occurs; temporary files are cleaned up and the
            directory is left in its pre-save state.
        LifecycleError: The spec's lifecycle state forbids the attempted save
            (e.g., intent body was altered in an *active* spec, or any field
            was changed on a *sealed* / *superseded* / *archived* spec).
    """
    from afspec.saver import save_spec as _save_spec

    _save_spec(spec, path)


def validate(spec: Spec) -> list[ValidationError]:
    """Validate a spec against all three validation layers.

    Runs the following checks in order, collecting all violations rather than
    stopping at the first error:

    1. **Schema validation** — each JSON artifact is validated against its
       bundled JSON Schema (``requirements.v1.json``, ``test_spec.v1.json``,
       ``tasks.v1.json``) and the PRD frontmatter is validated against
       ``prd-frontmatter.v1.json``.
    2. **ID format validation** — every ID field is checked against the
       patterns defined in spec-format.md Appendix A, including ``spec_id``
       consistency and positive-integer numeric components.
    3. **Cross-file integrity** — the seven rules from spec-format.md §9.2
       (orphan references, coverage gaps, glossary cross-check, spec_id
       consistency across all four files).

    Args:
        spec: The spec to validate (typically returned by :func:`load_spec`).

    Returns:
        A list of :class:`~afspec.models.ValidationError` instances.  An empty
        list means the spec is fully valid.  Each error carries ``file``,
        ``path``, ``rule``, ``message``, and ``severity`` (``"error"`` or
        ``"warning"``).
    """
    from afspec.validator import validate as _validate

    return _validate(spec)


def render_requirements(requirements: Requirements) -> str:
    """Render a ``requirements.json`` artifact to markdown.

    Produces a deterministic markdown document containing the introduction,
    glossary, requirements with EARS-formatted acceptance criteria and edge
    cases, correctness properties, execution paths, and error-handling table.

    EARS sentence templates used:

    - ubiquitous: ``THE {system} SHALL {action}``
    - event_driven: ``WHEN {trigger}, THE {system} SHALL {action}``
    - complex_event: ``WHEN {trigger} AND {condition}, THE {system} SHALL {action}``
    - state_driven: ``WHILE {state}, THE {system} SHALL {action}``
    - unwanted: ``IF {error_condition}, THEN THE {system} SHALL {action}``
    - optional: ``WHERE {feature}, THE {system} SHALL {action}``

    Empty fields render as ``<missing>``; a non-empty ``return_contract``
    appends ``AND return {return_contract}`` to the sentence.

    Args:
        requirements: The in-memory requirements artifact.

    Returns:
        A deterministic markdown string; multiple calls with the same input
        produce byte-identical output.
    """
    from afspec.renderer import render_requirements as _render_requirements

    return _render_requirements(requirements)


def render_test_spec(test_spec: TestSpec) -> str:
    """Render a ``test_spec.json`` artifact to markdown.

    Produces a deterministic markdown document containing all test cases,
    property tests, edge-case tests, smoke tests, and the coverage matrix.

    Args:
        test_spec: The in-memory test-spec artifact.

    Returns:
        A deterministic markdown string.
    """
    from afspec.renderer import render_test_spec as _render_test_spec

    return _render_test_spec(test_spec)


def render_tasks(tasks: Tasks) -> str:
    """Render a ``tasks.json`` artifact to markdown.

    Produces a deterministic markdown document containing all task groups,
    subtasks (with state), verification subtasks, dependencies, and the
    traceability table.

    Args:
        tasks: The in-memory tasks artifact.

    Returns:
        A deterministic markdown string.
    """
    from afspec.renderer import render_tasks as _render_tasks

    return _render_tasks(tasks)


def render_combined(spec: Spec) -> str:
    """Render all four spec artifacts into one combined markdown document.

    The output is structured as:

    1. The PRD body verbatim (as authored — not re-serialised).
    2. A ``# Requirements`` section containing the rendered requirements.
    3. A ``# Test Specification`` section containing the rendered test spec.
    4. A ``# Tasks`` section containing the rendered tasks.

    Args:
        spec: The complete spec to render.

    Returns:
        A deterministic combined markdown string.  The PRD body is always the
        leading content; section order is fixed as listed above.
    """
    from afspec.renderer import render_combined as _render_combined

    return _render_combined(spec)


def transition(spec: Spec, target_status: str) -> Spec:
    """Apply a lifecycle transition to a spec, returning the updated spec.

    Legal transitions (all others raise :class:`LifecycleError`):

    - ``draft → active`` — computes and stores the ``intent_hash`` (SHA-256
      of the normalised ``## Intent`` section body).
    - ``draft → archived``
    - ``active → sealed``
    - ``sealed → superseded`` — adds a deprecation banner to all four files.
    - ``sealed → archived``

    The returned :class:`Spec` is a new frozen instance; the original is not
    modified.  Call :func:`save_spec` to persist the result.

    Args:
        spec: The current spec (must be loaded from disk or newly constructed).
        target_status: One of ``"active"``, ``"sealed"``, ``"superseded"``,
            ``"archived"``.

    Returns:
        A new :class:`Spec` with the updated lifecycle state and any
        automatically computed fields (e.g. ``intent_hash``).

    Raises:
        LifecycleError: The requested transition is not legal from the spec's
            current state, or an immutable field was altered in an *active*
            spec, or the intent body has been tampered with.
    """
    from afspec.lifecycle import transition as _transition

    return _transition(spec, target_status)


def discover(spec_root: pathlib.Path | None = None) -> DiscoveryResult:
    """Discover spec folders in a root directory and build a dependency graph.

    Scans *spec_root* for directories matching the ``{NN}_{snake_case_name}``
    naming pattern (e.g. ``01_my_feature``, ``02_other_feature``).  The
    ``archive/`` subdirectory is always skipped.

    For each discovered folder only the PRD frontmatter is read (not all four
    artifacts), making this function fast even for large spec trees.  Folders
    that match the naming pattern but are missing required files are included
    in the results with ``complete=False``.

    A dependency graph is built from ``tasks.json`` dependency declarations
    when those files are present.

    Args:
        spec_root: Directory to scan.  Defaults to the current working
            directory when ``None``.

    Returns:
        A :class:`~afspec.discovery.DiscoveryResult` containing a list of
        :class:`~afspec.discovery.SpecEntry` instances and a
        :class:`~afspec.discovery.DependencyGraph` that supports topological
        sorting and cycle detection.

    Raises:
        FileNotFoundError: *spec_root* does not exist or is not a directory.
        CyclicDependencyError: The dependency graph contains a cycle; the
            exception message identifies the spec IDs involved.
    """
    from afspec.discovery import discover as _discover

    return _discover(spec_root)


def schema_version() -> int:
    """Return the bundled JSON Schema version number.

    All four bundled schemas (``prd-frontmatter.v1.json``,
    ``requirements.v1.json``, ``test_spec.v1.json``, ``tasks.v1.json``) track
    a single schema version.  This function exposes that version so callers
    can verify compatibility.

    Returns:
        The integer schema version (currently ``1``).
    """
    from afspec.validator import _SCHEMA_VERSION

    return _SCHEMA_VERSION


# BootstrapSpec is imported at the top of this module from afspec.bootstrap
