"""Validation logic for afspec.

Implements schema loading (task group 3) and full validation pipeline
(task group 7): schema validation, ID format checks, and cross-file
integrity rules.
"""
from __future__ import annotations

import dataclasses
import importlib.resources
import json
import re
from typing import Any

import jsonschema
import jsonschema.exceptions

from afspec.models import Spec, ValidationError

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = 1

# Mapping from file name to bundled schema file name
_SCHEMA_FILE_MAP: dict[str, str] = {
    "requirements.json": "requirements.v1.json",
    "test_spec.json": "test_spec.v1.json",
    "tasks.json": "tasks.v1.json",
    "prd.md": "prd-frontmatter.v1.json",
    "prd-frontmatter": "prd-frontmatter.v1.json",
    # Also allow direct schema file names
    "requirements.v1.json": "requirements.v1.json",
    "test_spec.v1.json": "test_spec.v1.json",
    "tasks.v1.json": "tasks.v1.json",
    "prd-frontmatter.v1.json": "prd-frontmatter.v1.json",
}

# Fields to check for glossary crosscheck (per spec-format.md §9.2 rule 6)
_GLOSSARY_CHECKED_FIELDS: frozenset[str] = frozenset(
    ["action", "trigger", "condition", "error_condition", "state", "feature", "for_any", "invariant"]
)

# Regex to extract backtick-wrapped terms
_BACKTICK_RE = re.compile(r"`([^`]+)`")


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


def _load_schema(schema_name: str) -> dict[str, Any]:
    """Load a bundled JSON Schema file by name.

    Args:
        schema_name: The schema file name (e.g., 'requirements.v1.json').

    Returns:
        Parsed JSON Schema dict.
    """
    package = importlib.resources.files("afspec.schemas")
    schema_file = package.joinpath(schema_name)
    text = schema_file.read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def _get_schema_for_file(file_name: str) -> dict[str, Any] | None:
    """Return the bundled schema for the given file name, or None if unknown."""
    schema_file = _SCHEMA_FILE_MAP.get(file_name)
    if schema_file is None:
        return None
    return _load_schema(schema_file)


# ---------------------------------------------------------------------------
# JSON Schema error processing
# ---------------------------------------------------------------------------


def _flatten_jsonschema_errors(
    errors: list[jsonschema.exceptions.ValidationError],
) -> list[jsonschema.exceptions.ValidationError]:
    """Recursively flatten composite validator errors (oneOf/anyOf/allOf context).

    For each error with a non-empty ``context`` (produced by oneOf/anyOf/allOf),
    the sub-errors are recursively expanded.  Leaf errors (those without context)
    are yielded directly.  This ensures that specific field-level errors from
    oneOf alternatives (e.g., "Additional properties are not allowed") are
    surfaced rather than the generic "is not valid under any of the given schemas"
    umbrella message.
    """
    result: list[jsonschema.exceptions.ValidationError] = []
    for error in errors:
        if error.context:
            result.extend(_flatten_jsonschema_errors(list(error.context)))
        else:
            result.append(error)
    return result


def _jsonschema_errors_to_validation_errors(
    file_name: str,
    js_errors: list[jsonschema.exceptions.ValidationError],
) -> list[ValidationError]:
    """Convert jsonschema ValidationError instances to afspec ValidationError instances.

    Flattens composite errors (oneOf/anyOf) so specific leaf errors surface.
    Deduplicates by (path, message) to avoid repetitive output.
    Includes the JSON path prefix in the message for easier identification of
    which field caused the problem.
    """
    flat_errors = _flatten_jsonschema_errors(js_errors)

    seen: set[tuple[str, str]] = set()
    result: list[ValidationError] = []

    for err in flat_errors:
        # Build a JSON path string from the error path
        path_parts: list[str] = []
        for part in err.absolute_path:
            if isinstance(part, int):
                path_parts.append(f"[{part}]")
            else:
                path_parts.append(str(part))
        path = "/" + "/".join(path_parts) if path_parts else ""

        # Include path in message so field names are always visible to callers
        raw_message = err.message
        message = f"{path}: {raw_message}" if path else raw_message

        key = (path, raw_message)
        if key in seen:
            continue
        seen.add(key)

        result.append(
            ValidationError(
                file=file_name,
                path=path,
                rule="schema",
                message=message,
                severity="error",
            )
        )
    return result


def validate_dict_against_schema(
    file_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate a dict against the bundled JSON Schema for the given file.

    Args:
        file_name: The artifact file name (e.g., 'requirements.json').
        data: The dict to validate.

    Returns:
        List of ValidationError instances (empty if valid).
    """
    schema = _get_schema_for_file(file_name)
    if schema is None:
        return []

    validator = jsonschema.Draft7Validator(schema)
    js_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return _jsonschema_errors_to_validation_errors(file_name, list(js_errors))


# ---------------------------------------------------------------------------
# PRD frontmatter serialization for validation
# ---------------------------------------------------------------------------


def _frontmatter_to_dict(fm: Any) -> dict[str, Any]:
    """Convert a PRDFrontmatter dataclass to a JSON-compatible dict."""
    return {
        "spec_id": fm.spec_id,
        "spec_name": fm.spec_name,
        "title": fm.title,
        "status": fm.status,
        "created_at": fm.created_at,
        "updated_at": fm.updated_at,
        "owner": fm.owner,
        "source": fm.source,
        "supersedes": list(fm.supersedes),
        "tags": list(fm.tags),
        "intent_hash": fm.intent_hash,
        "schema_version": fm.schema_version,
    }


# ---------------------------------------------------------------------------
# Schema validation (task group 7)
# ---------------------------------------------------------------------------


def _validate_schemas(spec: Spec) -> list[ValidationError]:
    """Run per-file JSON Schema validation against bundled schemas.

    Prefers raw JSON dicts preserved at load time (available via spec._raw_*),
    which retain fields that deserialization may strip (e.g., unknown EARS
    properties).  Falls back to re-serializing the in-memory dataclasses when
    raw dicts are unavailable (e.g., for specs constructed programmatically).

    Returns:
        List of ValidationError instances (empty if all files are schema-valid).
    """
    from afspec.saver import _requirements_to_dict, _tasks_to_dict, _test_spec_to_dict

    errors: list[ValidationError] = []

    # Validate requirements.json
    req_dict: dict[str, Any] = (
        spec._raw_requirements
        if spec._raw_requirements is not None
        else _requirements_to_dict(spec.requirements)
    )
    errors.extend(validate_dict_against_schema("requirements.json", req_dict))

    # Validate test_spec.json
    ts_dict: dict[str, Any] = (
        spec._raw_test_spec
        if spec._raw_test_spec is not None
        else _test_spec_to_dict(spec.test_spec)
    )
    errors.extend(validate_dict_against_schema("test_spec.json", ts_dict))

    # Validate tasks.json
    tasks_dict: dict[str, Any] = (
        spec._raw_tasks
        if spec._raw_tasks is not None
        else _tasks_to_dict(spec.tasks)
    )
    errors.extend(validate_dict_against_schema("tasks.json", tasks_dict))

    # Validate prd.md frontmatter
    fm_dict: dict[str, Any] = (
        spec._raw_frontmatter
        if spec._raw_frontmatter is not None
        else _frontmatter_to_dict(spec.prd.frontmatter)
    )
    errors.extend(validate_dict_against_schema("prd.md", fm_dict))

    return errors


# ---------------------------------------------------------------------------
# Cross-file integrity validation (task group 7)
# ---------------------------------------------------------------------------


def _validate_cross_file(spec: Spec) -> list[ValidationError]:
    """Run cross-file integrity validation (seven rules from spec-format.md §9.2).

    Rules:
      1. Every requirement_id referenced in test_spec, tasks traceability, and
         requirements error_handling must exist as a criterion/edge-case ID.
      2. Every acceptance criterion and edge case must have a test case.
      3. Every correctness property must have a property test.
      4. Every execution path must have a smoke test.
      5. Every test_spec_id referenced in tasks must exist in test_spec.
      6. Every backtick-wrapped term in checked fields must be in the glossary.
      7. spec_id and spec_name must be consistent across all four files.

    Returns:
        List of ValidationError instances (empty if no violations found).
    """
    errors: list[ValidationError] = []

    # ------------------------------------------------------------------
    # Build lookup sets
    # ------------------------------------------------------------------

    # All criterion IDs (acceptance_criteria + edge_cases) from requirements
    all_criterion_ids: set[str] = set()
    for req in spec.requirements.requirements:
        for c in req.acceptance_criteria:
            all_criterion_ids.add(c.id)
        for ec in req.edge_cases:
            all_criterion_ids.add(ec.id)

    # All test spec IDs (all four test artifact types)
    all_ts_ids: set[str] = set()
    for tc in spec.test_spec.test_cases:
        all_ts_ids.add(tc.id)
    for pt in spec.test_spec.property_tests:
        all_ts_ids.add(pt.id)
    for ect in spec.test_spec.edge_case_tests:
        all_ts_ids.add(ect.id)
    for st in spec.test_spec.smoke_tests:
        all_ts_ids.add(st.id)

    # Criterion IDs covered by test_spec test_cases and edge_case_tests
    covered_by_tests: set[str] = set()
    for tc in spec.test_spec.test_cases:
        covered_by_tests.add(tc.requirement_id)
    for ect in spec.test_spec.edge_case_tests:
        covered_by_tests.add(ect.requirement_id)

    # Property IDs covered by property tests
    covered_properties: set[str] = {pt.property_id for pt in spec.test_spec.property_tests}

    # Execution path IDs covered by smoke tests
    covered_paths: set[str] = {st.execution_path_id for st in spec.test_spec.smoke_tests}

    # Glossary keys for term lookup
    glossary_keys: set[str] = set(spec.requirements.glossary.keys())

    # ------------------------------------------------------------------
    # Rule 1: requirement_id existence
    # ------------------------------------------------------------------

    def _check_req_id_exists(req_id: str, context: str) -> None:
        """Emit an error if req_id does not exist in all_criterion_ids."""
        if req_id and req_id not in all_criterion_ids:
            errors.append(
                ValidationError(
                    file="test_spec.json",
                    path=context,
                    rule="integrity-1",
                    message=(
                        f"requirement_id '{req_id}' referenced in {context} "
                        f"does not exist as a criterion or edge case in requirements.json"
                    ),
                    severity="error",
                )
            )

    for tc in spec.test_spec.test_cases:
        _check_req_id_exists(
            tc.requirement_id, f"test_spec.json/test_cases (id={tc.id})"
        )
    for ect in spec.test_spec.edge_case_tests:
        _check_req_id_exists(
            ect.requirement_id, f"test_spec.json/edge_case_tests (id={ect.id})"
        )
    for eh in spec.requirements.error_handling:
        _check_req_id_exists(
            eh.requirement_id, f"requirements.json/error_handling (id={eh.id})"
        )
    for tr in spec.tasks.traceability:
        _check_req_id_exists(tr.requirement_id, "tasks.json/traceability")

    # ------------------------------------------------------------------
    # Rule 2: criterion/edge case coverage
    # ------------------------------------------------------------------

    for req in spec.requirements.requirements:
        for c in req.acceptance_criteria:
            if c.id not in covered_by_tests:
                errors.append(
                    ValidationError(
                        file="requirements.json",
                        path=f"requirements/{req.id}/acceptance_criteria",
                        rule="integrity-2",
                        message=(
                            f"Acceptance criterion '{c.id}' is uncovered: "
                            f"no test case in test_spec.json references it"
                        ),
                        severity="error",
                    )
                )
        for ec in req.edge_cases:
            if ec.id not in covered_by_tests:
                errors.append(
                    ValidationError(
                        file="requirements.json",
                        path=f"requirements/{req.id}/edge_cases",
                        rule="integrity-2",
                        message=(
                            f"Edge case '{ec.id}' is uncovered: "
                            f"no test case in test_spec.json references it"
                        ),
                        severity="error",
                    )
                )

    # ------------------------------------------------------------------
    # Rule 3: correctness property coverage
    # ------------------------------------------------------------------

    for cp in spec.requirements.correctness_properties:
        if cp.id not in covered_properties:
            errors.append(
                ValidationError(
                    file="requirements.json",
                    path="correctness_properties",
                    rule="integrity-3",
                    message=(
                        f"Correctness property '{cp.id}' has no corresponding "
                        f"property_test in test_spec.json"
                    ),
                    severity="error",
                )
            )

    # ------------------------------------------------------------------
    # Rule 4: execution path coverage
    # ------------------------------------------------------------------

    for ep in spec.requirements.execution_paths:
        if ep.id not in covered_paths:
            errors.append(
                ValidationError(
                    file="requirements.json",
                    path="execution_paths",
                    rule="integrity-4",
                    message=(
                        f"Execution path '{ep.id}' has no corresponding "
                        f"smoke_test in test_spec.json"
                    ),
                    severity="error",
                )
            )

    # ------------------------------------------------------------------
    # Rule 5: test_spec_id existence
    # ------------------------------------------------------------------

    def _check_ts_id_exists(ts_id: str, context: str) -> None:
        """Emit an error if ts_id does not exist in all_ts_ids."""
        if ts_id and ts_id not in all_ts_ids:
            errors.append(
                ValidationError(
                    file="tasks.json",
                    path=context,
                    rule="integrity-5",
                    message=(
                        f"test_spec_id '{ts_id}' referenced in {context} "
                        f"does not exist in test_spec.json"
                    ),
                    severity="error",
                )
            )

    for tr in spec.tasks.traceability:
        _check_ts_id_exists(tr.test_spec_id, "tasks.json/traceability")
    for tg in spec.tasks.task_groups:
        for subtask in tg.subtasks:
            for ts_ref in subtask.test_spec_refs:
                _check_ts_id_exists(
                    ts_ref,
                    f"tasks.json/task_groups/{tg.id}/subtasks/{subtask.id}/test_spec_refs",
                )

    # ------------------------------------------------------------------
    # Rule 6: glossary crosscheck
    # ------------------------------------------------------------------

    def _extract_backtick_terms(text: str) -> list[str]:
        return _BACKTICK_RE.findall(text)

    def _check_glossary_terms(field_name: str, value: str, context: str) -> None:
        """Check backtick-wrapped terms in value against the glossary."""
        if field_name not in _GLOSSARY_CHECKED_FIELDS:
            return
        for term in _extract_backtick_terms(value):
            if term not in glossary_keys:
                errors.append(
                    ValidationError(
                        file="requirements.json",
                        path=context,
                        rule="integrity-6",
                        message=(
                            f"Term '{term}' used in {field_name} field at {context} "
                            f"is not defined in the glossary"
                        ),
                        severity="error",
                    )
                )

    # Check EARS criteria fields
    for req in spec.requirements.requirements:
        for criteria_list, criteria_type in [
            (req.acceptance_criteria, "acceptance_criteria"),
            (req.edge_cases, "edge_cases"),
        ]:
            for c in criteria_list:
                ctx = f"requirements/{req.id}/{criteria_type}/{c.id}"
                _check_glossary_terms("action", c.action, ctx)
                if hasattr(c, "trigger"):
                    _check_glossary_terms("trigger", c.trigger, ctx)
                if hasattr(c, "condition"):
                    _check_glossary_terms("condition", c.condition, ctx)
                if hasattr(c, "error_condition"):
                    _check_glossary_terms("error_condition", c.error_condition, ctx)
                if hasattr(c, "state"):
                    _check_glossary_terms("state", c.state, ctx)
                if hasattr(c, "feature"):
                    _check_glossary_terms("feature", c.feature, ctx)

    # Check correctness property fields
    for cp in spec.requirements.correctness_properties:
        ctx = f"correctness_properties/{cp.id}"
        _check_glossary_terms("for_any", cp.for_any, ctx)
        _check_glossary_terms("invariant", cp.invariant, ctx)

    # Check error handling condition fields
    for eh in spec.requirements.error_handling:
        ctx = f"error_handling/{eh.id}"
        _check_glossary_terms("condition", eh.condition, ctx)

    # ------------------------------------------------------------------
    # Rule 7: spec_id / spec_name consistency across all four files
    # ------------------------------------------------------------------

    prd_spec_id = spec.prd.frontmatter.spec_id
    prd_spec_name = spec.prd.frontmatter.spec_name

    for file_name, file_spec_id, file_spec_name in [
        ("requirements.json", spec.requirements.spec_id, spec.requirements.spec_name),
        ("test_spec.json", spec.test_spec.spec_id, spec.test_spec.spec_name),
        ("tasks.json", spec.tasks.spec_id, spec.tasks.spec_name),
    ]:
        if file_spec_id != prd_spec_id:
            errors.append(
                ValidationError(
                    file=file_name,
                    path="spec_id",
                    rule="integrity-7",
                    message=(
                        f"spec_id is inconsistent: {file_name} has '{file_spec_id}' "
                        f"but prd.md has '{prd_spec_id}'"
                    ),
                    severity="error",
                )
            )
        if file_spec_name != prd_spec_name:
            errors.append(
                ValidationError(
                    file=file_name,
                    path="spec_name",
                    rule="integrity-7",
                    message=(
                        f"spec_name is inconsistent: {file_name} has '{file_spec_name}' "
                        f"but prd.md has '{prd_spec_name}'"
                    ),
                    severity="error",
                )
            )

    return errors


# ---------------------------------------------------------------------------
# Full validation entry point (task group 7)
# ---------------------------------------------------------------------------


def validate(spec: Spec) -> list[ValidationError]:
    """Run full validation: schema, ID format, and cross-file integrity checks.

    Aggregates errors from all three validation layers:
      - Layer 1: Per-file JSON Schema validation
      - Layer 2: ID format validation (pattern, spec_id consistency, positivity)
      - Layer 3: Cross-file integrity (seven rules)

    Args:
        spec: The loaded spec to validate.

    Returns:
        List of ValidationError instances (empty if fully valid).
    """
    from afspec.ids import check_sequential, validate_id

    errors: list[ValidationError] = []

    # ------------------------------------------------------------------
    # Layer 1: Schema validation
    # ------------------------------------------------------------------
    errors.extend(_validate_schemas(spec))

    # ------------------------------------------------------------------
    # Layer 2: ID format validation
    # ------------------------------------------------------------------
    spec_id = spec.prd.frontmatter.spec_id

    def _add_id_errors(id_str: str, file_name: str) -> None:
        for e in validate_id(id_str, spec_id):
            errors.append(dataclasses.replace(e, file=file_name))

    # Requirement IDs (and their criteria)
    req_ids: list[str] = []
    for req in spec.requirements.requirements:
        _add_id_errors(req.id, "requirements.json")
        req_ids.append(req.id)
        for c in req.acceptance_criteria:
            _add_id_errors(c.id, "requirements.json")
        for ec in req.edge_cases:
            _add_id_errors(ec.id, "requirements.json")

    # Sequential check on requirement IDs
    for e in check_sequential(req_ids):
        errors.append(dataclasses.replace(e, file="requirements.json"))

    # Correctness property IDs
    for cp in spec.requirements.correctness_properties:
        _add_id_errors(cp.id, "requirements.json")

    # Execution path IDs
    for ep in spec.requirements.execution_paths:
        _add_id_errors(ep.id, "requirements.json")

    # Error handling IDs
    for eh in spec.requirements.error_handling:
        _add_id_errors(eh.id, "requirements.json")

    # Test spec IDs
    for tc in spec.test_spec.test_cases:
        _add_id_errors(tc.id, "test_spec.json")
    for pt in spec.test_spec.property_tests:
        _add_id_errors(pt.id, "test_spec.json")
    for ect in spec.test_spec.edge_case_tests:
        _add_id_errors(ect.id, "test_spec.json")
    for smoke_test in spec.test_spec.smoke_tests:
        _add_id_errors(smoke_test.id, "test_spec.json")

    # Tasks subtask IDs (no spec_id component — validate_id returns [] immediately)
    for tg in spec.tasks.task_groups:
        for subtask in tg.subtasks:
            _add_id_errors(subtask.id, "tasks.json")

    # ------------------------------------------------------------------
    # Layer 3: Cross-file integrity
    # ------------------------------------------------------------------
    errors.extend(_validate_cross_file(spec))

    return errors
