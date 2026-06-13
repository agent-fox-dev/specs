"""Tests for git worktree lifecycle management.

Covers: TS-14-17, TS-14-18, TS-14-21, TS-14-29 through TS-14-31.
Edge cases: TS-14-E5, TS-14-E7, TS-14-E11.
Property tests: TS-14-P4, TS-14-P5.
Smoke tests: TS-14-SMOKE-2.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

import pytest
from coder.tools import create_coding_tools
from coder.worktree import (
    WorktreeError,
    cleanup_worktree,
    commit_task_group,
    create_worktree,
    merge_worktree,
)
from conftest import init_git_repo
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestCreateWorktree:
    """TS-14-17: Worktree created with correct branch name.

    Requirement: 14-REQ-5.1
    """

    def test_worktree_path_and_branch(
        self, git_repo: Path
    ) -> None:
        """Verify worktree exists at expected path with expected branch."""
        wt = create_worktree(
            git_repo, "base_app", "claude-opus-4-6"
        )
        assert wt.path.exists()
        assert wt.branch == "coder/claude-opus-4-6/base_app"


class TestMergeWorktree:
    """TS-14-18: Worktree merged on success.

    Requirement: 14-REQ-5.3
    """

    def test_merge_success(self, git_repo: Path) -> None:
        """Verify successful merge back to source branch."""
        wt = create_worktree(
            git_repo, "merge_spec", "claude-opus-4-6"
        )
        (wt.path / "new_file.txt").write_text("test content")
        subprocess.run(
            ["git", "-C", str(wt.path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wt.path), "commit", "-m", "Add file"],
            check=True,
            capture_output=True,
        )
        result = merge_worktree(wt)
        assert result is True


class TestCommitMessage:
    """TS-14-21: Task group commit message format.

    Requirement: 14-REQ-7.2
    """

    def test_commit_message_format(self, git_repo: Path) -> None:
        """Verify commit message follows conventional format."""
        wt = create_worktree(
            git_repo, "commit_spec", "claude-opus-4-6"
        )
        (wt.path / "impl.py").write_text("# implementation")
        subprocess.run(
            ["git", "-C", str(wt.path), "add", "."],
            check=True,
            capture_output=True,
        )
        commit_task_group(wt, 2, "Core models")
        log = subprocess.run(
            [
                "git",
                "-C",
                str(wt.path),
                "log",
                "-1",
                "--format=%s",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        message = log.stdout.strip()
        assert "feat(" in message
        assert "task group 2" in message
        assert "Core models" in message


class TestFileOpsInWorktree:
    """TS-14-29: File operations execute in worktree.

    Requirement: 14-REQ-5.2
    """

    def test_writes_target_worktree(self, git_repo: Path) -> None:
        """Verify file operations target worktree, not repo root."""
        wt = create_worktree(
            git_repo, "ops_spec", "claude-opus-4-6"
        )
        tools = create_coding_tools(wt.path)
        tools["write_file"].invoke(
            {"path": "new.txt", "content": "test"}
        )
        assert (wt.path / "new.txt").exists()
        assert not (git_repo / "new.txt").exists()


class TestCleanupAfterMerge:
    """TS-14-30: Worktree removed after successful merge.

    Requirement: 14-REQ-5.4
    """

    def test_cleanup_removes_worktree(
        self, git_repo: Path
    ) -> None:
        """Verify worktree directory is removed after cleanup."""
        wt = create_worktree(
            git_repo, "cleanup_spec", "claude-opus-4-6"
        )
        (wt.path / "file.txt").write_text("content")
        subprocess.run(
            ["git", "-C", str(wt.path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wt.path), "commit", "-m", "Add file"],
            check=True,
            capture_output=True,
        )
        merge_worktree(wt)
        cleanup_worktree(wt)
        assert not wt.path.exists()
        wt_list = subprocess.run(
            ["git", "-C", str(git_repo), "worktree", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert str(wt.path) not in wt_list.stdout


class TestFastForwardMergeFailure:
    """TS-14-31: Fast-forward merge failure leaves worktree.

    Requirement: 14-REQ-5.5
    """

    def test_diverged_merge_fails(self, git_repo: Path) -> None:
        """Verify diverged branches report merge failure."""
        wt = create_worktree(
            git_repo, "ff_spec", "claude-opus-4-6"
        )
        # Commit in worktree
        (wt.path / "wt_file.txt").write_text("worktree change")
        subprocess.run(
            ["git", "-C", str(wt.path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(wt.path),
                "commit",
                "-m",
                "Worktree change",
            ],
            check=True,
            capture_output=True,
        )
        # Commit different change on source branch (diverge)
        (git_repo / "repo_file.txt").write_text("repo change")
        subprocess.run(
            ["git", "-C", str(git_repo), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(git_repo),
                "commit",
                "-m",
                "Repo change",
            ],
            check=True,
            capture_output=True,
        )
        result = merge_worktree(wt)
        assert result is False
        assert wt.path.exists()


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestStaleWorktreeCleanup:
    """TS-14-E5: Stale worktree removed before creation.

    Requirement: 14-REQ-5.E1
    """

    def test_stale_worktree_replaced(
        self, git_repo: Path
    ) -> None:
        """Verify stale worktree directory is cleaned up."""
        stale_path = (
            git_repo / ".coder" / "worktrees" / "stale_spec"
        )
        stale_path.mkdir(parents=True)
        wt = create_worktree(
            git_repo, "stale_spec", "claude-opus-4-6"
        )
        assert wt.path.exists()


class TestCommitNothing:
    """TS-14-E7: Commit failure does not crash.

    Requirement: 14-REQ-7.E1
    """

    def test_nothing_to_commit(
        self,
        git_repo: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify commit with no changes doesn't raise."""
        wt = create_worktree(
            git_repo, "empty_spec", "claude-opus-4-6"
        )
        with caplog.at_level(logging.WARNING):
            commit_task_group(wt, 1, "Tests")
        log_text = " ".join(
            r.message for r in caplog.records
        ).lower()
        assert "warning" in log_text or "nothing" in log_text


class TestWorktreeCreationFailure:
    """TS-14-E11: Worktree creation failure raises WorktreeError.

    Requirement: 14-REQ-5.E2
    """

    def test_creation_in_non_git_dir_raises(
        self, tmp_path: Path
    ) -> None:
        """Verify WorktreeError raised when not in a git repo."""
        non_git = tmp_path / "not_a_repo"
        non_git.mkdir()
        with pytest.raises(WorktreeError):
            create_worktree(
                non_git, "some_spec", "claude-opus-4-6"
            )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPropertyWorktreeIsolation:
    """TS-14-P4: Worktree isolation.

    Property 4 from design.md.
    Validates: 14-REQ-5.2

    All file modifications occur within the worktree directory,
    not in the original repository root.
    """

    @given(n_files=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=30000)
    def test_property_worktree_isolation(
        self, n_files: int
    ) -> None:
        """No files outside worktree modified during writes."""
        repo = init_git_repo(Path(tempfile.mkdtemp()) / "repo")
        initial_content = (repo / "README.md").read_text()

        wt = create_worktree(repo, "iso_spec", "test-model")
        tools = create_coding_tools(wt.path)
        for i in range(n_files):
            tools["write_file"].invoke(
                {"path": f"file_{i}.txt", "content": f"content {i}"}
            )

        # Verify repo root unchanged
        assert (repo / "README.md").read_text() == initial_content
        for i in range(n_files):
            assert not (repo / f"file_{i}.txt").exists()


class TestPropertyCommitAfterSuccess:
    """TS-14-P5: Commit after success.

    Property 5 from design.md.
    Validates: 14-REQ-7.2

    Each completed task group produces exactly one commit.
    """

    @given(n_groups=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=30000)
    def test_property_commit_per_group(
        self, n_groups: int
    ) -> None:
        """Commit count equals completed task group count."""
        repo = init_git_repo(Path(tempfile.mkdtemp()) / "repo")
        wt = create_worktree(repo, "p5_spec", "test-model")

        initial_count = int(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(wt.path),
                    "rev-list",
                    "--count",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )

        for i in range(1, n_groups + 1):
            (wt.path / f"group_{i}.py").write_text(
                f"# group {i}"
            )
            subprocess.run(
                ["git", "-C", str(wt.path), "add", "."],
                check=True,
                capture_output=True,
            )
            commit_task_group(wt, i, f"Group {i}")

        final_count = int(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(wt.path),
                    "rev-list",
                    "--count",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        assert final_count - initial_count == n_groups


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmokeWorktreeLifecycle:
    """TS-14-SMOKE-2: Worktree lifecycle end-to-end.

    Execution Path: Path 2 from design.md.
    Verify create -> commit -> merge -> cleanup worktree cycle.
    """

    @pytest.mark.smoke
    def test_full_worktree_lifecycle(
        self, git_repo: Path
    ) -> None:
        """Verify create, write, commit, merge, cleanup cycle."""
        wt = create_worktree(
            git_repo, "lifecycle_spec", "claude-opus-4-6"
        )
        (wt.path / "new.txt").write_text("content")
        subprocess.run(
            ["git", "-C", str(wt.path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(wt.path),
                "commit",
                "-m",
                "feat: add file",
            ],
            check=True,
            capture_output=True,
        )
        merge_worktree(wt)
        cleanup_worktree(wt)
        assert not wt.path.exists()
        # Verify source branch has the new file
        assert (git_repo / "new.txt").read_text() == "content"
