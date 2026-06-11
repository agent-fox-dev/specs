# Erratum: Spec 01 Scaffold Tests Updated for Monorepo

## Context

Spec 10 (monorepo restructure) moved the CLI entry point from the root
`pyproject.toml` (`af-spec = "speclib.cli:main"`) to
`packages/spec-cli/pyproject.toml` (`spec = "spec_cli.cli:main"`).

Runtime dependencies were also split across packages:
- `packages/speclib/pyproject.toml`: afspec, anthropic, pyyaml
- `packages/spec-cli/pyproject.toml`: speclib, click, rich

## Affected Tests

### `test_ts01_1_package_installable` (TS-01-1)

**Original:** Checked root `pyproject.toml` for `af-spec` entry in
`[project.scripts]`.

**Updated:** Checks `packages/spec-cli/pyproject.toml` for `spec` entry
in `[project.scripts]`.

### `test_ts01_2_runtime_deps` (TS-01-2)

**Original:** Checked root `pyproject.toml` for afspec, anthropic,
click, pyyaml in `[project] dependencies`.

**Updated:** Checks `packages/speclib/pyproject.toml` for afspec,
anthropic, pyyaml and `packages/spec-cli/pyproject.toml` for click.

## Justification

The monorepo restructure (spec 10) supersedes the single-package
structure assumed by spec 01. The test intent (verifying that the
project is installable with correct dependencies and entry points) is
preserved; only the locations being checked changed to match the new
package layout.
