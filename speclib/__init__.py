"""speclib — AI-powered spec creation tool.

Re-exports key types from submodules for convenient access.
"""

from __future__ import annotations

from speclib.auth import create_client
from speclib.config import SpecToolConfig, load_config
from speclib.errors import ConfigError, SpeclibError

__all__ = [
    "ConfigError",
    "SpeclibError",
    "SpecToolConfig",
    "create_client",
    "load_config",
]
