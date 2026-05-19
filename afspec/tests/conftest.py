"""Shared test fixtures for afspec tests."""
from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

# Path to golden fixtures
GOLDEN_DIR = pathlib.Path(__file__).parent.parent.parent / "testdata" / "golden"
GOLDEN_SPEC_PATH = GOLDEN_DIR / "05_example_feature"


# ---------------------------------------------------------------------------
# Raw content helpers
# ---------------------------------------------------------------------------

VALID_PRD_CONTENT = textwrap.dedent("""\
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

    ## Background

    This is a test fixture.
    """)

VALID_REQUIREMENTS_DATA = {
    "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
    "spec_id": "05",
    "spec_name": "test_feature",
    "schema_version": 1,
    "introduction": "A test feature for testing.",
    "glossary": {
        "TestSystem": "The system under test.",
    },
    "requirements": [
        {
            "id": "05-REQ-1",
            "title": "Test requirement",
            "user_story": {
                "role": "operator",
                "goal": "do something",
                "benefit": "get value",
            },
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
            "title": "Processing is deterministic",
            "for_any": "valid input",
            "invariant": "result is always the same",
            "validates": ["05-REQ-1.1"],
        }
    ],
    "execution_paths": [
        {
            "id": "05-PATH-1",
            "title": "Operator processes a request",
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

VALID_TEST_SPEC_DATA = {
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
            "description": "Processing is deterministic",
            "for_any_strategy": "valid input strings",
            "invariant_check": "system.process(x) == system.process(x)",
        }
    ],
    "edge_case_tests": [
        {
            "id": "TS-05-E1",
            "requirement_id": "05-REQ-1.E1",
            "kind": "unit",
            "description": "Null input returns error",
            "preconditions": [],
            "input": {"value": None},
            "expected": {"error": True},
            "assertion_pseudocode": "assert system.process(None).is_error",
        }
    ],
    "smoke_tests": [
        {
            "id": "TS-05-SMOKE-1",
            "execution_path_id": "05-PATH-1",
            "description": "End-to-end request processing",
            "trigger": "operator submits request",
            "real_components": ["`TestSystem`"],
            "mockable": [],
            "expected_effects": ["result returned"],
        }
    ],
    "coverage": {
        "requirements_covered": ["05-REQ-1.1", "05-REQ-1.E1"],
        "properties_covered": ["05-PROP-1"],
        "paths_covered": ["05-PATH-1"],
        "gaps": [],
    },
}

VALID_TASKS_DATA = {
    "$schema": "https://agent-fox.dev/schemas/tasks.v1.json",
    "spec_id": "05",
    "spec_name": "test_feature",
    "schema_version": 1,
    "test_commands": {
        "spec_tests": "pytest -q afspec/tests/",
        "all_tests": "pytest -q",
        "linter": "ruff check",
    },
    "dependencies": [],
    "task_groups": [
        {
            "id": 1,
            "kind": "tests",
            "title": "Write failing tests",
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
            "verification": {
                "id": "1.V",
                "checks": ["All tests fail: pytest -q"],
            },
        },
        {
            "id": 2,
            "kind": "wiring_verification",
            "title": "Wiring verification",
            "subtasks": [
                {
                    "id": "2.1",
                    "title": "Trace paths",
                    "details": ["Verify paths are live"],
                    "test_spec_refs": ["TS-05-SMOKE-1"],
                    "requirement_refs": ["05-REQ-1.1"],
                    "state": "pending",
                    "optional": False,
                }
            ],
            "verification": {
                "id": "2.V",
                "checks": ["All smoke tests pass"],
            },
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


# ---------------------------------------------------------------------------
# Filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_spec_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary spec folder with all four valid files."""
    spec_dir = tmp_path / "05_test_feature"
    spec_dir.mkdir()

    (spec_dir / "prd.md").write_text(VALID_PRD_CONTENT, encoding="utf-8")
    (spec_dir / "requirements.json").write_text(
        json.dumps(VALID_REQUIREMENTS_DATA, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (spec_dir / "test_spec.json").write_text(
        json.dumps(VALID_TEST_SPEC_DATA, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (spec_dir / "tasks.json").write_text(
        json.dumps(VALID_TASKS_DATA, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return spec_dir


@pytest.fixture()
def golden_spec_dir() -> pathlib.Path:
    """Return the path to the golden fixture spec."""
    return GOLDEN_SPEC_PATH


@pytest.fixture()
def tmp_spec_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary spec root with one spec folder."""
    spec_dir = tmp_path / "01_alpha"
    spec_dir.mkdir()
    prd_content = VALID_PRD_CONTENT.replace('spec_id: "05"', 'spec_id: "01"').replace(
        'spec_name: "test_feature"', 'spec_name: "alpha"'
    )
    (spec_dir / "prd.md").write_text(prd_content, encoding="utf-8")
    req_data = {**VALID_REQUIREMENTS_DATA, "spec_id": "01", "spec_name": "alpha"}
    (spec_dir / "requirements.json").write_text(
        json.dumps(req_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    ts_data = {**VALID_TEST_SPEC_DATA, "spec_id": "01", "spec_name": "alpha"}
    (spec_dir / "test_spec.json").write_text(
        json.dumps(ts_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    tasks_data = {**VALID_TASKS_DATA, "spec_id": "01", "spec_name": "alpha"}
    (spec_dir / "tasks.json").write_text(
        json.dumps(tasks_data, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return tmp_path
