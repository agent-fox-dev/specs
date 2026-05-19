# Errata 04: Makefile Python Target Deviations

**Spec:** `04_build_and_release`  
**Date:** 2026-05-19  
**Status:** Accepted divergence

## Divergence 1: Python targets require `uv.lock` in addition to `pyproject.toml`

**Spec says (04-REQ-4.5):**
> WHILE the Python project structure (`pyproject.toml`) does not exist, THE Makefile's
> Python targets SHALL skip with an informational message and return exit code 0.

**Implementation:**
Python targets (`test-python`, `lint-python`) skip when either `pyproject.toml` or
`uv.lock` is absent.

**Reason:**
The dev tools (pytest, ruff, mypy) are declared as optional dependencies under
`[project.optional-dependencies]`. A bare `pyproject.toml` without `uv.lock` means the
project has not been locked, and `uv run` would create a fresh venv without the dev tools,
causing the commands to fail. Requiring `uv.lock` ensures the environment is properly
set up before running Python checks. The property test (TS-04-P3) generates minimal
`pyproject.toml` files without `uv.lock`, and the graceful skip prevents spurious failures.

## Divergence 2: `--all-extras` flag added to `uv run` invocations

**Spec says (04-REQ-4.2, 04-REQ-1.4):**
> `uv run pytest -q`, `uv run ruff check`, `uv run mypy afspec/`

**Implementation:**
> `uv run --all-extras pytest -q`, `uv run --all-extras ruff check`, `uv run --all-extras mypy afspec/`

**Reason:**
pytest, ruff, and mypy are declared as optional `dev` extras in `pyproject.toml`.
Without `--all-extras`, `uv run` syncs only the main dependencies and the commands
fail with "Failed to spawn: `<tool>`". The `--all-extras` flag ensures all optional
dependency groups (including `dev`) are synced before the tool is invoked.
