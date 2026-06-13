"""Tests for the verification runner.

Covers: TS-14-19, TS-14-20, TS-14-32, TS-14-33.
Edge cases: TS-14-E6, TS-14-E12.
Property tests: TS-14-P7.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest
from afspec.models import TestCommands
from coder.verify import VerificationResult, VerificationRunner
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture()
def worktree_dir(tmp_path: Path) -> Path:
    """Create a temporary worktree directory for verification tests."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestPassResult:
    """TS-14-19: Verification runner returns pass for exit 0.

    Requirement: 14-REQ-6.2, 14-REQ-6.3
    """

    def test_exit_zero_is_pass(self, worktree_dir: Path) -> None:
        """Verify exit code 0 maps to passed=True."""
        cmds = TestCommands(spec_tests="echo ok")
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds)
        assert isinstance(result, VerificationResult)
        assert result.passed is True
        assert result.exit_code == 0


class TestFailResult:
    """TS-14-20: Verification runner returns fail for non-zero exit.

    Requirement: 14-REQ-6.3
    """

    def test_nonzero_exit_is_fail(self, worktree_dir: Path) -> None:
        """Verify non-zero exit code maps to passed=False."""
        cmds = TestCommands(spec_tests="exit 1")
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds)
        assert result.passed is False
        assert result.exit_code == 1


class TestCommandOrder:
    """TS-14-32: Verification runner executes commands in order.

    Requirement: 14-REQ-6.1
    """

    def test_nonfinal_runs_spec_tests_only(
        self, worktree_dir: Path
    ) -> None:
        """Verify non-final group only runs spec_tests."""
        cmds = TestCommands(
            spec_tests="echo spec",
            all_tests="echo all",
            linter="echo lint",
        )
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds, is_final_group=False)
        assert result.commands_run == ["spec_tests"]

    def test_final_runs_all_commands(
        self, worktree_dir: Path
    ) -> None:
        """Verify final group runs spec_tests, all_tests, and linter."""
        cmds = TestCommands(
            spec_tests="echo spec",
            all_tests="echo all",
            linter="echo lint",
        )
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds, is_final_group=True)
        assert result.commands_run == [
            "spec_tests",
            "all_tests",
            "linter",
        ]


class TestConfigurableTimeout:
    """TS-14-33: Verification runner enforces configurable timeout.

    Requirement: 14-REQ-6.4
    """

    def test_timeout_returns_failure(
        self, worktree_dir: Path
    ) -> None:
        """Verify timeout enforcement produces failure."""
        cmds = TestCommands(spec_tests="sleep 60")
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds, timeout=1)
        assert result.passed is False
        assert (
            "timeout" in result.stderr.lower()
            or result.timed_out is True
        )


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestEmptyCommand:
    """TS-14-E6: Empty test command skipped.

    Requirement: 14-REQ-6.E1
    """

    def test_empty_command_skipped(
        self,
        worktree_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify empty test commands are skipped."""
        cmds = TestCommands(spec_tests="")
        runner = VerificationRunner(worktree_dir)
        with caplog.at_level(logging.WARNING):
            result = runner.run(cmds)
        assert result.passed is True
        log_text = " ".join(
            r.message for r in caplog.records
        ).lower()
        assert "skip" in log_text


class TestBinaryNotFound:
    """TS-14-E12: Command binary not found returns fail result.

    Requirement: 14-REQ-6.E2
    """

    def test_missing_binary_returns_fail(
        self, worktree_dir: Path
    ) -> None:
        """Verify missing command binary returns fail, not crash."""
        cmds = TestCommands(
            spec_tests="nonexistent_binary_xyz --test"
        )
        runner = VerificationRunner(worktree_dir)
        result = runner.run(cmds)
        assert result.passed is False
        assert (
            "not found" in result.stderr.lower()
            or result.exit_code != 0
        )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPropertyExitCodeSemantics:
    """TS-14-P7: Verification exit code semantics.

    Property 7 from design.md.
    Validates: 14-REQ-6.3

    Exit code 0 = pass, non-zero = fail.
    """

    @given(exit_code=st.integers(min_value=0, max_value=128))
    @settings(max_examples=30, deadline=10000)
    def test_property_exit_code_semantics(
        self, exit_code: int
    ) -> None:
        """Exit code maps correctly to pass/fail."""
        wt = Path(tempfile.mkdtemp()) / "worktree"
        wt.mkdir()
        cmds = TestCommands(spec_tests=f"exit {exit_code}")
        runner = VerificationRunner(wt)
        result = runner.run(cmds)
        if exit_code == 0:
            assert result.passed is True
        else:
            assert result.passed is False
