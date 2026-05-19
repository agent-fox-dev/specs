"""Spec loading from disk for afspec.

Implements task group 5: reading all four spec artifacts from a spec folder
into typed in-memory dataclass instances.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, TypeVar

import yaml

from afspec.exceptions import IncompleteSpecError, SpecValidationError
from afspec.models import (
    PRD,
    CorrectnessProperty,
    Coverage,
    Dependency,
    EARSCriterion,
    EdgeCaseTest,
    ErrorHandlingEntry,
    ExecutionPath,
    ExecutionPathStep,
    PRDFrontmatter,
    PropertyTest,
    Requirement,
    Requirements,
    SmokeTest,
    Spec,
    Subtask,
    SubtaskState,
    TaskGroup,
    Tasks,
    TestCase,
    TestSpec,
    TraceabilityEntry,
    UserStory,
    VerificationSubtask,
)

T = TypeVar("T")

# Files required in every spec folder
_REQUIRED_FILES = ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]

# Regex that matches a ## Intent heading line
_INTENT_HEADING = re.compile(r"^##\s+Intent\s*$", re.MULTILINE)

# Regex that matches any ## heading (to find where the Intent section ends)
_NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)


# ---------------------------------------------------------------------------
# Intent extraction
# ---------------------------------------------------------------------------


def _extract_intent(body: str) -> str:
    """Extract the ## Intent section body from a PRD markdown body.

    Returns the stripped text of the Intent section (the content between the
    ``## Intent`` heading and the next ``##`` heading, or end of string).

    Raises:
        SpecValidationError: If no ``## Intent`` section is found.
    """
    match = _INTENT_HEADING.search(body)
    if match is None:
        raise SpecValidationError(
            "PRD body does not contain a '## Intent' section",
            errors=[],
        )
    # Content starts right after the heading line
    after_heading = body[match.end() :]
    # Find the next ## heading within the remaining text
    next_match = _NEXT_HEADING.search(after_heading)
    if next_match:
        section_body = after_heading[: next_match.start()]
    else:
        section_body = after_heading
    return section_body.strip()


# ---------------------------------------------------------------------------
# PRD loading
# ---------------------------------------------------------------------------


def _load_prd(path: pathlib.Path) -> PRD:
    """Parse prd.md from disk into a PRD dataclass.

    The file must start with a YAML frontmatter block delimited by ``---``
    lines.  The markdown body (everything after the closing ``---``) must
    contain a ``## Intent`` section.

    Args:
        path: Absolute path to ``prd.md``.

    Returns:
        Populated ``PRD`` instance.

    Raises:
        ValueError: For missing/malformed frontmatter delimiters or bad YAML.
        SpecValidationError: If the ``## Intent`` section is absent.
    """
    content = path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Split into frontmatter and body
    # ------------------------------------------------------------------
    if not content.startswith("---"):
        raise ValueError(
            f"{path.name}: does not begin with '---' frontmatter delimiter"
        )

    # Strip the opening "---\n"
    after_open = content[3:]
    if after_open.startswith("\n"):
        after_open = after_open[1:]

    # Find the closing "---" on its own line
    close_match = re.search(r"^---\s*$", after_open, re.MULTILINE)
    if close_match is None:
        raise ValueError(
            f"{path.name}: frontmatter closing '---' delimiter not found"
        )

    yaml_text = after_open[: close_match.start()]
    body_raw = after_open[close_match.end() :]
    # Strip leading newline from body
    body = body_raw.lstrip("\n")

    # ------------------------------------------------------------------
    # Parse YAML frontmatter
    # ------------------------------------------------------------------
    try:
        fm_data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"{path.name}: malformed YAML frontmatter: {exc}"
        ) from exc

    if not isinstance(fm_data, dict):
        raise ValueError(
            f"{path.name}: YAML frontmatter is not a mapping"
        )

    # ------------------------------------------------------------------
    # Validate Intent section present in body
    # ------------------------------------------------------------------
    if not _INTENT_HEADING.search(body):
        raise SpecValidationError(
            f"{path.name}: missing '## Intent' section in body",
            errors=[],
        )

    # ------------------------------------------------------------------
    # Build PRDFrontmatter
    # Use .get() with defaults for all fields so that a partially-formed
    # frontmatter (e.g., during validation testing) loads without KeyError.
    # Schema validation (task group 7) is responsible for catching missing fields.
    # ------------------------------------------------------------------
    frontmatter = PRDFrontmatter(
        spec_id=str(fm_data.get("spec_id", "")),
        spec_name=str(fm_data.get("spec_name", "")),
        title=str(fm_data.get("title", "")),
        status=str(fm_data.get("status", "")),
        created_at=str(fm_data.get("created_at", "")),
        updated_at=str(fm_data.get("updated_at", "")),
        owner=str(fm_data.get("owner", "")),
        source=str(fm_data.get("source", "")),
        supersedes=list(fm_data.get("supersedes") or []),
        tags=list(fm_data.get("tags") or []),
        intent_hash=fm_data.get("intent_hash"),
        schema_version=int(fm_data.get("schema_version") or 0),
    )

    return PRD(frontmatter=frontmatter, body=body)


# ---------------------------------------------------------------------------
# JSON deserialization helpers
# ---------------------------------------------------------------------------


def _deserialize_requirement(data: dict[str, Any]) -> Requirement:
    """Deserialize a requirements.json requirement dict to a Requirement."""
    return Requirement(
        id=data["id"],
        title=data["title"],
        user_story=UserStory(
            role=data["user_story"]["role"],
            goal=data["user_story"]["goal"],
            benefit=data["user_story"]["benefit"],
        ),
        acceptance_criteria=[
            EARSCriterion.from_dict(c) for c in data.get("acceptance_criteria", [])
        ],
        edge_cases=[
            EARSCriterion.from_dict(c) for c in data.get("edge_cases", [])
        ],
    )


def _deserialize_requirements(data: dict[str, Any]) -> Requirements:
    """Deserialize a requirements.json dict to a Requirements dataclass."""
    return Requirements(
        spec_id=str(data["spec_id"]),
        spec_name=str(data["spec_name"]),
        schema_version=int(data["schema_version"]),
        introduction=str(data.get("introduction", "")),
        glossary=dict(data.get("glossary") or {}),
        requirements=[
            _deserialize_requirement(r) for r in data.get("requirements", [])
        ],
        correctness_properties=[
            CorrectnessProperty(
                id=p["id"],
                title=p["title"],
                for_any=p["for_any"],
                invariant=p["invariant"],
                validates=list(p.get("validates", [])),
            )
            for p in data.get("correctness_properties", [])
        ],
        execution_paths=[
            ExecutionPath(
                id=ep["id"],
                title=ep["title"],
                steps=[
                    ExecutionPathStep(actor=s["actor"], action=s["action"])
                    for s in ep.get("steps", [])
                ],
            )
            for ep in data.get("execution_paths", [])
        ],
        error_handling=[
            ErrorHandlingEntry(
                id=eh["id"],
                condition=eh["condition"],
                behavior=eh["behavior"],
                requirement_id=eh["requirement_id"],
            )
            for eh in data.get("error_handling", [])
        ],
    )


def _deserialize_test_spec(data: dict[str, Any]) -> TestSpec:
    """Deserialize a test_spec.json dict to a TestSpec dataclass."""
    coverage_data = data.get("coverage") or {}
    coverage = Coverage(
        requirements_covered=list(coverage_data.get("requirements_covered", [])),
        properties_covered=list(coverage_data.get("properties_covered", [])),
        paths_covered=list(coverage_data.get("paths_covered", [])),
        gaps=list(coverage_data.get("gaps", [])),
    )
    return TestSpec(
        spec_id=str(data["spec_id"]),
        spec_name=str(data["spec_name"]),
        schema_version=int(data["schema_version"]),
        test_cases=[
            TestCase(
                id=tc["id"],
                requirement_id=tc["requirement_id"],
                kind=tc["kind"],
                description=tc["description"],
                preconditions=list(tc.get("preconditions", [])),
                input=dict(tc.get("input") or {}),
                expected=dict(tc.get("expected") or {}),
                assertion_pseudocode=tc.get("assertion_pseudocode", ""),
            )
            for tc in data.get("test_cases", [])
        ],
        property_tests=[
            PropertyTest(
                id=pt["id"],
                property_id=pt["property_id"],
                validates=list(pt.get("validates", [])),
                description=pt["description"],
                for_any_strategy=pt["for_any_strategy"],
                invariant_check=pt["invariant_check"],
            )
            for pt in data.get("property_tests", [])
        ],
        edge_case_tests=[
            EdgeCaseTest(
                id=et["id"],
                requirement_id=et["requirement_id"],
                kind=et["kind"],
                description=et["description"],
                preconditions=list(et.get("preconditions", [])),
                input=dict(et.get("input") or {}),
                expected=dict(et.get("expected") or {}),
                assertion_pseudocode=et.get("assertion_pseudocode", ""),
            )
            for et in data.get("edge_case_tests", [])
        ],
        smoke_tests=[
            SmokeTest(
                id=st["id"],
                execution_path_id=st["execution_path_id"],
                description=st["description"],
                trigger=st["trigger"],
                real_components=list(st.get("real_components", [])),
                mockable=list(st.get("mockable", [])),
                expected_effects=list(st.get("expected_effects", [])),
            )
            for st in data.get("smoke_tests", [])
        ],
        coverage=coverage,
    )


def _deserialize_tasks(data: dict[str, Any]) -> Tasks:
    """Deserialize a tasks.json dict to a Tasks dataclass."""
    task_groups = []
    for tg in data.get("task_groups", []):
        subtasks = []
        for st in tg.get("subtasks", []):
            state_val = st.get("state", "pending")
            state = SubtaskState(state_val)
            subtasks.append(
                Subtask(
                    id=st["id"],
                    title=st["title"],
                    details=list(st.get("details", [])),
                    test_spec_refs=list(st.get("test_spec_refs", [])),
                    requirement_refs=list(st.get("requirement_refs", [])),
                    state=state,
                    optional=bool(st.get("optional", False)),
                )
            )
        verification_data = tg.get("verification", {})
        verification = VerificationSubtask(
            id=verification_data.get("id", f"{tg['id']}.V"),
            checks=list(verification_data.get("checks", [])),
        )
        task_groups.append(
            TaskGroup(
                id=int(tg["id"]),
                kind=str(tg.get("kind", "")),
                title=str(tg["title"]),
                subtasks=subtasks,
                verification=verification,
            )
        )

    traceability = [
        TraceabilityEntry(
            requirement_id=tr["requirement_id"],
            test_spec_id=tr["test_spec_id"],
            task_id=tr["task_id"],
            test_path=tr.get("test_path"),
        )
        for tr in data.get("traceability", [])
    ]

    return Tasks(
        spec_id=str(data["spec_id"]),
        spec_name=str(data["spec_name"]),
        schema_version=int(data["schema_version"]),
        test_commands=dict(data.get("test_commands") or {}),
        dependencies=[
            Dependency(
                spec_id=dep["spec_id"],
                kind=dep["kind"],
            )
            for dep in data.get("dependencies", [])
        ],
        task_groups=task_groups,
        traceability=traceability,
    )


# ---------------------------------------------------------------------------
# Generic JSON loader
# ---------------------------------------------------------------------------

# Dispatch table: target type → deserializer function
_DESERIALIZERS: dict[type, Any] = {
    Requirements: _deserialize_requirements,
    TestSpec: _deserialize_test_spec,
    Tasks: _deserialize_tasks,
}


def _load_json(path: pathlib.Path, target_type: type[T]) -> T:
    """Deserialize a JSON file from disk into the target dataclass type.

    Args:
        path: Path to the JSON file.
        target_type: The dataclass type to deserialize into (Requirements,
            TestSpec, or Tasks).

    Returns:
        Populated instance of ``target_type``.

    Raises:
        ValueError: If the JSON is malformed or the type is unsupported.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{path.name}: cannot read file: {exc}") from exc

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name}: malformed JSON at line {exc.lineno}: {exc.msg}"
        ) from exc

    deserializer = _DESERIALIZERS.get(target_type)
    if deserializer is None:
        raise ValueError(
            f"No deserializer registered for type {target_type.__name__!r}"
        )

    return deserializer(data)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Spec loading entry point
# ---------------------------------------------------------------------------


def load_spec(path: pathlib.Path) -> Spec:
    """Load a spec folder from disk into in-memory dataclass instances.

    Reads all four required files (``prd.md``, ``requirements.json``,
    ``test_spec.json``, ``tasks.json``) and returns a fully-populated
    ``Spec`` aggregate.

    Args:
        path: Path to the spec folder directory.

    Returns:
        Populated ``Spec`` instance.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        NotADirectoryError: If ``path`` exists but is not a directory.
        IncompleteSpecError: If one or more required files are missing.
        ValueError: If a file contains malformed JSON or YAML.
        SpecValidationError: If ``prd.md`` is missing the ``## Intent`` section.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Spec folder does not exist: {path}"
        )
    if not path.is_dir():
        raise NotADirectoryError(
            f"Spec path is not a directory: {path}"
        )

    # Check for missing required files
    missing = [f for f in _REQUIRED_FILES if not (path / f).exists()]
    if missing:
        raise IncompleteSpecError(
            f"Spec folder {path} is missing required files: {', '.join(missing)}",
            missing_files=missing,
        )

    # Load each artifact (also capture raw JSON dicts for schema validation)
    prd = _load_prd(path / "prd.md")
    requirements = _load_json(path / "requirements.json", Requirements)
    test_spec = _load_json(path / "test_spec.json", TestSpec)
    tasks = _load_json(path / "tasks.json", Tasks)

    # Read raw JSON dicts to preserve fields that deserialization strips
    # (e.g., extra properties in EARS criteria that are silently dropped).
    # Best-effort: failure is non-fatal; None falls back to re-serialization.
    def _try_load_raw_json(filepath: pathlib.Path) -> "dict[str, Any] | None":
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except Exception:
            return None

    def _try_load_raw_frontmatter(filepath: pathlib.Path) -> "dict[str, Any] | None":
        """Re-parse only the YAML frontmatter of prd.md as a plain dict."""
        try:
            content = filepath.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None
            after_open = content[3:]
            if after_open.startswith("\n"):
                after_open = after_open[1:]
            close_match = re.search(r"^---\s*$", after_open, re.MULTILINE)
            if close_match is None:
                return None
            yaml_text = after_open[: close_match.start()]
            raw = yaml.safe_load(yaml_text)
            return raw if isinstance(raw, dict) else None
        except Exception:
            return None

    return Spec(
        prd=prd,
        requirements=requirements,
        test_spec=test_spec,
        tasks=tasks,
        _raw_requirements=_try_load_raw_json(path / "requirements.json"),
        _raw_test_spec=_try_load_raw_json(path / "test_spec.json"),
        _raw_tasks=_try_load_raw_json(path / "tasks.json"),
        _raw_frontmatter=_try_load_raw_frontmatter(path / "prd.md"),
    )


__all__ = [
    "_load_prd",
    "_load_json",
    "_extract_intent",
    "load_spec",
]
