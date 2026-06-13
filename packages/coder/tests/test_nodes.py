"""Tests for LangGraph workflow node implementations.

Covers: TS-14-2 through TS-14-8 (node behavior).
Edge cases: TS-14-E1, TS-14-E2.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from coder.nodes import (
    analyze_codebase,
    implement,
    run_tests,
    understand_spec,
    verify_intent,
    verify_test_coverage,
    write_tests,
)
from coder.verify import VerificationResult

# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestUnderstandSpec:
    """TS-14-2: understand_spec node populates spec_context.

    Requirement: 14-REQ-2.1
    """

    def test_populates_spec_context(self) -> None:
        """Verify understand_spec writes to spec_context."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Spec intent summary"
        )
        state: dict = {
            "current_phase": "understand_spec",
            "spec_context": "",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = understand_spec(state, mock_llm)
        assert len(new_state["spec_context"]) > 0


class TestAnalyzeCodebase:
    """TS-14-3: analyze_codebase node populates analysis.

    Requirement: 14-REQ-2.2
    """

    def test_populates_codebase_analysis(self) -> None:
        """Verify analyze_codebase writes codebase analysis."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Codebase analysis"
        )
        state: dict = {
            "current_phase": "analyze_codebase",
            "codebase_analysis": "",
            "spec_context": "Some context",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = analyze_codebase(state, mock_llm)
        assert len(new_state["codebase_analysis"]) > 0


class TestWriteTests:
    """TS-14-4: write_tests node invokes LLM with test spec.

    Requirement: 14-REQ-2.3
    """

    def test_invokes_llm_with_test_content(self) -> None:
        """Verify write_tests sends test_spec content to LLM."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Test code written"
        )
        state: dict = {
            "current_phase": "write_tests",
            "spec_context": "Spec context with test cases",
            "messages": [],
            "attempt_count": 0,
            "current_task_group": 1,
            "halted": False,
        }
        write_tests(state, mock_llm)
        assert mock_llm.invoke.called
        messages = mock_llm.invoke.call_args[0][0]
        assert any("test" in str(m).lower() for m in messages)


class TestVerifyTestCoverage:
    """TS-14-5: verify_test_coverage sets coverage_ok flag.

    Requirement: 14-REQ-2.4
    """

    def test_sets_coverage_ok(self) -> None:
        """Verify coverage check sets the flag."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Coverage: all test cases covered"
        )
        state: dict = {
            "current_phase": "verify_test_coverage",
            "spec_context": "Spec context",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = verify_test_coverage(state, mock_llm)
        assert "coverage_ok" in new_state
        assert isinstance(new_state["coverage_ok"], bool)


class TestImplement:
    """TS-14-6: implement node invokes LLM with coder persona.

    Requirement: 14-REQ-2.5
    """

    def test_invokes_llm(self) -> None:
        """Verify implement node invokes the LLM."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Implementation code"
        )
        state: dict = {
            "current_phase": "implement",
            "spec_context": "Spec context",
            "codebase_analysis": "Analysis",
            "test_results": "",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        implement(state, mock_llm)
        assert mock_llm.invoke.called


class TestRunTests:
    """TS-14-7: run_tests node executes verification runner.

    Requirement: 14-REQ-2.6
    """

    def test_calls_verification_runner(self) -> None:
        """Verify run_tests calls the verification runner."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = VerificationResult(
            passed=True,
            exit_code=0,
            stdout="All tests passed",
            stderr="",
            command="pytest",
            elapsed_seconds=1.5,
        )
        state: dict = {
            "current_phase": "run_tests",
            "test_results": "",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = run_tests(state, mock_runner)
        assert "pass" in new_state["test_results"].lower()


class TestVerifyIntent:
    """TS-14-8: verify_intent uses reviewer persona.

    Requirement: 14-REQ-2.7
    """

    def test_sets_drift_detected(self) -> None:
        """Verify intent check sets drift_detected flag."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="No drift detected"
        )
        state: dict = {
            "current_phase": "verify_intent",
            "spec_context": "Spec context",
            "test_results": "PASS",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = verify_intent(state, mock_llm)
        assert isinstance(new_state["drift_detected"], bool)


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestEmptyLLMResponse:
    """TS-14-E1: LLM empty response triggers retry.

    Requirement: 14-REQ-2.E1
    """

    def test_empty_response_increments_attempt(self) -> None:
        """Verify empty LLM response increments attempt count."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="")
        state: dict = {
            "current_phase": "implement",
            "spec_context": "Spec context",
            "codebase_analysis": "Analysis",
            "test_results": "",
            "messages": [],
            "attempt_count": 0,
            "halted": False,
        }
        new_state = implement(state, mock_llm)
        assert new_state["attempt_count"] == 1


class TestHaltedPassthrough:
    """TS-14-E2: Halted state skips node execution.

    Requirement: 14-REQ-3.E1
    """

    def test_halted_state_unchanged(self) -> None:
        """Verify nodes pass through when halted."""
        mock_llm = MagicMock()
        halted_state: dict = {
            "current_phase": "implement",
            "spec_context": "",
            "codebase_analysis": "",
            "test_results": "",
            "messages": [],
            "attempt_count": 3,
            "max_attempts": 5,
            "halted": True,
            "halt_reason": "Max attempts exceeded",
        }
        new_state = implement(halted_state, mock_llm)
        assert new_state == halted_state
        assert not mock_llm.invoke.called
