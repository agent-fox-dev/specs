# Implementation Plan: afspec Build and Release

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

The implementation follows a test-first approach. Task group 1 writes all failing tests from test_spec.md. Subsequent groups create the infrastructure files (Makefile, workflows, scripts) to make those tests pass. The order is: Makefile + config (foundational, used by CI), CI workflow, release workflow + version validation. The final group performs wiring verification.

## Test Commands

- Spec tests: `go test -count=1 -run 'TestTS04' ./internal/ci/`
- Unit tests: `go test -count=1 -run 'TestTS04|TestProperty' ./internal/ci/`
- Property tests: `go test -count=1 -run 'TestProperty' ./internal/ci/`
- Integration tests: `go test -count=1 -timeout 300s -run 'TestSmoke' ./internal/ci/`
- All tests: `go test -count=1 -timeout 300s ./...`
- Linter: `go vet ./...`

## Tasks

- [x] 1. Write failing spec tests
  - [x] 1.1 Set up test file structure and dependencies
    - Create `internal/ci/ci_test.go` with package declaration and imports
    - Add `gopkg.in/yaml.v3` dependency: `go get gopkg.in/yaml.v3`
    - Create helper function `repoRoot(t)` that finds the repo root from `runtime.Caller(0)` by navigating up two directories
    - Create helper function `parseWorkflow(t, path)` that reads and parses a YAML file into `map[string]interface{}`
    - _Test Spec: all_

  - [x] 1.2 Translate workflow YAML tests (TS-04-1 through TS-04-9, TS-04-22)
    - CI trigger tests (TS-04-1, TS-04-2): parse ci.yml, check `on.push.branches` and `on.pull_request.branches`
    - CI job step tests (TS-04-3, TS-04-4, TS-04-5): verify Go and Python job structure, steps, matrix, runners
    - Release workflow tests (TS-04-6 through TS-04-9): verify release.yml job structure, conditions, steps
    - golangci-lint in CI test (TS-04-22): verify Go job installs/uses golangci-lint
    - Tests MUST fail (workflow files don't exist yet for some, or Makefile structure differs)
    - _Test Spec: TS-04-1 through TS-04-9, TS-04-22_

  - [x] 1.3 Translate Makefile, version, and config tests (TS-04-10 through TS-04-21)
    - Tag format regex tests (TS-04-10, TS-04-11): validate Go and Python tag patterns
    - Version source tests (TS-04-12, TS-04-13): verify version constants/fields exist
    - Makefile target tests (TS-04-14 through TS-04-19): verify targets exist and behave correctly
    - golangci-lint config tests (TS-04-20, TS-04-21): verify `.golangci.yml` structure
    - Tests MUST fail (Makefile targets don't exist yet, config file doesn't exist)
    - _Test Spec: TS-04-10 through TS-04-21_

  - [x] 1.4 Translate edge case tests (TS-04-E1 through TS-04-E7)
    - CI edge cases (TS-04-E1, TS-04-E2): Python job skip condition, no continue-on-error
    - Release edge cases (TS-04-E3, TS-04-E4): version mismatch, build failure order
    - Tag format edge case (TS-04-E5): invalid tag rejection
    - Makefile edge case (TS-04-E6): both languages missing
    - Config edge case (TS-04-E7): golangci.yml existence check
    - Tests MUST fail
    - _Test Spec: TS-04-E1 through TS-04-E7_

  - [x] 1.5 Translate property and smoke tests (TS-04-P1 through TS-04-P4, TS-04-SMOKE-1 through TS-04-SMOKE-4)
    - Property tests using `testing/quick` or table-driven exhaustive tests
    - TS-04-P1: tag pattern exclusivity across generated semver strings
    - TS-04-P2: version extraction correctness with temp files
    - TS-04-P3: Makefile degradation with all present/absent combinations
    - TS-04-P4: CI trigger branch list correctness
    - Smoke tests (TS-04-SMOKE-1 through TS-04-SMOKE-4): full path verification
    - Tests MUST fail
    - _Test Spec: TS-04-P1 through TS-04-P4, TS-04-SMOKE-1 through TS-04-SMOKE-4_

  - [x] 1.V Verify task group 1
    - [x] All spec tests exist and are syntactically valid: `go build ./internal/ci/...` (if ci_test.go has build tag or compiles)
    - [x] All spec tests FAIL (red) — no implementation yet: `go test -count=1 -timeout 300s ./internal/ci/` shows failures
    - [x] No linter warnings introduced: `go vet ./...`

- [x] 2. Makefile targets and golangci-lint configuration
  - [x] 2.1 Update Makefile with language-specific and combined targets
    - Rename existing `test` target to `test-go` and `lint` target to `lint-go`
    - Add `test-python` and `lint-python` targets
    - Add combined `test` (depends on `test-go test-python`) and `lint` (depends on `lint-go lint-python`) targets
    - Update `check` to depend on `lint test` (unchanged dependency, but now `lint` and `test` aggregate both languages)
    - Update `.PHONY` declaration with all new targets
    - Add `golangci-lint run` to `lint-go` target (after `go vet ./...`)
    - _Requirements: 04-REQ-4.1, 04-REQ-4.2, 04-REQ-4.3, 04-REQ-4.4_

  - [x] 2.2 Add graceful degradation logic
    - Wrap `test-go` and `lint-go` in `@if [ -f go.mod ]; then ... else echo "Skipping ..."; fi`
    - Wrap `test-python` and `lint-python` in `@if [ -f pyproject.toml ] && [ -f uv.lock ]; then ... else echo "Skipping ..."; fi`
    - Verify skip messages print "Skipping Go" or "Skipping Python" as appropriate
    - _Requirements: 04-REQ-4.5, 04-REQ-4.6_

  - [x] 2.3 Create `.golangci.yml` configuration
    - Create `.golangci.yml` at repo root
    - Enable `govet` and `staticcheck` linters (with `default: none` per golangci-lint v2 format)
    - _Requirements: 04-REQ-5.1, 04-REQ-5.2_

  - [x] 2.V Verify task group 2
    - [x] Spec tests TS-04-15 through TS-04-19, TS-04-20, TS-04-21 pass
    - [x] Edge case tests TS-04-E6, TS-04-E7 pass
    - [x] Property test TS-04-P3 (Makefile degradation) passes
    - [ ] Spec test TS-04-14 (make test-go/lint-go) — blocked: `go test ./...` fails until ci.yml exists (group 3)
    - [ ] Smoke test TS-04-SMOKE-1 (make check) — blocked: requires workflow files (group 3) and scripts (group 4)
    - [ ] All tests pass — blocked: workflow/script tests still failing (groups 3, 4 not yet implemented)
    - [ ] `make check` passes — blocked: pending groups 3, 4
    - [x] No linter warnings introduced: `go vet ./...` and `golangci-lint run` both clean
    - [x] Requirements 04-REQ-4.1 through 04-REQ-4.6, 04-REQ-4.E1, 04-REQ-5.1, 04-REQ-5.2, 04-REQ-5.E1 met

- [x] 3. CI workflow
  - [x] 3.1 Create `.github/workflows/` directory structure
    - Create `.github/workflows/` directory
    - _Requirements: 04-REQ-1.1_

  - [x] 3.2 Create `ci.yml` with Go and Python jobs
    - Define triggers: `on.push.branches: [main, develop]` and `on.pull_request.branches: [main, develop]`
    - Create `go` job: checkout → setup-go (go-version-file: go.mod) → golangci-lint-action → make lint-go → make test-go
    - Create `python` job: checkout → setup-python (matrix: 3.10, 3.13) → setup-uv → make lint-python → make test-python
    - All jobs use `runs-on: ubuntu-latest`
    - _Requirements: 04-REQ-1.1, 04-REQ-1.2, 04-REQ-1.3, 04-REQ-1.4, 04-REQ-1.5, 04-REQ-5.3_

  - [x] 3.3 Add conditional Python job execution
    - Add `if: hashFiles('pyproject.toml') != ''` to Python job
    - Verify no step uses `continue-on-error: true`
    - _Requirements: 04-REQ-1.E1, 04-REQ-1.E2_

  - [x] 3.V Verify task group 3
    - [x] Spec tests TS-04-1 through TS-04-5, TS-04-22 pass
    - [x] Edge case tests TS-04-E1, TS-04-E2 pass
    - [x] Property test TS-04-P4 (CI trigger correctness) passes
    - [x] Smoke test TS-04-SMOKE-2 (CI structural completeness) passes
    - [ ] All existing tests still pass: `go test -count=1 -timeout 300s ./...` — blocked: release.yml and scripts/check-version.sh pending group 4
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 04-REQ-1.1 through 04-REQ-1.5, 04-REQ-1.E1, 04-REQ-1.E2, 04-REQ-5.3 met

- [ ] 4. Release workflow and version validation
  - [ ] 4.1 Create version validation script
    - Create `scripts/check-version.sh` (bash script)
    - Accept two arguments: language (`go` or `python`) and tag string
    - Go: strip `pkg/afspec/v` prefix from tag, extract `Version` constant from `internal/version/version.go`, compare
    - Python: strip `afspec-v` prefix from tag, extract `version` from `pyproject.toml`, compare
    - Exit 0 on match, exit 1 on mismatch with descriptive stderr message
    - Validate tag format (reject non-semver tags with exit 1)
    - Validate language argument (reject unknown languages with exit 1)
    - Make script executable: `chmod +x scripts/check-version.sh`
    - _Requirements: 04-REQ-2.3, 04-REQ-3.1, 04-REQ-3.2, 04-REQ-3.3, 04-REQ-3.4_

  - [ ] 4.2 Create `release.yml` with Go release job
    - Define triggers: `on.push.tags: ['pkg/afspec/v*', 'afspec-v*']`
    - Add `permissions: contents: write`
    - Create `release-go` job with `if: startsWith(github.ref_name, 'pkg/afspec/v')`
    - Steps: checkout → check-version.sh go → gh release create with --generate-notes
    - _Requirements: 04-REQ-2.1, 04-REQ-2.4_

  - [ ] 4.3 Add Python release job
    - Create `release-python` job with `if: startsWith(github.ref_name, 'afspec-v')`
    - Steps: checkout → setup-python (3.13) → setup-uv → check-version.sh python → uv build → gh release create with dist/* and --generate-notes
    - Ensure `uv build` step precedes `gh release create` (no continue-on-error)
    - _Requirements: 04-REQ-2.2, 04-REQ-2.4_

  - [ ] 4.V Verify task group 4
    - [ ] Spec tests TS-04-6 through TS-04-13 pass
    - [ ] Edge case tests TS-04-E3, TS-04-E4, TS-04-E5 pass
    - [ ] Property tests TS-04-P1 (tag exclusivity), TS-04-P2 (version extraction) pass
    - [ ] Smoke tests TS-04-SMOKE-3 (Go release), TS-04-SMOKE-4 (Python release) pass
    - [ ] All existing tests still pass: `go test -count=1 -timeout 300s ./...`
    - [ ] `make check` still passes: `make check`
    - [ ] No linter warnings introduced: `go vet ./...`
    - [ ] Requirements 04-REQ-2.1 through 04-REQ-2.4, 04-REQ-2.E1, 04-REQ-2.E2, 04-REQ-3.1 through 04-REQ-3.4, 04-REQ-3.E1 met

- [ ] 5. Wiring verification

  - [ ] 5.1 Trace every execution path from design.md end-to-end
    - Path 1 (make check): verify `check` depends on `lint` → `lint-go` + `lint-python`, and `test` → `test-go` + `test-python`
    - Path 2 (CI on push/PR): verify ci.yml triggers are correct, Go job runs make targets, Python job runs make targets
    - Path 3 (Go release): verify release.yml → release-go job → check-version.sh → gh release create
    - Path 4 (Python release): verify release.yml → release-python job → check-version.sh → uv build → gh release create
    - Every path must be live — no stub targets or placeholder steps
    - _Requirements: all_

  - [ ] 5.2 Verify return values propagate correctly
    - `scripts/check-version.sh` exit code is consumed by the release workflow (non-zero exits the job)
    - `make lint-go` and `make test-go` exit codes propagate through `make lint` and `make test` to `make check`
    - Verify no Makefile target silently swallows errors (e.g., `|| true` or missing `set -e`)
    - _Requirements: all_

  - [ ] 5.3 Run the integration smoke tests
    - All TS-04-SMOKE-1 through TS-04-SMOKE-4 tests pass
    - _Test Spec: TS-04-SMOKE-1 through TS-04-SMOKE-4_

  - [ ] 5.4 Stub / dead-code audit
    - Search `scripts/check-version.sh` for: `echo "TODO"`, `exit 0` after a TODO, placeholder logic
    - Search `Makefile` for: targets that are defined but never referenced, placeholder commands
    - Search workflow YAML for: steps with `run: echo` placeholders, commented-out steps
    - Each hit must be justified or replaced with real implementation
    - Document any intentional stubs here with rationale

  - [ ] 5.5 Cross-spec entry point verification
    - Verify `make check` works as the quality gate (called by `config.toml` `quality_gate`)
    - Verify `make test` and `make lint` are usable as standalone entry points
    - Verify `scripts/check-version.sh` is callable from the release workflow
    - Since CI workflows execute on GitHub Actions (not locally), verify structural correctness via YAML inspection (TS-04-SMOKE-2 through TS-04-SMOKE-4)
    - _Requirements: all_

  - [ ] 5.V Verify wiring group
    - [ ] All smoke tests pass: `go test -count=1 -timeout 300s -run 'TestSmoke' ./internal/ci/`
    - [ ] No unjustified stubs remain in touched files
    - [ ] All execution paths from design.md are live (traceable in code/config)
    - [ ] All cross-spec entry points are callable
    - [ ] All existing tests still pass: `go test -count=1 -timeout 300s ./...`
    - [ ] `make check` passes: `make check`

### Checkbox States

| Syntax   | Meaning                |
|----------|------------------------|
| `- [ ]`  | Not started (required) |
| `- [ ]*` | Not started (optional) |
| `- [x]`  | Completed              |
| `- [-]`  | In progress            |
| `- [~]`  | Queued                 |

Tasks are **required by default**. Mark optional tasks with `*` after checkbox: `- [ ]* Optional task`

## Traceability

| Requirement | Test Spec Entry | Implemented By Task | Verified By Test |
|-------------|-----------------|---------------------|------------------|
| 04-REQ-1.1 | TS-04-1 | 3.2 | internal/ci/ci_test.go::TestTS04_01 |
| 04-REQ-1.2 | TS-04-2 | 3.2 | internal/ci/ci_test.go::TestTS04_02 |
| 04-REQ-1.3 | TS-04-3 | 3.2 | internal/ci/ci_test.go::TestTS04_03 |
| 04-REQ-1.4 | TS-04-4 | 3.2, 3.3 | internal/ci/ci_test.go::TestTS04_04 |
| 04-REQ-1.5 | TS-04-5 | 3.2 | internal/ci/ci_test.go::TestTS04_05 |
| 04-REQ-1.E1 | TS-04-E1 | 3.3 | internal/ci/ci_test.go::TestTS04_E01 |
| 04-REQ-1.E2 | TS-04-E2 | 3.2 | internal/ci/ci_test.go::TestTS04_E02 |
| 04-REQ-2.1 | TS-04-6 | 4.2 | internal/ci/ci_test.go::TestTS04_06 |
| 04-REQ-2.2 | TS-04-7 | 4.3 | internal/ci/ci_test.go::TestTS04_07 |
| 04-REQ-2.3 | TS-04-8 | 4.1 | internal/ci/ci_test.go::TestTS04_08 |
| 04-REQ-2.4 | TS-04-9 | 4.2, 4.3 | internal/ci/ci_test.go::TestTS04_09 |
| 04-REQ-2.E1 | TS-04-E3 | 4.1 | internal/ci/ci_test.go::TestTS04_E03 |
| 04-REQ-2.E2 | TS-04-E4 | 4.3 | internal/ci/ci_test.go::TestTS04_E04 |
| 04-REQ-3.1 | TS-04-10 | 4.1 | internal/ci/ci_test.go::TestTS04_10 |
| 04-REQ-3.2 | TS-04-11 | 4.1 | internal/ci/ci_test.go::TestTS04_11 |
| 04-REQ-3.3 | TS-04-12 | 4.1 | internal/ci/ci_test.go::TestTS04_12 |
| 04-REQ-3.4 | TS-04-13 | 4.1 | internal/ci/ci_test.go::TestTS04_13 |
| 04-REQ-3.E1 | TS-04-E5 | 4.1 | internal/ci/ci_test.go::TestTS04_E05 |
| 04-REQ-4.1 | TS-04-14 | 2.1 | internal/ci/ci_test.go::TestTS04_14 |
| 04-REQ-4.2 | TS-04-15 | 2.1 | internal/ci/ci_test.go::TestTS04_15 |
| 04-REQ-4.3 | TS-04-16 | 2.1 | internal/ci/ci_test.go::TestTS04_16 |
| 04-REQ-4.4 | TS-04-17 | 2.1 | internal/ci/ci_test.go::TestTS04_17 |
| 04-REQ-4.5 | TS-04-18 | 2.2 | internal/ci/ci_test.go::TestTS04_18 |
| 04-REQ-4.6 | TS-04-19 | 2.2 | internal/ci/ci_test.go::TestTS04_19 |
| 04-REQ-4.E1 | TS-04-E6 | 2.2 | internal/ci/ci_test.go::TestTS04_E06 |
| 04-REQ-5.1 | TS-04-20 | 2.3 | internal/ci/ci_test.go::TestTS04_20 |
| 04-REQ-5.2 | TS-04-21 | 2.3 | internal/ci/ci_test.go::TestTS04_21 |
| 04-REQ-5.3 | TS-04-22 | 3.2 | internal/ci/ci_test.go::TestTS04_22 |
| 04-REQ-5.E1 | TS-04-E7 | 2.3 | internal/ci/ci_test.go::TestTS04_E07 |
| Property 1 | TS-04-P1 | 4.1 | internal/ci/ci_test.go::TestPropertyP1 |
| Property 2 | TS-04-P2 | 4.1 | internal/ci/ci_test.go::TestPropertyP2 |
| Property 3 | TS-04-P3 | 2.2 | internal/ci/ci_test.go::TestPropertyP3 |
| Property 4 | TS-04-P4 | 3.2 | internal/ci/ci_test.go::TestPropertyP4 |
| Path 1 | TS-04-SMOKE-1 | 2.1 | internal/ci/ci_test.go::TestSmoke1 |
| Path 2 | TS-04-SMOKE-2 | 3.2 | internal/ci/ci_test.go::TestSmoke2 |
| Path 3 | TS-04-SMOKE-3 | 4.2 | internal/ci/ci_test.go::TestSmoke3 |
| Path 4 | TS-04-SMOKE-4 | 4.3 | internal/ci/ci_test.go::TestSmoke4 |

## Notes

- **YAML dependency**: The test file requires `gopkg.in/yaml.v3` for parsing workflow and configuration files. This dependency is added in task group 1 and will also be needed by spec 01 (Go library).
- **Integration test timeouts**: Tests that run `make` targets or shell scripts need a longer timeout (300s) to account for Go compilation and test execution time.
- **Python test skipping**: Tests that validate Python project structure (TS-04-13, TS-04-15) should use `t.Skip()` if `pyproject.toml` doesn't exist yet, since spec 02 may not be implemented.
- **golangci-lint prerequisite**: Makefile integration tests (TS-04-14) and the smoke test (TS-04-SMOKE-1) require `golangci-lint` to be installed locally. Tests should skip with a clear message if the binary is not found.
- **Repo root discovery**: The test helper `repoRoot(t)` uses `runtime.Caller(0)` to find the test file path, then navigates up from `internal/ci/` to reach the repo root. This is a standard Go testing pattern.
