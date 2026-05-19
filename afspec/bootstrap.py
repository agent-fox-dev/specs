"""Bootstrap mode for incremental spec creation.

Implements task group 11: BootstrapSpec context manager for writing spec
artifacts one at a time with per-file schema validation, deferring cross-file
validation until all four files are present.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import yaml

from afspec.exceptions import IncompleteSpecError, SpecValidationError
from afspec.models import PRD, Requirements, Spec, Tasks, TestSpec, ValidationError

_REQUIRED_FILES = ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]


class BootstrapSpec:
    """Context manager for incremental spec creation.

    Allows writing spec artifacts one at a time.  Per-file schema validation
    runs on every write.  Cross-file validation is deferred until the context
    manager exits (or ``finalize()`` is called explicitly).

    Usage::

        with BootstrapSpec(spec_root, "05", "my_feature") as bs:
            bs.write_prd(prd_str)
            bs.write_requirements(requirements_str)
            bs.write_test_spec(test_spec_str)
            bs.write_tasks(tasks_str)
        spec = bs.result
    """

    def __init__(self, spec_root: pathlib.Path, spec_id: str, spec_name: str) -> None:
        self._spec_root = spec_root
        self._spec_id = spec_id
        self._spec_name = spec_name
        self._folder = spec_root / f"{spec_id}_{spec_name}"
        self._result: Spec | None = None

    def __enter__(self) -> BootstrapSpec:
        """Create the spec folder and return self.

        Raises:
            FileExistsError: If the spec folder already exists.
        """
        if self._folder.exists():
            raise FileExistsError(
                f"Spec folder already exists: {self._folder}. "
                "BootstrapSpec will not overwrite an existing spec folder."
            )
        self._folder.mkdir(parents=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Finalize the spec on normal exit; propagate all exceptions."""
        if exc_type is None:
            # Normal exit: run finalize (may raise IncompleteSpecError or SpecValidationError)
            self._finalize()
        # Do not suppress exceptions — let them propagate

    def write_prd(self, prd: PRD | str) -> None:
        """Write prd.md to the spec folder with per-file validation.

        Accepts either a :class:`~afspec.models.PRD` dataclass (serialized via
        the saver) or a raw string (written verbatim).

        Per-file validation:
        - YAML frontmatter validated against ``prd-frontmatter.v1.json``.
        - Presence of a ``## Intent`` section verified.

        Raises:
            SpecValidationError: If frontmatter schema or Intent section check fails.
        """
        if isinstance(prd, str):
            content = prd
        else:
            from afspec.saver import _serialize_prd

            content = _serialize_prd(prd)

        prd_path = self._folder / "prd.md"
        prd_path.write_text(content, encoding="utf-8")

        # Per-file validation (raises on failure)
        self._validate_prd_content(content)

    def write_requirements(self, requirements: Requirements | str) -> None:
        """Write requirements.json to the spec folder with per-file schema validation.

        Accepts either a :class:`~afspec.models.Requirements` dataclass or a raw
        JSON string.

        Raises:
            SpecValidationError: If schema validation fails.
        """
        if isinstance(requirements, str):
            content = requirements
        else:
            from afspec.saver import _requirements_to_dict, _serialize_json

            content = _serialize_json(_requirements_to_dict(requirements))

        req_path = self._folder / "requirements.json"
        req_path.write_text(content, encoding="utf-8")
        self._validate_json_content(content, "requirements.json")

    def write_test_spec(self, test_spec: TestSpec | str) -> None:
        """Write test_spec.json to the spec folder with per-file schema validation.

        Accepts either a :class:`~afspec.models.TestSpec` dataclass or a raw
        JSON string.

        Raises:
            SpecValidationError: If schema validation fails.
        """
        if isinstance(test_spec, str):
            content = test_spec
        else:
            from afspec.saver import _serialize_json, _test_spec_to_dict

            content = _serialize_json(_test_spec_to_dict(test_spec))

        ts_path = self._folder / "test_spec.json"
        ts_path.write_text(content, encoding="utf-8")
        self._validate_json_content(content, "test_spec.json")

    def write_tasks(self, tasks: Tasks | str) -> None:
        """Write tasks.json to the spec folder with per-file schema validation.

        Accepts either a :class:`~afspec.models.Tasks` dataclass or a raw
        JSON string.

        Raises:
            SpecValidationError: If schema validation fails.
        """
        if isinstance(tasks, str):
            content = tasks
        else:
            from afspec.saver import _serialize_json, _tasks_to_dict

            content = _serialize_json(_tasks_to_dict(tasks))

        tasks_path = self._folder / "tasks.json"
        tasks_path.write_text(content, encoding="utf-8")
        self._validate_json_content(content, "tasks.json")

    # ------------------------------------------------------------------
    # Per-file validation helpers
    # ------------------------------------------------------------------

    def _validate_prd_content(self, content: str) -> None:
        """Validate PRD markdown: frontmatter schema + Intent section presence.

        Raises:
            SpecValidationError: On any validation failure.
        """
        if not content.startswith("---"):
            raise SpecValidationError(
                "prd.md must start with YAML frontmatter (---)",
                errors=[
                    ValidationError(
                        file="prd.md",
                        path="/",
                        rule="schema",
                        message="prd.md must start with YAML frontmatter (---)",
                        severity="error",
                    )
                ],
            )

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise SpecValidationError(
                "prd.md frontmatter is not properly closed with ---",
                errors=[],
            )

        fm_yaml = parts[1]
        body = parts[2]

        # Parse YAML frontmatter
        try:
            fm_dict = yaml.safe_load(fm_yaml) or {}
        except yaml.YAMLError as e:
            raise SpecValidationError(
                f"prd.md frontmatter YAML parse error: {e}",
                errors=[],
            )

        if not isinstance(fm_dict, dict):
            fm_dict = {}

        # Schema validation of frontmatter
        from afspec.validator import validate_dict_against_schema

        errors = validate_dict_against_schema("prd.md", fm_dict)
        if errors:
            raise SpecValidationError(
                f"prd.md schema validation failed: {errors[0].message}",
                errors=list(errors),
            )

        # Intent section check
        if not re.search(r"^##\s+Intent\s*$", body, re.MULTILINE):
            raise SpecValidationError(
                "prd.md does not contain a '## Intent' section",
                errors=[
                    ValidationError(
                        file="prd.md",
                        path="/",
                        rule="intent-section",
                        message="PRD body does not contain a '## Intent' section",
                        severity="error",
                    )
                ],
            )

    def _validate_json_content(self, content: str, file_name: str) -> None:
        """Parse JSON content and validate against the bundled schema.

        Raises:
            SpecValidationError: On parse error or schema violation.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise SpecValidationError(
                f"{file_name}: JSON parse error: {e}",
                errors=[],
            )

        from afspec.validator import validate_dict_against_schema

        errors = validate_dict_against_schema(file_name, data)
        if errors:
            raise SpecValidationError(
                f"{file_name} schema validation failed: {errors[0].message}",
                errors=list(errors),
            )

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def _finalize(self) -> None:
        """Check all files written, load spec, run full validation, set result.

        Raises:
            IncompleteSpecError: If not all four files have been written.
            SpecValidationError: If the completed spec fails validation.
        """
        missing = [f for f in _REQUIRED_FILES if not (self._folder / f).exists()]
        if missing:
            raise IncompleteSpecError(
                f"Bootstrap spec is missing files: {missing}",
                missing_files=missing,
            )

        from afspec.loader import load_spec
        from afspec.validator import validate

        spec = load_spec(self._folder)
        errors = validate(spec)
        if errors:
            blocking = [e for e in errors if e.severity == "error"]
            if blocking:
                raise SpecValidationError(
                    f"Spec validation failed with {len(blocking)} error(s)",
                    errors=list(errors),
                )

        self._result = spec

    # ------------------------------------------------------------------
    # Public property
    # ------------------------------------------------------------------

    @property
    def result(self) -> Spec:
        """Return the completed Spec after finalization.

        Raises:
            RuntimeError: If the context manager has not yet exited normally.
        """
        if self._result is None:
            raise RuntimeError(
                "BootstrapSpec.result is only available after the context manager "
                "has exited normally (all four files written and validated)."
            )
        return self._result


__all__ = ["BootstrapSpec"]
