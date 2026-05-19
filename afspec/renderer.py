"""Markdown rendering for afspec JSON artifacts.

STUB — real implementation in task group 9.
"""
from __future__ import annotations

from afspec.models import EARSCriterion, Requirements, Spec, Tasks, TestSpec


def render_ears(criterion: EARSCriterion) -> str:
    """Render a single EARS criterion to its sentence form.

    STUB: raises NotImplementedError. Implemented in task group 9.
    """
    raise NotImplementedError("render_ears not yet implemented (task group 9)")


def render_requirements(requirements: Requirements) -> str:
    """Render requirements.json artifact to markdown.

    STUB: raises NotImplementedError. Implemented in task group 9.
    """
    raise NotImplementedError("render_requirements not yet implemented (task group 9)")


def render_test_spec(test_spec: TestSpec) -> str:
    """Render test_spec.json artifact to markdown.

    STUB: raises NotImplementedError. Implemented in task group 9.
    """
    raise NotImplementedError("render_test_spec not yet implemented (task group 9)")


def render_tasks(tasks: Tasks) -> str:
    """Render tasks.json artifact to markdown.

    STUB: raises NotImplementedError. Implemented in task group 9.
    """
    raise NotImplementedError("render_tasks not yet implemented (task group 9)")


def render_combined(spec: Spec) -> str:
    """Render all four spec artifacts into one combined markdown document.

    STUB: raises NotImplementedError. Implemented in task group 9.
    """
    raise NotImplementedError("render_combined not yet implemented (task group 9)")
