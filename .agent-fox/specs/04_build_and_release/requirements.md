# Requirements Document

## Introduction

This document specifies the requirements for the build, test, and release infrastructure of the afspec monorepo. The infrastructure consists of GitHub Actions workflows for continuous integration and release automation, a Makefile for local development commands, and supporting configuration files. The system enables developers to run a unified quality gate locally and ensures automated testing and release processes in CI.

## Glossary

- **CI**: Continuous Integration — automated testing and linting triggered by code changes.
- **semver**: Semantic Versioning — versioning scheme using `MAJOR.MINOR.PATCH` format per https://semver.org/.
- **wheel**: Python binary distribution format (`.whl` file) built by packaging tools.
- **sdist**: Python source distribution format (`.tar.gz` file) containing source code and metadata.
- **Go module proxy**: Google's proxy service (`proxy.golang.org`) that indexes Go modules from public repositories via git tags.
- **golangci-lint**: Aggregated Go linter that runs multiple linters (govet, staticcheck, etc.) in parallel.
- **tag**: Git tag used to mark a release point. This spec uses two tag patterns for independent versioning.
- **uv**: Python package manager and build tool used for dependency management and building distributions.
- **quality gate**: A set of checks (lint + test) that must pass before code can be merged.
- **graceful skip**: A target or job that detects a missing prerequisite and exits successfully with an informational message instead of failing.
- **ubuntu-latest**: GitHub Actions runner image label specifying the latest Ubuntu LTS version available on GitHub-hosted runners.
- **artifacts**: Build output files (wheels, sdists, archives) attached to a GitHub release for distribution.
- **matrix strategy**: GitHub Actions feature that runs a job multiple times with different parameter combinations (e.g., multiple Python versions).

## Requirements

### Requirement 1: Continuous Integration Workflow

**User Story:** As a developer, I want automated tests and linting to run on every push and pull request to integration branches, so that regressions are caught before code is merged.

#### Acceptance Criteria

1. [04-REQ-1.1] WHEN a push occurs to the `main` or `develop` branch, THE CI workflow SHALL run the Go CI job and the Python CI job.
2. [04-REQ-1.2] WHEN a pull request targets the `main` or `develop` branch, THE CI workflow SHALL run the Go CI job and the Python CI job.
3. [04-REQ-1.3] THE CI workflow's Go job SHALL execute `go test -count=1 ./...`, `go vet ./...`, and `golangci-lint run` using the Go version specified in `go.mod` AND exit the job with status 0 (success) or non-zero (failure).
4. [04-REQ-1.4] THE CI workflow's Python job SHALL execute `uv run pytest -q`, `uv run ruff check`, and `uv run mypy afspec/` on Python 3.10 and 3.13 via a matrix strategy AND exit the job with status 0 (success) or non-zero (failure).
5. [04-REQ-1.5] THE CI workflow SHALL run all jobs on `ubuntu-latest` runners.

#### Edge Cases

1. [04-REQ-1.E1] IF the Python project structure (`pyproject.toml`) does not exist in the repository, THEN THE CI workflow's Python job SHALL skip without failing the overall workflow.
2. [04-REQ-1.E2] IF any test or lint step within a CI job fails, THEN THE CI workflow SHALL report the failure and the job SHALL exit with a non-zero status code.

### Requirement 2: Release Workflow

**User Story:** As a maintainer, I want releases to be created automatically when I push a version tag, so that distribution artifacts are consistently built and published.

#### Acceptance Criteria

1. [04-REQ-2.1] WHEN a tag matching the pattern `pkg/afspec/v*` is pushed, THE release workflow SHALL create a GitHub release with the tag name as the release title and auto-generated release notes.
2. [04-REQ-2.2] WHEN a tag matching the pattern `afspec-v*` is pushed, THE release workflow SHALL build a Python wheel and sdist using `uv build`, create a GitHub release, and attach the built artifacts to the release.
3. [04-REQ-2.3] WHEN a release tag is pushed, THE release workflow SHALL execute a version validation step that extracts the version from the tag and from the library code, and SHALL fail the job with a non-zero exit code if the versions do not match.
4. [04-REQ-2.4] THE release workflow SHALL use a single workflow file (`release.yml`) with conditional jobs that dispatch based on the tag pattern.

#### Edge Cases

1. [04-REQ-2.E1] IF the tag version does not match the version in the library code, THEN THE release workflow SHALL fail with an error message identifying the expected and actual versions.
2. [04-REQ-2.E2] IF the Python build step (`uv build`) fails, THEN THE release workflow SHALL fail without creating a GitHub release.

### Requirement 3: Version Management

**User Story:** As a maintainer, I want independent version tracks for Go and Python libraries with a consistent scheme, so that consumers can pin to specific versions of each library.

#### Acceptance Criteria

1. [04-REQ-3.1] THE Go library SHALL use git tags in the format `pkg/afspec/v{MAJOR}.{MINOR}.{PATCH}` where MAJOR, MINOR, and PATCH are non-negative integers conforming to semver.
2. [04-REQ-3.2] THE Python library SHALL use git tags in the format `afspec-v{MAJOR}.{MINOR}.{PATCH}` where MAJOR, MINOR, and PATCH are non-negative integers conforming to semver.
3. [04-REQ-3.3] THE Go library version source of truth SHALL be the `Version` constant in `internal/version/version.go`.
4. [04-REQ-3.4] THE Python library version source of truth SHALL be the `version` field under `[project]` in `pyproject.toml`.

#### Edge Cases

1. [04-REQ-3.E1] IF a pushed tag does not conform to the expected semver format for its tag pattern, THEN THE release workflow SHALL reject the tag and fail with a descriptive error message.

### Requirement 4: Makefile Build Targets

**User Story:** As a developer, I want unified Makefile targets for testing and linting both languages, so that I can run the quality gate with a single command.

#### Acceptance Criteria

1. [04-REQ-4.1] THE Makefile SHALL provide `test-go` and `lint-go` targets that run Go tests (`go test -count=1 ./...`) and Go linting (`go vet ./...` and `golangci-lint run`) respectively AND return exit code 0 on success.
2. [04-REQ-4.2] THE Makefile SHALL provide `test-python` and `lint-python` targets that run Python tests (`uv run pytest -q`) and Python linting (`uv run ruff check` and `uv run mypy afspec/`) respectively AND return exit code 0 on success.
3. [04-REQ-4.3] THE Makefile SHALL provide a `test` target that runs both `test-go` and `test-python`, and a `lint` target that runs both `lint-go` and `lint-python`.
4. [04-REQ-4.4] THE Makefile SHALL provide a `check` target that runs `lint` followed by `test` as the quality gate AND return exit code 0 if and only if all enabled checks pass.
5. [04-REQ-4.5] WHILE the Python project structure (`pyproject.toml`) does not exist, THE Makefile's Python targets (`test-python`, `lint-python`) SHALL skip with an informational message and return exit code 0.
6. [04-REQ-4.6] WHILE the Go project structure (`go.mod`) does not exist, THE Makefile's Go targets (`test-go`, `lint-go`) SHALL skip with an informational message and return exit code 0.

#### Edge Cases

1. [04-REQ-4.E1] IF both Go and Python project structures are absent, THEN THE Makefile `check` target SHALL exit with code 0 and print a warning message indicating no languages are configured.

### Requirement 5: Go Linter Configuration

**User Story:** As a developer, I want a standardized Go linter configuration, so that code quality checks are consistent across local development and CI environments.

#### Acceptance Criteria

1. [04-REQ-5.1] THE repository SHALL include a `.golangci.yml` configuration file at the repository root.
2. [04-REQ-5.2] THE `.golangci.yml` SHALL enable the `govet` and `staticcheck` linters at minimum.
3. [04-REQ-5.3] THE CI workflow's Go job SHALL install `golangci-lint` and execute it as part of the lint step.

#### Edge Cases

1. [04-REQ-5.E1] IF `.golangci.yml` is missing or empty, THEN `golangci-lint` SHALL fall back to its default configuration without failing.
