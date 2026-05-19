"""Markdown rendering for afspec JSON artifacts.

Provides deterministic markdown rendering for all four spec artifact types.
The same in-memory state always produces byte-identical output.
"""
from __future__ import annotations

from afspec.models import (
    ComplexEventCriterion,
    CorrectnessProperty,
    Coverage,
    EARSCriterion,
    EdgeCaseTest,
    ErrorHandlingEntry,
    EventDrivenCriterion,
    ExecutionPath,
    OptionalCriterion,
    PropertyTest,
    Requirement,
    Requirements,
    SmokeTest,
    Spec,
    StateDrivenCriterion,
    Subtask,
    TaskGroup,
    Tasks,
    TestCase,
    TestSpec,
    TraceabilityEntry,
    UbiquitousCriterion,
    UnwantedCriterion,
)

_PLACEHOLDER = "<missing>"


def _f(value: str) -> str:
    """Return value, or placeholder if value is an empty string."""
    return value if value else _PLACEHOLDER


# ---------------------------------------------------------------------------
# EARS sentence rendering
# ---------------------------------------------------------------------------


def render_ears(criterion: EARSCriterion) -> str:
    """Render a single EARS criterion to its sentence form.

    Uses the six sentence templates from spec-format.md §5.2.1.
    Empty string fields are replaced with '<missing>'.
    Non-empty return_contract is appended as 'AND return {contract}'.
    None or empty-string return_contract is omitted.
    """
    if isinstance(criterion, UbiquitousCriterion):
        sentence = f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
    elif isinstance(criterion, EventDrivenCriterion):
        sentence = (
            f"WHEN {_f(criterion.trigger)}, "
            f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
        )
    elif isinstance(criterion, ComplexEventCriterion):
        sentence = (
            f"WHEN {_f(criterion.trigger)} AND {_f(criterion.condition)}, "
            f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
        )
    elif isinstance(criterion, StateDrivenCriterion):
        sentence = (
            f"WHILE {_f(criterion.state)}, "
            f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
        )
    elif isinstance(criterion, UnwantedCriterion):
        sentence = (
            f"IF {_f(criterion.error_condition)}, "
            f"THEN THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
        )
    elif isinstance(criterion, OptionalCriterion):
        sentence = (
            f"WHERE {_f(criterion.feature)}, "
            f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"
        )
    else:
        # Fallback for base class (should not occur in practice)
        sentence = f"THE {_f(criterion.system)} SHALL {_f(criterion.action)}"

    if criterion.return_contract:
        sentence += f" AND return {criterion.return_contract}"

    return sentence


# ---------------------------------------------------------------------------
# Per-file rendering helpers
# ---------------------------------------------------------------------------


def _render_requirement(req: Requirement) -> str:
    """Render a single Requirement to markdown."""
    lines: list[str] = []
    lines.append(f"### {req.id}: {req.title}")
    lines.append("")
    lines.append(
        f"**As a** {req.user_story.role}, "
        f"**I want** {req.user_story.goal}, "
        f"**so that** {req.user_story.benefit}."
    )
    lines.append("")

    if req.acceptance_criteria:
        lines.append("**Acceptance Criteria:**")
        lines.append("")
        for criterion in req.acceptance_criteria:
            lines.append(f"[{criterion.id}] {render_ears(criterion)}")
        lines.append("")

    if req.edge_cases:
        lines.append("**Edge Cases:**")
        lines.append("")
        for criterion in req.edge_cases:
            lines.append(f"[{criterion.id}] {render_ears(criterion)}")
        lines.append("")

    return "\n".join(lines)


def _render_correctness_property(prop: CorrectnessProperty) -> str:
    """Render a correctness property to markdown."""
    lines: list[str] = []
    lines.append(f"### {prop.id}: {prop.title}")
    lines.append("")
    lines.append(f"*For any* {prop.for_any}, the following invariant holds:")
    lines.append("")
    lines.append(f"**Invariant:** {prop.invariant}")
    lines.append("")
    if prop.validates:
        lines.append(f"**Validates:** {', '.join(prop.validates)}")
        lines.append("")
    return "\n".join(lines)


def _render_execution_path(path: ExecutionPath) -> str:
    """Render an execution path to markdown."""
    lines: list[str] = []
    lines.append(f"### {path.id}: {path.title}")
    lines.append("")
    for i, step in enumerate(path.steps, start=1):
        lines.append(f"{i}. **{step.actor}** — {step.action}")
    lines.append("")
    return "\n".join(lines)


def _render_error_handling_entry(entry: ErrorHandlingEntry) -> str:
    """Render an error handling entry as a table row."""
    return f"| {entry.id} | {entry.condition} | {entry.behavior} | {entry.requirement_id} |"


def _render_test_case(tc: TestCase) -> str:
    """Render a test case to markdown."""
    lines: list[str] = []
    lines.append(f"### {tc.id}")
    lines.append("")
    lines.append(f"**Requirement:** {tc.requirement_id}")
    lines.append(f"**Kind:** {tc.kind}")
    lines.append(f"**Description:** {tc.description}")
    lines.append("")
    if tc.preconditions:
        lines.append("**Preconditions:**")
        for p in tc.preconditions:
            lines.append(f"- {p}")
        lines.append("")
    lines.append("**Assertion pseudocode:**")
    lines.append("")
    lines.append("```")
    lines.append(tc.assertion_pseudocode)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _render_property_test(pt: PropertyTest) -> str:
    """Render a property test to markdown."""
    lines: list[str] = []
    lines.append(f"### {pt.id}")
    lines.append("")
    lines.append(f"**Property:** {pt.property_id}")
    lines.append(f"**Description:** {pt.description}")
    lines.append(f"**For any:** {pt.for_any_strategy}")
    lines.append("")
    lines.append("**Invariant check:**")
    lines.append("")
    lines.append("```")
    lines.append(pt.invariant_check)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _render_edge_case_test(et: EdgeCaseTest) -> str:
    """Render an edge case test to markdown."""
    lines: list[str] = []
    lines.append(f"### {et.id}")
    lines.append("")
    lines.append(f"**Requirement:** {et.requirement_id}")
    lines.append(f"**Kind:** {et.kind}")
    lines.append(f"**Description:** {et.description}")
    lines.append("")
    lines.append("**Assertion pseudocode:**")
    lines.append("")
    lines.append("```")
    lines.append(et.assertion_pseudocode)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _render_smoke_test(st: SmokeTest) -> str:
    """Render a smoke test to markdown."""
    lines: list[str] = []
    lines.append(f"### {st.id}")
    lines.append("")
    lines.append(f"**Execution path:** {st.execution_path_id}")
    lines.append(f"**Description:** {st.description}")
    lines.append(f"**Trigger:** {st.trigger}")
    lines.append("")
    if st.expected_effects:
        lines.append("**Expected effects:**")
        for e in st.expected_effects:
            lines.append(f"- {e}")
        lines.append("")
    return "\n".join(lines)


def _render_coverage(coverage: Coverage) -> str:
    """Render the coverage summary to markdown."""
    lines: list[str] = []
    lines.append("## Coverage Summary")
    lines.append("")
    if coverage.requirements_covered:
        lines.append(
            f"**Requirements covered:** {', '.join(sorted(coverage.requirements_covered))}"
        )
    if coverage.properties_covered:
        lines.append(
            f"**Properties covered:** {', '.join(sorted(coverage.properties_covered))}"
        )
    if coverage.paths_covered:
        lines.append(
            f"**Paths covered:** {', '.join(sorted(coverage.paths_covered))}"
        )
    if coverage.gaps:
        lines.append(f"**Gaps:** {', '.join(sorted(coverage.gaps))}")
    lines.append("")
    return "\n".join(lines)


def _render_subtask(subtask: Subtask) -> str:
    """Render a subtask to markdown."""
    optional_marker = " *(optional)*" if subtask.optional else ""
    lines: list[str] = []
    state_val = subtask.state.value if hasattr(subtask.state, "value") else str(subtask.state)
    lines.append(f"- **{subtask.id}** [{state_val}]{optional_marker}: {subtask.title}")
    for detail in subtask.details:
        lines.append(f"  - {detail}")
    return "\n".join(lines)


def _render_task_group(tg: TaskGroup) -> str:
    """Render a task group to markdown."""
    lines: list[str] = []
    lines.append(f"### Group {tg.id}: {tg.title} ({tg.kind})")
    lines.append("")
    for subtask in tg.subtasks:
        lines.append(_render_subtask(subtask))
    lines.append("")
    lines.append(f"**Verification ({tg.verification.id}):**")
    for check in tg.verification.checks:
        lines.append(f"- {check}")
    lines.append("")
    return "\n".join(lines)


def _render_traceability(entries: list[TraceabilityEntry]) -> str:
    """Render the traceability table to markdown."""
    if not entries:
        return ""
    lines: list[str] = []
    lines.append("## Traceability")
    lines.append("")
    lines.append("| Requirement | Test Spec | Task | Test Path |")
    lines.append("|-------------|-----------|------|-----------|")
    for entry in entries:
        test_path = entry.test_path or ""
        lines.append(
            f"| {entry.requirement_id} | {entry.test_spec_id} | {entry.task_id} | {test_path} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public per-file rendering
# ---------------------------------------------------------------------------


def render_requirements(requirements: Requirements) -> str:
    """Render requirements.json artifact to markdown.

    Produces deterministic output — same state always produces byte-identical markdown.
    """
    lines: list[str] = []

    lines.append("## Introduction")
    lines.append("")
    lines.append(requirements.introduction)
    lines.append("")

    if requirements.glossary:
        lines.append("## Glossary")
        lines.append("")
        lines.append("| Term | Definition |")
        lines.append("|------|-----------|")
        for term in sorted(requirements.glossary):
            defn = requirements.glossary[term]
            lines.append(f"| {term} | {defn} |")
        lines.append("")

    if requirements.requirements:
        lines.append("## Requirements")
        lines.append("")
        for req in requirements.requirements:
            lines.append(_render_requirement(req))

    if requirements.correctness_properties:
        lines.append("## Correctness Properties")
        lines.append("")
        for prop in requirements.correctness_properties:
            lines.append(_render_correctness_property(prop))

    if requirements.execution_paths:
        lines.append("## Execution Paths")
        lines.append("")
        for path in requirements.execution_paths:
            lines.append(_render_execution_path(path))

    if requirements.error_handling:
        lines.append("## Error Handling")
        lines.append("")
        lines.append("| ID | Condition | Behavior | Requirement |")
        lines.append("|----|-----------|----------|-------------|")
        for entry in requirements.error_handling:
            lines.append(_render_error_handling_entry(entry))
        lines.append("")

    return "\n".join(lines)


def render_test_spec(test_spec: TestSpec) -> str:
    """Render test_spec.json artifact to markdown.

    Produces deterministic output — same state always produces byte-identical markdown.
    """
    lines: list[str] = []

    if test_spec.test_cases:
        lines.append("## Test Cases")
        lines.append("")
        for tc in test_spec.test_cases:
            lines.append(_render_test_case(tc))

    if test_spec.property_tests:
        lines.append("## Property Tests")
        lines.append("")
        for pt in test_spec.property_tests:
            lines.append(_render_property_test(pt))

    if test_spec.edge_case_tests:
        lines.append("## Edge Case Tests")
        lines.append("")
        for et in test_spec.edge_case_tests:
            lines.append(_render_edge_case_test(et))

    if test_spec.smoke_tests:
        lines.append("## Smoke Tests")
        lines.append("")
        for st in test_spec.smoke_tests:
            lines.append(_render_smoke_test(st))

    lines.append(_render_coverage(test_spec.coverage))

    return "\n".join(lines)


def render_tasks(tasks: Tasks) -> str:
    """Render tasks.json artifact to markdown.

    Produces deterministic output — same state always produces byte-identical markdown.
    """
    lines: list[str] = []

    if tasks.test_commands:
        lines.append("## Test Commands")
        lines.append("")
        for name in sorted(tasks.test_commands):
            lines.append(f"- **{name}:** `{tasks.test_commands[name]}`")
        lines.append("")

    if tasks.dependencies:
        lines.append("## Dependencies")
        lines.append("")
        for dep in tasks.dependencies:
            lines.append(f"- {dep.spec_id} ({dep.kind})")
        lines.append("")

    if tasks.task_groups:
        lines.append("## Task Groups")
        lines.append("")
        for tg in tasks.task_groups:
            lines.append(_render_task_group(tg))

    if tasks.traceability:
        lines.append(_render_traceability(tasks.traceability))

    return "\n".join(lines)


def render_combined(spec: Spec) -> str:
    """Render all four spec artifacts into one combined markdown document.

    Produces PRD body verbatim, followed by rendered requirements, test_spec,
    and tasks markdown each under a top-level markdown headline separator.
    Deterministic — same state always produces byte-identical output.
    """
    parts: list[str] = []

    # PRD body verbatim (no headline)
    parts.append(spec.prd.body)

    # Requirements section
    parts.append("# Requirements\n")
    parts.append(render_requirements(spec.requirements))

    # Test Specification section
    parts.append("# Test Specification\n")
    parts.append(render_test_spec(spec.test_spec))

    # Tasks section
    parts.append("# Tasks\n")
    parts.append(render_tasks(spec.tasks))

    return "\n".join(parts)
