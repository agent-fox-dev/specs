"""Tests for spec discovery.

Covers: TS-02-38, TS-02-39, TS-02-40, TS-02-41, TS-02-42, TS-02-E18, TS-02-E19, TS-02-E20
"""
from __future__ import annotations

import json
import os
import pathlib
import textwrap

import pytest

from afspec import discover


def _make_spec_dir(
    root: pathlib.Path,
    spec_id: str,
    spec_name: str,
    complete: bool = True,
    depends_on: list[str] | None = None,
) -> pathlib.Path:
    """Helper to create a spec folder in root."""
    spec_dir = root / f"{spec_id}_{spec_name}"
    spec_dir.mkdir(parents=True, exist_ok=True)
    prd = textwrap.dedent(f"""\
        ---
        spec_id: "{spec_id}"
        spec_name: "{spec_name}"
        title: "Spec {spec_id}"
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
        # Spec {spec_id}

        ## Intent

        Test spec {spec_id}.
        """)
    (spec_dir / "prd.md").write_text(prd)
    if not complete:
        return spec_dir
    req = {
        "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
        "spec_id": spec_id,
        "spec_name": spec_name,
        "schema_version": 1,
        "introduction": f"Spec {spec_id}.",
        "glossary": {},
        "requirements": [],
        "correctness_properties": [],
        "execution_paths": [],
        "error_handling": [],
    }
    (spec_dir / "requirements.json").write_text(json.dumps(req, indent=2) + "\n")
    ts = {
        "$schema": "https://agent-fox.dev/schemas/test_spec.v1.json",
        "spec_id": spec_id,
        "spec_name": spec_name,
        "schema_version": 1,
        "test_cases": [],
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
    (spec_dir / "test_spec.json").write_text(json.dumps(ts, indent=2) + "\n")
    deps = [{"depends_on_spec": d, "from_group": 1, "to_group": 1,
              "relationship": "dep", "sentinel": False} for d in (depends_on or [])]
    tasks = {
        "$schema": "https://agent-fox.dev/schemas/tasks.v1.json",
        "spec_id": spec_id,
        "spec_name": spec_name,
        "schema_version": 1,
        "test_commands": {
            "spec_tests": "pytest -q", "all_tests": "pytest -q", "linter": "ruff check"
        },
        "dependencies": deps,
        "task_groups": [
            {
                "id": 1,
                "kind": "tests",
                "title": "Tests",
                "subtasks": [
                    {
                        "id": "1.1", "title": "t", "details": [],
                        "test_spec_refs": [], "requirement_refs": [],
                        "state": "pending", "optional": False,
                    }
                ],
                "verification": {"id": "1.V", "checks": ["pass"]},
            },
            {
                "id": 2,
                "kind": "wiring_verification",
                "title": "Wiring",
                "subtasks": [
                    {
                        "id": "2.1", "title": "wire", "details": [],
                        "test_spec_refs": [], "requirement_refs": [],
                        "state": "pending", "optional": False,
                    }
                ],
                "verification": {"id": "2.V", "checks": ["pass"]},
            },
        ],
        "traceability": [],
    }
    (spec_dir / "tasks.json").write_text(json.dumps(tasks, indent=2) + "\n")
    return spec_dir


def test_discover_specs_in_root(tmp_path: pathlib.Path) -> None:
    """TS-02-38: discovery scans for spec folders matching {NN}_{snake_case_name}."""
    _make_spec_dir(tmp_path, "01", "alpha")
    _make_spec_dir(tmp_path, "02", "beta")
    (tmp_path / "not_a_spec").mkdir()  # No numeric prefix — should be ignored
    result = discover(tmp_path)
    ids = [e.spec_id for e in result.entries]
    assert "01" in ids
    assert "02" in ids


def test_discover_skips_archive(tmp_path: pathlib.Path) -> None:
    """TS-02-39: discovery skips the archive/ subdirectory."""
    _make_spec_dir(tmp_path, "01", "alpha")
    archive = tmp_path / "archive"
    archive.mkdir()
    _make_spec_dir(archive, "03", "old")
    result = discover(tmp_path)
    ids = [e.spec_id for e in result.entries]
    assert "01" in ids
    assert "03" not in ids


def test_discover_loads_metadata_only(tmp_path: pathlib.Path) -> None:
    """TS-02-40: discovery reads PRD frontmatter only, not all artifacts."""
    spec_dir = _make_spec_dir(tmp_path, "05", "test")
    # Corrupt requirements.json — discovery should still succeed
    (spec_dir / "requirements.json").write_text("{invalid json")
    result = discover(tmp_path)
    entry = next(e for e in result.entries if e.spec_id == "05")
    assert entry.spec_id == "05"
    assert entry.status == "draft"


def test_discover_builds_dependency_graph(tmp_path: pathlib.Path) -> None:
    """TS-02-41: discovery builds a dependency graph from tasks.json declarations."""
    _make_spec_dir(tmp_path, "01", "alpha")
    _make_spec_dir(tmp_path, "02", "beta", depends_on=["01"])
    result = discover(tmp_path)
    assert result.dependency_graph.has_edge("01", "02")
    order = result.dependency_graph.topological_sort()
    assert order.index("01") < order.index("02")


def test_discover_defaults_to_cwd(tmp_path: pathlib.Path) -> None:
    """TS-02-42: discover() with no argument defaults to current working directory."""
    _make_spec_dir(tmp_path, "01", "alpha")
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = discover()
        assert len(result.entries) > 0
    finally:
        os.chdir(original_cwd)


def test_discover_nonexistent_root_raises_error() -> None:
    """TS-02-E18: discovery on non-existent directory raises error."""
    with pytest.raises(Exception):
        discover(pathlib.Path("/nonexistent/path/xyz"))


def test_discover_incomplete_spec_marked_as_incomplete(tmp_path: pathlib.Path) -> None:
    """TS-02-E19: incomplete spec folders are included but marked as incomplete."""
    _make_spec_dir(tmp_path, "05", "test", complete=False)  # Only prd.md
    result = discover(tmp_path)
    entry = next((e for e in result.entries if e.spec_id == "05"), None)
    assert entry is not None
    assert entry.complete is False


def test_discover_cycle_detection(tmp_path: pathlib.Path) -> None:
    """TS-02-E20: circular dependency is detected and reported."""
    _make_spec_dir(tmp_path, "01", "alpha", depends_on=["02"])
    _make_spec_dir(tmp_path, "02", "beta", depends_on=["01"])
    with pytest.raises(Exception) as exc_info:
        discover(tmp_path)
    error_msg = str(exc_info.value)
    assert "01" in error_msg
    assert "02" in error_msg
