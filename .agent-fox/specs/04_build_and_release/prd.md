# afspec Build and Release Setup

## Intent

Create a common build, test, and release infrastructure for the afspec monorepo using GitHub Actions, semantic versioning, and GitHub-only distribution for both the Go and Python libraries.

## Goals

- GitHub Actions CI workflow that tests and lints both Go and Python on every push and PR.
- GitHub Actions release workflow for creating versioned releases.
- Semantic versioning scheme for the monorepo with independent version tracks for Go and Python libraries.
- Makefile updates to support monorepo operations (test/lint/build for both languages).
- Distribution via GitHub releases only (no PyPI, Go module proxy via standard GitHub tags).

## Non-Goals

- No PyPI publishing.
- No Docker images or container builds.
- No deployment pipelines (the libraries are consumed as dependencies, not deployed).
- No nightly or scheduled builds.
- No code coverage reporting services.

## Background

The afspec monorepo contains two libraries: a Go library at `pkg/afspec/` and a Python library at `afspec/`. Both need CI pipelines for testing and linting, and a release workflow for creating versioned distributions. The Go library is distributed as a Go module (via GitHub tags and the Go module proxy). The Python library is distributed as source via GitHub releases (wheel/sdist attached to release assets).

## Design Decisions

1. **CI system**: GitHub Actions. Two workflow files: `ci.yml` for continuous integration, `release.yml` for releases.
2. **Go CI**: `go test ./...`, `go vet ./...`, `golangci-lint` (if configured). Runs on Go 1.22+ matrix.
3. **Python CI**: `pytest`, `ruff check`, `mypy` (type checking). Runs on Python 3.10+ matrix.
4. **Versioning**: Semantic versioning (semver). The Go library uses tags prefixed with `pkg/afspec/v` (e.g., `pkg/afspec/v1.0.0`) for Go module proxy compatibility. The Python library uses tags prefixed with `afspec-v` (e.g., `afspec-v1.0.0`). Version strings are embedded in library code.
5. **Release workflow**: Triggered by tag push. Builds assets, creates a GitHub release, attaches artifacts (Go: source archive; Python: wheel and sdist).
6. **Makefile**: Updated with targets for both languages — `make test-go`, `make test-python`, `make test` (both), `make lint-go`, `make lint-python`, `make lint` (both), `make check` (lint + test for both).
7. **Python build**: Uses `uv` for building wheel and sdist. `pyproject.toml` for metadata.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 01_golang_library | 0 | 1 | Needs Go library source structure to set up CI (From Group TBD — upstream spec not yet planned; using sentinel 0) |
| 02_python_library | 0 | 1 | Needs Python library source structure to set up CI (From Group TBD — upstream spec not yet planned; using sentinel 0) |
| 03_library_documentation | 0 | 3 | Needs docs structure for docs build/validation in CI (From Group TBD — upstream spec not yet planned; using sentinel 0) |

## Source

Source: Input provided by Michael Kuehl via interactive prompt
