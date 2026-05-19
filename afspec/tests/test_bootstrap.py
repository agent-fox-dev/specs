"""Tests for BootstrapSpec context manager.

Covers: TS-02-34, TS-02-35, TS-02-36, TS-02-37, TS-02-E12, TS-02-E13, TS-02-E14
"""
from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

from afspec import validate
from afspec.bootstrap import BootstrapSpec
from afspec.exceptions import IncompleteSpecError, SpecValidationError

# Minimal valid PRD content for bootstrap tests
_VALID_PRD = textwrap.dedent("""\
    ---
    spec_id: "05"
    spec_name: "test"
    title: "Bootstrap Test"
    status: "draft"
    created_at: "2026-05-18T12:00:00Z"
    updated_at: "2026-05-18T12:00:00Z"
    owner: "tester"
    source: "interactive"
    supersedes: []
    tags: []
    intent_hash: null
    schema_version: 1
    ---
    # Bootstrap Test

    ## Intent

    Test the bootstrap context manager.
    """)

_VALID_REQUIREMENTS = {
    "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
    "spec_id": "05",
    "spec_name": "test",
    "schema_version": 1,
    "introduction": "Bootstrap test spec.",
    "glossary": {},
    "requirements": [
        {
            "id": "05-REQ-1",
            "title": "Req",
            "user_story": {"role": "op", "goal": "do", "benefit": "get"},
            "acceptance_criteria": [
                {
                    "id": "05-REQ-1.1",
                    "ears_pattern": "ubiquitous",
                    "system": "sys",
                    "action": "act",
                    "return_contract": None,
                }
            ],
            "edge_cases": [],
        }
    ],
    "correctness_properties": [],
    "execution_paths": [],
    "error_handling": [],
}

_VALID_TEST_SPEC = {
    "$schema": "https://agent-fox.dev/schemas/test_spec.v1.json",
    "spec_id": "05",
    "spec_name": "test",
    "schema_version": 1,
    "test_cases": [
        {
            "id": "TS-05-1",
            "requirement_id": "05-REQ-1.1",
            "kind": "unit",
            "description": "test",
            "preconditions": [],
            "input": {},
            "expected": {},
            "assertion_pseudocode": "assert True",
        }
    ],
    "property_tests": [],
    "edge_case_tests": [],
    "smoke_tests": [],
    "coverage": {
        "requirements_covered": [],
        "properties_covered": [],
        "paths_covered": [],
        "gaps": [],
    },
}

_VALID_TASKS = {
    "$schema": "https://agent-fox.dev/schemas/tasks.v1.json",
    "spec_id": "05",
    "spec_name": "test",
    "schema_version": 1,
    "test_commands": {
        "spec_tests": "pytest -q",
        "all_tests": "pytest -q",
        "linter": "ruff check",
    },
    "dependencies": [],
    "task_groups": [
        {
            "id": 1,
            "kind": "tests",
            "title": "Tests",
            "subtasks": [
                {
                    "id": "1.1",
                    "title": "Write tests",
                    "details": [],
                    "test_spec_refs": ["TS-05-1"],
                    "requirement_refs": ["05-REQ-1.1"],
                    "state": "pending",
                    "optional": False,
                }
            ],
            "verification": {"id": "1.V", "checks": ["All tests pass"]},
        },
        {
            "id": 2,
            "kind": "wiring_verification",
            "title": "Wiring",
            "subtasks": [
                {
                    "id": "2.1",
                    "title": "Check wiring",
                    "details": [],
                    "test_spec_refs": [],
                    "requirement_refs": [],
                    "state": "pending",
                    "optional": False,
                }
            ],
            "verification": {"id": "2.V", "checks": ["Wiring verified"]},
        },
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


def test_bootstrap_creates_folder(tmp_path: pathlib.Path) -> None:
    """TS-02-34: BootstrapSpec creates the spec folder and allows file writes."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    with BootstrapSpec(spec_root, "05", "test") as bs:
        assert (spec_root / "05_test").is_dir()
        bs.write_prd(_VALID_PRD)
        bs.write_requirements(json.dumps(_VALID_REQUIREMENTS))
        bs.write_test_spec(json.dumps(_VALID_TEST_SPEC))
        bs.write_tasks(json.dumps(_VALID_TASKS))
    spec = bs.result
    assert spec is not None
    assert spec.prd.frontmatter.spec_id == "05"


def test_bootstrap_defers_cross_file_validation(tmp_path: pathlib.Path) -> None:
    """TS-02-35: per-file validation runs on write; cross-file deferred until exit."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    # Per-file validation: invalid PRD should raise immediately
    with pytest.raises(SpecValidationError):
        with BootstrapSpec(spec_root, "05", "test") as bs:
            # Write invalid PRD (missing required frontmatter field)
            bad_prd = "---\nspec_id: '05'\n---\n# No Intent\n"
            bs.write_prd(bad_prd)


def test_bootstrap_per_file_validation_on_valid_write(tmp_path: pathlib.Path) -> None:
    """TS-02-35: writing valid files one at a time does not trigger cross-file errors."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    # Write only two valid files — no cross-file error during writes
    with pytest.raises(IncompleteSpecError):
        with BootstrapSpec(spec_root, "05", "test") as bs:
            bs.write_prd(_VALID_PRD)
            bs.write_requirements(json.dumps(_VALID_REQUIREMENTS))
            # Exit without test_spec and tasks — should raise IncompleteSpecError, not
            # a cross-file validation error during individual writes


def test_bootstrap_finalize_runs_full_validation(tmp_path: pathlib.Path) -> None:
    """TS-02-36: finalize (context exit) runs full validation and returns Spec."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    with BootstrapSpec(spec_root, "05", "test") as bs:
        bs.write_prd(_VALID_PRD)
        bs.write_requirements(json.dumps(_VALID_REQUIREMENTS))
        bs.write_test_spec(json.dumps(_VALID_TEST_SPEC))
        bs.write_tasks(json.dumps(_VALID_TASKS))
    spec = bs.result
    assert spec is not None
    errors = validate(spec)
    assert len(errors) == 0


def test_bootstrap_allows_individual_file_writes(tmp_path: pathlib.Path) -> None:
    """TS-02-37: writing any single file works without requiring others to exist."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    with pytest.raises(IncompleteSpecError):
        with BootstrapSpec(spec_root, "05", "test") as bs:
            # Write only requirements first — no error during the write itself
            bs.write_requirements(json.dumps(_VALID_REQUIREMENTS))
            assert (spec_root / "05_test" / "requirements.json").exists()
            # Context exits with missing files → IncompleteSpecError


def test_bootstrap_incomplete_finalize_raises_incomplete_spec_error(
    tmp_path: pathlib.Path,
) -> None:
    """TS-02-E12: finalize before all files written raises IncompleteSpecError."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    with pytest.raises(IncompleteSpecError) as exc_info:
        with BootstrapSpec(spec_root, "05", "test") as bs:
            bs.write_prd(_VALID_PRD)
            bs.write_requirements(json.dumps(_VALID_REQUIREMENTS))
            # Missing test_spec.json and tasks.json
    error = exc_info.value
    assert "test_spec.json" in error.missing_files or any(
        "test_spec" in f for f in error.missing_files
    )


def test_bootstrap_allows_file_overwrite(tmp_path: pathlib.Path) -> None:
    """TS-02-E13: writing the same file twice during bootstrap overwrites without error."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    prd_v2 = _VALID_PRD.replace("Bootstrap Test", "Bootstrap Test V2")
    with pytest.raises(IncompleteSpecError):
        with BootstrapSpec(spec_root, "05", "test") as bs:
            bs.write_prd(_VALID_PRD)
            bs.write_prd(prd_v2)  # Overwrite — no error
            content = (spec_root / "05_test" / "prd.md").read_text()
            assert "Bootstrap Test V2" in content
            # Exit without all files to trigger IncompleteSpecError


def test_bootstrap_existing_folder_raises_error(tmp_path: pathlib.Path) -> None:
    """TS-02-E14: BootstrapSpec on existing folder raises error."""
    spec_root = tmp_path / "specs"
    spec_root.mkdir()
    existing = spec_root / "05_test"
    existing.mkdir()
    with pytest.raises(Exception):  # FileExistsError or similar
        with BootstrapSpec(spec_root, "05", "test"):
            pass
