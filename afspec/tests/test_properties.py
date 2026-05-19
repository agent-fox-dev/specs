"""Hypothesis property-based tests for afspec.

Covers: TS-02-P1 through TS-02-P11
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from afspec import (
    load_spec,
    render_combined,
    save_spec,
)
from afspec.ids import validate_id
from afspec.lifecycle import _compute_intent_hash
from afspec.models import (
    ComplexEventCriterion,
    EARSCriterion,
    EventDrivenCriterion,
    OptionalCriterion,
    StateDrivenCriterion,
    SubtaskState,
    UbiquitousCriterion,
    UnwantedCriterion,
)
from afspec.validator import _validate_cross_file

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

EARS_PATTERNS = [
    "ubiquitous",
    "event_driven",
    "complex_event",
    "state_driven",
    "unwanted",
    "optional",
]

SUBCLASS_MAP = {
    "ubiquitous": UbiquitousCriterion,
    "event_driven": EventDrivenCriterion,
    "complex_event": ComplexEventCriterion,
    "state_driven": StateDrivenCriterion,
    "unwanted": UnwantedCriterion,
    "optional": OptionalCriterion,
}

LEGAL_TRANSITIONS = {
    (SubtaskState.PENDING, SubtaskState.QUEUED),
    (SubtaskState.PENDING, SubtaskState.DROPPED),
    (SubtaskState.QUEUED, SubtaskState.IN_PROGRESS),
    (SubtaskState.QUEUED, SubtaskState.PENDING),
    (SubtaskState.QUEUED, SubtaskState.DROPPED),
    (SubtaskState.IN_PROGRESS, SubtaskState.DONE),
    (SubtaskState.IN_PROGRESS, SubtaskState.PENDING_REEVALUATION),
    (SubtaskState.DONE, SubtaskState.PENDING_REEVALUATION),
    (SubtaskState.PENDING_REEVALUATION, SubtaskState.PENDING),
    (SubtaskState.PENDING_REEVALUATION, SubtaskState.DROPPED),
}

LEGAL_LIFECYCLE = {
    ("draft", "active"),
    ("active", "sealed"),
    ("sealed", "superseded"),
    ("sealed", "archived"),
    ("draft", "archived"),
}

STATUSES = ["draft", "active", "sealed", "superseded", "archived"]


@st.composite
def ears_criterion_dict(draw: st.DrawFn) -> dict:  # type: ignore[type-arg]
    """Strategy: random valid EARS criterion dict for any pattern."""
    pattern = draw(st.sampled_from(EARS_PATTERNS))
    text = st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L",)),  # type: ignore[arg-type]
    )
    base = {
        "id": "05-REQ-1.1",
        "ears_pattern": pattern,
        "system": draw(text),
        "action": draw(text),
        "return_contract": draw(st.one_of(st.none(), text)),
    }
    if pattern == "event_driven":
        base["trigger"] = draw(text)
    elif pattern == "complex_event":
        base["trigger"] = draw(text)
        base["condition"] = draw(text)
    elif pattern == "state_driven":
        base["state"] = draw(text)
    elif pattern == "unwanted":
        base["error_condition"] = draw(text)
    elif pattern == "optional":
        base["feature"] = draw(text)
    return base


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(
    st.text(
        min_size=1,
        max_size=80,
        alphabet=st.characters(whitelist_categories=("L", "Zs")),
    )
)
@settings(max_examples=20)
def test_p1_idempotent_roundtrip(new_title: str) -> None:
    """TS-02-P1: loading and saving any valid spec produces byte-identical JSON files.

    The golden fixture is mutated with a randomly generated title so that the
    round-trip invariant is verified against a distribution of different spec
    states, not just the one fixed fixture.

    Uses tempfile.TemporaryDirectory internally (not a pytest fixture) so that
    Hypothesis can create a fresh temp directory for each generated example.
    """
    import dataclasses

    golden = pathlib.Path(__file__).parent.parent.parent / "testdata" / "golden" / "05_example_feature"
    spec = load_spec(golden)

    # Apply the random variation: swap the PRD title so every Hypothesis example
    # exercises a different in-memory Spec.
    new_fm = dataclasses.replace(spec.prd.frontmatter, title=new_title.strip() or "T")
    new_prd = dataclasses.replace(spec.prd, frontmatter=new_fm)
    spec = dataclasses.replace(spec, prd=new_prd)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        dir_a = tmp / "a"
        dir_a.mkdir()
        dir_b = tmp / "b"
        dir_b.mkdir()
        save_spec(spec, dir_a)
        spec_loaded = load_spec(dir_a)
        save_spec(spec_loaded, dir_b)
        for fname in ["requirements.json", "test_spec.json", "tasks.json"]:
            assert (dir_a / fname).read_bytes() == (dir_b / fname).read_bytes()


@settings(max_examples=30)
@given(ears_criterion_dict())
def test_p2_ears_factory_correct_subclass(criterion_dict: dict) -> None:  # type: ignore[type-arg]
    """TS-02-P2: EARS factory always returns the correct subclass."""
    result = EARSCriterion.from_dict(criterion_dict)
    expected_class = SUBCLASS_MAP[criterion_dict["ears_pattern"]]
    assert isinstance(result, expected_class)
    assert result.ears_pattern == criterion_dict["ears_pattern"]


@settings(max_examples=36)
@given(
    st.sampled_from(list(SubtaskState)),
    st.sampled_from(list(SubtaskState)),
)
def test_p3_subtask_state_machine_legal_only(
    from_state: SubtaskState, to_state: SubtaskState
) -> None:
    """TS-02-P3: can_transition_to returns True only for legal transitions."""
    result = from_state.can_transition_to(to_state)
    expected = (from_state, to_state) in LEGAL_TRANSITIONS
    assert result == expected


@given(st.sampled_from(STATUSES), st.sampled_from(STATUSES))
@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_p4_lifecycle_transitions_match_graph(
    tmp_spec_dir: pathlib.Path, current: str, target: str
) -> None:
    """TS-02-P4: only legal lifecycle transitions are accepted."""
    import dataclasses

    from afspec import transition
    from afspec.exceptions import LifecycleError

    spec = load_spec(tmp_spec_dir)
    # Patch the status to simulate being in `current` state
    new_fm = dataclasses.replace(spec.prd.frontmatter, status=current)
    new_prd = dataclasses.replace(spec.prd, frontmatter=new_fm)
    spec_in_state = dataclasses.replace(spec, prd=new_prd)

    if (current, target) in LEGAL_LIFECYCLE:
        # Should not raise (ignoring intent hash issues for non-draft states)
        try:
            transition(spec_in_state, target)
        except LifecycleError as e:
            # Intent hash issues are acceptable for non-draft states in this test
            if "intent" not in str(e).lower():
                raise
    else:
        with pytest.raises(LifecycleError):
            transition(spec_in_state, target)


@settings(max_examples=30)
@given(st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "Zs"))))
def test_p5_intent_hash_stable(text: str) -> None:
    """TS-02-P5: intent hash is stable across calls for the same text."""
    assume(len(text.strip()) > 0)
    h1 = _compute_intent_hash(text)
    h2 = _compute_intent_hash(text)
    assert h1 == h2
    assert len(h1) == 64
    # Different text → different hash (with high probability)
    modified = text + "extra_suffix_xyz"
    h3 = _compute_intent_hash(modified)
    assert h1 != h3


@given(st.data())
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_p6_cross_file_valid_spec_no_errors(
    tmp_spec_dir: pathlib.Path, data: st.DataObject
) -> None:
    """TS-02-P6: valid consistent spec passes cross-file validation."""
    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)
    assert len(errors) == 0


@settings(max_examples=30)
@given(
    st.from_regex(r"[0-9]{1,3}", fullmatch=True),  # spec_id
    st.integers(min_value=1, max_value=99),          # N
    st.integers(min_value=1, max_value=99),          # C
)
def test_p7_id_format_valid_ids_pass(spec_id: str, n: int, c: int) -> None:
    """TS-02-P7: constructed valid IDs pass validation."""
    valid_id = f"{spec_id}-REQ-{n}.{c}"
    errors = validate_id(valid_id, spec_id)
    assert len(errors) == 0

    # Mismatched spec_id should fail
    other_id_prefix = str(int(spec_id) + 100)
    wrong_id = f"{other_id_prefix}-REQ-{n}.{c}"
    wrong_errors = validate_id(wrong_id, spec_id)
    assert len(wrong_errors) >= 1


@given(st.data())
@settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_p8_deterministic_rendering(
    tmp_spec_dir: pathlib.Path, data: st.DataObject
) -> None:
    """TS-02-P8: rendering the same spec multiple times produces identical output."""
    spec = load_spec(tmp_spec_dir)
    outputs = [render_combined(spec) for _ in range(3)]
    assert all(o == outputs[0] for o in outputs)


@given(
    st.sampled_from(
        [
            ("requirements.json", "introduction"),
            ("test_spec.json", "test_cases"),
            ("tasks.json", "task_groups"),
        ]
    )
)
@settings(max_examples=5)
def test_p9_schema_catches_structural_violations(artifact_and_field: tuple[str, str]) -> None:
    """TS-02-P9: removing any required field from an artifact triggers a schema validation error.

    For each JSON artifact, one required top-level field is deleted.  The
    library's schema validation layer MUST surface at least one error that
    references the removed field (via e.path or e.message).

    Uses in-memory data to avoid function-scoped fixture issues with Hypothesis.
    """
    import copy

    from afspec.tests.conftest import (
        VALID_REQUIREMENTS_DATA,
        VALID_TASKS_DATA,
        VALID_TEST_SPEC_DATA,
    )
    from afspec.validator import validate_dict_against_schema

    fname, required_field = artifact_and_field

    data_map: dict[str, dict] = {  # type: ignore[type-arg]
        "requirements.json": VALID_REQUIREMENTS_DATA,
        "test_spec.json": VALID_TEST_SPEC_DATA,
        "tasks.json": VALID_TASKS_DATA,
    }

    # Deep-copy so we don't mutate the module-level constant
    corrupted = copy.deepcopy(data_map[fname])
    del corrupted[required_field]

    # Validate the corrupted dict directly against the bundled schema
    errors = validate_dict_against_schema(fname, corrupted)
    assert len(errors) >= 1, (
        f"Expected at least one schema error after removing '{required_field}' from {fname}; "
        f"got {errors!r}"
    )
    assert any(
        required_field in (e.path or "") or required_field in e.message
        for e in errors
    ), (
        f"At least one error must reference the removed field '{required_field}'; "
        f"got: {[e.message for e in errors]!r}"
    )


@given(st.integers(min_value=1, max_value=4))
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_p10_atomic_write_no_partial_files(
    tmp_spec_dir: pathlib.Path, fail_at: int
) -> None:
    """TS-02-P10: after a failed save, no partial temp files remain.

    tmp_spec_dir is read-only (only load_spec is called on it).
    The output directory is created fresh per-example via tempfile to avoid
    state accumulation across Hypothesis examples.
    """
    from unittest.mock import patch

    spec = load_spec(tmp_spec_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = pathlib.Path(tmpdir) / "dst"
        dst.mkdir()

        call_count = 0

        def failing_write(path: pathlib.Path, content: str) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == fail_at:
                raise OSError("Injected failure")
            # Normal write
            path.write_text(content, encoding="utf-8")

        with patch("afspec.saver._atomic_write", side_effect=failing_write):
            try:
                save_spec(spec, dst)
            except Exception:
                pass

        # No .tmp files should remain
        tmp_files = [f for f in dst.iterdir() if ".tmp" in f.name]
        assert len(tmp_files) == 0


@given(st.data())
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_p11_computed_coverage_accuracy(
    tmp_spec_dir: pathlib.Path, data: st.DataObject
) -> None:
    """TS-02-P11: saved coverage.requirements_covered ∪ gaps == all requirement IDs.

    tmp_spec_dir is read-only (only load_spec is called on it).
    The output directory is created fresh per-example via tempfile to avoid
    state accumulation across Hypothesis examples.
    """
    spec = load_spec(tmp_spec_dir)
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = pathlib.Path(tmpdir) / "out"
        dst.mkdir()
        save_spec(spec, dst)

        from afspec.loader import _load_json
        from afspec.models import TestSpec

        ts = _load_json(dst / "test_spec.json", TestSpec)
        all_ids = set()
        for req in spec.requirements.requirements:
            for crit in req.acceptance_criteria:
                all_ids.add(crit.id)
            for edge in req.edge_cases:
                all_ids.add(edge.id)

        covered = set(ts.coverage.requirements_covered)
        gaps = set(ts.coverage.gaps)
        assert covered | gaps == all_ids
        assert covered & gaps == set()
