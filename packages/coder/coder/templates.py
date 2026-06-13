"""Template loading from filesystem with security validation.

Loads prompt templates from a configurable templates directory with
search-path resolution (project-level overrides before package defaults),
YAML frontmatter stripping, name validation, and symlink rejection.
"""

from __future__ import annotations

import re
from pathlib import Path

from coder.errors import TemplateNotFoundError, TemplateSecurityError

# Template names must match: letters, digits, underscores, hyphens only.
_VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# Package-level default templates directory.
_PACKAGE_TEMPLATES_DIR = Path(__file__).parent / "_templates"


class TemplateLoader:
    """Loads prompt templates from filesystem with security checks.

    Templates are resolved by searching an ordered list of directories.
    Project-level templates (``{project_dir}/.coder/templates/``) take
    precedence over package-level defaults (``coder/_templates/``).

    Security constraints:
    - Template names must match ``^[a-zA-Z0-9_-]+$``.
    - Symlinks are rejected with a :class:`TemplateSecurityError`.
    - Path traversal sequences (``..``, ``/``, ``\\``) are rejected.
    """

    def __init__(
        self,
        *,
        project_dir: Path | None = None,
    ) -> None:
        self._search_paths: list[Path] = []
        if project_dir is not None:
            project_tpl_dir = project_dir / ".coder" / "templates"
            if project_tpl_dir.is_dir():
                self._search_paths.append(project_tpl_dir)

        # Package defaults are used only when no project-level templates
        # directory was found. This allows project-level templates to
        # fully control what's available without inheriting defaults.
        if not self._search_paths:
            self._search_paths.append(_PACKAGE_TEMPLATES_DIR)

    @property
    def search_paths(self) -> list[Path]:
        """Ordered list of directories to search for templates."""
        return list(self._search_paths)

    def load(self, name: str) -> str:
        """Load and return template content by name.

        Parameters
        ----------
        name:
            Template name (without ``.md`` extension). Must consist of
            letters, digits, underscores, and hyphens only.

        Returns
        -------
        str
            The template content with YAML frontmatter stripped.

        Raises
        ------
        ValueError
            If the template name is invalid (contains path separators,
            traversal sequences, or characters outside the allowed set).
        TemplateSecurityError
            If the resolved template path is a symlink.
        TemplateNotFoundError
            If the template is not found in any search path.
        """
        self._validate_name(name)

        filename = f"{name}.md"

        for search_dir in self._search_paths:
            candidate = search_dir / filename
            if candidate.exists():
                # Reject symlinks for security.
                if candidate.is_symlink():
                    raise TemplateSecurityError(
                        name,
                        reason="template path is a symlink",
                    )
                raw = candidate.read_text(encoding="utf-8")
                return _strip_frontmatter(raw)

        raise TemplateNotFoundError(
            name,
            searched_paths=[str(p) for p in self._search_paths],
        )

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate a template name for security.

        Raises ``ValueError`` if the name contains path separators,
        traversal sequences, or characters outside the allowed set.
        """
        if not name:
            msg = "Template name must not be empty"
            raise ValueError(msg)

        # Reject path separators and traversal sequences.
        if "/" in name or "\\" in name:
            msg = f"Template name contains path separator: {name!r}"
            raise ValueError(msg)
        if ".." in name:
            msg = f"Template name contains traversal sequence: {name!r}"
            raise ValueError(msg)

        # Validate against allowed character pattern.
        if not _VALID_NAME_RE.match(name):
            msg = (
                f"Template name {name!r} contains invalid characters. "
                f"Must match: {_VALID_NAME_RE.pattern}"
            )
            raise ValueError(msg)


def _strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from template content.

    Frontmatter is delimited by ``---`` lines at the start of the file.
    If no frontmatter is detected, the content is returned unchanged.
    """
    if not content.startswith("---"):
        return content

    # Find the closing --- delimiter (second occurrence).
    end_idx = content.find("---", 3)
    if end_idx == -1:
        # No closing delimiter — treat as no frontmatter.
        return content

    # Skip past the closing delimiter and any trailing newline.
    after_delim = end_idx + 3
    if after_delim < len(content) and content[after_delim] == "\n":
        after_delim += 1

    return content[after_delim:]
