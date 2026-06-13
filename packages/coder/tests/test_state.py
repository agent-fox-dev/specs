"""Tests for run state persistence.

Covers: TS-14-22, TS-14-23, TS-14-37.
Edge cases: TS-14-E9, TS-14-E13.
Property tests: TS-14-P6.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from coder.nodes import implement
from coder.state import StateTransition, persist_state
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture()
def worktree_dir(tmp_path: Path) -> Path:
    """Create a temporary worktree directory for state tests."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestPersistState:
    """TS-14-22: Run state persisted after node transition.

    Requirement: 14-REQ-8.1
    """

    def test_run_json_written(self, worktree_dir: Path) -> None:
        """Verify _run.json is written after state changes."""
        state: dict = {
            "current_phase": "implement",
            "current_task_group": 2,
            "attempt_count": 1,
            "max_attempts": 5,
            "halted": False,
            "halt_reason": "",
        }
        persist_state(state, worktree_dir)
        run_json = json.loads(
            (worktree_dir / "_run.json").read_text()
        )
        assert run_json["current_phase"] == "implement"
        assert run_json["current_task_group"] == 2


class TestStateHistory:
    """TS-14-23: Run state includes transition history.

    Requirement: 14-REQ-8.2
    """

    def test_history_preserved(self, worktree_dir: Path) -> None:
        """Verify history array is maintained."""
        transition1 = StateTransition(
            phase="understand_spec",
            task_group=1,
            attempt=0,
            timestamp="2026-06-13T10:00:00Z",
            result="ok",
        )
        transition2 = StateTransition(
            phase="write_tests",
            task_group=1,
            attempt=0,
            timestamp="2026-06-13T10:01:00Z",
            result="ok",
        )
        state: dict = {
            "current_phase": "implement",
            "current_task_group": 1,
            "attempt_count": 0,
            "max_attempts": 5,
            "halted": False,
            "halt_reason": "",
            "history": [transition1, transition2],
        }
        persist_state(state, worktree_dir)
        run_json = json.loads(
            (worktree_dir / "_run.json").read_text()
        )
        assert len(run_json["history"]) == 2


class TestAtomicWrite:
    """TS-14-37: Run state written atomically.

    Requirement: 14-REQ-8.3
    """

    def test_atomic_write_on_failure(
        self, worktree_dir: Path
    ) -> None:
        """Verify atomic write prevents corruption on crash."""
        state_v1: dict = {
            "current_phase": "understand_spec",
            "current_task_group": 1,
            "attempt_count": 0,
            "halted": False,
        }
        persist_state(state_v1, worktree_dir)
        initial = (worktree_dir / "_run.json").read_text()

        state_v2: dict = {
            "current_phase": "implement",
            "current_task_group": 2,
            "attempt_count": 3,
            "halted": False,
        }
        # Mock os.rename to fail, simulating crash during atomic write
        with patch("os.rename", side_effect=OSError("disk full")):
            try:
                persist_state(state_v2, worktree_dir)
            except OSError:
                pass

        # Original file should be unchanged (atomic guarantee)
        assert (worktree_dir / "_run.json").read_text() == initial


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestMissingStateFieldDefaults:
    """TS-14-E9: Missing state field uses sensible default.

    Requirement: 14-REQ-1.E1
    """

    def test_incomplete_state_no_keyerror(self) -> None:
        """Verify nodes handle missing state fields gracefully."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Implementation"
        )
        incomplete_state: dict = {
            "current_phase": "implement",
            "messages": [],
        }
        # Should not raise KeyError
        new_state = implement(incomplete_state, mock_llm)
        assert new_state["attempt_count"] >= 0
        assert new_state["halted"] in (True, False)


class TestWriteFailureHandled:
    """TS-14-E13: Run state write failure handled gracefully.

    Requirement: 14-REQ-8.E1
    """

    def test_write_failure_no_crash(
        self,
        worktree_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify write failure logs warning without crashing."""
        state: dict = {
            "current_phase": "implement",
            "current_task_group": 1,
            "attempt_count": 0,
            "halted": False,
        }
        with patch(
            "builtins.open", side_effect=OSError("disk full")
        ):
            with caplog.at_level(logging.WARNING):
                persist_state(state, worktree_dir)
        log_text = " ".join(
            r.message for r in caplog.records
        ).lower()
        assert "warning" in log_text or "disk" in log_text


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPropertyStatePersistence:
    """TS-14-P6: State persistence completeness.

    Property 6 from design.md.
    Validates: 14-REQ-8.1

    After every node transition, _run.json reflects current state.
    """

    @given(
        phase=st.sampled_from(
            [
                "understand_spec",
                "analyze_codebase",
                "write_tests",
                "verify_test_coverage",
                "implement",
                "run_tests",
                "verify_intent",
            ]
        ),
        task_group=st.integers(min_value=1, max_value=5),
        attempt=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_state_persistence(
        self,
        phase: str,
        task_group: int,
        attempt: int,
    ) -> None:
        """_run.json always matches current phase and task group."""
        wt = Path(tempfile.mkdtemp()) / "worktree"
        wt.mkdir()
        state: dict = {
            "current_phase": phase,
            "current_task_group": task_group,
            "attempt_count": attempt,
            "halted": False,
        }
        persist_state(state, wt)
        saved = json.loads((wt / "_run.json").read_text())
        assert saved["current_phase"] == phase
        assert saved["current_task_group"] == task_group
