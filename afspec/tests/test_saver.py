"""Tests for afspec saver and round-trip behaviour (TS-02-9 through TS-02-13, TS-02-E8, TS-02-E9)."""
from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone

import pytest

from afspec import load_spec, save_spec
from afspec.loader import _load_json, _load_prd
from afspec.models import TestSpec

# ---------------------------------------------------------------------------
# TS-02-9
# ---------------------------------------------------------------------------


def test_deterministic_json(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-9: Save spec produces deterministic JSON with sorted keys and 2-space indent."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    save_spec(spec, dst)

    content = (dst / "requirements.json").read_text(encoding="utf-8")

    # Must end with a newline
    assert content.endswith("\n"), "requirements.json must end with a trailing newline"

    parsed = json.loads(content)
    keys = list(parsed.keys())
    assert keys == sorted(keys), (
        f"Top-level keys must be sorted alphabetically; got {keys}"
    )

    lines = content.split("\n")
    # Find the first line that is indented with spaces (not the top-level "{")
    indented = next((ln for ln in lines if ln.startswith("  ")), None)
    assert indented is not None, "No indented line found; expected 2-space indentation"
    assert indented.startswith("  "), "Indented lines must use 2-space indentation"


# ---------------------------------------------------------------------------
# TS-02-10
# ---------------------------------------------------------------------------

_EXPECTED_FM_FIELDS = [
    "spec_id",
    "spec_name",
    "title",
    "status",
    "created_at",
    "updated_at",
    "owner",
    "source",
    "supersedes",
    "tags",
    "intent_hash",
    "schema_version",
]


def test_deterministic_yaml(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-10: Save spec produces YAML frontmatter fields in the fixed canonical order."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    save_spec(spec, dst)

    content = (dst / "prd.md").read_text(encoding="utf-8")
    lines = content.split("\n")

    # Locate the YAML block between the first and second "---" delimiters
    assert lines[0] == "---", "prd.md must start with '---'"
    fm_start = 1
    fm_end = lines.index("---", fm_start)
    fm_lines = lines[fm_start:fm_end]

    # Extract top-level field names (lines that contain ":" and are not indented)
    field_names = [
        ln.split(":")[0].strip()
        for ln in fm_lines
        if ":" in ln and not ln.startswith(" ")
    ]

    assert field_names == _EXPECTED_FM_FIELDS, (
        f"Frontmatter field order mismatch.\n"
        f"  expected: {_EXPECTED_FM_FIELDS}\n"
        f"  got:      {field_names}"
    )


# ---------------------------------------------------------------------------
# TS-02-11
# ---------------------------------------------------------------------------

_JSON_ARTIFACTS = ["requirements.json", "test_spec.json", "tasks.json"]


def test_idempotent_roundtrip(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-11: Load → save produces byte-identical JSON files; in-memory state is equivalent."""
    dst = tmp_path / "out"
    dst.mkdir()

    spec1 = load_spec(tmp_spec_dir)
    save_spec(spec1, dst)

    # JSON files must be byte-identical after one round-trip
    for filename in _JSON_ARTIFACTS:
        src_bytes = (tmp_spec_dir / filename).read_bytes()
        dst_bytes = (dst / filename).read_bytes()
        assert src_bytes == dst_bytes, (
            f"{filename}: content differs after round-trip"
        )

    # In-memory model equivalence (ignoring updated_at)
    spec2 = load_spec(dst)
    assert spec1.requirements == spec2.requirements
    assert spec1.test_spec.test_cases == spec2.test_spec.test_cases
    assert spec1.tasks.task_groups == spec2.tasks.task_groups
    assert spec1.prd.body == spec2.prd.body


# ---------------------------------------------------------------------------
# TS-02-12
# ---------------------------------------------------------------------------


def test_auto_updated_at(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-12: Save auto-updates updated_at to approximately the current UTC timestamp."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    before = datetime.now(timezone.utc)
    save_spec(spec, dst)
    after = datetime.now(timezone.utc)

    prd = _load_prd(dst / "prd.md")
    raw_ts = prd.frontmatter.updated_at
    # Normalise "Z" suffix to "+00:00" for fromisoformat compatibility
    saved_time = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))

    assert before <= saved_time <= after, (
        f"updated_at={raw_ts!r} is outside the [{before.isoformat()}, {after.isoformat()}] window"
    )


# ---------------------------------------------------------------------------
# TS-02-13
# ---------------------------------------------------------------------------


def test_auto_computed_coverage(tmp_path: pathlib.Path) -> None:
    """TS-02-13: Save auto-computes coverage; uncovered criteria appear in gaps.

    This test uses a purpose-built fixture where 05-REQ-1.1 has a test case
    but 05-REQ-1.E1 does NOT.  After save, the library must recompute:
      - coverage.requirements_covered contains 05-REQ-1.1
      - coverage.gaps contains 05-REQ-1.E1
    """
    import textwrap

    # PRD content (spec_id 05, spec_name test_feature)
    prd_content = textwrap.dedent("""\
        ---
        spec_id: "05"
        spec_name: "test_feature"
        title: "Test Feature"
        status: "draft"
        created_at: "2026-05-18T12:00:00Z"
        updated_at: "2026-05-18T12:00:00Z"
        owner: "alice"
        source: "interactive"
        supersedes: []
        tags:
          - "v1"
        intent_hash: null
        schema_version: 1
        ---
        # Test Feature

        ## Intent

        Build a thing for testing purposes.
        """)

    # Requirements with two criteria: 05-REQ-1.1 and 05-REQ-1.E1
    requirements_data = {
        "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
        "spec_id": "05",
        "spec_name": "test_feature",
        "schema_version": 1,
        "introduction": "A test feature.",
        "glossary": {"TestSystem": "The system under test."},
        "requirements": [
            {
                "id": "05-REQ-1",
                "title": "Test requirement",
                "user_story": {"role": "operator", "goal": "do something", "benefit": "value"},
                "acceptance_criteria": [
                    {
                        "id": "05-REQ-1.1",
                        "ears_pattern": "ubiquitous",
                        "system": "`TestSystem`",
                        "action": "process the request",
                        "return_contract": "the result",
                    }
                ],
                "edge_cases": [
                    {
                        "id": "05-REQ-1.E1",
                        "ears_pattern": "unwanted",
                        "error_condition": "the input is null",
                        "system": "`TestSystem`",
                        "action": "return an error",
                        "return_contract": None,
                    }
                ],
            }
        ],
        "correctness_properties": [
            {
                "id": "05-PROP-1",
                "title": "Deterministic",
                "for_any": "valid input",
                "invariant": "result is always the same",
                "validates": ["05-REQ-1.1"],
            }
        ],
        "execution_paths": [
            {
                "id": "05-PATH-1",
                "title": "Process request",
                "steps": [
                    {"actor": "operator", "action": "submit request"},
                    {"actor": "`TestSystem`", "action": "return result"},
                ],
            }
        ],
        "error_handling": [
            {
                "id": "05-ERR-1",
                "condition": "null input",
                "behavior": "return error",
                "requirement_id": "05-REQ-1.E1",
            }
        ],
    }

    # test_spec with a test case for 05-REQ-1.1 ONLY — 05-REQ-1.E1 is NOT covered
    partial_test_spec_data = {
        "$schema": "https://agent-fox.dev/schemas/test_spec.v1.json",
        "spec_id": "05",
        "spec_name": "test_feature",
        "schema_version": 1,
        "test_cases": [
            {
                "id": "TS-05-1",
                "requirement_id": "05-REQ-1.1",
                "kind": "unit",
                "description": "TestSystem processes valid request",
                "preconditions": ["system initialized"],
                "input": {"value": "test"},
                "expected": {"result": "ok"},
                "assertion_pseudocode": "assert system.process('test') == 'ok'",
            }
        ],
        "property_tests": [
            {
                "id": "TS-05-P1",
                "property_id": "05-PROP-1",
                "validates": ["05-REQ-1.1"],
                "description": "Deterministic",
                "for_any_strategy": "valid input strings",
                "invariant_check": "system.process(x) == system.process(x)",
            }
        ],
        "edge_case_tests": [],  # no test case for 05-REQ-1.E1
        "smoke_tests": [
            {
                "id": "TS-05-SMOKE-1",
                "execution_path_id": "05-PATH-1",
                "description": "End-to-end",
                "trigger": "operator submits request",
                "real_components": ["`TestSystem`"],
                "mockable": [],
                "expected_effects": ["result returned"],
            }
        ],
        "coverage": {
            "requirements_covered": [],
            "properties_covered": [],
            "paths_covered": [],
            "gaps": [],
        },
    }

    tasks_data = {
        "$schema": "https://agent-fox.dev/schemas/tasks.v1.json",
        "spec_id": "05",
        "spec_name": "test_feature",
        "schema_version": 1,
        "test_commands": {"spec_tests": "pytest -q", "all_tests": "pytest -q", "linter": "ruff check"},
        "dependencies": [],
        "task_groups": [
            {
                "id": 1,
                "kind": "tests",
                "title": "Write tests",
                "subtasks": [
                    {
                        "id": "1.1",
                        "title": "Write test file",
                        "details": ["Create test file"],
                        "test_spec_refs": ["TS-05-1"],
                        "requirement_refs": ["05-REQ-1.1"],
                        "state": "pending",
                        "optional": False,
                    }
                ],
                "verification": {"id": "1.V", "checks": ["Tests fail"]},
            }
        ],
        "traceability": [
            {
                "requirement_id": "05-REQ-1.1",
                "test_spec_id": "TS-05-1",
                "task_id": "1.1",
                "test_path": None,
            }
        ],
    }

    # Write the partial spec to disk
    partial_dir = tmp_path / "05_test_feature"
    partial_dir.mkdir()
    (partial_dir / "prd.md").write_text(prd_content, encoding="utf-8")
    (partial_dir / "requirements.json").write_text(
        json.dumps(requirements_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (partial_dir / "test_spec.json").write_text(
        json.dumps(partial_test_spec_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (partial_dir / "tasks.json").write_text(
        json.dumps(tasks_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    spec = load_spec(partial_dir)
    dst = tmp_path / "out"
    dst.mkdir()
    save_spec(spec, dst)

    ts = _load_json(dst / "test_spec.json", TestSpec)
    assert ts.coverage is not None, "coverage must be present in saved test_spec.json"
    assert "05-REQ-1.1" in ts.coverage.requirements_covered, (
        "05-REQ-1.1 must appear in coverage.requirements_covered"
    )
    assert "05-REQ-1.E1" in ts.coverage.gaps, (
        "05-REQ-1.E1 must appear in coverage.gaps — it has no test case"
    )


# ---------------------------------------------------------------------------
# TS-02-E8
# ---------------------------------------------------------------------------


def test_nonexistent_dir_error(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-E8: Save to a non-existent directory raises an error without creating it."""
    spec = load_spec(tmp_spec_dir)
    bad_path = tmp_path / "does_not_exist"

    assert not bad_path.exists(), "Precondition: target directory must not exist"

    with pytest.raises(Exception):
        save_spec(spec, bad_path)

    assert not bad_path.exists(), (
        "save_spec must not create the target directory when it does not exist"
    )


# ---------------------------------------------------------------------------
# TS-02-E9
# ---------------------------------------------------------------------------


def test_write_failure_cleanup(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-E9: Write failure leaves no .tmp files in the target directory."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    # Make the directory read-only to inject a write failure
    os.chmod(str(dst), 0o444)
    try:
        with pytest.raises(Exception):
            save_spec(spec, dst)
    finally:
        os.chmod(str(dst), 0o755)

    tmp_files = [f for f in dst.iterdir() if ".tmp" in f.name]
    assert len(tmp_files) == 0, (
        f"Temporary files must be cleaned up after write failure; found: {tmp_files}"
    )


# ---------------------------------------------------------------------------
# Additional round-trip: second save must also be idempotent (no drift)
# ---------------------------------------------------------------------------


def test_double_roundtrip_json_stable(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """Supplementary: two consecutive saves produce identical JSON artifacts."""
    dst1 = tmp_path / "pass1"
    dst2 = tmp_path / "pass2"
    dst1.mkdir()
    dst2.mkdir()

    spec1 = load_spec(tmp_spec_dir)
    save_spec(spec1, dst1)
    spec2 = load_spec(dst1)
    save_spec(spec2, dst2)

    for filename in _JSON_ARTIFACTS:
        assert (dst1 / filename).read_bytes() == (dst2 / filename).read_bytes(), (
            f"{filename}: content drifted between first and second save"
        )
