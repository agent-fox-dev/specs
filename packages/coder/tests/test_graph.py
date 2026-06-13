"""Tests for LangGraph state schema and conditional edge routing.

Covers: TS-14-1, TS-14-9 through TS-14-12, TS-14-26, TS-14-27.
Property tests: TS-14-P2.
"""

from __future__ import annotations

import pytest
from afspec.models import Requirements, SpecMeta, Tasks, TestSpec
from coder.graph import (
    create_initial_state,
    route_after_coverage,
    route_after_intent,
    route_after_tests,
)
from coder.models import ParsedSpec
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture()
def mock_parsed_spec() -> ParsedSpec:
    """Create a minimal ParsedSpec for state initialization tests."""
    meta = SpecMeta(
        spec_id="1",
        spec_name="test_spec",
        status="active",
        dir="/tmp/fake",
    )
    return ParsedSpec(
        meta=meta,
        requirements=Requirements(spec_id="1", spec_name="test_spec"),
        test_spec=TestSpec(spec_id="1", spec_name="test_spec"),
        tasks=Tasks(spec_id="1", spec_name="test_spec"),
        prd_text="# Test PRD\n",
    )


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestCoderStateInit:
    """TS-14-1: CoderState initializes with defaults.

    Requirement: 14-REQ-1.1, 14-REQ-1.2
    """

    def test_initial_phase(self, mock_parsed_spec: ParsedSpec) -> None:
        """Verify initial current_phase is 'understand_spec'."""
        state = create_initial_state(mock_parsed_spec)
        assert state["current_phase"] == "understand_spec"

    def test_initial_attempt_count(
        self, mock_parsed_spec: ParsedSpec
    ) -> None:
        """Verify initial attempt_count is 0."""
        state = create_initial_state(mock_parsed_spec)
        assert state["attempt_count"] == 0

    def test_initial_halted(
        self, mock_parsed_spec: ParsedSpec
    ) -> None:
        """Verify initial halted is False."""
        state = create_initial_state(mock_parsed_spec)
        assert state["halted"] is False

    def test_all_required_fields_present(
        self, mock_parsed_spec: ParsedSpec
    ) -> None:
        """Verify all required CoderState fields are present."""
        state = create_initial_state(mock_parsed_spec)
        required_fields = [
            "current_phase",
            "current_task_group",
            "attempt_count",
            "max_attempts",
            "test_results",
            "spec_context",
            "codebase_analysis",
            "messages",
            "halted",
            "halt_reason",
        ]
        for field in required_fields:
            assert field in state, f"Missing state field: {field}"


class TestCoverageRouting:
    """TS-14-9: Coverage failure routes back to write_tests.

    Requirement: 14-REQ-3.1
    """

    def test_coverage_insufficient_routes_to_write_tests(self) -> None:
        """Verify routing on coverage failure."""
        state: dict = {
            "coverage_ok": False,
            "attempt_count": 1,
            "max_attempts": 5,
            "halted": False,
        }
        next_node = route_after_coverage(state)
        assert next_node == "write_tests"

    def test_coverage_ok_routes_to_implement(self) -> None:
        """Verify routing on coverage success."""
        state: dict = {
            "coverage_ok": True,
            "attempt_count": 1,
            "max_attempts": 5,
            "halted": False,
        }
        next_node = route_after_coverage(state)
        assert next_node == "implement"


class TestTestRouting:
    """TS-14-10, TS-14-11, TS-14-12: Test result routing.

    Requirements: 14-REQ-3.2, 14-REQ-3.3, 14-REQ-3.6
    """

    def test_failure_routes_to_implement(self) -> None:
        """TS-14-10: Test failure routes back to implement.

        Requirement: 14-REQ-3.2
        """
        state: dict = {
            "test_results": "FAIL",
            "attempt_count": 1,
            "max_attempts": 5,
            "halted": False,
        }
        next_node = route_after_tests(state)
        assert next_node == "implement"

    def test_pass_routes_to_verify_intent(self) -> None:
        """TS-14-11: All tests pass routes to verify_intent.

        Requirement: 14-REQ-3.3
        """
        state: dict = {
            "test_results": "PASS",
            "attempt_count": 1,
            "max_attempts": 5,
            "halted": False,
        }
        next_node = route_after_tests(state)
        assert next_node == "verify_intent"

    def test_max_attempts_routes_to_halted(self) -> None:
        """TS-14-12: Max attempts triggers halt.

        Requirement: 14-REQ-3.6
        """
        state: dict = {
            "test_results": "FAIL",
            "attempt_count": 5,
            "max_attempts": 5,
            "halted": False,
        }
        next_node = route_after_tests(state)
        assert next_node == "halted"


class TestIntentRouting:
    """TS-14-26, TS-14-27: Intent verification routing.

    Requirements: 14-REQ-3.4, 14-REQ-3.5
    """

    def test_drift_routes_to_verify_test_coverage(self) -> None:
        """TS-14-26: Drift routes back to verify_test_coverage.

        Requirement: 14-REQ-3.4
        """
        state: dict = {
            "drift_detected": True,
            "attempt_count": 1,
            "max_attempts": 5,
            "current_task_group": 1,
            "total_groups": 3,
            "halted": False,
        }
        next_node = route_after_intent(state)
        assert next_node == "verify_test_coverage"

    def test_no_drift_routes_to_next_task_group(self) -> None:
        """TS-14-27: No drift with remaining groups routes to next.

        Requirement: 14-REQ-3.5
        """
        state: dict = {
            "drift_detected": False,
            "attempt_count": 1,
            "max_attempts": 5,
            "current_task_group": 1,
            "total_groups": 3,
            "halted": False,
        }
        next_node = route_after_intent(state)
        assert next_node == "next_task_group"

    def test_no_drift_last_group_routes_to_complete(self) -> None:
        """TS-14-27: No drift on last group routes to complete.

        Requirement: 14-REQ-3.5
        """
        state: dict = {
            "drift_detected": False,
            "attempt_count": 1,
            "max_attempts": 5,
            "current_task_group": 3,
            "total_groups": 3,
            "halted": False,
        }
        next_node = route_after_intent(state)
        assert next_node == "complete"

    def test_drift_max_attempts_routes_to_halted(self) -> None:
        """Drift at max attempts routes to halted.

        Requirement: 14-REQ-3.6 (applied to intent routing)
        """
        state: dict = {
            "drift_detected": True,
            "attempt_count": 5,
            "max_attempts": 5,
            "current_task_group": 1,
            "total_groups": 3,
            "halted": False,
        }
        next_node = route_after_intent(state)
        assert next_node == "halted"


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPropertyRetryBound:
    """TS-14-P2: Retry never exceeds max_attempts.

    Property 2 from design.md.
    Validates: 14-REQ-3.2, 14-REQ-3.6

    For any max_attempts value, the router halts once attempts are
    exhausted rather than allowing further retries.
    """

    @given(max_attempts=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=10000)
    def test_property_retry_bound(self, max_attempts: int) -> None:
        """Attempt count at or above max always routes to halted."""
        for attempt in range(max_attempts + 5):
            state: dict = {
                "test_results": "FAIL",
                "attempt_count": attempt,
                "max_attempts": max_attempts,
                "halted": False,
            }
            next_node = route_after_tests(state)
            if attempt >= max_attempts:
                assert next_node == "halted", (
                    f"Expected halt at attempt {attempt} with "
                    f"max_attempts={max_attempts}"
                )
            else:
                assert next_node == "implement"
