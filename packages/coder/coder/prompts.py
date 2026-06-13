"""Layered prompt assembly.

Composes system prompts from three layers: a base agent profile,
a persona-specific profile, and task context. Uses Python's
``string.Template`` for safe variable substitution.
"""

from __future__ import annotations

import string

from coder.errors import TemplateNotFoundError
from coder.templates import TemplateLoader


class PromptAssembler:
    """Composes system prompts from multiple template layers.

    The assembly process concatenates up to three layers, separated by
    double newlines:

    1. **Base profile** — loaded from ``agent.md`` (optional; skipped if
       the template does not exist).
    2. **Persona profile** — loaded from ``{persona}.md`` (required).
    3. **Task context** — provided directly as a string.

    Variable substitution uses ``$variable`` placeholders via Python's
    :class:`string.Template` with safe substitution (unrecognized
    placeholders are left unchanged).
    """

    def __init__(self, loader: TemplateLoader) -> None:
        self._loader = loader

    def assemble(
        self,
        *,
        persona: str,
        task_context: str,
        variables: dict[str, str] | None = None,
    ) -> str:
        """Compose a 3-layer prompt from base + persona + context.

        Parameters
        ----------
        persona:
            Name of the persona template to load (e.g., ``"coder"``).
        task_context:
            The task-specific context string (layer 3).
        variables:
            Optional mapping of placeholder names to values for
            ``$variable`` substitution across templates. Extra keys
            not present in any template are silently ignored.

        Returns
        -------
        str
            The assembled prompt string with layers separated by
            double newlines.
        """
        vars_dict = variables or {}
        layers: list[str] = []

        # Layer 1: Base profile (optional).
        try:
            base_content = self._loader.load("agent")
            base_content = self._substitute(base_content, vars_dict)
            layers.append(base_content)
        except TemplateNotFoundError:
            pass  # Base profile is optional.

        # Layer 2: Persona profile (required).
        persona_content = self._loader.load(persona)
        persona_content = self._substitute(persona_content, vars_dict)
        layers.append(persona_content)

        # Layer 3: Task context (provided directly).
        task_context = self._substitute(task_context, vars_dict)
        layers.append(task_context)

        return "\n\n".join(layers)

    @staticmethod
    def _substitute(template_text: str, variables: dict[str, str]) -> str:
        """Apply safe variable substitution to template text.

        Uses :meth:`string.Template.safe_substitute` so that
        unrecognized ``$placeholders`` are left unchanged.
        """
        if not variables:
            return template_text
        return string.Template(template_text).safe_substitute(variables)
