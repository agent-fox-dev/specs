"""Tests for markdown rendering.

Covers: TS-02-25, TS-02-26, TS-02-27, TS-02-28, TS-02-E21, TS-02-E22
"""
from __future__ import annotations

import pathlib

import pytest

from afspec import load_spec, render_combined, render_requirements, render_tasks, render_test_spec
from afspec.models import (
    ComplexEventCriterion,
    EventDrivenCriterion,
    OptionalCriterion,
    StateDrivenCriterion,
    UbiquitousCriterion,
    UnwantedCriterion,
)
from afspec.renderer import render_ears


def test_deterministic_rendering(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-25: rendering same input twice produces byte-identical output."""
    spec = load_spec(tmp_spec_dir)
    out1 = render_requirements(spec.requirements)
    out2 = render_requirements(spec.requirements)
    assert out1 == out2


def test_ears_ubiquitous_template() -> None:
    """TS-02-26: ubiquitous EARS template: THE {system} SHALL {action}."""
    criterion = UbiquitousCriterion(
        id="05-REQ-1.1",
        ears_pattern="ubiquitous",
        system="the system",
        action="do X",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "THE the system SHALL do X"


def test_ears_event_driven_template() -> None:
    """TS-02-26: event_driven template: WHEN {trigger}, THE {system} SHALL {action}."""
    criterion = EventDrivenCriterion(
        id="05-REQ-1.2",
        ears_pattern="event_driven",
        trigger="a request",
        system="the system",
        action="respond",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "WHEN a request, THE the system SHALL respond"


def test_ears_complex_event_template() -> None:
    """TS-02-26: complex_event template: WHEN {trigger} AND {condition}, THE {sys} SHALL {act}."""
    criterion = ComplexEventCriterion(
        id="05-REQ-1.3",
        ears_pattern="complex_event",
        trigger="T",
        condition="C",
        system="the system",
        action="act",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "WHEN T AND C, THE the system SHALL act"


def test_ears_state_driven_template() -> None:
    """TS-02-26: state_driven template: WHILE {state}, THE {system} SHALL {action}."""
    criterion = StateDrivenCriterion(
        id="05-REQ-1.4",
        ears_pattern="state_driven",
        state="active",
        system="the system",
        action="monitor",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "WHILE active, THE the system SHALL monitor"


def test_ears_unwanted_template() -> None:
    """TS-02-26: unwanted template: IF {error_condition}, THEN THE {system} SHALL {action}."""
    criterion = UnwantedCriterion(
        id="05-REQ-1.5",
        ears_pattern="unwanted",
        error_condition="timeout",
        system="the system",
        action="retry",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "IF timeout, THEN THE the system SHALL retry"


def test_ears_optional_template() -> None:
    """TS-02-26: optional template: WHERE {feature}, THE {system} SHALL {action}."""
    criterion = OptionalCriterion(
        id="05-REQ-1.6",
        ears_pattern="optional",
        feature="dark mode",
        system="the system",
        action="adjust",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "WHERE dark mode, THE the system SHALL adjust"


def test_per_file_requirements_rendering(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-27: render_requirements returns non-empty markdown with REQ- content."""
    spec = load_spec(tmp_spec_dir)
    result = render_requirements(spec.requirements)
    assert len(result) > 0
    assert "REQ-" in result


def test_per_file_test_spec_rendering(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-27: render_test_spec returns non-empty markdown string."""
    spec = load_spec(tmp_spec_dir)
    result = render_test_spec(spec.test_spec)
    assert len(result) > 0


def test_per_file_tasks_rendering(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-27: render_tasks returns non-empty markdown string."""
    spec = load_spec(tmp_spec_dir)
    result = render_tasks(spec.tasks)
    assert len(result) > 0


def test_combined_rendering_structure(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-28: combined rendering starts with PRD body and has section headlines."""
    spec = load_spec(tmp_spec_dir)
    combined = render_combined(spec)
    # Starts with PRD body
    assert combined.startswith(spec.prd.body)
    # Section headlines present in order
    req_pos = combined.index("# Requirements")
    ts_pos = combined.index("# Test Specification")
    tasks_pos = combined.index("# Tasks")
    assert req_pos < ts_pos < tasks_pos


def test_combined_rendering_is_deterministic(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-28: combined rendering is deterministic across multiple calls."""
    spec = load_spec(tmp_spec_dir)
    out1 = render_combined(spec)
    out2 = render_combined(spec)
    assert out1 == out2


def test_ears_empty_field_uses_placeholder() -> None:
    """TS-02-E21: empty string fields render as <missing>."""
    criterion = UbiquitousCriterion(
        id="05-REQ-1.1",
        ears_pattern="ubiquitous",
        system="",
        action="do X",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert result == "THE <missing> SHALL do X"


def test_ears_null_return_contract_omitted() -> None:
    """TS-02-E22: None return_contract is omitted from rendered sentence."""
    criterion = EventDrivenCriterion(
        id="05-REQ-1.1",
        ears_pattern="event_driven",
        trigger="request",
        system="sys",
        action="respond",
        return_contract=None,
    )
    result = render_ears(criterion)
    assert "return" not in result.lower()


def test_ears_empty_string_return_contract_omitted() -> None:
    """TS-02-E22: empty string return_contract is omitted from rendered sentence."""
    criterion = EventDrivenCriterion(
        id="05-REQ-1.2",
        ears_pattern="event_driven",
        trigger="request",
        system="sys",
        action="respond",
        return_contract="",
    )
    result = render_ears(criterion)
    assert "return" not in result.lower()


def test_ears_nonempty_return_contract_appended() -> None:
    """TS-02-E22: non-empty return_contract is appended with AND return clause."""
    criterion = EventDrivenCriterion(
        id="05-REQ-1.3",
        ears_pattern="event_driven",
        trigger="request",
        system="sys",
        action="respond",
        return_contract="list of items",
    )
    result = render_ears(criterion)
    assert "AND return list of items" in result


@pytest.mark.parametrize(
    "field,value,expected_placeholder",
    [
        ("system", "", "THE <missing> SHALL act"),
        ("action", "", "THE sys SHALL <missing>"),
    ],
)
def test_ears_various_empty_fields(
    field: str, value: str, expected_placeholder: str
) -> None:
    """TS-02-E21: multiple empty field positions produce <missing> placeholder."""
    kwargs = {
        "id": "05-REQ-1.1",
        "ears_pattern": "ubiquitous",
        "system": "sys",
        "action": "act",
        "return_contract": None,
    }
    kwargs[field] = value
    criterion = UbiquitousCriterion(**kwargs)  # type: ignore[arg-type]
    result = render_ears(criterion)
    assert result == expected_placeholder
