# afspec Build and Release Setup

## Intent

Create a common build, test, and release infrastructure for the afspec monorepo using GitHub Actions, semantic versioning, and GitHub-only distribution for both the Go and Python libraries.

## Goals

- GitHub Actions CI workflow that tests and lints both Go and Python on every push to `main`/`develop` and every PR targeting those branches.
- GitHub Actions release workflow for creating versioned releases, triggered by tag pushes.
- Semantic versioning scheme for the monorepo with independent version tracks for Go and Python libraries.
- Makefile updates to support monorepo operations (test/lint/build for both languages) with graceful degradation when a language is not yet set up.
- Distribution via GitHub releases only (no PyPI, Go module proxy via standard GitHub tags).

## Non-Goals

- No PyPI publishing.
- No Docker images or container builds.
- No deployment pipelines (the libraries are consumed as dependencies, not deployed).
- No nightly or scheduled builds.
- No code coverage reporting services.

## Background

The afspec monorepo contains two libraries: a Go library at the repository root (module `github.com/agent-fox/afspec`, per spec 01 design decision 1) and a Python library at `afspec/`. Both need CI pipelines for testing and linting, and a release workflow for creating versioned distributions. The Go library is distributed as a Go module (via GitHub tags and the Go module proxy). The Python library is distributed as source via GitHub releases (wheel/sdist attached to release assets).

## Design Decisions

1. **CI system**: GitHub Actions. Two workflow files: `ci.yml` for continuous integration, `release.yml` for releases.
2. **Go CI**: `go test ./...`, `go vet ./...`, `golangci-lint run`. Runs on the Go version specified in `go.mod`.
3. **Python CI**: `uv run pytest -q`, `uv run ruff check`, `uv run mypy afspec/`. Runs on Python 3.10 and 3.13 (minimum supported and latest stable).
4. **Versioning**: Semantic versioning (semver). The Go library uses tags prefixed with `pkg/afspec/v` (e.g., `pkg/afspec/v1.0.0`) for Go module proxy compatibility. The Python library uses tags prefixed with `afspec-v` (e.g., `afspec-v1.0.0`). Version strings are embedded in library code.
5. **Release workflow**: Triggered by tag push. Creates a GitHub release. Python releases attach wheel and sdist artifacts built by `uv build`. Go releases rely on GitHub's auto-generated source archives and the Go module proxy for distribution.
6. **Makefile**: Updated with targets for both languages — `make test-go`, `make test-python`, `make test` (both), `make lint-go`, `make lint-python`, `make lint` (both), `make check` (lint + test for both).
7. **Python build**: Uses `uv` for building wheel and sdist. `pyproject.toml` for metadata (owned by spec 02).
8. **CI trigger scope**: CI runs on pushes to `main` and `develop` branches, and on all pull requests targeting `main` or `develop`. Feature branches are local-only (per project conventions), so CI does not trigger on arbitrary branch pushes. Rationale: focuses CI resources on integration branches while catching regressions before merge.
9. **CI runner OS**: Ubuntu-latest only. Both libraries are platform-independent (no CGo, no native extensions), so cross-platform CI adds cost without value. Rationale: minimizes CI minutes and complexity.
10. **Go version matrix**: Single version matching the `go.mod` directive (currently 1.26.x). The `go.mod` `go` directive is the authoritative minimum version. Rationale: the module already constrains the minimum; testing on older versions would fail due to `go.mod` requirements. A single version keeps CI fast.
11. **Python version matrix**: Two versions — 3.10 (minimum supported per spec 02) and 3.13 (latest stable). Rationale: testing minimum and latest catches both forward and backward compatibility issues without excessive matrix expansion.
12. **golangci-lint**: Included in CI with a `.golangci.yml` configuration file at the repo root. Uses the `golangci/golangci-lint-action` GitHub Action for installation and caching. Default rule set with `govet` and `staticcheck` enabled. Rationale: starting with a linter from day one prevents lint debt accumulation.
13. **Release workflow tag routing**: A single `release.yml` with two jobs — `release-go` (runs when tag matches `pkg/afspec/v*`) and `release-python` (runs when tag matches `afspec-v*`). Each job uses an `if` condition on the tag name. Rationale: one file is easier to maintain than two, and tag-based conditionals are straightforward.
14. **Version source of truth**: Version is authored in code. Go: `internal/version/version.go` contains a `Version` constant. Python: `pyproject.toml` `[project].version` field. The release workflow validates that the pushed tag's version matches the code version before creating the release. If they mismatch, the workflow fails with an error. Rationale: code-is-source-of-truth prevents version drift; tag validation catches mistakes early.
15. **Makefile graceful degradation**: Each language-specific Makefile target checks for the presence of prerequisites before running. `make test-python` and `make lint-python` check for `pyproject.toml` and skip with an informational message if not found. `make test-go` and `make lint-go` check for `go.mod`. The combined targets (`make test`, `make lint`, `make check`) aggregate results from both, skipping absent languages. Rationale: allows `make check` to pass in the early project phase when only Go is set up, without breaking the quality gate.
16. **pyproject.toml ownership**: This spec does NOT create `pyproject.toml`. It is owned by spec 02 (Python library). This spec's CI and release workflows assume `pyproject.toml` exists when Python targets are invoked. The Makefile handles its absence gracefully (per decision 15).
17. **Go release artifacts**: No additional artifacts beyond GitHub's auto-generated source archives. The Go module proxy indexes the tag automatically. The release job creates a GitHub release with generated release notes only. Rationale: Go distribution is handled entirely by the module proxy; additional archives add maintenance burden without value.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 02_python_library | 1 | 3 | Python CI job runs meaningfully after pyproject.toml exists (created in spec 02 group 1); spec 04 handles absence gracefully via 04-REQ-1.E1, so this is a soft dependency |

## Source

Source: Input provided by Michael Kuehl via interactive prompt
