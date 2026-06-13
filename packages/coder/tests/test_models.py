"""Tests for coder execution plan data models.

Covers: TS-13-8 (ExecutionPlan serialization).
"""

from __future__ import annotations

import json

from afspec.models import Requirements, SpecMeta, Tasks, TestSpec
from coder.errors import DependencyCycleError, SpecParseError  # noqa: F401
from coder.models import ExecutionPlan, ParsedSpec


class TestExecutionPlanSerialization:
    """TS-13-8: Execution plan is serializable.

    Requirement: 13-REQ-5.1, 13-REQ-5.3
    Verify ExecutionPlan can be serialized to JSON and the output
    contains the expected top-level keys.
    """

    def test_plan_serializable(self) -> None:
        """TS-13-8: Verify ExecutionPlan serializes to valid JSON.

        Requirement: 13-REQ-5.1, 13-REQ-5.3
        """
        meta = SpecMeta(
            spec_id="1",
            spec_name="test_spec",
            status="active",
            dir="/tmp/fake",
        )
        parsed = ParsedSpec(
            meta=meta,
            requirements=Requirements(spec_id="1", spec_name="test_spec"),
            test_spec=TestSpec(spec_id="1", spec_name="test_spec"),
            tasks=Tasks(spec_id="1", spec_name="test_spec"),
            prd_text="# Test PRD\n",
        )
        plan = ExecutionPlan(
            specs=[parsed],
            count=1,
            timestamp="2026-06-13T10:00:00Z",
        )

        json_str = plan.model_dump_json()
        data = json.loads(json_str)

        assert "specs" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["count"] == 1
        assert len(data["specs"]) == 1

    def test_plan_is_frozen(self) -> None:
        """Verify ExecutionPlan is immutable (frozen pydantic model).

        Requirement: 13-REQ-5.3
        """
        import pytest

        meta = SpecMeta(
            spec_id="1",
            spec_name="test_spec",
            status="active",
            dir="/tmp/fake",
        )
        parsed = ParsedSpec(
            meta=meta,
            requirements=Requirements(spec_id="1", spec_name="test_spec"),
            test_spec=TestSpec(spec_id="1", spec_name="test_spec"),
            tasks=Tasks(spec_id="1", spec_name="test_spec"),
            prd_text="# Test PRD\n",
        )
        plan = ExecutionPlan(
            specs=[parsed],
            count=1,
            timestamp="2026-06-13T10:00:00Z",
        )

        with pytest.raises(Exception):
            plan.count = 99  # type: ignore[misc]
