"""Tests for afspec loader — spec folder loading and parsing.

These tests translate the test contracts from test_spec.md sections TS-02-6
through TS-02-8 and edge cases TS-02-E3 through TS-02-E7.  They import
directly from the (not-yet-implemented) afspec modules; pytest will report
collection errors until the implementation exists.

The ``tmp_spec_dir`` fixture is provided by conftest.py and returns a
``pathlib.Path`` pointing to a temporary directory populated with all four
valid spec files for spec_id "05".
"""
from __future__ import annotations

import json
import pathlib

import pytest

from afspec import Spec, load_spec
from afspec.exceptions import IncompleteSpecError, SpecValidationError
from afspec.loader import _extract_intent, _load_json, _load_prd
from afspec.models import Requirements

# ---------------------------------------------------------------------------
# TS-02-6: Load a valid spec folder
# ---------------------------------------------------------------------------


def test_load_valid_spec(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-6: load_spec returns a fully-populated Spec from a valid folder."""
    spec = load_spec(tmp_spec_dir)

    assert isinstance(spec, Spec)
    assert spec.prd.frontmatter.spec_id == "05"
    assert len(spec.requirements.requirements) >= 1
    assert len(spec.test_spec.test_cases) >= 1
    assert len(spec.tasks.task_groups) >= 1


# ---------------------------------------------------------------------------
# TS-02-7: Parse PRD frontmatter and Intent section
# ---------------------------------------------------------------------------


def test_parse_prd_frontmatter(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-7: _load_prd parses YAML frontmatter and extracts the Intent section."""
    prd_path = tmp_spec_dir / "prd.md"

    prd = _load_prd(prd_path)

    assert prd.frontmatter.spec_id == "05"
    assert "## Intent" in prd.body

    intent_body = _extract_intent(prd.body)
    assert "thing" in intent_body


# ---------------------------------------------------------------------------
# TS-02-8: Load JSON files into typed dataclasses
# ---------------------------------------------------------------------------


def test_load_json_preserves_nulls(tmp_path: pathlib.Path) -> None:
    """TS-02-8: _load_json preserves null JSON fields as None on the dataclass."""
    req_data = {
        "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
        "spec_id": "05",
        "spec_name": "test",
        "schema_version": 1,
        "introduction": "intro",
        "glossary": {},
        "requirements": [
            {
                "id": "05-REQ-1",
                "title": "T",
                "user_story": {
                    "role": "operator",
                    "goal": "do X",
                    "benefit": "get Y",
                },
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

    req_path = tmp_path / "requirements.json"
    req_path.write_text(json.dumps(req_data, indent=2) + "\n", encoding="utf-8")

    loaded = _load_json(req_path, Requirements)

    assert isinstance(loaded, Requirements)
    assert loaded.requirements[0].acceptance_criteria[0].return_contract is None


# ---------------------------------------------------------------------------
# TS-02-E3: Missing spec files raises IncompleteSpecError
# ---------------------------------------------------------------------------


def test_missing_files_raises_incomplete_spec_error(tmp_path: pathlib.Path) -> None:
    """TS-02-E3: load_spec raises IncompleteSpecError when files are absent."""
    incomplete_dir = tmp_path / "05_incomplete"
    incomplete_dir.mkdir()

    # Write only prd.md and requirements.json; omit test_spec.json and tasks.json
    prd_content = (
        "---\n"
        'spec_id: "05"\n'
        'spec_name: "incomplete"\n'
        'title: "Incomplete"\n'
        'status: "draft"\n'
        'created_at: "2026-05-18T12:00:00Z"\n'
        'updated_at: "2026-05-18T12:00:00Z"\n'
        'owner: "alice"\n'
        'source: "interactive"\n'
        "supersedes: []\n"
        "tags: []\n"
        "intent_hash: null\n"
        "schema_version: 1\n"
        "---\n"
        "# Incomplete\n\n"
        "## Intent\n\n"
        "A partial spec.\n"
    )
    (incomplete_dir / "prd.md").write_text(prd_content, encoding="utf-8")

    req_data = {
        "spec_id": "05",
        "spec_name": "incomplete",
        "schema_version": 1,
        "introduction": "intro",
        "glossary": {},
        "requirements": [],
        "correctness_properties": [],
        "execution_paths": [],
        "error_handling": [],
    }
    (incomplete_dir / "requirements.json").write_text(
        json.dumps(req_data, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(IncompleteSpecError) as exc_info:
        load_spec(incomplete_dir)

    error = exc_info.value
    assert "test_spec.json" in error.missing_files
    assert "tasks.json" in error.missing_files


# ---------------------------------------------------------------------------
# TS-02-E4: Malformed JSON raises parse error mentioning filename
# ---------------------------------------------------------------------------


def test_malformed_json_raises_parse_error_with_filename(
    tmp_spec_dir: pathlib.Path,
) -> None:
    """TS-02-E4: Malformed requirements.json raises an error mentioning the filename."""
    (tmp_spec_dir / "requirements.json").write_text("{invalid", encoding="utf-8")

    with pytest.raises(Exception) as exc_info:
        load_spec(tmp_spec_dir)

    assert "requirements.json" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TS-02-E5: Malformed YAML raises error
# ---------------------------------------------------------------------------


def test_malformed_yaml_raises_error(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-E5: Malformed YAML frontmatter in prd.md raises a parse error."""
    bad_prd = "---\n  bad: yaml: :\n---\n\n# Title\n\n## Intent\n\nSome intent.\n"
    (tmp_spec_dir / "prd.md").write_text(bad_prd, encoding="utf-8")

    with pytest.raises(Exception):
        load_spec(tmp_spec_dir)


# ---------------------------------------------------------------------------
# TS-02-E6: Missing ## Intent section raises SpecValidationError
# ---------------------------------------------------------------------------


def test_missing_intent_section_raises_spec_validation_error(
    tmp_spec_dir: pathlib.Path,
) -> None:
    """TS-02-E6: PRD without ## Intent section raises SpecValidationError."""
    no_intent_prd = (
        "---\n"
        'spec_id: "05"\n'
        'spec_name: "test_feature"\n'
        'title: "Test Feature"\n'
        'status: "draft"\n'
        'created_at: "2026-05-18T12:00:00Z"\n'
        'updated_at: "2026-05-18T12:00:00Z"\n'
        'owner: "alice"\n'
        'source: "interactive"\n'
        "supersedes: []\n"
        "tags: []\n"
        "intent_hash: null\n"
        "schema_version: 1\n"
        "---\n"
        "# Test Feature\n\n"
        "## Background\n\n"
        "No Intent section here.\n"
    )
    (tmp_spec_dir / "prd.md").write_text(no_intent_prd, encoding="utf-8")

    with pytest.raises(SpecValidationError):
        load_spec(tmp_spec_dir)


# ---------------------------------------------------------------------------
# TS-02-E7: Non-existent path raises FileNotFoundError
# ---------------------------------------------------------------------------


def test_nonexistent_path_raises_file_not_found_error() -> None:
    """TS-02-E7: load_spec raises FileNotFoundError for a non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_spec(pathlib.Path("/nonexistent/path/that/does/not/exist"))
