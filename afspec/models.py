"""Data models for the afspec library.

Frozen dataclasses for all spec-format entities: PRD, Requirements, TestSpec,
Tasks, EARS criteria (discriminated union), subtask state machine, and the
top-level Spec aggregate.
"""
from __future__ import annotations

import dataclasses
import enum
from typing import Any

# ---------------------------------------------------------------------------
# Subtask state machine
# ---------------------------------------------------------------------------

_LEGAL_SUBTASK_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pending", "queued"),
        ("pending", "dropped"),
        ("queued", "in_progress"),
        ("queued", "pending"),
        ("queued", "dropped"),
        ("in_progress", "done"),
        ("in_progress", "pending_reevaluation"),
        ("done", "pending_reevaluation"),
        ("pending_reevaluation", "pending"),
        ("pending_reevaluation", "dropped"),
    }
)


class SubtaskState(enum.Enum):
    """Lifecycle states for a task subtask."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    PENDING_REEVALUATION = "pending_reevaluation"
    DROPPED = "dropped"

    def can_transition_to(self, target: SubtaskState) -> bool:
        """Return True iff this → target is a legal transition."""
        return (self.value, target.value) in _LEGAL_SUBTASK_TRANSITIONS


# ---------------------------------------------------------------------------
# PRD data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PRDFrontmatter:
    """YAML frontmatter from prd.md — 12 structured fields."""

    spec_id: str
    spec_name: str
    title: str
    status: str
    created_at: str
    updated_at: str
    owner: str
    source: str
    supersedes: list[str]
    tags: list[str]
    intent_hash: str | None
    schema_version: int


@dataclasses.dataclass(frozen=True)
class PRD:
    """Parsed prd.md file: frontmatter + markdown body."""

    frontmatter: PRDFrontmatter
    body: str


# ---------------------------------------------------------------------------
# EARS discriminated union
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class EARSCriterion:
    """Base class for all EARS acceptance criteria.

    Subclass instances are constructed via the ``from_dict`` factory method,
    which dispatches on the ``ears_pattern`` field.
    """

    id: str
    ears_pattern: str
    system: str
    action: str
    return_contract: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EARSCriterion:
        """Construct the correct EARS subclass for the given dict."""
        pattern = data["ears_pattern"]
        common: dict[str, Any] = {
            "id": data["id"],
            "ears_pattern": data["ears_pattern"],
            "system": data["system"],
            "action": data["action"],
            "return_contract": data.get("return_contract"),
        }
        if pattern == "ubiquitous":
            return UbiquitousCriterion(**common)
        elif pattern == "event_driven":
            return EventDrivenCriterion(**common, trigger=data["trigger"])
        elif pattern == "complex_event":
            return ComplexEventCriterion(
                **common,
                trigger=data["trigger"],
                condition=data["condition"],
            )
        elif pattern == "state_driven":
            return StateDrivenCriterion(**common, state=data["state"])
        elif pattern == "unwanted":
            return UnwantedCriterion(**common, error_condition=data["error_condition"])
        elif pattern == "optional":
            return OptionalCriterion(**common, feature=data["feature"])
        else:
            raise ValueError(f"Unknown ears_pattern: {pattern!r}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON serialization.

        Preserves None values (not omitted) and empty lists.
        """
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class UbiquitousCriterion(EARSCriterion):
    """THE {system} SHALL {action}."""


@dataclasses.dataclass(frozen=True)
class EventDrivenCriterion(EARSCriterion):
    """WHEN {trigger}, THE {system} SHALL {action}."""

    trigger: str


@dataclasses.dataclass(frozen=True)
class ComplexEventCriterion(EARSCriterion):
    """WHEN {trigger} AND {condition}, THE {system} SHALL {action}."""

    trigger: str
    condition: str


@dataclasses.dataclass(frozen=True)
class StateDrivenCriterion(EARSCriterion):
    """WHILE {state}, THE {system} SHALL {action}."""

    state: str


@dataclasses.dataclass(frozen=True)
class UnwantedCriterion(EARSCriterion):
    """IF {error_condition}, THEN THE {system} SHALL {action}."""

    error_condition: str


@dataclasses.dataclass(frozen=True)
class OptionalCriterion(EARSCriterion):
    """WHERE {feature}, THE {system} SHALL {action}."""

    feature: str


# ---------------------------------------------------------------------------
# Requirements data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class UserStory:
    """User story (role, goal, benefit) attached to a requirement."""

    role: str
    goal: str
    benefit: str


@dataclasses.dataclass(frozen=True)
class Requirement:
    """A single requirement with acceptance criteria and edge cases."""

    id: str
    title: str
    user_story: UserStory
    acceptance_criteria: list[EARSCriterion]
    edge_cases: list[EARSCriterion]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict, preserving empty lists and None values."""
        return {
            "id": self.id,
            "title": self.title,
            "user_story": dataclasses.asdict(self.user_story),
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "edge_cases": [c.to_dict() for c in self.edge_cases],
        }


@dataclasses.dataclass(frozen=True)
class CorrectnessProperty:
    """A correctness property (invariant) for the spec."""

    id: str
    title: str
    for_any: str
    invariant: str
    validates: list[str]


@dataclasses.dataclass(frozen=True)
class ExecutionPathStep:
    """One step in an execution path."""

    actor: str
    action: str


@dataclasses.dataclass(frozen=True)
class ExecutionPath:
    """A named execution path with ordered steps."""

    id: str
    title: str
    steps: list[ExecutionPathStep]


@dataclasses.dataclass(frozen=True)
class ErrorHandlingEntry:
    """Error handling table entry linking a condition to a requirement."""

    id: str
    condition: str
    behavior: str
    requirement_id: str


@dataclasses.dataclass(frozen=True)
class Requirements:
    """Top-level container for requirements.json."""

    spec_id: str
    spec_name: str
    schema_version: int
    introduction: str
    glossary: dict[str, str]
    requirements: list[Requirement]
    correctness_properties: list[CorrectnessProperty]
    execution_paths: list[ExecutionPath]
    error_handling: list[ErrorHandlingEntry]


# ---------------------------------------------------------------------------
# TestSpec data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TestCase:
    """A unit or integration test case."""

    id: str
    requirement_id: str
    kind: str
    description: str
    preconditions: list[str]
    input: dict[str, Any]
    expected: dict[str, Any]
    assertion_pseudocode: str


@dataclasses.dataclass(frozen=True)
class PropertyTest:
    """A property-based (hypothesis) test."""

    id: str
    property_id: str
    validates: list[str]
    description: str
    for_any_strategy: str
    invariant_check: str


@dataclasses.dataclass(frozen=True)
class EdgeCaseTest:
    """A test case for an edge case criterion."""

    id: str
    requirement_id: str
    kind: str
    description: str
    preconditions: list[str]
    input: dict[str, Any]
    expected: dict[str, Any]
    assertion_pseudocode: str


@dataclasses.dataclass(frozen=True)
class SmokeTest:
    """An integration smoke test for an execution path."""

    id: str
    execution_path_id: str
    description: str
    trigger: str
    real_components: list[str]
    mockable: list[str]
    expected_effects: list[str]


@dataclasses.dataclass(frozen=True)
class Coverage:
    """Computed test coverage summary for a spec."""

    requirements_covered: list[str]
    properties_covered: list[str]
    paths_covered: list[str]
    gaps: list[str]


@dataclasses.dataclass(frozen=True)
class TestSpec:
    """Top-level container for test_spec.json."""

    spec_id: str
    spec_name: str
    schema_version: int
    test_cases: list[TestCase]
    property_tests: list[PropertyTest]
    edge_case_tests: list[EdgeCaseTest]
    smoke_tests: list[SmokeTest]
    coverage: Coverage


# ---------------------------------------------------------------------------
# Tasks data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Dependency:
    """Cross-spec dependency declaration in tasks.json."""

    spec_id: str
    kind: str


@dataclasses.dataclass(frozen=True)
class Subtask:
    """A single implementation subtask within a task group."""

    id: str
    title: str
    details: list[str]
    test_spec_refs: list[str]
    requirement_refs: list[str]
    state: SubtaskState
    optional: bool


@dataclasses.dataclass(frozen=True)
class VerificationSubtask:
    """The verification checklist subtask at the end of a task group."""

    id: str
    checks: list[str]


@dataclasses.dataclass(frozen=True)
class TaskGroup:
    """A group of related subtasks (e.g., one implementation increment)."""

    id: int
    kind: str
    title: str
    subtasks: list[Subtask]
    verification: VerificationSubtask


@dataclasses.dataclass(frozen=True)
class TraceabilityEntry:
    """Links a requirement to a test spec entry and implementing task."""

    requirement_id: str
    test_spec_id: str
    task_id: str
    test_path: str | None


@dataclasses.dataclass(frozen=True)
class Tasks:
    """Top-level container for tasks.json."""

    spec_id: str
    spec_name: str
    schema_version: int
    test_commands: dict[str, str]
    dependencies: list[Dependency]
    task_groups: list[TaskGroup]
    traceability: list[TraceabilityEntry]


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ValidationError:
    """A single validation error or warning from schema / cross-file checks."""

    file: str
    path: str
    rule: str
    message: str
    severity: str  # "error" | "warning"


# ---------------------------------------------------------------------------
# Spec aggregate
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Spec:
    """Aggregate of all four spec artifacts."""

    prd: PRD
    requirements: Requirements
    test_spec: TestSpec
    tasks: Tasks
    # Raw JSON dicts preserved from disk loading for schema validation.
    # These preserve fields that may be stripped during deserialization
    # (e.g., additional properties in EARS criteria that the loader ignores).
    # Excluded from equality, hashing, and repr to keep them invisible to consumers.
    _raw_requirements: "dict[str, Any] | None" = dataclasses.field(
        default=None, compare=False, repr=False
    )
    _raw_test_spec: "dict[str, Any] | None" = dataclasses.field(
        default=None, compare=False, repr=False
    )
    _raw_tasks: "dict[str, Any] | None" = dataclasses.field(
        default=None, compare=False, repr=False
    )
    _raw_frontmatter: "dict[str, Any] | None" = dataclasses.field(
        default=None, compare=False, repr=False
    )
