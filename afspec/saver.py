"""Spec saving to disk for afspec.

Implements task group 6: writing all four spec artifacts from in-memory
dataclass instances to a spec folder using atomic writes, deterministic
serialization, and auto-computed fields (updated_at, coverage).
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
from datetime import datetime, timezone
from typing import Any

import yaml

from afspec.models import (
    PRD,
    CorrectnessProperty,
    Coverage,
    ErrorHandlingEntry,
    ExecutionPath,
    PropertyTest,
    Requirement,
    Requirements,
    SmokeTest,
    Spec,
    Subtask,
    TaskGroup,
    Tasks,
    TestCase,
    TestSpec,
    TraceabilityEntry,
)

# ---------------------------------------------------------------------------
# Schema URLs for $schema field in JSON artifacts
# ---------------------------------------------------------------------------

_SCHEMA_URL_REQUIREMENTS = "https://agent-fox.dev/schemas/requirements.v1.json"
_SCHEMA_URL_TEST_SPEC = "https://agent-fox.dev/schemas/test_spec.v1.json"
_SCHEMA_URL_TASKS = "https://agent-fox.dev/schemas/tasks.v1.json"

# Fixed YAML frontmatter field order (per spec-format.md §4.1 and design.md)
_FM_FIELD_ORDER = [
    "spec_id",
    "spec_name",
    "title",
    "status",
    "created_at",
    "updated_at",
    "owner",
    "source",
    "supersedes",
    "tags",
    "intent_hash",
    "schema_version",
]


# ---------------------------------------------------------------------------
# Deterministic JSON serialization
# ---------------------------------------------------------------------------


def _serialize_json(data: dict[str, Any]) -> str:
    """Produce deterministic JSON: keys sorted, 2-space indent, trailing newline."""
    return json.dumps(data, sort_keys=True, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Dict converters for each artifact type
# ---------------------------------------------------------------------------


def _requirement_to_dict(req: Requirement) -> dict[str, Any]:
    return {
        "id": req.id,
        "title": req.title,
        "user_story": {
            "role": req.user_story.role,
            "goal": req.user_story.goal,
            "benefit": req.user_story.benefit,
        },
        "acceptance_criteria": [_ears_to_dict(c) for c in req.acceptance_criteria],
        "edge_cases": [_ears_to_dict(c) for c in req.edge_cases],
    }


def _ears_to_dict(c: Any) -> dict[str, Any]:
    """Convert an EARS criterion (any subclass) to a plain dict.

    Uses dataclasses.asdict() which recursively converts; enums are not
    nested here so no special handling needed for EARSCriterion.
    """
    import dataclasses

    return dataclasses.asdict(c)


def _cp_to_dict(cp: CorrectnessProperty) -> dict[str, Any]:
    return {
        "id": cp.id,
        "title": cp.title,
        "for_any": cp.for_any,
        "invariant": cp.invariant,
        "validates": list(cp.validates),
    }


def _ep_to_dict(ep: ExecutionPath) -> dict[str, Any]:
    return {
        "id": ep.id,
        "title": ep.title,
        "steps": [{"actor": s.actor, "action": s.action} for s in ep.steps],
    }


def _eh_to_dict(eh: ErrorHandlingEntry) -> dict[str, Any]:
    return {
        "id": eh.id,
        "condition": eh.condition,
        "behavior": eh.behavior,
        "requirement_id": eh.requirement_id,
    }


def _requirements_to_dict(req: Requirements) -> dict[str, Any]:
    return {
        "$schema": _SCHEMA_URL_REQUIREMENTS,
        "spec_id": req.spec_id,
        "spec_name": req.spec_name,
        "schema_version": req.schema_version,
        "introduction": req.introduction,
        "glossary": dict(req.glossary),
        "requirements": [_requirement_to_dict(r) for r in req.requirements],
        "correctness_properties": [_cp_to_dict(cp) for cp in req.correctness_properties],
        "execution_paths": [_ep_to_dict(ep) for ep in req.execution_paths],
        "error_handling": [_eh_to_dict(eh) for eh in req.error_handling],
    }


def _tc_to_dict(tc: TestCase) -> dict[str, Any]:
    return {
        "id": tc.id,
        "requirement_id": tc.requirement_id,
        "kind": tc.kind,
        "description": tc.description,
        "preconditions": list(tc.preconditions),
        "input": dict(tc.input),
        "expected": dict(tc.expected),
        "assertion_pseudocode": tc.assertion_pseudocode,
    }


def _pt_to_dict(pt: PropertyTest) -> dict[str, Any]:
    return {
        "id": pt.id,
        "property_id": pt.property_id,
        "validates": list(pt.validates),
        "description": pt.description,
        "for_any_strategy": pt.for_any_strategy,
        "invariant_check": pt.invariant_check,
    }


def _ect_to_dict(ect: Any) -> dict[str, Any]:
    """EdgeCaseTest → dict (same fields as TestCase)."""
    return {
        "id": ect.id,
        "requirement_id": ect.requirement_id,
        "kind": ect.kind,
        "description": ect.description,
        "preconditions": list(ect.preconditions),
        "input": dict(ect.input),
        "expected": dict(ect.expected),
        "assertion_pseudocode": ect.assertion_pseudocode,
    }


def _st_to_dict(st: SmokeTest) -> dict[str, Any]:
    return {
        "id": st.id,
        "execution_path_id": st.execution_path_id,
        "description": st.description,
        "trigger": st.trigger,
        "real_components": list(st.real_components),
        "mockable": list(st.mockable),
        "expected_effects": list(st.expected_effects),
    }


def _coverage_to_dict(cov: Coverage) -> dict[str, Any]:
    return {
        "requirements_covered": list(cov.requirements_covered),
        "properties_covered": list(cov.properties_covered),
        "paths_covered": list(cov.paths_covered),
        "gaps": list(cov.gaps),
    }


def _test_spec_to_dict(ts: TestSpec) -> dict[str, Any]:
    return {
        "$schema": _SCHEMA_URL_TEST_SPEC,
        "spec_id": ts.spec_id,
        "spec_name": ts.spec_name,
        "schema_version": ts.schema_version,
        "test_cases": [_tc_to_dict(tc) for tc in ts.test_cases],
        "property_tests": [_pt_to_dict(pt) for pt in ts.property_tests],
        "edge_case_tests": [_ect_to_dict(ect) for ect in ts.edge_case_tests],
        "smoke_tests": [_st_to_dict(st) for st in ts.smoke_tests],
        "coverage": _coverage_to_dict(ts.coverage),
    }


def _subtask_to_dict(st: Subtask) -> dict[str, Any]:
    return {
        "id": st.id,
        "title": st.title,
        "details": list(st.details),
        "test_spec_refs": list(st.test_spec_refs),
        "requirement_refs": list(st.requirement_refs),
        "state": st.state.value,  # enum → string value
        "optional": st.optional,
    }


def _tg_to_dict(tg: TaskGroup) -> dict[str, Any]:
    return {
        "id": tg.id,
        "kind": tg.kind,
        "title": tg.title,
        "subtasks": [_subtask_to_dict(st) for st in tg.subtasks],
        "verification": {
            "id": tg.verification.id,
            "checks": list(tg.verification.checks),
        },
    }


def _tr_to_dict(tr: TraceabilityEntry) -> dict[str, Any]:
    return {
        "requirement_id": tr.requirement_id,
        "test_spec_id": tr.test_spec_id,
        "task_id": tr.task_id,
        "test_path": tr.test_path,
    }


def _tasks_to_dict(tasks: Tasks) -> dict[str, Any]:
    return {
        "$schema": _SCHEMA_URL_TASKS,
        "spec_id": tasks.spec_id,
        "spec_name": tasks.spec_name,
        "schema_version": tasks.schema_version,
        "test_commands": dict(tasks.test_commands),
        "dependencies": [
            {"spec_id": d.spec_id, "kind": d.kind} for d in tasks.dependencies
        ],
        "task_groups": [_tg_to_dict(tg) for tg in tasks.task_groups],
        "traceability": [_tr_to_dict(tr) for tr in tasks.traceability],
    }


# ---------------------------------------------------------------------------
# PRD serialization (YAML frontmatter + markdown body)
# ---------------------------------------------------------------------------


def _serialize_prd(prd: PRD) -> str:
    """Serialize a PRD to the prd.md string with fixed-order YAML frontmatter.

    The YAML frontmatter fields are written in the canonical order defined by
    ``_FM_FIELD_ORDER``. The markdown body is appended verbatim after the
    closing ``---`` delimiter.

    Returns:
        The full prd.md file content as a string.
    """
    fm = prd.frontmatter
    # Build an OrderedDict-equivalent by constructing a dict in field order.
    # Python 3.7+ dicts preserve insertion order, so this is safe.
    fm_dict: dict[str, Any] = {}
    fm_dict["spec_id"] = fm.spec_id
    fm_dict["spec_name"] = fm.spec_name
    fm_dict["title"] = fm.title
    fm_dict["status"] = fm.status
    fm_dict["created_at"] = fm.created_at
    fm_dict["updated_at"] = fm.updated_at
    fm_dict["owner"] = fm.owner
    fm_dict["source"] = fm.source
    fm_dict["supersedes"] = list(fm.supersedes)
    fm_dict["tags"] = list(fm.tags)
    fm_dict["intent_hash"] = fm.intent_hash
    fm_dict["schema_version"] = fm.schema_version

    # Use yaml.dump with sort_keys=False to preserve field order.
    # allow_unicode=True avoids escaping non-ASCII characters.
    yaml_text = yaml.dump(fm_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # File format: opening ---, YAML block, closing ---, then body.
    # There is exactly one newline after the closing --- before the body.
    return f"---\n{yaml_text}---\n{prd.body}"


# ---------------------------------------------------------------------------
# Coverage computation
# ---------------------------------------------------------------------------


def _compute_coverage(requirements: Requirements, test_spec: TestSpec) -> Coverage:
    """Compute test coverage by scanning test cases against requirements.

    Coverage fields computed:
    - ``requirements_covered``: criterion + edge case IDs that have a test case
    - ``gaps``: criterion + edge case IDs without any test case
    - ``properties_covered``: correctness property IDs that have a property test
    - ``paths_covered``: execution path IDs that have a smoke test

    The ordering of IDs in each list follows the declaration order in
    ``requirements.json`` (acceptance criteria before edge cases, in requirement
    order), so that consecutive saves produce identical JSON output.

    Args:
        requirements: The loaded requirements artifact.
        test_spec: The loaded test spec artifact.

    Returns:
        A new ``Coverage`` instance with computed fields.
    """
    # Gather all requirement criterion IDs (acceptance criteria then edge cases)
    all_req_ids: list[str] = []
    for req in requirements.requirements:
        for c in req.acceptance_criteria:
            all_req_ids.append(c.id)
        for ec in req.edge_cases:
            all_req_ids.append(ec.id)

    # Covered requirement IDs: from test_cases and edge_case_tests
    covered_req_ids: set[str] = set()
    for tc in test_spec.test_cases:
        covered_req_ids.add(tc.requirement_id)
    for etc in test_spec.edge_case_tests:
        covered_req_ids.add(etc.requirement_id)

    requirements_covered = [rid for rid in all_req_ids if rid in covered_req_ids]
    gaps = [rid for rid in all_req_ids if rid not in covered_req_ids]

    # Properties covered: from property_tests
    all_prop_ids = [p.id for p in requirements.correctness_properties]
    covered_prop_ids = {pt.property_id for pt in test_spec.property_tests}
    properties_covered = [pid for pid in all_prop_ids if pid in covered_prop_ids]

    # Paths covered: from smoke_tests
    all_path_ids = [ep.id for ep in requirements.execution_paths]
    covered_path_ids = {st.execution_path_id for st in test_spec.smoke_tests}
    paths_covered = [pid for pid in all_path_ids if pid in covered_path_ids]

    return Coverage(
        requirements_covered=requirements_covered,
        properties_covered=properties_covered,
        paths_covered=paths_covered,
        gaps=gaps,
    )


# ---------------------------------------------------------------------------
# Computed fields update
# ---------------------------------------------------------------------------


def _update_computed_fields(spec: Spec) -> Spec:
    """Return a new Spec with updated_at set to now and coverage recomputed.

    Creates new frozen dataclass instances for the affected fields.  The
    original ``spec`` is not mutated.

    Args:
        spec: The spec to update.

    Returns:
        A new ``Spec`` with refreshed ``updated_at`` and ``coverage``.
    """
    import dataclasses

    # Set updated_at to the current UTC timestamp in ISO 8601 format
    now = datetime.now(timezone.utc)
    updated_at = now.isoformat().replace("+00:00", "Z")

    new_fm = dataclasses.replace(spec.prd.frontmatter, updated_at=updated_at)
    new_prd = dataclasses.replace(spec.prd, frontmatter=new_fm)

    # Recompute coverage from the current requirements and test spec
    new_coverage = _compute_coverage(spec.requirements, spec.test_spec)
    new_test_spec = dataclasses.replace(spec.test_spec, coverage=new_coverage)

    return dataclasses.replace(spec, prd=new_prd, test_spec=new_test_spec)


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------


def _atomic_write(path: pathlib.Path, content: str) -> None:
    """Write ``content`` to ``path`` using an atomic write-then-rename strategy.

    Creates a temporary file in the same directory as ``path``, writes the
    content, then renames the temp file to ``path`` atomically (``os.replace``).
    On failure, the temp file is cleaned up and the exception is re-raised.

    Args:
        path: Destination file path.
        content: String content to write (UTF-8).

    Raises:
        OSError: If the directory is not writable or any I/O error occurs.
    """
    tmp_path: pathlib.Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        tmp_path = pathlib.Path(tmp_str)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
        tmp_path = None  # rename succeeded; no cleanup needed
    except Exception:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def save_spec(spec: Spec, path: pathlib.Path) -> None:
    """Write all four spec artifacts to ``path`` with atomic writes.

    Before writing, computes ``updated_at`` (current UTC timestamp) and
    recomputes ``coverage`` in ``test_spec.json``.  All four files are written
    using write-to-temp-then-rename so that a failure mid-write leaves no
    partial files behind.

    Args:
        spec: The in-memory spec to persist.
        path: Directory to write into (must already exist).

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        NotADirectoryError: If ``path`` is not a directory.
        OSError: If any file write fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Target directory does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {path}")

    # Update computed fields (updated_at, coverage)
    updated_spec = _update_computed_fields(spec)

    # Serialize each artifact to a string
    prd_content = _serialize_prd(updated_spec.prd)
    req_content = _serialize_json(_requirements_to_dict(updated_spec.requirements))
    ts_content = _serialize_json(_test_spec_to_dict(updated_spec.test_spec))
    tasks_content = _serialize_json(_tasks_to_dict(updated_spec.tasks))

    # Write atomically; _atomic_write cleans up temp files on failure
    _atomic_write(path / "prd.md", prd_content)
    _atomic_write(path / "requirements.json", req_content)
    _atomic_write(path / "test_spec.json", ts_content)
    _atomic_write(path / "tasks.json", tasks_content)


__all__ = [
    "save_spec",
    "_serialize_json",
    "_serialize_prd",
    "_compute_coverage",
    "_update_computed_fields",
    "_atomic_write",
]
