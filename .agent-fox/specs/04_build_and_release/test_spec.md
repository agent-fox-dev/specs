# Test Specification: afspec Build and Release

## Overview

This test specification defines test contracts for the build and release infrastructure. Tests validate GitHub Actions workflow YAML structure, Makefile target behavior, version validation logic, and linter configuration. All tests are implemented as Go test functions in `internal/ci/ci_test.go`, using YAML parsing for static analysis of workflow files and `os/exec` for integration testing of Makefile targets and shell scripts.

## Test Cases

### TS-04-1: CI triggers on push to main/develop

**Requirement:** 04-REQ-1.1
**Type:** unit
**Description:** Verify that ci.yml triggers on pushes to `main` and `develop` branches.

**Preconditions:**
- `.github/workflows/ci.yml` exists and is valid YAML.

**Input:**
- Parsed YAML structure of ci.yml.

**Expected:**
- `on.push.branches` contains both `"main"` and `"develop"`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
ASSERT "main" IN ci["on"]["push"]["branches"]
ASSERT "develop" IN ci["on"]["push"]["branches"]
```

### TS-04-2: CI triggers on PR to main/develop

**Requirement:** 04-REQ-1.2
**Type:** unit
**Description:** Verify that ci.yml triggers on pull requests targeting `main` and `develop`.

**Preconditions:**
- `.github/workflows/ci.yml` exists and is valid YAML.

**Input:**
- Parsed YAML structure of ci.yml.

**Expected:**
- `on.pull_request.branches` contains both `"main"` and `"develop"`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
ASSERT "main" IN ci["on"]["pull_request"]["branches"]
ASSERT "develop" IN ci["on"]["pull_request"]["branches"]
```

### TS-04-3: Go CI job steps

**Requirement:** 04-REQ-1.3
**Type:** unit
**Description:** Verify the Go CI job contains required steps for testing and linting.

**Preconditions:**
- `.github/workflows/ci.yml` exists with a Go job.

**Input:**
- Parsed YAML structure of ci.yml, Go job definition.

**Expected:**
- Job has steps using `actions/checkout`, `actions/setup-go` (with `go-version-file: go.mod`), golangci-lint installation, and `make lint-go`, `make test-go` run steps.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
go_job = ci["jobs"]["go"]
step_uses = [s["uses"] for s in go_job["steps"] if "uses" in s]
step_runs = [s["run"] for s in go_job["steps"] if "run" in s]
ASSERT any(u.startswith("actions/checkout") for u in step_uses)
ASSERT any(u.startswith("actions/setup-go") for u in step_uses)
ASSERT "make lint-go" IN step_runs OR "make test-go" IN step_runs
```

### TS-04-4: Python CI job steps

**Requirement:** 04-REQ-1.4
**Type:** unit
**Description:** Verify the Python CI job contains required steps and uses a version matrix.

**Preconditions:**
- `.github/workflows/ci.yml` exists with a Python job.

**Input:**
- Parsed YAML structure of ci.yml, Python job definition.

**Expected:**
- Job has a matrix strategy with `python-version` containing `"3.10"` and `"3.13"`.
- Job has steps using `actions/setup-python` and `astral-sh/setup-uv`.
- Job has run steps for `make lint-python` and `make test-python`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
py_job = ci["jobs"]["python"]
versions = py_job["strategy"]["matrix"]["python-version"]
ASSERT "3.10" IN versions
ASSERT "3.13" IN versions
step_runs = [s["run"] for s in py_job["steps"] if "run" in s]
ASSERT "make lint-python" IN step_runs
ASSERT "make test-python" IN step_runs
```

### TS-04-5: CI runs on ubuntu-latest

**Requirement:** 04-REQ-1.5
**Type:** unit
**Description:** Verify all CI jobs use `ubuntu-latest` runners.

**Preconditions:**
- `.github/workflows/ci.yml` exists.

**Input:**
- Parsed YAML structure of ci.yml.

**Expected:**
- Every job in ci.yml has `runs-on: ubuntu-latest`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
FOR job IN ci["jobs"].values():
    ASSERT job["runs-on"] == "ubuntu-latest"
```

### TS-04-6: Go release job creates GitHub release

**Requirement:** 04-REQ-2.1
**Type:** unit
**Description:** Verify the release workflow has a Go release job that creates a GitHub release.

**Preconditions:**
- `.github/workflows/release.yml` exists.

**Input:**
- Parsed YAML structure of release.yml.

**Expected:**
- A job exists with an `if` condition matching `pkg/afspec/v*` tags.
- The job has a step that runs `gh release create`.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
go_job = rel["jobs"]["release-go"]
ASSERT "pkg/afspec/v" IN go_job["if"]
step_runs = [s["run"] for s in go_job["steps"] if "run" in s]
ASSERT any("gh release create" in r for r in step_runs)
```

### TS-04-7: Python release job builds and uploads artifacts

**Requirement:** 04-REQ-2.2
**Type:** unit
**Description:** Verify the release workflow has a Python release job that builds wheel/sdist and creates a release with artifacts.

**Preconditions:**
- `.github/workflows/release.yml` exists.

**Input:**
- Parsed YAML structure of release.yml.

**Expected:**
- A job exists with an `if` condition matching `afspec-v*` tags.
- The job has a step running `uv build`.
- The job has a step running `gh release create` with `dist/*` artifacts.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
py_job = rel["jobs"]["release-python"]
ASSERT "afspec-v" IN py_job["if"]
step_runs = [s["run"] for s in py_job["steps"] if "run" in s]
ASSERT any("uv build" in r for r in step_runs)
ASSERT any("gh release create" in r AND "dist/" in r for r in step_runs)
```

### TS-04-8: Release workflow validates version

**Requirement:** 04-REQ-2.3
**Type:** unit
**Description:** Verify both release jobs call the version validation script before creating the release.

**Preconditions:**
- `.github/workflows/release.yml` exists.

**Input:**
- Parsed YAML structure of release.yml.

**Expected:**
- Both `release-go` and `release-python` jobs have a step running `scripts/check-version.sh` before the `gh release create` step.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
FOR job_name IN ["release-go", "release-python"]:
    steps = rel["jobs"][job_name]["steps"]
    check_idx = find_step_index(steps, "check-version.sh")
    release_idx = find_step_index(steps, "gh release create")
    ASSERT check_idx < release_idx
```

### TS-04-9: Single release workflow file

**Requirement:** 04-REQ-2.4
**Type:** unit
**Description:** Verify the release workflow uses a single file with both Go and Python jobs.

**Preconditions:**
- `.github/workflows/` directory exists.

**Input:**
- List of files in `.github/workflows/`.

**Expected:**
- Exactly one release workflow file (`release.yml`).
- The file contains both `release-go` and `release-python` jobs.

**Assertion pseudocode:**
```
files = list_files(".github/workflows/")
ASSERT "release.yml" IN files
ASSERT NOT any(f.startswith("release-") AND f != "release.yml" for f in files)
rel = parse_yaml(".github/workflows/release.yml")
ASSERT "release-go" IN rel["jobs"]
ASSERT "release-python" IN rel["jobs"]
```

### TS-04-10: Go tag format validation

**Requirement:** 04-REQ-3.1
**Type:** unit
**Description:** Verify Go tags conform to the expected semver format.

**Preconditions:**
- None.

**Input:**
- Valid tags: `pkg/afspec/v1.0.0`, `pkg/afspec/v0.1.0`, `pkg/afspec/v10.20.30`.
- Invalid tags: `v1.0.0`, `pkg/afspec/1.0.0`, `pkg/afspec/v1.0`, `afspec-v1.0.0`.

**Expected:**
- Valid tags match the Go tag regex.
- Invalid tags do not match.

**Assertion pseudocode:**
```
go_tag_re = compile("^pkg/afspec/v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$")
ASSERT go_tag_re.match("pkg/afspec/v1.0.0")
ASSERT go_tag_re.match("pkg/afspec/v0.1.0")
ASSERT NOT go_tag_re.match("v1.0.0")
ASSERT NOT go_tag_re.match("afspec-v1.0.0")
```

### TS-04-11: Python tag format validation

**Requirement:** 04-REQ-3.2
**Type:** unit
**Description:** Verify Python tags conform to the expected semver format.

**Preconditions:**
- None.

**Input:**
- Valid tags: `afspec-v1.0.0`, `afspec-v0.1.0`, `afspec-v10.20.30`.
- Invalid tags: `v1.0.0`, `afspec-1.0.0`, `afspec-v1.0`, `pkg/afspec/v1.0.0`.

**Expected:**
- Valid tags match the Python tag regex.
- Invalid tags do not match.

**Assertion pseudocode:**
```
py_tag_re = compile("^afspec-v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$")
ASSERT py_tag_re.match("afspec-v1.0.0")
ASSERT NOT py_tag_re.match("v1.0.0")
ASSERT NOT py_tag_re.match("pkg/afspec/v1.0.0")
```

### TS-04-12: Go version source of truth

**Requirement:** 04-REQ-3.3
**Type:** unit
**Description:** Verify that `internal/version/version.go` contains a `Version` constant.

**Preconditions:**
- `internal/version/version.go` exists.

**Input:**
- Contents of `internal/version/version.go`.

**Expected:**
- File contains a line matching `const Version = "..."` with a non-empty string value.

**Assertion pseudocode:**
```
content = read_file("internal/version/version.go")
ASSERT regex_match(content, 'const Version = "([^"]+)"')
```

### TS-04-13: Python version source of truth

**Requirement:** 04-REQ-3.4
**Type:** unit
**Description:** Verify that `pyproject.toml` contains a `version` field under `[project]`.

**Preconditions:**
- `pyproject.toml` exists (this test is skipped if Python project is not set up).

**Input:**
- Contents of `pyproject.toml`.

**Expected:**
- File contains a `version` field in the `[project]` section with a non-empty string value.

**Assertion pseudocode:**
```
IF NOT file_exists("pyproject.toml"):
    SKIP "pyproject.toml not present (spec 02 not yet implemented)"
content = read_file("pyproject.toml")
ASSERT regex_match(content, 'version\s*=\s*"([^"]+)"')
```

### TS-04-14: Go Makefile targets exist and work

**Requirement:** 04-REQ-4.1
**Type:** integration
**Description:** Verify `make test-go` and `make lint-go` targets exist and execute successfully.

**Preconditions:**
- `Makefile` exists at the repo root.
- Go toolchain and golangci-lint are installed.

**Input:**
- Run `make test-go` and `make lint-go` from repo root.

**Expected:**
- Both commands exit with code 0.

**Assertion pseudocode:**
```
result_test = exec("make", "test-go", cwd=repo_root)
ASSERT result_test.exit_code == 0
result_lint = exec("make", "lint-go", cwd=repo_root)
ASSERT result_lint.exit_code == 0
```

### TS-04-15: Python Makefile targets exist

**Requirement:** 04-REQ-4.2
**Type:** unit
**Description:** Verify `make test-python` and `make lint-python` targets are defined in the Makefile.

**Preconditions:**
- `Makefile` exists at the repo root.

**Input:**
- Contents of `Makefile`.

**Expected:**
- Makefile contains `test-python:` and `lint-python:` target definitions.

**Assertion pseudocode:**
```
content = read_file("Makefile")
ASSERT "test-python:" IN content
ASSERT "lint-python:" IN content
```

### TS-04-16: Combined Makefile targets

**Requirement:** 04-REQ-4.3
**Type:** unit
**Description:** Verify `make test` and `make lint` aggregate both language-specific targets.

**Preconditions:**
- `Makefile` exists at the repo root.

**Input:**
- Contents of `Makefile`.

**Expected:**
- `test` target depends on `test-go` and `test-python`.
- `lint` target depends on `lint-go` and `lint-python`.

**Assertion pseudocode:**
```
content = read_file("Makefile")
ASSERT line_matches(content, "test:.*test-go.*test-python")
ASSERT line_matches(content, "lint:.*lint-go.*lint-python")
```

### TS-04-17: Check target is quality gate

**Requirement:** 04-REQ-4.4
**Type:** integration
**Description:** Verify `make check` runs lint followed by test and succeeds.

**Preconditions:**
- `Makefile` exists. Go toolchain installed. All Go tests pass.

**Input:**
- Run `make check` from repo root.

**Expected:**
- Command exits with code 0.

**Assertion pseudocode:**
```
result = exec("make", "check", cwd=repo_root)
ASSERT result.exit_code == 0
```

### TS-04-18: Python targets skip when pyproject.toml missing

**Requirement:** 04-REQ-4.5
**Type:** integration
**Description:** Verify Python Makefile targets skip gracefully when `pyproject.toml` does not exist.

**Preconditions:**
- A temporary directory with a Makefile but no `pyproject.toml`.

**Input:**
- Run `make -f <repo_makefile> test-python` from a directory without `pyproject.toml`.

**Expected:**
- Command exits with code 0.
- Output contains "Skipping" or similar informational message.

**Assertion pseudocode:**
```
tmpdir = create_temp_dir()
copy_file(repo_root / "Makefile", tmpdir / "Makefile")
result = exec("make", "test-python", cwd=tmpdir)
ASSERT result.exit_code == 0
ASSERT "skip" IN result.stdout.lower() OR "Skipping" IN result.stdout
```

### TS-04-19: Go targets skip when go.mod missing

**Requirement:** 04-REQ-4.6
**Type:** integration
**Description:** Verify Go Makefile targets skip gracefully when `go.mod` does not exist.

**Preconditions:**
- A temporary directory with a Makefile but no `go.mod`.

**Input:**
- Run `make -f <repo_makefile> test-go` from a directory without `go.mod`.

**Expected:**
- Command exits with code 0.
- Output contains "Skipping" or similar informational message.

**Assertion pseudocode:**
```
tmpdir = create_temp_dir()
copy_file(repo_root / "Makefile", tmpdir / "Makefile")
result = exec("make", "test-go", cwd=tmpdir)
ASSERT result.exit_code == 0
ASSERT "skip" IN result.stdout.lower() OR "Skipping" IN result.stdout
```

### TS-04-20: golangci.yml exists

**Requirement:** 04-REQ-5.1
**Type:** unit
**Description:** Verify `.golangci.yml` exists at the repository root.

**Preconditions:**
- None.

**Input:**
- File system check for `.golangci.yml`.

**Expected:**
- File exists and is valid YAML.

**Assertion pseudocode:**
```
ASSERT file_exists(repo_root / ".golangci.yml")
content = read_file(repo_root / ".golangci.yml")
ASSERT parse_yaml(content) != error
```

### TS-04-21: golangci.yml enables required linters

**Requirement:** 04-REQ-5.2
**Type:** unit
**Description:** Verify `.golangci.yml` enables `govet` and `staticcheck`.

**Preconditions:**
- `.golangci.yml` exists and is valid YAML.

**Input:**
- Parsed YAML structure of `.golangci.yml`.

**Expected:**
- `linters.enable` list contains `"govet"` and `"staticcheck"`.

**Assertion pseudocode:**
```
config = parse_yaml(".golangci.yml")
enabled = config["linters"]["enable"]
ASSERT "govet" IN enabled
ASSERT "staticcheck" IN enabled
```

### TS-04-22: CI installs golangci-lint

**Requirement:** 04-REQ-5.3
**Type:** unit
**Description:** Verify the CI workflow's Go job installs golangci-lint.

**Preconditions:**
- `.github/workflows/ci.yml` exists.

**Input:**
- Parsed YAML structure of ci.yml, Go job steps.

**Expected:**
- Go job has a step that installs or invokes golangci-lint (via action or command).

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
go_job = ci["jobs"]["go"]
step_uses = [s.get("uses", "") for s in go_job["steps"]]
step_runs = [s.get("run", "") for s in go_job["steps"]]
ASSERT any("golangci-lint" in u for u in step_uses) OR any("golangci-lint" in r for r in step_runs)
```

## Edge Case Tests

### TS-04-E1: Python CI job skips when project missing

**Requirement:** 04-REQ-1.E1
**Type:** unit
**Description:** Verify the Python CI job has a condition that skips it when `pyproject.toml` is absent.

**Preconditions:**
- `.github/workflows/ci.yml` exists with a Python job.

**Input:**
- Parsed YAML structure of ci.yml.

**Expected:**
- Python job has an `if` condition that evaluates to false when `pyproject.toml` doesn't exist.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
py_job = ci["jobs"]["python"]
ASSERT "hashFiles" IN py_job["if"] AND "pyproject.toml" IN py_job["if"]
```

### TS-04-E2: CI step failure propagates

**Requirement:** 04-REQ-1.E2
**Type:** unit
**Description:** Verify CI job steps do not use `continue-on-error: true` (so failures propagate).

**Preconditions:**
- `.github/workflows/ci.yml` exists.

**Input:**
- Parsed YAML structure of ci.yml.

**Expected:**
- No step in any job has `continue-on-error: true`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
FOR job IN ci["jobs"].values():
    FOR step IN job["steps"]:
        ASSERT step.get("continue-on-error") != true
```

### TS-04-E3: Version mismatch fails release

**Requirement:** 04-REQ-2.E1
**Type:** integration
**Description:** Verify `check-version.sh` exits with error when tag and code versions don't match.

**Preconditions:**
- `scripts/check-version.sh` exists and is executable.
- `internal/version/version.go` contains `Version = "0.0.0-dev"`.

**Input:**
- Run `scripts/check-version.sh go "pkg/afspec/v1.0.0"` (mismatched — code has "0.0.0-dev").

**Expected:**
- Script exits with code 1.
- Stderr contains "mismatch" or error message.

**Assertion pseudocode:**
```
result = exec("scripts/check-version.sh", "go", "pkg/afspec/v1.0.0", cwd=repo_root)
ASSERT result.exit_code == 1
ASSERT "mismatch" IN result.stderr.lower()
```

### TS-04-E4: Build failure prevents release

**Requirement:** 04-REQ-2.E2
**Type:** unit
**Description:** Verify the Python release job runs `uv build` before `gh release create` so a build failure prevents the release.

**Preconditions:**
- `.github/workflows/release.yml` exists.

**Input:**
- Parsed YAML structure of release.yml, Python release job.

**Expected:**
- `uv build` step index is less than `gh release create` step index.
- No `continue-on-error` on the build step.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
py_steps = rel["jobs"]["release-python"]["steps"]
build_idx = find_step_index(py_steps, "uv build")
release_idx = find_step_index(py_steps, "gh release create")
ASSERT build_idx < release_idx
ASSERT py_steps[build_idx].get("continue-on-error") != true
```

### TS-04-E5: Invalid tag format rejected

**Requirement:** 04-REQ-3.E1
**Type:** integration
**Description:** Verify `check-version.sh` rejects tags that don't conform to semver format.

**Preconditions:**
- `scripts/check-version.sh` exists and is executable.

**Input:**
- Run with invalid tags: `scripts/check-version.sh go "pkg/afspec/vnotaversion"`, `scripts/check-version.sh python "afspec-v1.0"`.

**Expected:**
- Script exits with code 1 for each invalid tag.

**Assertion pseudocode:**
```
result1 = exec("scripts/check-version.sh", "go", "pkg/afspec/vnotaversion")
ASSERT result1.exit_code == 1
result2 = exec("scripts/check-version.sh", "python", "afspec-v1.0")
ASSERT result2.exit_code == 1
```

### TS-04-E6: Both languages missing

**Requirement:** 04-REQ-4.E1
**Type:** integration
**Description:** Verify `make check` succeeds with a warning when neither Go nor Python is configured.

**Preconditions:**
- A temporary directory with only the Makefile (no `go.mod`, no `pyproject.toml`).

**Input:**
- Run `make -f <repo_makefile> check` from the temporary directory.

**Expected:**
- Command exits with code 0.
- Output contains skip/warning messages for both languages.

**Assertion pseudocode:**
```
tmpdir = create_temp_dir()
copy_file(repo_root / "Makefile", tmpdir / "Makefile")
result = exec("make", "check", cwd=tmpdir)
ASSERT result.exit_code == 0
ASSERT "Skipping Go" IN result.stdout
ASSERT "Skipping Python" IN result.stdout
```

### TS-04-E7: Missing golangci.yml uses defaults

**Requirement:** 04-REQ-5.E1
**Type:** unit
**Description:** Document that golangci-lint uses its default configuration when `.golangci.yml` is absent (this is built-in golangci-lint behavior, not custom code).

**Preconditions:**
- None.

**Input:**
- N/A (documents built-in golangci-lint behavior).

**Expected:**
- `.golangci.yml` is present in the repository (the test verifies file existence rather than testing golangci-lint's fallback behavior, which is third-party code).

**Assertion pseudocode:**
```
ASSERT file_exists(repo_root / ".golangci.yml")
```

## Property Test Cases

### TS-04-P1: Tag pattern exclusivity

**Property:** Property 1 from design.md
**Validates:** 04-REQ-2.4, 04-REQ-3.1, 04-REQ-3.2
**Type:** property
**Description:** For any valid semver string, a Go tag and a Python tag are mutually exclusive — neither matches the other's pattern.

**For any:** semver version string V = `{M}.{N}.{P}` where M, N, P are non-negative integers (0–999)
**Invariant:** `"pkg/afspec/v" + V` matches the Go tag regex AND does NOT match the Python tag regex; `"afspec-v" + V` matches the Python tag regex AND does NOT match the Go tag regex.

**Assertion pseudocode:**
```
go_re = compile("^pkg/afspec/v...")
py_re = compile("^afspec-v...")
FOR ANY (M, N, P) IN integers(0, 999):
    V = format("{}.{}.{}", M, N, P)
    go_tag = "pkg/afspec/v" + V
    py_tag = "afspec-v" + V
    ASSERT go_re.match(go_tag) AND NOT py_re.match(go_tag)
    ASSERT py_re.match(py_tag) AND NOT go_re.match(py_tag)
```

### TS-04-P2: Version extraction correctness

**Property:** Property 2 from design.md
**Validates:** 04-REQ-2.3, 04-REQ-3.3, 04-REQ-3.4
**Type:** property
**Description:** For any valid semver string, `check-version.sh` correctly extracts the version from the tag and matches it against a code file containing the same version.

**For any:** semver version string V = `{M}.{N}.{P}` where M, N, P are non-negative integers (0–99)
**Invariant:** When the tag contains version V and the code file contains version V, the script exits with code 0.

**Assertion pseudocode:**
```
FOR ANY (M, N, P) IN integers(0, 99):
    V = format("{}.{}.{}", M, N, P)
    tmpdir = create_temp_dir()
    write_file(tmpdir / "internal/version/version.go",
               'package version\nconst Version = "' + V + '"')
    result = exec("scripts/check-version.sh", "go", "pkg/afspec/v" + V, cwd=tmpdir)
    ASSERT result.exit_code == 0
```

### TS-04-P3: Makefile graceful degradation

**Property:** Property 3 from design.md
**Validates:** 04-REQ-4.4, 04-REQ-4.5, 04-REQ-4.6
**Type:** property
**Description:** For any combination of present/absent language project structures, `make check` exits 0 when present languages pass.

**For any:** (go_present, python_present) in {(true, true), (true, false), (false, true), (false, false)}
**Invariant:** `make check` exits with code 0 (given that present-language checks pass).

**Assertion pseudocode:**
```
FOR ANY (go_present, python_present) IN [(T,T), (T,F), (F,T), (F,F)]:
    tmpdir = create_temp_dir_with_makefile()
    IF go_present: create_minimal_go_project(tmpdir)
    IF python_present: create_minimal_python_project(tmpdir)
    result = exec("make", "check", cwd=tmpdir)
    ASSERT result.exit_code == 0
```

### TS-04-P4: CI trigger correctness

**Property:** Property 4 from design.md
**Validates:** 04-REQ-1.1, 04-REQ-1.2
**Type:** property
**Description:** The CI workflow triggers on and only on `main` and `develop` branches.

**For any:** branch name B in {"main", "develop", "feature/foo", "release/1.0", "hotfix/bar", "master"}
**Invariant:** B is in the CI trigger list if and only if B is `"main"` or `"develop"`.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
push_branches = ci["on"]["push"]["branches"]
pr_branches = ci["on"]["pull_request"]["branches"]
FOR ANY branch IN ["main", "develop", "feature/foo", "release/1.0", "master"]:
    expected = branch IN ["main", "develop"]
    ASSERT (branch IN push_branches) == expected
    ASSERT (branch IN pr_branches) == expected
```

## Integration Smoke Tests

### TS-04-SMOKE-1: Local quality gate end-to-end

**Execution Path:** Path 1 from design.md
**Description:** Verify `make check` runs lint and test for all available languages end-to-end.

**Setup:** Repo root with existing Go project (go.mod, internal/version/). No mocking of make targets — real execution.

**Trigger:** Run `make check` from repo root.

**Expected side effects:**
- `go vet` runs against the codebase.
- `golangci-lint run` runs against the codebase.
- `go test -count=1 ./...` runs all tests.
- Overall exit code is 0.

**Must NOT satisfy with:** Mocking make targets, skipping go vet or go test.

**Assertion pseudocode:**
```
result = exec("make", "check", cwd=repo_root)
ASSERT result.exit_code == 0
ASSERT "PASS" IN result.stdout OR "ok" IN result.stdout
```

### TS-04-SMOKE-2: CI workflow structural completeness

**Execution Path:** Path 2 from design.md
**Description:** Verify ci.yml contains all required elements for a functional CI pipeline.

**Setup:** None (static YAML analysis).

**Trigger:** Parse and inspect `.github/workflows/ci.yml`.

**Expected side effects:**
- File is valid YAML.
- Has exactly two trigger types (push, pull_request) on exactly two branches (main, develop).
- Has a Go job and a Python job.
- Go job has checkout, setup-go, golangci-lint, make lint-go, make test-go.
- Python job has checkout, setup-python with matrix, setup-uv, make lint-python, make test-python.
- Python job has conditional execution.

**Must NOT satisfy with:** Testing individual steps in isolation without verifying they're all present in the same workflow.

**Assertion pseudocode:**
```
ci = parse_yaml(".github/workflows/ci.yml")
ASSERT len(ci["on"]) >= 2
ASSERT "go" IN ci["jobs"]
ASSERT "python" IN ci["jobs"]
go_steps = [s.get("run", s.get("uses", "")) for s in ci["jobs"]["go"]["steps"]]
ASSERT all required steps present in go_steps
py_steps = [s.get("run", s.get("uses", "")) for s in ci["jobs"]["python"]["steps"]]
ASSERT all required steps present in py_steps
ASSERT ci["jobs"]["python"].get("if") is not None
```

### TS-04-SMOKE-3: Go release workflow structural completeness

**Execution Path:** Path 3 from design.md
**Description:** Verify the Go release path in release.yml is structurally complete: checkout → version validation → release creation.

**Setup:** None (static YAML analysis).

**Trigger:** Parse and inspect `.github/workflows/release.yml`, `release-go` job.

**Expected side effects:**
- release.yml triggers on tag `pkg/afspec/v*`.
- `release-go` job has conditional on tag pattern.
- Steps appear in order: checkout → check-version.sh → gh release create.
- Permissions include `contents: write`.

**Must NOT satisfy with:** Only checking that the file exists without verifying step ordering and completeness.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
ASSERT "pkg/afspec/v*" IN rel["on"]["push"]["tags"]
go_job = rel["jobs"]["release-go"]
steps = go_job["steps"]
checkout_idx = find_step_using(steps, "actions/checkout")
check_idx = find_step_running(steps, "check-version.sh")
release_idx = find_step_running(steps, "gh release create")
ASSERT checkout_idx < check_idx < release_idx
ASSERT rel.get("permissions", {}).get("contents") == "write"
```

### TS-04-SMOKE-4: Python release workflow structural completeness

**Execution Path:** Path 4 from design.md
**Description:** Verify the Python release path in release.yml is structurally complete: checkout → setup → version validation → build → release with artifacts.

**Setup:** None (static YAML analysis).

**Trigger:** Parse and inspect `.github/workflows/release.yml`, `release-python` job.

**Expected side effects:**
- release.yml triggers on tag `afspec-v*`.
- `release-python` job has conditional on tag pattern.
- Steps appear in order: checkout → setup-python → setup-uv → check-version.sh → uv build → gh release create with dist/*.
- Permissions include `contents: write`.

**Must NOT satisfy with:** Only checking individual steps without verifying ordering and artifact attachment.

**Assertion pseudocode:**
```
rel = parse_yaml(".github/workflows/release.yml")
ASSERT "afspec-v*" IN rel["on"]["push"]["tags"]
py_job = rel["jobs"]["release-python"]
steps = py_job["steps"]
check_idx = find_step_running(steps, "check-version.sh")
build_idx = find_step_running(steps, "uv build")
release_idx = find_step_running(steps, "gh release create")
ASSERT check_idx < build_idx < release_idx
release_step = steps[release_idx]
ASSERT "dist/" IN release_step["run"]
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 04-REQ-1.1 | TS-04-1 | unit |
| 04-REQ-1.2 | TS-04-2 | unit |
| 04-REQ-1.3 | TS-04-3 | unit |
| 04-REQ-1.4 | TS-04-4 | unit |
| 04-REQ-1.5 | TS-04-5 | unit |
| 04-REQ-1.E1 | TS-04-E1 | unit |
| 04-REQ-1.E2 | TS-04-E2 | unit |
| 04-REQ-2.1 | TS-04-6 | unit |
| 04-REQ-2.2 | TS-04-7 | unit |
| 04-REQ-2.3 | TS-04-8 | unit |
| 04-REQ-2.4 | TS-04-9 | unit |
| 04-REQ-2.E1 | TS-04-E3 | integration |
| 04-REQ-2.E2 | TS-04-E4 | unit |
| 04-REQ-3.1 | TS-04-10 | unit |
| 04-REQ-3.2 | TS-04-11 | unit |
| 04-REQ-3.3 | TS-04-12 | unit |
| 04-REQ-3.4 | TS-04-13 | unit |
| 04-REQ-3.E1 | TS-04-E5 | integration |
| 04-REQ-4.1 | TS-04-14 | integration |
| 04-REQ-4.2 | TS-04-15 | unit |
| 04-REQ-4.3 | TS-04-16 | unit |
| 04-REQ-4.4 | TS-04-17 | integration |
| 04-REQ-4.5 | TS-04-18 | integration |
| 04-REQ-4.6 | TS-04-19 | integration |
| 04-REQ-4.E1 | TS-04-E6 | integration |
| 04-REQ-5.1 | TS-04-20 | unit |
| 04-REQ-5.2 | TS-04-21 | unit |
| 04-REQ-5.3 | TS-04-22 | unit |
| 04-REQ-5.E1 | TS-04-E7 | unit |
| Property 1 | TS-04-P1 | property |
| Property 2 | TS-04-P2 | property |
| Property 3 | TS-04-P3 | property |
| Property 4 | TS-04-P4 | property |
| Path 1 | TS-04-SMOKE-1 | integration |
| Path 2 | TS-04-SMOKE-2 | integration |
| Path 3 | TS-04-SMOKE-3 | integration |
| Path 4 | TS-04-SMOKE-4 | integration |
