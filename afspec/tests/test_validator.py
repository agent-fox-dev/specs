"""Tests for afspec schema and cross-file validation (TS-02-14 through TS-02-24, TS-02-E10/E11/E15)."""
from __future__ import annotations

import json
import pathlib

import pytest

from afspec import BootstrapSpec, load_spec, schema_version, validate
from afspec.exceptions import IncompleteSpecError
from afspec.models import ValidationError
from afspec.validator import _load_schema, _validate_cross_file, _validate_schemas

# ---------------------------------------------------------------------------
# TS-02-14: Schema validation against bundled schemas
# ---------------------------------------------------------------------------


def test_schema_validation(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-14: Valid spec has no schema errors; invalid spec (missing introduction) has errors."""
    valid_spec = load_spec(tmp_spec_dir)
    errors = validate(valid_spec)
    assert errors == [], f"Valid spec must produce no errors; got {errors}"

    # Build an invalid requirements dict without the required "introduction" field
    invalid_req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(invalid_req_path.read_text(encoding="utf-8"))
    data.pop("introduction", None)
    invalid_req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    invalid_spec = load_spec(tmp_spec_dir)
    errors_invalid = validate(invalid_spec)

    assert len(errors_invalid) >= 1, "Missing 'introduction' must produce at least one error"
    req_errors = [e for e in errors_invalid if e.file == "requirements.json"]
    assert req_errors, "At least one error must reference requirements.json"
    assert any("introduction" in e.message for e in req_errors), (
        "Error message must mention 'introduction'"
    )


# ---------------------------------------------------------------------------
# TS-02-15: PRD frontmatter schema validation
# ---------------------------------------------------------------------------


def test_prd_frontmatter_validation(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-15: PRD missing spec_id in frontmatter produces a validation error for prd.md."""
    prd_path = tmp_spec_dir / "prd.md"
    content = prd_path.read_text(encoding="utf-8")
    # Remove the spec_id line from the frontmatter
    lines = content.split("\n")
    lines = [ln for ln in lines if not ln.startswith("spec_id:")]
    prd_path.write_text("\n".join(lines), encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = validate(spec)

    prd_errors = [e for e in errors if e.file == "prd.md"]
    assert prd_errors, "Must produce at least one error referencing prd.md"
    assert any("spec_id" in e.message for e in prd_errors), (
        "Error message must mention 'spec_id'"
    )


# ---------------------------------------------------------------------------
# TS-02-16: Bundled schemas accessible via importlib.resources
# ---------------------------------------------------------------------------

_SCHEMA_NAMES = [
    "requirements.v1.json",
    "test_spec.v1.json",
    "tasks.v1.json",
    "prd-frontmatter.v1.json",
]


def test_bundled_schemas() -> None:
    """TS-02-16: All four bundled schema files are loadable and parseable as dicts."""
    for name in _SCHEMA_NAMES:
        schema = _load_schema(name)
        assert isinstance(schema, dict), f"Schema {name!r} must be a dict; got {type(schema)}"

    assert schema_version() == 1, "schema_version() must return 1"


# ---------------------------------------------------------------------------
# TS-02-17: Schema validation reports all errors
# ---------------------------------------------------------------------------


def test_all_errors_reported(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-17: Schema validation collects all errors, not just the first."""
    req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    # Remove two required top-level fields
    data.pop("introduction", None)
    data.pop("glossary", None)
    req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = validate(spec)

    req_errors = [e for e in errors if e.file == "requirements.json"]
    assert len(req_errors) >= 2, (
        f"Must report at least 2 errors for requirements.json; got {len(req_errors)}"
    )


# ---------------------------------------------------------------------------
# TS-02-18: Cross-file integrity — all seven rules
# ---------------------------------------------------------------------------


def test_cross_file_all_rules(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-18: A carefully crafted spec that violates all 7 cross-file rules."""
    # Rule 1: orphan requirement_id in test_spec (05-REQ-99.1 not in requirements)
    # Rule 2: acceptance criterion 05-REQ-1.1 has no test case
    # Rule 3: 05-PROP-1 has no property test
    # Rule 4: 05-PATH-1 has no smoke test
    # Rule 5: traceability references TS-05-99 which does not exist in test_spec
    # Rule 6: action uses `UnknownTerm` not in glossary
    # Rule 7: requirements.json has spec_id "06" instead of "05"

    req_path = tmp_spec_dir / "requirements.json"
    req_data = json.loads(req_path.read_text(encoding="utf-8"))

    # Introduce an unknown backtick term in the acceptance criteria action (rule 6)
    req_data["requirements"][0]["acceptance_criteria"][0]["action"] = (
        "process via `UnknownTerm`"
    )
    # Change spec_id to break rule 7
    req_data["spec_id"] = "06"

    req_path.write_text(json.dumps(req_data, indent=2) + "\n", encoding="utf-8")

    ts_path = tmp_spec_dir / "test_spec.json"
    ts_data = json.loads(ts_path.read_text(encoding="utf-8"))

    # Rule 1: add a test case that references a non-existent requirement ID
    ts_data["test_cases"][0]["requirement_id"] = "05-REQ-99.1"
    # Rule 2: no valid test case covers 05-REQ-1.1 any more (already changed above)
    # Rule 3: remove the property test so 05-PROP-1 has no coverage
    ts_data["property_tests"] = []
    # Rule 4: remove the smoke test so 05-PATH-1 has no coverage
    ts_data["smoke_tests"] = []

    ts_path.write_text(json.dumps(ts_data, indent=2) + "\n", encoding="utf-8")

    tasks_path = tmp_spec_dir / "tasks.json"
    tasks_data = json.loads(tasks_path.read_text(encoding="utf-8"))

    # Rule 5: traceability references TS-05-99 which doesn't exist
    tasks_data["traceability"][0]["test_spec_id"] = "TS-05-99"

    tasks_path.write_text(json.dumps(tasks_data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    assert len(errors) >= 7, (
        f"Expected at least 7 cross-file errors; got {len(errors)}: {errors}"
    )
    messages = [e.message for e in errors]

    # Rule 1: orphan requirement_id
    assert any(
        "requirement_id" in m or "05-REQ-99.1" in m for m in messages
    ), "Rule 1 error (orphan requirement_id) not found"

    # Rule 2: uncovered criterion
    assert any("uncovered" in m or "05-REQ-1.1" in m for m in messages), (
        "Rule 2 error (uncovered criterion) not found"
    )

    # Rule 3: uncovered property
    assert any("property" in m.lower() or "05-PROP-1" in m for m in messages), (
        "Rule 3 error (uncovered property) not found"
    )

    # Rule 4: uncovered path or smoke test
    assert any(
        "path" in m.lower() or "smoke" in m.lower() or "05-PATH-1" in m
        for m in messages
    ), "Rule 4 error (uncovered execution path) not found"

    # Rule 5: orphan test_spec_id
    assert any("test_spec_id" in m or "TS-05-99" in m for m in messages), (
        "Rule 5 error (orphan test_spec_id) not found"
    )

    # Rule 6: missing glossary term
    assert any("glossary" in m.lower() or "UnknownTerm" in m for m in messages), (
        "Rule 6 error (missing glossary term) not found"
    )

    # Rule 7: spec_id / spec_name inconsistency
    assert any("spec_id" in m or "spec_name" in m for m in messages), (
        "Rule 7 error (spec_id inconsistency) not found"
    )


# ---------------------------------------------------------------------------
# TS-02-19: Cross-file — requirement_id reference check (rule 1)
# ---------------------------------------------------------------------------


def test_orphan_requirement_id(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-19: Orphan requirement_id in test_spec is caught by cross-file validation."""
    ts_path = tmp_spec_dir / "test_spec.json"
    data = json.loads(ts_path.read_text(encoding="utf-8"))
    data["test_cases"][0]["requirement_id"] = "05-REQ-99.1"
    ts_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    assert any("05-REQ-99.1" in e.message for e in errors), (
        "Error must identify the orphan requirement_id '05-REQ-99.1'"
    )


# ---------------------------------------------------------------------------
# TS-02-20: Cross-file — requirement coverage check (rule 2)
# ---------------------------------------------------------------------------


def test_uncovered_requirement(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-20: Acceptance criterion without a test case triggers a coverage error."""
    ts_path = tmp_spec_dir / "test_spec.json"
    data = json.loads(ts_path.read_text(encoding="utf-8"))
    # Change the test case to cover a non-existent requirement so 05-REQ-1.1 is uncovered
    data["test_cases"][0]["requirement_id"] = "05-REQ-99.1"
    ts_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    coverage_errors = [
        e
        for e in errors
        if "05-REQ-1.1" in e.message and "uncovered" in e.message.lower()
    ]
    assert coverage_errors, (
        "Must report that 05-REQ-1.1 is uncovered; "
        f"messages: {[e.message for e in errors]}"
    )


# ---------------------------------------------------------------------------
# TS-02-21: Cross-file — property and path coverage (rules 3, 4)
# ---------------------------------------------------------------------------


def test_uncovered_property_path(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-21: Uncovered correctness property and execution path produce distinct errors."""
    ts_path = tmp_spec_dir / "test_spec.json"
    data = json.loads(ts_path.read_text(encoding="utf-8"))
    data["property_tests"] = []
    data["smoke_tests"] = []
    ts_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    messages = [e.message for e in errors]
    assert any("05-PROP-1" in m for m in messages), (
        "Error must identify uncovered property 05-PROP-1"
    )
    assert any("05-PATH-1" in m for m in messages), (
        "Error must identify uncovered execution path 05-PATH-1"
    )


# ---------------------------------------------------------------------------
# TS-02-22: Cross-file — test_spec_id reference check (rule 5)
# ---------------------------------------------------------------------------


def test_orphan_test_spec_id(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-22: Orphan test_spec_id in tasks traceability is caught."""
    tasks_path = tmp_spec_dir / "tasks.json"
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    data["traceability"][0]["test_spec_id"] = "TS-05-99"
    tasks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    assert any("TS-05-99" in e.message for e in errors), (
        "Error must identify orphan test_spec_id 'TS-05-99'"
    )


# ---------------------------------------------------------------------------
# TS-02-23: Cross-file — glossary cross-check (rule 6)
# ---------------------------------------------------------------------------


def test_glossary_crosscheck(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-23: Backtick term in action field without glossary entry triggers an error."""
    req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    # Insert a backtick-wrapped term that is not in the glossary
    data["requirements"][0]["acceptance_criteria"][0]["action"] = (
        "delegate to `SpaceManager`"
    )
    req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    assert any(
        "SpaceManager" in e.message and "glossary" in e.message.lower()
        for e in errors
    ), (
        "Error must mention 'SpaceManager' and 'glossary'; "
        f"got messages: {[e.message for e in errors]}"
    )


# ---------------------------------------------------------------------------
# TS-02-24: Cross-file — spec_id/spec_name consistency (rule 7)
# ---------------------------------------------------------------------------


def test_spec_id_consistency(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-24: Different spec_id in requirements.json vs prd.md triggers an error."""
    req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    data["spec_id"] = "06"
    req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_cross_file(spec)

    assert any(
        "spec_id" in e.message and "inconsistent" in e.message.lower()
        for e in errors
    ), (
        "Error must mention spec_id inconsistency; "
        f"got messages: {[e.message for e in errors]}"
    )


# ---------------------------------------------------------------------------
# TS-02-E10: Unknown JSON fields rejected by schema
# ---------------------------------------------------------------------------


def test_unknown_fields_rejected(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-E10: Extra fields in requirements.json are rejected with field path."""
    req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    data["bogus_field"] = True
    req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_schemas(spec)

    assert any("bogus_field" in e.path or "bogus_field" in e.message for e in errors), (
        "Schema validation must reject the unknown field 'bogus_field'; "
        f"got errors: {errors}"
    )


# ---------------------------------------------------------------------------
# TS-02-E11: EARS pattern field mismatch rejected
# ---------------------------------------------------------------------------


def test_ears_pattern_mismatch(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-E11: A ubiquitous criterion with a trigger field is rejected by schema validation."""
    req_path = tmp_spec_dir / "requirements.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    # Add a trigger field to a ubiquitous criterion — invalid for that pattern
    criterion = data["requirements"][0]["acceptance_criteria"][0]
    assert criterion["ears_pattern"] == "ubiquitous"
    criterion["trigger"] = "a spurious event"
    req_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    spec = load_spec(tmp_spec_dir)
    errors = _validate_schemas(spec)

    assert any("trigger" in e.message for e in errors), (
        "Schema validation must report that 'trigger' is invalid for a ubiquitous criterion; "
        f"got errors: {errors}"
    )


# ---------------------------------------------------------------------------
# TS-02-E15: Bootstrap — cross-file validation skipped for missing files
# ---------------------------------------------------------------------------


def test_bootstrap_skip_missing(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-E15: Cross-file validation is skipped for files not yet written in bootstrap mode.

    A bootstrap session that has only written prd.md and requirements.json must not
    raise a cross-file error about the missing test_spec.json and tasks.json while
    still inside the context block.
    """
    # Load valid prd and requirements from the fixture spec so they pass per-file schema
    spec = load_spec(tmp_spec_dir)

    spec_root = tmp_path / "specs"
    spec_root.mkdir()

    # The context manager exit raises IncompleteSpecError (only 2 of 4 files written),
    # but NO error should be raised *inside* the block during the two writes.
    # That is what this test verifies: cross-file validation is deferred to exit-time.
    with pytest.raises(IncompleteSpecError):
        with BootstrapSpec(spec_root, "05", "test_feature") as bs:
            # These two writes must succeed without raising any cross-file error
            bs.write_prd(spec.prd)
            bs.write_requirements(spec.requirements)
            # Intentionally leave test_spec and tasks unwritten


# ---------------------------------------------------------------------------
# ValidationError is a dataclass — verify it can be instantiated
# ---------------------------------------------------------------------------


def test_validation_error_dataclass() -> None:
    """Structural: ValidationError dataclass exposes the expected fields."""
    err = ValidationError(
        file="requirements.json",
        path="/requirements/0",
        rule="schema",
        message="missing required field",
        severity="error",
    )
    assert err.file == "requirements.json"
    assert err.path == "/requirements/0"
    assert err.rule == "schema"
    assert err.message == "missing required field"
    assert err.severity == "error"
