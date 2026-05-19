package afspec_test

// bootstrap_test.go covers:
//   TS-01-34  (BootstrapSpec API creation)
//   TS-01-35  (Bootstrap defers cross-file validation)
//   TS-01-36  (Bootstrap Finalize runs full validation)
//   TS-01-37  (Bootstrap write files independently)
//   TS-01-E17 (Finalize before all files written)
//   TS-01-E18 (Bootstrap overwrites duplicate file)
//   TS-01-E19 (Bootstrap on existing folder)
//   TS-01-P8  (Bootstrap deferred validation property)

import (
	"os"
	"path/filepath"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-34: BootstrapSpec API creation
// ---------------------------------------------------------------------------

func TestTS01_34(t *testing.T) {
	tmpdir := t.TempDir()
	specDir := filepath.Join(tmpdir, "05_my_feature")

	bs, err := afspec.NewBootstrap(specDir, "05", "my_feature")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}
	if bs == nil {
		t.Fatal("NewBootstrap returned nil Bootstrap handle")
	}

	// Directory must be created
	info, statErr := os.Stat(specDir)
	if os.IsNotExist(statErr) {
		t.Errorf("NewBootstrap should create directory %q", specDir)
	} else if !info.IsDir() {
		t.Errorf("%q is not a directory", specDir)
	}
}

// ---------------------------------------------------------------------------
// TS-01-35: Bootstrap defers cross-file validation
// ---------------------------------------------------------------------------

func TestTS01_35(t *testing.T) {
	tmpdir := t.TempDir()
	bs, err := afspec.NewBootstrap(filepath.Join(tmpdir, "01_bs_test"), "01", "bs_test")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	prd := makeBootstrapPRD("01", "bs_test")

	// Writing only prd.md should succeed (no cross-file validation yet)
	if err := bs.WritePRD(prd); err != nil {
		t.Fatalf("WritePRD: %v", err)
	}

	specDir := filepath.Join(tmpdir, "01_bs_test")
	// prd.md must exist
	if _, err := os.Stat(filepath.Join(specDir, "prd.md")); os.IsNotExist(err) {
		t.Error("prd.md should exist after WritePRD")
	}
	// requirements.json must NOT exist yet
	if _, err := os.Stat(filepath.Join(specDir, "requirements.json")); !os.IsNotExist(err) {
		t.Error("requirements.json should not exist before WriteRequirements")
	}
}

// ---------------------------------------------------------------------------
// TS-01-36: Bootstrap Finalize runs full validation
// ---------------------------------------------------------------------------

func TestTS01_36(t *testing.T) {
	tmpdir := t.TempDir()
	specDir := filepath.Join(tmpdir, "01_full_bs")
	bs, err := afspec.NewBootstrap(specDir, "01", "full_bs")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	if err := bs.WritePRD(makeBootstrapPRD("01", "full_bs")); err != nil {
		t.Fatalf("WritePRD: %v", err)
	}
	if err := bs.WriteRequirements(makeBootstrapReq("01", "full_bs")); err != nil {
		t.Fatalf("WriteRequirements: %v", err)
	}
	if err := bs.WriteTestSpec(makeBootstrapTestSpec("01", "full_bs")); err != nil {
		t.Fatalf("WriteTestSpec: %v", err)
	}
	if err := bs.WriteTasks(makeBootstrapTasks("01", "full_bs")); err != nil {
		t.Fatalf("WriteTasks: %v", err)
	}

	spec, err := bs.Finalize()
	if err != nil {
		t.Fatalf("Finalize: %v", err)
	}
	if spec == nil {
		t.Fatal("Finalize returned nil Spec")
	}
	if spec.PRD == nil {
		t.Error("Finalize.Spec.PRD is nil")
	}
	if spec.Requirements == nil {
		t.Error("Finalize.Spec.Requirements is nil")
	}
	if spec.TestSpec == nil {
		t.Error("Finalize.Spec.TestSpec is nil")
	}
	if spec.Tasks == nil {
		t.Error("Finalize.Spec.Tasks is nil")
	}
}

// ---------------------------------------------------------------------------
// TS-01-37: Bootstrap write files independently (any order)
// ---------------------------------------------------------------------------

func TestTS01_37(t *testing.T) {
	tmpdir := t.TempDir()
	bs, err := afspec.NewBootstrap(filepath.Join(tmpdir, "01_order_test"), "01", "order_test")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	// Write in non-standard order: tasks first, then req, ts, prd
	if err := bs.WriteTasks(makeBootstrapTasks("01", "order_test")); err != nil {
		t.Fatalf("WriteTasks: %v", err)
	}
	if err := bs.WriteRequirements(makeBootstrapReq("01", "order_test")); err != nil {
		t.Fatalf("WriteRequirements: %v", err)
	}
	if err := bs.WriteTestSpec(makeBootstrapTestSpec("01", "order_test")); err != nil {
		t.Fatalf("WriteTestSpec: %v", err)
	}
	if err := bs.WritePRD(makeBootstrapPRD("01", "order_test")); err != nil {
		t.Fatalf("WritePRD: %v", err)
	}

	spec, err := bs.Finalize()
	if err != nil {
		t.Fatalf("Finalize after out-of-order writes: %v", err)
	}
	if spec == nil {
		t.Fatal("Finalize returned nil after out-of-order writes")
	}
}

// ---------------------------------------------------------------------------
// TS-01-E17: Finalize before all files written
// ---------------------------------------------------------------------------

func TestTS01_E17(t *testing.T) {
	tmpdir := t.TempDir()
	bs, err := afspec.NewBootstrap(filepath.Join(tmpdir, "01_partial"), "01", "partial")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	// Write only prd.md
	if err := bs.WritePRD(makeBootstrapPRD("01", "partial")); err != nil {
		t.Fatalf("WritePRD: %v", err)
	}

	spec, err := bs.Finalize()
	if err == nil {
		t.Fatal("Finalize should fail with incomplete spec, got nil error")
	}
	if spec != nil {
		t.Errorf("Finalize should return nil spec on error, got %v", spec)
	}

	// Error must be IncompleteSpecError
	incErr, ok := err.(*afspec.IncompleteSpecError)
	if !ok {
		t.Errorf("Finalize error should be *IncompleteSpecError, got %T: %v", err, err)
	} else {
		// Missing files must be reported
		for _, f := range []string{"requirements.json", "test_spec.json", "tasks.json"} {
			found := false
			for _, missing := range incErr.MissingFiles {
				if missing == f {
					found = true
					break
				}
			}
			if !found {
				t.Errorf("IncompleteSpecError should list %q as missing; got %v", f, incErr.MissingFiles)
			}
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-E18: Bootstrap overwrites duplicate file
// ---------------------------------------------------------------------------

func TestTS01_E18(t *testing.T) {
	tmpdir := t.TempDir()
	bs, err := afspec.NewBootstrap(filepath.Join(tmpdir, "01_overwrite"), "01", "overwrite")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	prdA := makeBootstrapPRD("01", "overwrite")
	prdA.Frontmatter.Title = "Version A"

	if err := bs.WritePRD(prdA); err != nil {
		t.Fatalf("WritePRD (A): %v", err)
	}

	prdB := makeBootstrapPRD("01", "overwrite")
	prdB.Frontmatter.Title = "Version B"

	// Second write should succeed (overwrite)
	if err := bs.WritePRD(prdB); err != nil {
		t.Fatalf("WritePRD (B — overwrite): %v", err)
	}

	// File on disk should contain Version B
	specDir := filepath.Join(tmpdir, "01_overwrite")
	data, err := os.ReadFile(filepath.Join(specDir, "prd.md"))
	if err != nil {
		t.Fatalf("ReadFile prd.md: %v", err)
	}
	content := string(data)
	if !containsString(content, "Version B") {
		t.Errorf("prd.md should contain 'Version B' after overwrite; content = %q", content[:min(200, len(content))])
	}
	if containsString(content, "Version A") {
		t.Errorf("prd.md should NOT contain 'Version A' after overwrite; content = %q", content[:min(200, len(content))])
	}
}

// containsString is a helper to check substring presence.
func containsString(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsSubstr(s, substr))
}

func containsSubstr(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------------------
// TS-01-E19: Bootstrap on existing folder
// ---------------------------------------------------------------------------

func TestTS01_E19(t *testing.T) {
	tmpdir := t.TempDir()
	existing := filepath.Join(tmpdir, "01_existing")
	if err := os.MkdirAll(existing, 0755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}

	bs, err := afspec.NewBootstrap(existing, "01", "existing")
	if err == nil {
		t.Fatal("NewBootstrap should fail for existing directory, got nil error")
	}
	if bs != nil {
		t.Errorf("NewBootstrap should return nil handle on error, got %v", bs)
	}
}

// ---------------------------------------------------------------------------
// TS-01-P8: Bootstrap deferred validation (property test)
// ---------------------------------------------------------------------------

func TestPropertyP8(t *testing.T) {
	// Writing any subset of 1-3 files should not trigger cross-file errors.
	type fileWriter struct {
		name  string
		write func(bs *afspec.Bootstrap) error
	}

	writers := []fileWriter{
		{"prd", func(bs *afspec.Bootstrap) error {
			return bs.WritePRD(makeBootstrapPRD("01", "p8_test"))
		}},
		{"requirements", func(bs *afspec.Bootstrap) error {
			return bs.WriteRequirements(makeBootstrapReq("01", "p8_test"))
		}},
		{"testspec", func(bs *afspec.Bootstrap) error {
			return bs.WriteTestSpec(makeBootstrapTestSpec("01", "p8_test"))
		}},
		{"tasks", func(bs *afspec.Bootstrap) error {
			return bs.WriteTasks(makeBootstrapTasks("01", "p8_test"))
		}},
	}

	// Test each individual file write (no cross-file errors expected)
	for _, w := range writers {
		t.Run("single_"+w.name, func(t *testing.T) {
			tmpdir := t.TempDir()
			bs, err := afspec.NewBootstrap(filepath.Join(tmpdir, "01_p8_test"), "01", "p8_test")
			if err != nil {
				t.Fatalf("NewBootstrap: %v", err)
			}
			if err := w.write(bs); err != nil {
				t.Fatalf("writing %s should not produce cross-file errors: %v", w.name, err)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// Bootstrap test helpers
// ---------------------------------------------------------------------------

func makeBootstrapPRD(specID, specName string) *afspec.PRD {
	return &afspec.PRD{
		Frontmatter: afspec.Frontmatter{
			SpecID:        specID,
			SpecName:      specName,
			Title:         "Bootstrap Test",
			Status:        afspec.StatusDraft,
			CreatedAt:     "2026-01-01T00:00:00Z",
			UpdatedAt:     "2026-01-01T00:00:00Z",
			Owner:         "test",
			Source:        "test",
			Supersedes:    []string{},
			Tags:          []string{},
			SchemaVersion: 1,
		},
		Body: "# Bootstrap Test\n\n## Intent\n\nTest the bootstrap workflow.\n",
	}
}

func makeBootstrapReq(specID, specName string) *afspec.Requirements {
	return &afspec.Requirements{
		SpecID:   specID,
		SpecName: specName,
		Requirements: []afspec.Requirement{
			{
				ID:    specID + "-REQ-1",
				Title: "R1",
				UserStory: afspec.UserStory{
					Role:    "consumer",
					Goal:    "bootstrap",
					Benefit: "create specs",
				},
				AcceptanceCriteria: []afspec.Criterion{
					{
						ID:          specID + "-REQ-1.1",
						EarsPattern: "ubiquitous",
						System:      "the library",
						Action:      "create a spec",
					},
				},
				EdgeCases: []afspec.Criterion{},
			},
		},
		CorrectnessProperties: []afspec.CorrectnessProperty{},
		ExecutionPaths:        []afspec.ExecutionPath{},
		ErrorHandling:         []afspec.ErrorHandlingEntry{},
		Glossary:              map[string]string{},
		SchemaVersion:         1,
	}
}

func makeBootstrapTestSpec(specID, specName string) *afspec.TestSpecDoc {
	return &afspec.TestSpecDoc{
		SpecID:   specID,
		SpecName: specName,
		TestCases: []afspec.TestCase{
			{
				ID:                  "TS-" + specID + "-1",
				RequirementID:       specID + "-REQ-1.1",
				Kind:                "unit",
				Description:         "test spec creation",
				Preconditions:       []string{},
				AssertionPseudocode: "ASSERT spec != nil",
			},
		},
		PropertyTests: []afspec.PropertyTest{},
		EdgeCaseTests: []afspec.EdgeCaseTest{},
		SmokeTests:    []afspec.SmokeTest{},
		Coverage: afspec.Coverage{
			RequirementsCovered: []string{specID + "-REQ-1.1"},
			PropertiesCovered:   []string{},
			PathsCovered:        []string{},
			Gaps:                []string{},
		},
		SchemaVersion: 1,
	}
}

func makeBootstrapTasks(specID, specName string) *afspec.Tasks {
	return &afspec.Tasks{
		SpecID:   specID,
		SpecName: specName,
		TestCommands: afspec.TestCommands{
			SpecTests: "go test ./...",
			AllTests:  "go test ./...",
			Linter:    "go vet ./...",
		},
		Dependencies: []afspec.TaskDependency{},
		TaskGroups: []afspec.TaskGroup{
			{
				ID:    1,
				Kind:  "tests",
				Title: "Tests",
				Subtasks: []afspec.Subtask{
					{
						ID:              "1.1",
						Title:           "Write tests",
						Details:         []string{},
						TestSpecRefs:    []string{"TS-" + specID + "-1"},
						RequirementRefs: []string{specID + "-REQ-1.1"},
						State:           afspec.StatePending,
						Optional:        false,
					},
				},
				Verification: afspec.VerificationSubtask{
					ID:     "1.V",
					Checks: []string{"tests pass"},
				},
			},
			{
				ID:    2,
				Kind:  "wiring_verification",
				Title: "Wiring",
				Subtasks: []afspec.Subtask{},
				Verification: afspec.VerificationSubtask{
					ID:     "2.V",
					Checks: []string{},
				},
			},
		},
		Traceability: []afspec.TraceabilityEntry{
			{
				RequirementID: specID + "-REQ-1.1",
				TestSpecID:    "TS-" + specID + "-1",
				TaskID:        "1.1",
				TestPath:      nil,
			},
		},
		SchemaVersion: 1,
	}
}
