"""Tool definitions for structured output via Anthropic tool use.

Defines the JSON-schema-based tool specs (submit_assessment,
submit_prd_update, submit_artifact) that constrain the model's output
shape when using tool_use for structured output.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tool definition constants
# ---------------------------------------------------------------------------

SUBMIT_ASSESSMENT_TOOL: dict[str, Any] = {
    "name": "submit_assessment",
    "description": "Submit a structured assessment of the PRD quality.",
    "input_schema": {
        "type": "object",
        "required": ["quality", "summary", "gaps", "questions"],
        "properties": {
            "quality": {
                "type": "string",
                "enum": ["ready", "needs_refinement", "incomplete"],
                "description": "Overall quality verdict for the PRD.",
            },
            "summary": {
                "type": "string",
                "description": (
                    "Brief summary of the PRD quality and main findings."
                ),
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of identified gaps or weaknesses in the PRD."
                ),
            },
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "text", "context", "options", "required"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for the question.",
                        },
                        "text": {
                            "type": "string",
                            "description": "The question text.",
                        },
                        "context": {
                            "type": "string",
                            "description": "Why this question matters.",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Suggested answer options (may be empty)."
                            ),
                        },
                        "required": {
                            "type": "boolean",
                            "description": (
                                "Whether the user must answer this question."
                            ),
                        },
                    },
                },
                "description": (
                    "Questions for the user to improve the PRD."
                ),
            },
        },
    },
}

SUBMIT_PRD_UPDATE_TOOL: dict[str, Any] = {
    "name": "submit_prd_update",
    "description": (
        "Submit the updated PRD text incorporating user answers."
    ),
    "input_schema": {
        "type": "object",
        "required": ["updated_prd"],
        "properties": {
            "updated_prd": {
                "type": "string",
                "description": (
                    "The full updated PRD text (body only, no frontmatter)."
                ),
            },
        },
    },
}

SUBMIT_ARTIFACT_TOOL: dict[str, Any] = {
    "name": "submit_artifact",
    "description": "Submit the generated artifact content as JSON.",
    "input_schema": {
        "type": "object",
        "required": ["artifact_name", "content"],
        "properties": {
            "artifact_name": {
                "type": "string",
                "enum": ["requirements", "test_spec", "tasks"],
                "description": "The name of the artifact being submitted.",
            },
            "content": {
                "type": "object",
                "description": (
                    "The artifact content conforming to the "
                    "spec-format v1.2 JSON schema."
                ),
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def assessment_tools() -> list[dict[str, Any]]:
    """Return tool definitions for PRD assessment.

    Defines the submit_assessment tool.
    """
    return [SUBMIT_ASSESSMENT_TOOL]


def refinement_tools() -> list[dict[str, Any]]:
    """Return tool definitions for PRD refinement.

    Defines submit_prd_update and submit_assessment tools.
    """
    return [SUBMIT_PRD_UPDATE_TOOL, SUBMIT_ASSESSMENT_TOOL]


def artifact_tool(artifact_name: str) -> list[dict[str, Any]]:
    """Return tool definition for generating one artifact.

    Defines the submit_artifact tool with schema appropriate
    for the given artifact_name.

    Args:
        artifact_name: One of "requirements", "test_spec", "tasks".
    """
    return [SUBMIT_ARTIFACT_TOOL]
