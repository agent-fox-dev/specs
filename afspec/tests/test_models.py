"""Tests for afspec.models — data model types and EARS factory dispatch.

These tests translate the test contracts from test_spec.md sections TS-02-1
through TS-02-5 and edge cases TS-02-E1 through TS-02-E2.  They import
directly from the (not-yet-implemented) afspec.models module; pytest will
report collection errors until the implementation exists.
"""
from __future__ import annotations

from afspec.models import (
    PRD,
    ComplexEventCriterion,
    CorrectnessProperty,
    Coverage,
    Dependency,
    EARSCriterion,
    EdgeCaseTest,
    ErrorHandlingEntry,
    EventDrivenCriterion,
    ExecutionPath,
    ExecutionPathStep,
    OptionalCriterion,
    PRDFrontmatter,
    PropertyTest,
    Requirement,
    Requirements,
    SmokeTest,
    Spec,
    StateDrivenCriterion,
    Subtask,
    SubtaskState,
    TaskGroup,
    Tasks,
    TestCase,
    TestSpec,
    TraceabilityEntry,
    UbiquitousCriterion,
    UnwantedCriterion,
    UserStory,
    VerificationSubtask,
)

# ---------------------------------------------------------------------------
# TS-02-1: PRD frontmatter dataclass contains all 12 fields
# ---------------------------------------------------------------------------


def test_prd_frontmatter_fields() -> None:
    """TS-02-1: PRDFrontmatter accepts all 12 fields and PRD wraps them."""
    fm = PRDFrontmatter(
        spec_id="05",
        spec_name="my_feature",
        title="My Feature",
        status="draft",
        created_at="2026-05-18T12:00:00Z",
        updated_at="2026-05-18T12:00:00Z",
        owner="alice",
        source="interactive",
        supersedes=[],
        tags=["v1"],
        intent_hash=None,
        schema_version=1,
    )

    assert fm.spec_id == "05"
    assert fm.spec_name == "my_feature"
    assert fm.title == "My Feature"
    assert fm.status == "draft"
    assert fm.created_at == "2026-05-18T12:00:00Z"
    assert fm.updated_at == "2026-05-18T12:00:00Z"
    assert fm.owner == "alice"
    assert fm.source == "interactive"
    assert fm.supersedes == []
    assert fm.tags == ["v1"]
    assert fm.intent_hash is None
    assert fm.schema_version == 1

    prd = PRD(frontmatter=fm, body="# Title\n\n## Intent\n\nSome intent.")
    assert "## Intent" in prd.body


# ---------------------------------------------------------------------------
# TS-02-2: Requirements container and nested types
# ---------------------------------------------------------------------------


def test_requirements_container() -> None:
    """TS-02-2: Requirements and all nested types can be constructed."""
    criterion = UbiquitousCriterion(
        id="05-REQ-1.1",
        ears_pattern="ubiquitous",
        system="sys",
        action="act",
        return_contract=None,
    )
    edge_case = ErrorHandlingEntry(
        id="05-ERR-1",
        condition="missing file",
        behavior="raise error",
        requirement_id="05-REQ-1.E1",
    )
    req = Requirements(
        spec_id="05",
        spec_name="test",
        schema_version=1,
        introduction="...",
        glossary={"term": "def"},
        requirements=[
            Requirement(
                id="05-REQ-1",
                title="R1",
                user_story=UserStory(role="operator", goal="do X", benefit="get Y"),
                acceptance_criteria=[criterion],
                edge_cases=[],
            )
        ],
        correctness_properties=[
            CorrectnessProperty(
                id="05-PROP-1",
                title="P1",
                for_any="any input",
                invariant="holds",
                validates=["05-REQ-1.1"],
            )
        ],
        execution_paths=[
            ExecutionPath(
                id="05-PATH-1",
                title="Path",
                steps=[
                    ExecutionPathStep(actor="SpaceManager", action="allocate"),
                    ExecutionPathStep(actor="user", action="confirm"),
                ],
            )
        ],
        error_handling=[edge_case],
    )

    assert req.requirements[0].user_story.role == "operator"
    assert req.correctness_properties[0].id == "05-PROP-1"
    assert req.execution_paths[0].steps[0].actor == "SpaceManager"


# ---------------------------------------------------------------------------
# TS-02-3: TestSpec and Tasks container types
# ---------------------------------------------------------------------------


def test_testspec_tasks_containers() -> None:
    """TS-02-3: TestSpec and Tasks containers with all nested types."""
    ts = TestSpec(
        spec_id="05",
        spec_name="test",
        schema_version=1,
        test_cases=[
            TestCase(
                id="TS-05-1",
                requirement_id="05-REQ-1.1",
                kind="unit",
                description="desc",
                preconditions=[],
                input={},
                expected={},
                assertion_pseudocode="assert True",
            )
        ],
        property_tests=[
            PropertyTest(
                id="TS-05-P1",
                property_id="05-PROP-1",
                validates=["05-REQ-1.1"],
                description="prop",
                for_any_strategy="any",
                invariant_check="True",
            )
        ],
        edge_case_tests=[
            EdgeCaseTest(
                id="TS-05-E1",
                requirement_id="05-REQ-1.E1",
                kind="unit",
                description="edge",
                preconditions=[],
                input={},
                expected={},
                assertion_pseudocode="assert True",
            )
        ],
        smoke_tests=[
            SmokeTest(
                id="TS-05-SMOKE-1",
                execution_path_id="05-PATH-1",
                description="smoke",
                trigger="invoke",
                real_components=["sys"],
                mockable=[],
                expected_effects=["done"],
            )
        ],
        coverage=Coverage(
            requirements_covered=["05-REQ-1.1"],
            properties_covered=["05-PROP-1"],
            paths_covered=["05-PATH-1"],
            gaps=[],
        ),
    )

    assert ts.test_cases[0].kind == "unit"
    assert ts.property_tests[0].property_id == "05-PROP-1"
    assert ts.edge_case_tests[0].requirement_id == "05-REQ-1.E1"
    assert ts.smoke_tests[0].execution_path_id == "05-PATH-1"
    assert ts.coverage.requirements_covered == ["05-REQ-1.1"]

    tasks = Tasks(
        spec_id="05",
        spec_name="test",
        schema_version=1,
        test_commands={
            "spec_tests": "pytest -q",
            "all_tests": "pytest -q",
            "linter": "ruff check",
        },
        dependencies=[],
        task_groups=[
            TaskGroup(
                id=1,
                kind="tests",
                title="Write tests",
                subtasks=[
                    Subtask(
                        id="1.1",
                        title="S1",
                        details=[],
                        test_spec_refs=[],
                        requirement_refs=[],
                        state=SubtaskState.PENDING,
                        optional=False,
                    )
                ],
                verification=VerificationSubtask(id="1.V", checks=["check"]),
            )
        ],
        traceability=[
            TraceabilityEntry(
                requirement_id="05-REQ-1.1",
                test_spec_id="TS-05-1",
                task_id="1.1",
                test_path=None,
            )
        ],
    )

    assert tasks.task_groups[0].subtasks[0].state == SubtaskState.PENDING
    assert tasks.traceability[0].test_spec_id == "TS-05-1"

    # Verify Dependency is importable (used when deps are non-empty)
    _ = Dependency
    # Verify Spec is importable
    _ = Spec


# ---------------------------------------------------------------------------
# TS-02-4: EARS discriminated union with factory method
# ---------------------------------------------------------------------------


def test_ears_factory_dispatch() -> None:
    """TS-02-4: EARSCriterion.from_dict dispatches to the correct subclass."""
    # ubiquitous
    ub = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.1",
            "ears_pattern": "ubiquitous",
            "system": "the system",
            "action": "do X",
            "return_contract": None,
        }
    )
    assert isinstance(ub, UbiquitousCriterion)
    assert not hasattr(ub, "trigger")

    # event_driven
    ed = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.2",
            "ears_pattern": "event_driven",
            "trigger": "a request",
            "system": "the system",
            "action": "respond",
            "return_contract": None,
        }
    )
    assert isinstance(ed, EventDrivenCriterion)
    assert ed.trigger == "a request"

    # complex_event
    ce = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.3",
            "ears_pattern": "complex_event",
            "trigger": "T",
            "condition": "C",
            "system": "sys",
            "action": "act",
            "return_contract": None,
        }
    )
    assert isinstance(ce, ComplexEventCriterion)
    assert ce.condition == "C"

    # state_driven
    sd = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.4",
            "ears_pattern": "state_driven",
            "state": "active",
            "system": "sys",
            "action": "monitor",
            "return_contract": None,
        }
    )
    assert isinstance(sd, StateDrivenCriterion)
    assert sd.state == "active"  # type: ignore[union-attr]

    # unwanted
    uw = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.5",
            "ears_pattern": "unwanted",
            "error_condition": "timeout",
            "system": "sys",
            "action": "retry",
            "return_contract": None,
        }
    )
    assert isinstance(uw, UnwantedCriterion)
    assert uw.error_condition == "timeout"  # type: ignore[union-attr]

    # optional
    op = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.6",
            "ears_pattern": "optional",
            "feature": "dark mode",
            "system": "sys",
            "action": "adjust",
            "return_contract": None,
        }
    )
    assert isinstance(op, OptionalCriterion)
    assert op.feature == "dark mode"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# TS-02-5: Subtask state machine transitions
# ---------------------------------------------------------------------------


def test_subtask_state_transitions() -> None:
    """TS-02-5: SubtaskState.can_transition_to enforces legal transitions."""
    # Legal transitions
    assert SubtaskState.PENDING.can_transition_to(SubtaskState.QUEUED) is True
    assert SubtaskState.PENDING.can_transition_to(SubtaskState.DROPPED) is True
    assert SubtaskState.QUEUED.can_transition_to(SubtaskState.IN_PROGRESS) is True
    assert SubtaskState.QUEUED.can_transition_to(SubtaskState.PENDING) is True
    assert SubtaskState.QUEUED.can_transition_to(SubtaskState.DROPPED) is True
    assert SubtaskState.IN_PROGRESS.can_transition_to(SubtaskState.DONE) is True
    assert SubtaskState.IN_PROGRESS.can_transition_to(SubtaskState.PENDING_REEVALUATION) is True
    assert SubtaskState.DONE.can_transition_to(SubtaskState.PENDING_REEVALUATION) is True
    assert SubtaskState.PENDING_REEVALUATION.can_transition_to(SubtaskState.PENDING) is True
    assert SubtaskState.PENDING_REEVALUATION.can_transition_to(SubtaskState.DROPPED) is True

    # Illegal transitions
    assert SubtaskState.PENDING.can_transition_to(SubtaskState.DONE) is False
    assert SubtaskState.PENDING.can_transition_to(SubtaskState.IN_PROGRESS) is False
    assert SubtaskState.PENDING.can_transition_to(SubtaskState.PENDING_REEVALUATION) is False
    assert SubtaskState.DROPPED.can_transition_to(SubtaskState.PENDING) is False
    assert SubtaskState.DROPPED.can_transition_to(SubtaskState.QUEUED) is False
    assert SubtaskState.DROPPED.can_transition_to(SubtaskState.IN_PROGRESS) is False
    assert SubtaskState.DROPPED.can_transition_to(SubtaskState.DONE) is False
    assert SubtaskState.IN_PROGRESS.can_transition_to(SubtaskState.PENDING) is False
    assert SubtaskState.IN_PROGRESS.can_transition_to(SubtaskState.QUEUED) is False
    assert SubtaskState.DONE.can_transition_to(SubtaskState.PENDING) is False
    assert SubtaskState.DONE.can_transition_to(SubtaskState.QUEUED) is False
    assert SubtaskState.DONE.can_transition_to(SubtaskState.IN_PROGRESS) is False


# ---------------------------------------------------------------------------
# TS-02-E1: Null field round-trip preservation
# ---------------------------------------------------------------------------


def test_null_field_roundtrip() -> None:
    """TS-02-E1: None return_contract is preserved through to_dict() round-trip."""
    criterion = EARSCriterion.from_dict(
        {
            "id": "05-REQ-1.1",
            "ears_pattern": "ubiquitous",
            "system": "sys",
            "action": "act",
            "return_contract": None,
        }
    )

    assert criterion.return_contract is None

    serialized = criterion.to_dict()
    assert "return_contract" in serialized
    assert serialized["return_contract"] is None


# ---------------------------------------------------------------------------
# TS-02-E2: Empty array round-trip as []
# ---------------------------------------------------------------------------


def test_empty_array_roundtrip() -> None:
    """TS-02-E2: Requirement with edge_cases=[] serializes 'edge_cases' as []."""
    req = Requirement(
        id="05-REQ-1",
        title="T",
        user_story=UserStory(role="r", goal="g", benefit="b"),
        acceptance_criteria=[
            UbiquitousCriterion(
                id="05-REQ-1.1",
                ears_pattern="ubiquitous",
                system="sys",
                action="act",
                return_contract=None,
            )
        ],
        edge_cases=[],
    )

    data = req.to_dict()
    assert "edge_cases" in data
    assert data["edge_cases"] == []
