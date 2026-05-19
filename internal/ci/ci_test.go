package ci_test

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"slices"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// repoRoot returns the repository root by navigating up two directories from
// this test file (internal/ci/ci_test.go → internal/ci → internal → repo root).
func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot determine test file path")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
}

// parseWorkflow reads and parses a YAML file into a generic map.
func parseWorkflow(t *testing.T, path string) map[string]any {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("cannot read file %q: %v", path, err)
	}
	var result map[string]any
	if err := yaml.Unmarshal(data, &result); err != nil {
		t.Fatalf("cannot parse YAML %q: %v", path, err)
	}
	return result
}

// asMap safely casts any to map[string]any.
func asMap(v any) map[string]any {
	m, _ := v.(map[string]any)
	return m
}

// asSlice safely casts any to []any.
func asSlice(v any) []any {
	s, _ := v.([]any)
	return s
}

// stepsUses returns the "uses" values from a steps slice.
func stepsUses(steps []any) []string {
	var out []string
	for _, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if u, ok := step["uses"].(string); ok {
				out = append(out, u)
			}
		}
	}
	return out
}

// stepsRuns returns the "run" values from a steps slice.
func stepsRuns(steps []any) []string {
	var out []string
	for _, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if r, ok := step["run"].(string); ok {
				out = append(out, r)
			}
		}
	}
	return out
}

// containsString reports whether slice contains str.
func containsString(slice []string, str string) bool {
	return slices.Contains(slice, str)
}

// anyContains reports whether any string in slice contains sub.
func anyContains(slice []string, sub string) bool {
	for _, s := range slice {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}

// anyHasPrefix reports whether any string in slice has the given prefix.
func anyHasPrefix(slice []string, prefix string) bool {
	for _, s := range slice {
		if strings.HasPrefix(s, prefix) {
			return true
		}
	}
	return false
}

// findStepRunIndex returns the index of the first step whose "run" contains sub, or -1.
func findStepRunIndex(steps []any, sub string) int {
	for i, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if r, ok := step["run"].(string); ok && strings.Contains(r, sub) {
				return i
			}
		}
	}
	return -1
}

// findStepUsesIndex returns the index of the first step whose "uses" has the given prefix, or -1.
func findStepUsesIndex(steps []any, prefix string) int {
	for i, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if u, ok := step["uses"].(string); ok && strings.HasPrefix(u, prefix) {
				return i
			}
		}
	}
	return -1
}

// copyFile copies src to dst, creating parent directories as needed.
func copyFile(t *testing.T, src, dst string) {
	t.Helper()
	srcFile, err := os.Open(src)
	if err != nil {
		t.Fatalf("copyFile: open src %q: %v", src, err)
	}
	defer srcFile.Close()
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		t.Fatalf("copyFile: mkdir for dst %q: %v", dst, err)
	}
	dstFile, err := os.Create(dst)
	if err != nil {
		t.Fatalf("copyFile: create dst %q: %v", dst, err)
	}
	defer dstFile.Close()
	if _, err := io.Copy(dstFile, srcFile); err != nil {
		t.Fatalf("copyFile: copy %q → %q: %v", src, dst, err)
	}
}

// testRecursionGuard is an environment variable name used to prevent infinite
// recursion when integration tests invoke `make` targets that themselves run
// `go test ./...` (which would re-invoke the same integration tests).
const testRecursionGuard = "AFSPEC_TEST_NO_RECURSION"

// runMake runs `make <targets...>` in dir and returns combined output and exit code.
// It sets testRecursionGuard in the subprocess environment to break recursion.
func runMake(t *testing.T, dir string, targets ...string) (string, int) {
	t.Helper()
	cmd := exec.Command("make", targets...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), testRecursionGuard+"=1")
	out, err := cmd.CombinedOutput()
	if err == nil {
		return string(out), 0
	}
	if exitErr, ok := err.(*exec.ExitError); ok {
		return string(out), exitErr.ExitCode()
	}
	t.Logf("runMake unexpected error (non-exit): %v", err)
	return string(out), -1
}

// ---------------------------------------------------------------------------
// Tag regexes (TS-04-10, TS-04-11, TS-04-P1)
// ---------------------------------------------------------------------------

// goTagRe is the authoritative regex for Go version tags.
var goTagRe = regexp.MustCompile(`^pkg/afspec/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`)

// pyTagRe is the authoritative regex for Python version tags.
var pyTagRe = regexp.MustCompile(`^afspec-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`)

// ---------------------------------------------------------------------------
// TS-04-1: CI triggers on push to main/develop
// ---------------------------------------------------------------------------

func TestTS04_01(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	onSection := asMap(ci["on"])
	pushSection := asMap(onSection["push"])
	branches := asSlice(pushSection["branches"])

	var branchStrs []string
	for _, b := range branches {
		if s, ok := b.(string); ok {
			branchStrs = append(branchStrs, s)
		}
	}

	if !containsString(branchStrs, "main") {
		t.Errorf("on.push.branches does not contain 'main'; got %v", branchStrs)
	}
	if !containsString(branchStrs, "develop") {
		t.Errorf("on.push.branches does not contain 'develop'; got %v", branchStrs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-2: CI triggers on PR to main/develop
// ---------------------------------------------------------------------------

func TestTS04_02(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	onSection := asMap(ci["on"])
	prSection := asMap(onSection["pull_request"])
	branches := asSlice(prSection["branches"])

	var branchStrs []string
	for _, b := range branches {
		if s, ok := b.(string); ok {
			branchStrs = append(branchStrs, s)
		}
	}

	if !containsString(branchStrs, "main") {
		t.Errorf("on.pull_request.branches does not contain 'main'; got %v", branchStrs)
	}
	if !containsString(branchStrs, "develop") {
		t.Errorf("on.pull_request.branches does not contain 'develop'; got %v", branchStrs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-3: Go CI job has required steps
// ---------------------------------------------------------------------------

func TestTS04_03(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	goJob := asMap(jobs["go"])
	if goJob == nil {
		t.Fatal("jobs.go not found in ci.yml")
	}

	steps := asSlice(goJob["steps"])
	uses := stepsUses(steps)
	runs := stepsRuns(steps)

	if !anyHasPrefix(uses, "actions/checkout") {
		t.Errorf("go job missing actions/checkout step; uses: %v", uses)
	}
	if !anyHasPrefix(uses, "actions/setup-go") {
		t.Errorf("go job missing actions/setup-go step; uses: %v", uses)
	}

	// setup-go must use go-version-file: go.mod
	for _, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if u, ok := step["uses"].(string); ok && strings.HasPrefix(u, "actions/setup-go") {
				withMap := asMap(step["with"])
				if withMap == nil || fmt.Sprintf("%v", withMap["go-version-file"]) != "go.mod" {
					t.Errorf("setup-go step missing 'go-version-file: go.mod'; with: %v", withMap)
				}
			}
		}
	}

	// Must have golangci-lint installation
	if !anyContains(uses, "golangci-lint") && !anyContains(runs, "golangci-lint") {
		t.Errorf("go job does not install or invoke golangci-lint; uses: %v, runs: %v", uses, runs)
	}

	if !anyContains(runs, "make lint-go") {
		t.Errorf("go job missing 'make lint-go' run step; runs: %v", runs)
	}
	if !anyContains(runs, "make test-go") {
		t.Errorf("go job missing 'make test-go' run step; runs: %v", runs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-4: Python CI job has required steps and matrix
// ---------------------------------------------------------------------------

func TestTS04_04(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	pyJob := asMap(jobs["python"])
	if pyJob == nil {
		t.Fatal("jobs.python not found in ci.yml")
	}

	// Check matrix strategy
	strategy := asMap(pyJob["strategy"])
	matrix := asMap(strategy["matrix"])
	versions := asSlice(matrix["python-version"])

	var versionStrs []string
	for _, v := range versions {
		versionStrs = append(versionStrs, fmt.Sprintf("%v", v))
	}
	if !containsString(versionStrs, "3.10") {
		t.Errorf("python-version matrix missing '3.10'; got %v", versionStrs)
	}
	if !containsString(versionStrs, "3.13") {
		t.Errorf("python-version matrix missing '3.13'; got %v", versionStrs)
	}

	steps := asSlice(pyJob["steps"])
	uses := stepsUses(steps)
	runs := stepsRuns(steps)

	if !anyHasPrefix(uses, "actions/setup-python") {
		t.Errorf("python job missing actions/setup-python step; uses: %v", uses)
	}
	if !anyHasPrefix(uses, "astral-sh/setup-uv") {
		t.Errorf("python job missing astral-sh/setup-uv step; uses: %v", uses)
	}
	if !anyContains(runs, "make lint-python") {
		t.Errorf("python job missing 'make lint-python' run step; runs: %v", runs)
	}
	if !anyContains(runs, "make test-python") {
		t.Errorf("python job missing 'make test-python' run step; runs: %v", runs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-5: All CI jobs run on ubuntu-latest
// ---------------------------------------------------------------------------

func TestTS04_05(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	for name, job := range jobs {
		j := asMap(job)
		if j == nil {
			t.Errorf("job %q is not a map", name)
			continue
		}
		runsOn := fmt.Sprintf("%v", j["runs-on"])
		if runsOn != "ubuntu-latest" {
			t.Errorf("job %q runs-on = %q, want 'ubuntu-latest'", name, runsOn)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-6: Go release job creates GitHub release
// ---------------------------------------------------------------------------

func TestTS04_06(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	jobs := asMap(rel["jobs"])
	goJob := asMap(jobs["release-go"])
	if goJob == nil {
		t.Fatal("jobs.release-go not found in release.yml")
	}

	ifCond := fmt.Sprintf("%v", goJob["if"])
	if !strings.Contains(ifCond, "pkg/afspec/v") {
		t.Errorf("release-go 'if' does not reference 'pkg/afspec/v'; got %q", ifCond)
	}

	runs := stepsRuns(asSlice(goJob["steps"]))
	if !anyContains(runs, "gh release create") {
		t.Errorf("release-go job missing 'gh release create' step; runs: %v", runs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-7: Python release job builds wheel/sdist and uploads artifacts
// ---------------------------------------------------------------------------

func TestTS04_07(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	jobs := asMap(rel["jobs"])
	pyJob := asMap(jobs["release-python"])
	if pyJob == nil {
		t.Fatal("jobs.release-python not found in release.yml")
	}

	ifCond := fmt.Sprintf("%v", pyJob["if"])
	if !strings.Contains(ifCond, "afspec-v") {
		t.Errorf("release-python 'if' does not reference 'afspec-v'; got %q", ifCond)
	}

	runs := stepsRuns(asSlice(pyJob["steps"]))
	if !anyContains(runs, "uv build") {
		t.Errorf("release-python job missing 'uv build' step; runs: %v", runs)
	}
	if !anyContains(runs, "gh release create") {
		t.Errorf("release-python job missing 'gh release create' step; runs: %v", runs)
	}

	// gh release create must reference dist/ for artifact upload
	var hasDistArtifact bool
	for _, r := range runs {
		if strings.Contains(r, "gh release create") && strings.Contains(r, "dist/") {
			hasDistArtifact = true
			break
		}
	}
	if !hasDistArtifact {
		t.Errorf("release-python 'gh release create' step does not reference dist/; runs: %v", runs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-8: Both release jobs call check-version.sh before gh release create
// ---------------------------------------------------------------------------

func TestTS04_08(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	jobs := asMap(rel["jobs"])
	for _, jobName := range []string{"release-go", "release-python"} {
		job := asMap(jobs[jobName])
		if job == nil {
			t.Errorf("jobs.%s not found in release.yml", jobName)
			continue
		}
		steps := asSlice(job["steps"])
		checkIdx := findStepRunIndex(steps, "check-version.sh")
		releaseIdx := findStepRunIndex(steps, "gh release create")

		if checkIdx < 0 {
			t.Errorf("job %s missing 'check-version.sh' step", jobName)
			continue
		}
		if releaseIdx < 0 {
			t.Errorf("job %s missing 'gh release create' step", jobName)
			continue
		}
		if checkIdx >= releaseIdx {
			t.Errorf("job %s: check-version.sh (idx %d) must come before gh release create (idx %d)",
				jobName, checkIdx, releaseIdx)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-9: Single release.yml with both release-go and release-python jobs
// ---------------------------------------------------------------------------

func TestTS04_09(t *testing.T) {
	root := repoRoot(t)
	workflowsDir := filepath.Join(root, ".github", "workflows")

	entries, err := os.ReadDir(workflowsDir)
	if err != nil {
		t.Fatalf("cannot read .github/workflows/: %v", err)
	}

	var releaseFiles []string
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), "release") {
			releaseFiles = append(releaseFiles, e.Name())
		}
	}

	if !containsString(releaseFiles, "release.yml") {
		t.Errorf(".github/workflows/release.yml not found; found: %v", releaseFiles)
	}
	for _, f := range releaseFiles {
		if f != "release.yml" {
			t.Errorf("unexpected release workflow file: %s (only release.yml is expected)", f)
		}
	}

	rel := parseWorkflow(t, filepath.Join(workflowsDir, "release.yml"))
	jobs := asMap(rel["jobs"])
	if jobs["release-go"] == nil {
		t.Error("release.yml missing 'release-go' job")
	}
	if jobs["release-python"] == nil {
		t.Error("release.yml missing 'release-python' job")
	}
}

// ---------------------------------------------------------------------------
// TS-04-10: Go tag format validation
// ---------------------------------------------------------------------------

func TestTS04_10(t *testing.T) {
	valid := []string{
		"pkg/afspec/v1.0.0",
		"pkg/afspec/v0.1.0",
		"pkg/afspec/v10.20.30",
		"pkg/afspec/v0.0.0",
	}
	invalid := []string{
		"v1.0.0",
		"pkg/afspec/1.0.0",
		"pkg/afspec/v1.0",
		"afspec-v1.0.0",
		"pkg/afspec/v01.0.0", // leading zero
		"pkg/afspec/v",
		"",
		"pkg/afspec/v1.0.0.0", // extra component
	}

	for _, tag := range valid {
		if !goTagRe.MatchString(tag) {
			t.Errorf("expected Go tag %q to match goTagRe, but it did not", tag)
		}
	}
	for _, tag := range invalid {
		if goTagRe.MatchString(tag) {
			t.Errorf("expected Go tag %q NOT to match goTagRe, but it did", tag)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-11: Python tag format validation
// ---------------------------------------------------------------------------

func TestTS04_11(t *testing.T) {
	valid := []string{
		"afspec-v1.0.0",
		"afspec-v0.1.0",
		"afspec-v10.20.30",
		"afspec-v0.0.0",
	}
	invalid := []string{
		"v1.0.0",
		"afspec-1.0.0",
		"afspec-v1.0",
		"pkg/afspec/v1.0.0",
		"afspec-v01.0.0", // leading zero
		"afspec-v",
		"",
		"afspec-v1.0.0.0", // extra component
	}

	for _, tag := range valid {
		if !pyTagRe.MatchString(tag) {
			t.Errorf("expected Python tag %q to match pyTagRe, but it did not", tag)
		}
	}
	for _, tag := range invalid {
		if pyTagRe.MatchString(tag) {
			t.Errorf("expected Python tag %q NOT to match pyTagRe, but it did", tag)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-12: Go version source of truth in internal/version/version.go
// ---------------------------------------------------------------------------

func TestTS04_12(t *testing.T) {
	root := repoRoot(t)
	versionFile := filepath.Join(root, "internal", "version", "version.go")

	data, err := os.ReadFile(versionFile)
	if err != nil {
		t.Fatalf("cannot read %s: %v", versionFile, err)
	}

	re := regexp.MustCompile(`const Version = "([^"]+)"`)
	if !re.Match(data) {
		t.Errorf("internal/version/version.go does not contain 'const Version = \"...\";  content:\n%s", data)
	}
}

// ---------------------------------------------------------------------------
// TS-04-13: Python version source of truth in pyproject.toml
// ---------------------------------------------------------------------------

func TestTS04_13(t *testing.T) {
	root := repoRoot(t)
	pyprojectPath := filepath.Join(root, "pyproject.toml")

	if _, err := os.Stat(pyprojectPath); os.IsNotExist(err) {
		t.Skip("pyproject.toml not present (spec 02 not yet implemented)")
	}

	data, err := os.ReadFile(pyprojectPath)
	if err != nil {
		t.Fatalf("cannot read pyproject.toml: %v", err)
	}

	re := regexp.MustCompile(`(?m)^\s*version\s*=\s*"([^"]+)"`)
	if !re.Match(data) {
		t.Errorf("pyproject.toml does not contain 'version = \"...\"'; content:\n%s", data)
	}
}

// ---------------------------------------------------------------------------
// TS-04-14: make test-go and make lint-go exist and succeed
// ---------------------------------------------------------------------------

func TestTS04_14(t *testing.T) {
	if os.Getenv(testRecursionGuard) != "" {
		t.Skip("skipping: recursive invocation from make")
	}
	root := repoRoot(t)

	if _, err := exec.LookPath("golangci-lint"); err != nil {
		t.Skip("golangci-lint not installed; skipping TS-04-14")
	}

	out, code := runMake(t, root, "test-go")
	if code != 0 {
		t.Errorf("make test-go exited %d; output:\n%s", code, out)
	}

	out, code = runMake(t, root, "lint-go")
	if code != 0 {
		t.Errorf("make lint-go exited %d; output:\n%s", code, out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-15: Python Makefile targets are defined
// ---------------------------------------------------------------------------

func TestTS04_15(t *testing.T) {
	root := repoRoot(t)
	data, err := os.ReadFile(filepath.Join(root, "Makefile"))
	if err != nil {
		t.Fatalf("cannot read Makefile: %v", err)
	}
	content := string(data)

	if !strings.Contains(content, "test-python:") {
		t.Error("Makefile missing 'test-python:' target")
	}
	if !strings.Contains(content, "lint-python:") {
		t.Error("Makefile missing 'lint-python:' target")
	}
}

// ---------------------------------------------------------------------------
// TS-04-16: Combined make test and make lint aggregate both languages
// ---------------------------------------------------------------------------

func TestTS04_16(t *testing.T) {
	root := repoRoot(t)
	data, err := os.ReadFile(filepath.Join(root, "Makefile"))
	if err != nil {
		t.Fatalf("cannot read Makefile: %v", err)
	}
	content := string(data)

	// test: target must depend on test-go and test-python
	testRe := regexp.MustCompile(`(?m)^test:.*test-go.*test-python`)
	if !testRe.MatchString(content) {
		t.Error("Makefile 'test' target does not depend on both 'test-go' and 'test-python'")
	}

	// lint: target must depend on lint-go and lint-python
	lintRe := regexp.MustCompile(`(?m)^lint:.*lint-go.*lint-python`)
	if !lintRe.MatchString(content) {
		t.Error("Makefile 'lint' target does not depend on both 'lint-go' and 'lint-python'")
	}
}

// ---------------------------------------------------------------------------
// TS-04-17: make check is the quality gate and exits 0
// ---------------------------------------------------------------------------

func TestTS04_17(t *testing.T) {
	if os.Getenv(testRecursionGuard) != "" {
		t.Skip("skipping: recursive invocation from make")
	}
	root := repoRoot(t)

	if _, err := exec.LookPath("golangci-lint"); err != nil {
		t.Skip("golangci-lint not installed; skipping TS-04-17")
	}

	out, code := runMake(t, root, "check")
	if code != 0 {
		t.Errorf("make check exited %d; output:\n%s", code, out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-18: Python Makefile targets skip when pyproject.toml is missing
// ---------------------------------------------------------------------------

func TestTS04_18(t *testing.T) {
	root := repoRoot(t)
	tmpDir := t.TempDir()

	copyFile(t, filepath.Join(root, "Makefile"), filepath.Join(tmpDir, "Makefile"))

	// No pyproject.toml in tmpDir
	out, code := runMake(t, tmpDir, "test-python")
	if code != 0 {
		t.Errorf("make test-python exited %d (want 0) in dir without pyproject.toml; output:\n%s", code, out)
	}
	if !strings.Contains(strings.ToLower(out), "skip") {
		t.Errorf("make test-python did not print a skip message; output:\n%s", out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-19: Go Makefile targets skip when go.mod is missing
// ---------------------------------------------------------------------------

func TestTS04_19(t *testing.T) {
	root := repoRoot(t)
	tmpDir := t.TempDir()

	copyFile(t, filepath.Join(root, "Makefile"), filepath.Join(tmpDir, "Makefile"))

	// No go.mod in tmpDir
	out, code := runMake(t, tmpDir, "test-go")
	if code != 0 {
		t.Errorf("make test-go exited %d (want 0) in dir without go.mod; output:\n%s", code, out)
	}
	if !strings.Contains(strings.ToLower(out), "skip") {
		t.Errorf("make test-go did not print a skip message; output:\n%s", out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-20: .golangci.yml exists at repo root
// ---------------------------------------------------------------------------

func TestTS04_20(t *testing.T) {
	root := repoRoot(t)
	path := filepath.Join(root, ".golangci.yml")

	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		t.Fatal(".golangci.yml does not exist at repo root")
	}
	if err != nil {
		t.Fatalf("cannot read .golangci.yml: %v", err)
	}

	var parsed map[string]any
	if err := yaml.Unmarshal(data, &parsed); err != nil {
		t.Fatalf(".golangci.yml is not valid YAML: %v", err)
	}
}

// ---------------------------------------------------------------------------
// TS-04-21: .golangci.yml enables govet and staticcheck
// ---------------------------------------------------------------------------

func TestTS04_21(t *testing.T) {
	root := repoRoot(t)
	path := filepath.Join(root, ".golangci.yml")

	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		t.Fatal(".golangci.yml does not exist")
	}
	if err != nil {
		t.Fatalf("cannot read .golangci.yml: %v", err)
	}

	var config map[string]any
	if err := yaml.Unmarshal(data, &config); err != nil {
		t.Fatalf("cannot parse .golangci.yml: %v", err)
	}

	lintersSection := asMap(config["linters"])
	if lintersSection == nil {
		t.Fatal(".golangci.yml missing 'linters' section")
	}

	enabledRaw := asSlice(lintersSection["enable"])
	var enabled []string
	for _, e := range enabledRaw {
		if s, ok := e.(string); ok {
			enabled = append(enabled, s)
		}
	}

	if !containsString(enabled, "govet") {
		t.Errorf(".golangci.yml does not enable 'govet'; enabled: %v", enabled)
	}
	if !containsString(enabled, "staticcheck") {
		t.Errorf(".golangci.yml does not enable 'staticcheck'; enabled: %v", enabled)
	}
}

// ---------------------------------------------------------------------------
// TS-04-22: CI Go job installs golangci-lint
// ---------------------------------------------------------------------------

func TestTS04_22(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	goJob := asMap(jobs["go"])
	if goJob == nil {
		t.Fatal("jobs.go not found in ci.yml")
	}

	steps := asSlice(goJob["steps"])
	uses := stepsUses(steps)
	runs := stepsRuns(steps)

	if !anyContains(uses, "golangci-lint") && !anyContains(runs, "golangci-lint") {
		t.Errorf("go job does not install or invoke golangci-lint; uses: %v, runs: %v", uses, runs)
	}
}

// ---------------------------------------------------------------------------
// TS-04-E1: Python CI job has conditional to skip when pyproject.toml missing
// ---------------------------------------------------------------------------

func TestTS04_E01(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	pyJob := asMap(jobs["python"])
	if pyJob == nil {
		t.Fatal("jobs.python not found in ci.yml")
	}

	ifCond := fmt.Sprintf("%v", pyJob["if"])
	if !strings.Contains(ifCond, "hashFiles") || !strings.Contains(ifCond, "pyproject.toml") {
		t.Errorf("python job 'if' condition does not use hashFiles('pyproject.toml'); got: %q", ifCond)
	}
}

// ---------------------------------------------------------------------------
// TS-04-E2: CI step failures propagate — no continue-on-error: true
// ---------------------------------------------------------------------------

func TestTS04_E02(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	jobs := asMap(ci["jobs"])
	for jobName, job := range jobs {
		j := asMap(job)
		if j == nil {
			continue
		}
		for i, s := range asSlice(j["steps"]) {
			if step, ok := s.(map[string]any); ok {
				if coe, exists := step["continue-on-error"]; exists {
					if b, ok := coe.(bool); ok && b {
						t.Errorf("job %q step %d has continue-on-error: true", jobName, i)
					}
				}
			}
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-E3: check-version.sh exits 1 on version mismatch
// ---------------------------------------------------------------------------

func TestTS04_E03(t *testing.T) {
	root := repoRoot(t)
	script := filepath.Join(root, "scripts", "check-version.sh")

	if _, err := os.Stat(script); os.IsNotExist(err) {
		t.Fatal("scripts/check-version.sh does not exist")
	}

	// internal/version/version.go has "0.0.0-dev"; tag has "1.0.0" — mismatch
	cmd := exec.Command(script, "go", "pkg/afspec/v1.0.0")
	cmd.Dir = root
	out, err := cmd.CombinedOutput()

	if err == nil {
		t.Errorf("check-version.sh should exit non-zero on version mismatch, but exited 0; output:\n%s", out)
		return
	}

	exitErr, ok := err.(*exec.ExitError)
	if !ok || exitErr.ExitCode() != 1 {
		t.Errorf("check-version.sh should exit 1 on mismatch; got: %v; output:\n%s", err, out)
		return
	}

	if !strings.Contains(strings.ToLower(string(out)), "mismatch") {
		t.Errorf("check-version.sh mismatch output should contain 'mismatch'; got:\n%s", out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-E4: uv build step before gh release create, no continue-on-error
// ---------------------------------------------------------------------------

func TestTS04_E04(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	jobs := asMap(rel["jobs"])
	pyJob := asMap(jobs["release-python"])
	if pyJob == nil {
		t.Fatal("jobs.release-python not found in release.yml")
	}

	steps := asSlice(pyJob["steps"])
	buildIdx := findStepRunIndex(steps, "uv build")
	releaseIdx := findStepRunIndex(steps, "gh release create")

	if buildIdx < 0 {
		t.Error("release-python job missing 'uv build' step")
		return
	}
	if releaseIdx < 0 {
		t.Error("release-python job missing 'gh release create' step")
		return
	}
	if buildIdx >= releaseIdx {
		t.Errorf("uv build (idx %d) must come before gh release create (idx %d)", buildIdx, releaseIdx)
	}

	// Build step must not have continue-on-error: true
	if step, ok := steps[buildIdx].(map[string]any); ok {
		if coe, exists := step["continue-on-error"]; exists {
			if b, ok := coe.(bool); ok && b {
				t.Error("uv build step has continue-on-error: true")
			}
		}
	}
}

// ---------------------------------------------------------------------------
// TS-04-E5: check-version.sh rejects invalid tag formats
// ---------------------------------------------------------------------------

func TestTS04_E05(t *testing.T) {
	root := repoRoot(t)
	script := filepath.Join(root, "scripts", "check-version.sh")

	if _, err := os.Stat(script); os.IsNotExist(err) {
		t.Fatal("scripts/check-version.sh does not exist")
	}

	cases := []struct {
		lang string
		tag  string
	}{
		{"go", "pkg/afspec/vnotaversion"},
		{"python", "afspec-v1.0"},      // missing patch
		{"go", "pkg/afspec/v1.0.0.0"}, // extra component
		{"python", "afspec-vfoo"},
	}

	for _, tc := range cases {
		t.Run(fmt.Sprintf("%s/%s", tc.lang, tc.tag), func(t *testing.T) {
			cmd := exec.Command(script, tc.lang, tc.tag)
			cmd.Dir = root
			out, err := cmd.CombinedOutput()
			if err == nil {
				t.Errorf("check-version.sh should fail for invalid tag %q, but exited 0; output:\n%s", tc.tag, out)
				return
			}
			exitErr, ok := err.(*exec.ExitError)
			if !ok || exitErr.ExitCode() == 0 {
				t.Errorf("check-version.sh should exit non-zero for invalid tag %q; got: %v; output:\n%s",
					tc.tag, err, out)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// TS-04-E6: make check succeeds with skip warnings when neither language is configured
// ---------------------------------------------------------------------------

func TestTS04_E06(t *testing.T) {
	root := repoRoot(t)
	tmpDir := t.TempDir()

	copyFile(t, filepath.Join(root, "Makefile"), filepath.Join(tmpDir, "Makefile"))

	// Neither go.mod nor pyproject.toml in tmpDir
	out, code := runMake(t, tmpDir, "check")
	if code != 0 {
		t.Errorf("make check exited %d (want 0) with no languages configured; output:\n%s", code, out)
	}

	outLower := strings.ToLower(out)
	if !strings.Contains(outLower, "skipping go") {
		t.Errorf("make check did not print 'Skipping Go' message; output:\n%s", out)
	}
	if !strings.Contains(outLower, "skipping python") {
		t.Errorf("make check did not print 'Skipping Python' message; output:\n%s", out)
	}
}

// ---------------------------------------------------------------------------
// TS-04-E7: .golangci.yml exists (documents golangci-lint default fallback)
// ---------------------------------------------------------------------------

func TestTS04_E07(t *testing.T) {
	root := repoRoot(t)
	path := filepath.Join(root, ".golangci.yml")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Fatal(".golangci.yml does not exist at repo root")
	}
}

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

// TestPropertyP1: Tag pattern exclusivity — for any semver, Go and Python tags
// match their respective regex and not the other's.
func TestPropertyP1(t *testing.T) {
	versions := []struct{ M, N, P int }{
		{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {0, 0, 1},
		{1, 2, 3}, {10, 20, 30}, {999, 0, 0}, {0, 999, 0},
		{100, 200, 300}, {0, 0, 999},
	}

	for _, v := range versions {
		ver := fmt.Sprintf("%d.%d.%d", v.M, v.N, v.P)
		goTag := "pkg/afspec/v" + ver
		pyTag := "afspec-v" + ver

		t.Run(ver, func(t *testing.T) {
			if !goTagRe.MatchString(goTag) {
				t.Errorf("Go tag %q should match goTagRe", goTag)
			}
			if pyTagRe.MatchString(goTag) {
				t.Errorf("Go tag %q should NOT match pyTagRe", goTag)
			}
			if !pyTagRe.MatchString(pyTag) {
				t.Errorf("Python tag %q should match pyTagRe", pyTag)
			}
			if goTagRe.MatchString(pyTag) {
				t.Errorf("Python tag %q should NOT match goTagRe", pyTag)
			}
		})
	}
}

// TestPropertyP2: Version extraction correctness — check-version.sh exits 0
// when the tag version matches the version in the code file.
// Uses absolute path to script with tmpdir as cwd (per Skeptic finding).
func TestPropertyP2(t *testing.T) {
	root := repoRoot(t)
	script := filepath.Join(root, "scripts", "check-version.sh")

	if _, err := os.Stat(script); os.IsNotExist(err) {
		t.Fatal("scripts/check-version.sh does not exist")
	}

	versions := []string{"0.0.0", "1.0.0", "0.1.0", "1.2.3", "10.20.30", "0.0.1", "99.0.0"}

	for _, ver := range versions {
		t.Run(ver, func(t *testing.T) {
			tmpDir := t.TempDir()

			// Create internal/version/version.go with the test version
			versionDir := filepath.Join(tmpDir, "internal", "version")
			if err := os.MkdirAll(versionDir, 0o755); err != nil {
				t.Fatalf("cannot create version dir: %v", err)
			}
			versionContent := fmt.Sprintf("package version\n\nconst Version = %q\n", ver)
			if err := os.WriteFile(filepath.Join(versionDir, "version.go"), []byte(versionContent), 0o644); err != nil {
				t.Fatalf("cannot write version.go: %v", err)
			}

			// Run the script from tmpdir using absolute path (Skeptic finding: relative invocation fails)
			tag := "pkg/afspec/v" + ver
			cmd := exec.Command(script, "go", tag)
			cmd.Dir = tmpDir
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Errorf("check-version.sh go %q should exit 0 when versions match; got: %v; output:\n%s",
					tag, err, out)
			}
		})
	}
}

// TestPropertyP3: Makefile graceful degradation — make check exits 0 for all
// combinations of present/absent Go and Python project structures.
func TestPropertyP3(t *testing.T) {
	root := repoRoot(t)

	cases := []struct {
		goPresent     bool
		pythonPresent bool
	}{
		{false, false},
		{true, false},
		{false, true},
		{true, true},
	}

	for _, tc := range cases {
		name := fmt.Sprintf("go=%v,python=%v", tc.goPresent, tc.pythonPresent)
		t.Run(name, func(t *testing.T) {
			tmpDir := t.TempDir()
			copyFile(t, filepath.Join(root, "Makefile"), filepath.Join(tmpDir, "Makefile"))

			if tc.goPresent {
				goModContent := "module example.com/test\n\ngo 1.21\n"
				if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte(goModContent), 0o644); err != nil {
					t.Fatalf("cannot write go.mod: %v", err)
				}
				// Minimal Go file so go vet and go test have a package to process
				if err := os.MkdirAll(filepath.Join(tmpDir, "pkg"), 0o755); err != nil {
					t.Fatalf("cannot create pkg dir: %v", err)
				}
				goSrc := "package pkg\n"
				if err := os.WriteFile(filepath.Join(tmpDir, "pkg", "pkg.go"), []byte(goSrc), 0o644); err != nil {
					t.Fatalf("cannot write pkg.go: %v", err)
				}
			}

			if tc.pythonPresent {
				pyprojectContent := "[project]\nname = \"test\"\nversion = \"0.0.0\"\n"
				if err := os.WriteFile(filepath.Join(tmpDir, "pyproject.toml"), []byte(pyprojectContent), 0o644); err != nil {
					t.Fatalf("cannot write pyproject.toml: %v", err)
				}
			}

			out, code := runMake(t, tmpDir, "check")
			if code != 0 {
				t.Errorf("make check exited %d (want 0) for %s; output:\n%s", code, name, out)
			}
		})
	}
}

// TestPropertyP4: CI trigger correctness — workflow triggers on main/develop only.
func TestPropertyP4(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	onSection := asMap(ci["on"])
	pushSection := asMap(onSection["push"])
	prSection := asMap(onSection["pull_request"])

	var pushBranches, prBranches []string
	for _, b := range asSlice(pushSection["branches"]) {
		if s, ok := b.(string); ok {
			pushBranches = append(pushBranches, s)
		}
	}
	for _, b := range asSlice(prSection["branches"]) {
		if s, ok := b.(string); ok {
			prBranches = append(prBranches, s)
		}
	}

	allBranches := []string{"main", "develop", "feature/foo", "release/1.0", "hotfix/bar", "master"}
	for _, branch := range allBranches {
		expected := branch == "main" || branch == "develop"

		if got := containsString(pushBranches, branch); got != expected {
			t.Errorf("push.branches: branch %q: present=%v, want %v", branch, got, expected)
		}
		if got := containsString(prBranches, branch); got != expected {
			t.Errorf("pull_request.branches: branch %q: present=%v, want %v", branch, got, expected)
		}
	}
}

// ---------------------------------------------------------------------------
// Smoke Tests
// ---------------------------------------------------------------------------

// TestSmoke1: Local quality gate end-to-end — make check from repo root.
func TestSmoke1(t *testing.T) {
	if os.Getenv(testRecursionGuard) != "" {
		t.Skip("skipping: recursive invocation from make")
	}
	root := repoRoot(t)

	if _, err := exec.LookPath("golangci-lint"); err != nil {
		t.Skip("golangci-lint not installed; skipping TestSmoke1")
	}

	out, code := runMake(t, root, "check")
	if code != 0 {
		t.Errorf("make check exited %d; output:\n%s", code, out)
	}
	if !strings.Contains(out, "ok") && !strings.Contains(out, "PASS") {
		t.Errorf("make check did not produce 'ok' or 'PASS' in output; got:\n%s", out)
	}
}

// TestSmoke2: CI workflow structural completeness.
func TestSmoke2(t *testing.T) {
	root := repoRoot(t)
	ci := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "ci.yml"))

	onSection := asMap(ci["on"])
	if onSection == nil {
		t.Fatal("ci.yml missing 'on' section")
	}
	if onSection["push"] == nil || onSection["pull_request"] == nil {
		t.Errorf("ci.yml 'on' section missing push or pull_request triggers; on: %v", onSection)
	}

	jobs := asMap(ci["jobs"])
	if jobs == nil {
		t.Fatal("ci.yml missing 'jobs' section")
	}
	if jobs["go"] == nil {
		t.Error("ci.yml missing 'go' job")
	}
	if jobs["python"] == nil {
		t.Error("ci.yml missing 'python' job")
	}

	// Verify go job completeness
	goJob := asMap(jobs["go"])
	if goJob != nil {
		goSteps := asSlice(goJob["steps"])
		goUses := stepsUses(goSteps)
		goRuns := stepsRuns(goSteps)

		type check struct {
			desc string
			ok   func() bool
		}
		required := []check{
			{"actions/checkout", func() bool { return anyHasPrefix(goUses, "actions/checkout") }},
			{"actions/setup-go", func() bool { return anyHasPrefix(goUses, "actions/setup-go") }},
			{"golangci-lint", func() bool {
				return anyContains(goUses, "golangci-lint") || anyContains(goRuns, "golangci-lint")
			}},
			{"make lint-go", func() bool { return anyContains(goRuns, "make lint-go") }},
			{"make test-go", func() bool { return anyContains(goRuns, "make test-go") }},
		}
		for _, req := range required {
			if !req.ok() {
				t.Errorf("go job missing required element: %s", req.desc)
			}
		}
	}

	// Verify python job completeness
	pyJob := asMap(jobs["python"])
	if pyJob != nil {
		pySteps := asSlice(pyJob["steps"])
		pyUses := stepsUses(pySteps)
		pyRuns := stepsRuns(pySteps)

		type check struct {
			desc string
			ok   func() bool
		}
		required := []check{
			{"actions/checkout", func() bool { return anyHasPrefix(pyUses, "actions/checkout") }},
			{"actions/setup-python", func() bool { return anyHasPrefix(pyUses, "actions/setup-python") }},
			{"astral-sh/setup-uv", func() bool { return anyHasPrefix(pyUses, "astral-sh/setup-uv") }},
			{"make lint-python", func() bool { return anyContains(pyRuns, "make lint-python") }},
			{"make test-python", func() bool { return anyContains(pyRuns, "make test-python") }},
		}
		for _, req := range required {
			if !req.ok() {
				t.Errorf("python job missing required element: %s", req.desc)
			}
		}

		// Python job must have a conditional
		if pyJob["if"] == nil {
			t.Error("python job missing 'if' conditional")
		}
	}
}

// TestSmoke3: Go release workflow structural completeness.
func TestSmoke3(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	// Verify tag triggers
	onSection := asMap(rel["on"])
	pushSection := asMap(onSection["push"])
	tagsRaw := asSlice(pushSection["tags"])
	var tags []string
	for _, tg := range tagsRaw {
		if s, ok := tg.(string); ok {
			tags = append(tags, s)
		}
	}
	if !containsString(tags, "pkg/afspec/v*") {
		t.Errorf("release.yml does not trigger on 'pkg/afspec/v*'; tags: %v", tags)
	}

	// Verify permissions
	perms := asMap(rel["permissions"])
	if perms == nil || fmt.Sprintf("%v", perms["contents"]) != "write" {
		t.Errorf("release.yml missing 'permissions.contents: write'; permissions: %v", perms)
	}

	// Verify release-go job structure
	jobs := asMap(rel["jobs"])
	goJob := asMap(jobs["release-go"])
	if goJob == nil {
		t.Fatal("release.yml missing 'release-go' job")
	}

	steps := asSlice(goJob["steps"])
	checkoutIdx := findStepUsesIndex(steps, "actions/checkout")
	checkIdx := findStepRunIndex(steps, "check-version.sh")
	releaseIdx := findStepRunIndex(steps, "gh release create")

	if checkoutIdx < 0 {
		t.Error("release-go job missing checkout step")
	}
	if checkIdx < 0 {
		t.Error("release-go job missing check-version.sh step")
	}
	if releaseIdx < 0 {
		t.Error("release-go job missing gh release create step")
	}
	if checkoutIdx >= 0 && checkIdx >= 0 && checkoutIdx >= checkIdx {
		t.Errorf("checkout (idx %d) must come before check-version.sh (idx %d)", checkoutIdx, checkIdx)
	}
	if checkIdx >= 0 && releaseIdx >= 0 && checkIdx >= releaseIdx {
		t.Errorf("check-version.sh (idx %d) must come before gh release create (idx %d)", checkIdx, releaseIdx)
	}
}

// TestSmoke4: Python release workflow structural completeness.
func TestSmoke4(t *testing.T) {
	root := repoRoot(t)
	rel := parseWorkflow(t, filepath.Join(root, ".github", "workflows", "release.yml"))

	// Verify tag triggers
	onSection := asMap(rel["on"])
	pushSection := asMap(onSection["push"])
	tagsRaw := asSlice(pushSection["tags"])
	var tags []string
	for _, tg := range tagsRaw {
		if s, ok := tg.(string); ok {
			tags = append(tags, s)
		}
	}
	if !containsString(tags, "afspec-v*") {
		t.Errorf("release.yml does not trigger on 'afspec-v*'; tags: %v", tags)
	}

	// Verify permissions
	perms := asMap(rel["permissions"])
	if perms == nil || fmt.Sprintf("%v", perms["contents"]) != "write" {
		t.Errorf("release.yml missing 'permissions.contents: write'; permissions: %v", perms)
	}

	// Verify release-python job structure
	jobs := asMap(rel["jobs"])
	pyJob := asMap(jobs["release-python"])
	if pyJob == nil {
		t.Fatal("release.yml missing 'release-python' job")
	}

	ifCond := fmt.Sprintf("%v", pyJob["if"])
	if !strings.Contains(ifCond, "afspec-v") {
		t.Errorf("release-python 'if' does not reference 'afspec-v'; got: %q", ifCond)
	}

	steps := asSlice(pyJob["steps"])
	checkIdx := findStepRunIndex(steps, "check-version.sh")
	buildIdx := findStepRunIndex(steps, "uv build")
	releaseIdx := findStepRunIndex(steps, "gh release create")

	if checkIdx < 0 {
		t.Error("release-python job missing check-version.sh step")
	}
	if buildIdx < 0 {
		t.Error("release-python job missing uv build step")
	}
	if releaseIdx < 0 {
		t.Error("release-python job missing gh release create step")
	}
	if checkIdx >= 0 && buildIdx >= 0 && checkIdx >= buildIdx {
		t.Errorf("check-version.sh (idx %d) must come before uv build (idx %d)", checkIdx, buildIdx)
	}
	if buildIdx >= 0 && releaseIdx >= 0 && buildIdx >= releaseIdx {
		t.Errorf("uv build (idx %d) must come before gh release create (idx %d)", buildIdx, releaseIdx)
	}

	// gh release create must reference dist/
	for _, s := range steps {
		if step, ok := s.(map[string]any); ok {
			if r, ok := step["run"].(string); ok && strings.Contains(r, "gh release create") {
				if !strings.Contains(r, "dist/") {
					t.Errorf("gh release create step does not reference dist/; run: %q", r)
				}
			}
		}
	}
}
