"""Shared test fixtures for coder package tests."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "smoke: smoke / integration tests"
    )


@pytest.fixture()
def tmp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for config tests."""
    return tmp_path


@pytest.fixture()
def campaign_dir(tmp_path: Path) -> Path:
    """Create a temporary campaign directory with required structure."""
    campaign = tmp_path / "test_campaign"
    campaign.mkdir()
    return campaign


@pytest.fixture()
def clean_coder_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all CODER_* and provider API key env vars.

    Ensures test isolation from host environment variables that could
    affect configuration loading or provider creation.
    """
    keys_to_remove = [
        k
        for k in os.environ
        if k.startswith("CODER_")
        or k in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
    ]
    for key in keys_to_remove:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def fake_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set a fake Anthropic API key for testing.

    Returns the fake key value for assertions.
    """
    key = "sk-ant-test-key-12345"
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    return key


@pytest.fixture()
def fake_google_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set a fake Google API key for testing.

    Returns the fake key value for assertions.
    """
    key = "google-test-key-12345"
    monkeypatch.setenv("GOOGLE_API_KEY", key)
    return key


@pytest.fixture()
def template_dir(tmp_path: Path) -> Path:
    """Create a project-level template directory.

    Returns the path to .coder/templates/ within the temporary directory.
    """
    tpl_dir = tmp_path / ".coder" / "templates"
    tpl_dir.mkdir(parents=True)
    return tpl_dir


# ---------------------------------------------------------------------------
# Spec 13: Spec pack helpers and fixtures
# ---------------------------------------------------------------------------


def make_prd_md(
    spec_id: str,
    spec_name: str,
    status: str = "active",
    *,
    include_status: bool = True,
) -> str:
    """Create minimal valid prd.md content with YAML frontmatter.

    Parameters
    ----------
    spec_id:
        The spec ID to embed in the frontmatter.
    spec_name:
        The spec name to embed in the frontmatter.
    status:
        The lifecycle status (e.g. "active", "draft").
    include_status:
        If False, omit the status field entirely from the frontmatter.
    """
    status_line = f'status: "{status}"' if include_status else ""
    return (
        "---\n"
        f'spec_id: "{spec_id}"\n'
        f'spec_name: "{spec_name}"\n'
        f'title: "Test spec: {spec_name}"\n'
        f"{status_line}\n"
        'created_at: "2026-01-01T00:00:00Z"\n'
        'updated_at: "2026-01-01T00:00:00Z"\n'
        'owner: "test"\n'
        'source: "test"\n'
        "supersedes: []\n"
        "tags: []\n"
        "intent_hash: null\n"
        "schema_version: 1\n"
        "---\n"
        f"# {spec_name}\n\nTest PRD content.\n"
    )


def make_requirements_json(spec_id: str, spec_name: str) -> str:
    """Create minimal valid requirements.json content."""
    return json.dumps(
        {
            "spec_id": spec_id,
            "spec_name": spec_name,
            "schema_version": 1,
            "introduction": "Test requirements",
            "glossary": {},
            "requirements": [],
            "correctness_properties": [],
            "execution_paths": [],
            "error_handling": [],
        }
    )


def make_test_spec_json(spec_id: str, spec_name: str) -> str:
    """Create minimal valid test_spec.json content."""
    return json.dumps(
        {
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
    )


def make_tasks_json(
    spec_id: str,
    spec_name: str,
    dependencies: list[dict[str, object]] | None = None,
) -> str:
    """Create minimal valid tasks.json content."""
    return json.dumps(
        {
            "spec_id": spec_id,
            "spec_name": spec_name,
            "schema_version": 1,
            "test_commands": {
                "spec_tests": "",
                "all_tests": "",
                "linter": "",
            },
            "dependencies": dependencies or [],
            "task_groups": [],
            "traceability": [],
        }
    )


def create_spec_pack(
    campaign_dir: Path,
    folder_name: str,
    spec_id: str,
    spec_name: str,
    *,
    status: str = "active",
    dependencies: list[dict[str, object]] | None = None,
    include_prd: bool = True,
    include_status: bool = True,
    requirements_content: str | None = None,
    test_spec_content: str | None = None,
    tasks_content: str | None = None,
) -> Path:
    """Create a complete spec pack inside a campaign directory.

    Returns the path to the created spec pack folder.
    """
    spec_dir = campaign_dir / folder_name
    spec_dir.mkdir(parents=True, exist_ok=True)

    if include_prd:
        (spec_dir / "prd.md").write_text(
            make_prd_md(
                spec_id, spec_name, status, include_status=include_status
            ),
            encoding="utf-8",
        )

    (spec_dir / "requirements.json").write_text(
        requirements_content or make_requirements_json(spec_id, spec_name),
        encoding="utf-8",
    )
    (spec_dir / "test_spec.json").write_text(
        test_spec_content or make_test_spec_json(spec_id, spec_name),
        encoding="utf-8",
    )
    (spec_dir / "tasks.json").write_text(
        tasks_content or make_tasks_json(spec_id, spec_name, dependencies),
        encoding="utf-8",
    )

    return spec_dir


# ---------------------------------------------------------------------------
# Spec 14: Git repo helpers and fixtures for worktree / runner tests
# ---------------------------------------------------------------------------


def init_git_repo(path: Path) -> Path:
    """Initialize a git repository with an initial commit.

    Creates the directory if it does not exist, runs ``git init``,
    writes a README.md, and commits it so the repo has at least one
    commit (required before worktrees can be created).

    Parameters
    ----------
    path:
        Directory path for the new git repo.

    Returns
    -------
    Path to the initialized repository (same as *path*).
    """
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", str(path)],
        check=True,
        capture_output=True,
    )
    readme = path / "README.md"
    readme.write_text("# Test repo\n")
    subprocess.run(
        ["git", "-C", str(path), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )
    return path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with one commit.

    Suitable for worktree and runner integration tests that need a
    real git repository to operate on.
    """
    return init_git_repo(tmp_path / "repo")
