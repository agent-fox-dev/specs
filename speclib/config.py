"""Configuration loading from YAML and environment variables.

Reads ``~/.af/settings.yaml`` and environment variables to produce a
``SpecToolConfig``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from speclib.errors import ConfigError


@dataclass
class SpecToolConfig:
    """Resolved configuration for the spec tool.

    Attributes:
        model: The Anthropic model to use.
        auth_method: Authentication method (``api_key``, ``bedrock``, or ``vertex``).
        api_key: Anthropic API key (for ``api_key`` auth method).
        vertex_project: GCP project ID (for ``vertex`` auth method).
        vertex_region: GCP region (for ``vertex`` auth method).
    """

    model: str = "claude-sonnet-4-6"
    auth_method: str = "api_key"
    api_key: str | None = None
    vertex_project: str | None = None
    vertex_region: str | None = None


def load_config() -> SpecToolConfig:
    """Load configuration from ``~/.af/settings.yaml`` and env vars.

    Reads the ``spec_tool`` section from the settings file, then applies
    environment variable overrides. Returns a ``SpecToolConfig`` with
    resolved values.

    Raises:
        ConfigError: If the settings file contains invalid YAML.
    """
    config = SpecToolConfig()

    # Step 1: Read settings.yaml if it exists
    settings_path = Path.home() / ".af" / "settings.yaml"
    if settings_path.exists():
        _load_from_yaml(config, settings_path)

    # Step 2: Apply environment variable overrides
    _apply_env_overrides(config)

    return config


def _load_from_yaml(config: SpecToolConfig, settings_path: Path) -> None:
    """Parse settings.yaml and populate config from the spec_tool section.

    Args:
        config: The config object to populate.
        settings_path: Path to the settings.yaml file.

    Raises:
        ConfigError: If the file contains invalid YAML.
    """
    try:
        data = yaml.safe_load(settings_path.read_text())
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML in {settings_path}: {exc}"
        raise ConfigError(msg) from exc

    if data is None:
        # Empty file — use defaults
        return

    if not isinstance(data, dict):
        actual_type = type(data).__name__
        msg = (
            f"Invalid YAML in {settings_path}: "
            f"expected a mapping, got {actual_type}"
        )
        raise ConfigError(msg)

    spec_tool = data.get("spec_tool")
    if spec_tool is None:
        return

    if not isinstance(spec_tool, dict):
        return

    # Read top-level spec_tool keys
    if "model" in spec_tool:
        config.model = str(spec_tool["model"])

    # Read nested auth section
    auth = spec_tool.get("auth")
    if isinstance(auth, dict):
        if "method" in auth:
            config.auth_method = str(auth["method"])
        if "api_key" in auth:
            config.api_key = str(auth["api_key"])
        if "vertex_project" in auth:
            config.vertex_project = str(auth["vertex_project"])
        if "vertex_region" in auth:
            config.vertex_region = str(auth["vertex_region"])


def _apply_env_overrides(config: SpecToolConfig) -> None:
    """Override config values from environment variables.

    Environment variables take precedence over YAML values:
    - AF_SPEC_MODEL -> config.model
    - AF_SPEC_AUTH -> config.auth_method
    - ANTHROPIC_API_KEY -> config.api_key
    - AF_SPEC_VERTEX_PROJECT -> config.vertex_project
    - AF_SPEC_VERTEX_REGION -> config.vertex_region
    """
    env_model = os.environ.get("AF_SPEC_MODEL")
    if env_model is not None:
        config.model = env_model

    env_auth = os.environ.get("AF_SPEC_AUTH")
    if env_auth is not None:
        config.auth_method = env_auth

    env_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_api_key is not None:
        config.api_key = env_api_key

    env_vertex_project = os.environ.get("AF_SPEC_VERTEX_PROJECT")
    if env_vertex_project is not None:
        config.vertex_project = env_vertex_project

    env_vertex_region = os.environ.get("AF_SPEC_VERTEX_REGION")
    if env_vertex_region is not None:
        config.vertex_region = env_vertex_region
