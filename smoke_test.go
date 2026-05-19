package afspec_test

// smoke_test.go covers end-to-end integration smoke tests:
//   TS-01-SMOKE-1 (Load spec from disk end-to-end)
//   TS-01-SMOKE-2 (Save spec to disk end-to-end)
//   TS-01-SMOKE-3 (Validate spec end-to-end)
//   TS-01-SMOKE-4 (Render per-file end-to-end)
//   TS-01-SMOKE-5 (Render combined end-to-end)
//   TS-01-SMOKE-6 (Lifecycle transition end-to-end)
//   TS-01-SMOKE-7 (Bootstrap end-to-end)
//   TS-01-SMOKE-8 (Discover specs end-to-end)

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-SMOKE-1: Load spec from disk end-to-end
// ---------------------------------------------------------------------------

func TestSmoke1(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}
	if spec == nil {
		t.Fatal("LoadSpec returned nil spec")
	}

	// All four artifacts must be populated
	if spec.PRD == nil {
		t.Error("spec.PRD is nil")
	}
	if spec.Requirements == nil {
		t.Error("spec.Requirements is nil")
	}
	if spec.TestSpec == nil {
		t.Error("spec.TestSpec is nil")
	}
	if spec.Tasks == nil {
		t.Error("spec.Tasks is nil")
	}

	// PRD frontmatter fields must be populated
	if spec.PRD != nil {
		if spec.PRD.Frontmatter.SpecID == "" {
			t.Error("PRD.Frontmatter.SpecID is empty")
		}
		if spec.PRD.Frontmatter.SpecName == "" {
			t.Error("PRD.Frontmatter.SpecName is empty")
		}
	}

	// Requirements must have at least one requirement
	if spec.Requirements != nil && len(spec.Requirements.Requirements) == 0 {
		t.Error("spec.Requirements.Requirements is empty")
	}

	// TestSpec must have at least one test case
	if spec.TestSpec != nil && len(spec.TestSpec.TestCases) == 0 {
		t.Error("spec.TestSpec.TestCases is empty")
	}

	// Tasks must have task groups
	if spec.Tasks != nil && len(spec.Tasks.TaskGroups) == 0 {
		t.Error("spec.Tasks.TaskGroups is empty")
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-2: Save spec to disk end-to-end
// ---------------------------------------------------------------------------

func TestSmoke2(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	// All four files must exist
	for _, f := range []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"} {
		if _, err := os.Stat(filepath.Join(tmpdir, f)); os.IsNotExist(err) {
			t.Errorf("file %q should exist after SaveSpec", f)
		}
	}

	// Round-trip: reload should produce the same spec
	spec2, err := afspec.LoadSpec(tmpdir)
	if err != nil {
		t.Fatalf("LoadSpec (round-trip): %v", err)
	}
	if spec2.PRD.Frontmatter.SpecID != spec.PRD.Frontmatter.SpecID {
		t.Errorf("SpecID mismatch after round-trip: %q vs %q",
			spec2.PRD.Frontmatter.SpecID, spec.PRD.Frontmatter.SpecID)
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-3: Validate spec end-to-end
// ---------------------------------------------------------------------------

func TestSmoke3(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	errs, err := afspec.Validate(spec)
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}

	// Valid spec must produce zero errors
	for _, e := range errs {
		if e.Severity == afspec.SeverityError {
			t.Errorf("Validate produced unexpected error: %+v", e)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-4: Render per-file end-to-end
// ---------------------------------------------------------------------------

func TestSmoke4(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/all_ears_patterns")
	if err != nil {
		t.Fatalf("LoadSpec all_ears_patterns: %v", err)
	}

	md, err := afspec.RenderRequirements(spec.Requirements)
	if err != nil {
		t.Fatalf("RenderRequirements: %v", err)
	}
	if len(md) == 0 {
		t.Fatal("RenderRequirements returned empty output")
	}

	content := string(md)
	// Must contain EARS-pattern keywords
	if !strings.Contains(content, "SHALL") {
		t.Error("rendered requirements should contain 'SHALL'")
	}
	if !strings.Contains(content, "WHEN") {
		t.Error("rendered requirements should contain 'WHEN' (event_driven pattern)")
	}
	if !strings.Contains(content, "WHILE") {
		t.Error("rendered requirements should contain 'WHILE' (state_driven pattern)")
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-5: Render combined end-to-end
// ---------------------------------------------------------------------------

func TestSmoke5(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	combined, err := afspec.RenderCombined(spec)
	if err != nil {
		t.Fatalf("RenderCombined: %v", err)
	}
	if len(combined) == 0 {
		t.Fatal("RenderCombined returned empty output")
	}

	content := string(combined)

	// PRD body must appear verbatim
	prdSnippet := "## Intent"
	if !strings.Contains(content, prdSnippet) {
		t.Errorf("combined output should contain PRD body snippet %q", prdSnippet)
	}

	// SHALL from EARS rendering
	if !strings.Contains(content, "SHALL") {
		t.Error("combined output should contain 'SHALL' from rendered requirements")
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-6: Lifecycle transition end-to-end
// ---------------------------------------------------------------------------

func TestSmoke6(t *testing.T) {
	draft, err := afspec.LoadSpec("testdata/draft_spec")
	if err != nil {
		t.Fatalf("LoadSpec draft_spec: %v", err)
	}
	if draft.PRD.Frontmatter.Status != afspec.StatusDraft {
		t.Skipf("draft_spec status = %q, not draft", draft.PRD.Frontmatter.Status)
	}

	active, err := afspec.Transition(draft, afspec.StatusActive)
	if err != nil {
		t.Fatalf("Transition draft→active: %v", err)
	}
	if active == nil {
		t.Fatal("Transition returned nil spec")
	}

	// Status must be active
	if active.PRD.Frontmatter.Status != afspec.StatusActive {
		t.Errorf("Status = %q, want %q", active.PRD.Frontmatter.Status, afspec.StatusActive)
	}

	// IntentHash must be set and be a 64-char hex string
	if active.PRD.Frontmatter.IntentHash == nil {
		t.Fatal("IntentHash must be set after draft→active transition")
	}
	hash := *active.PRD.Frontmatter.IntentHash
	if len(hash) != 64 {
		t.Errorf("IntentHash length = %d, want 64 (SHA-256 hex)", len(hash))
	}

	// Original spec must be unchanged (immutable)
	if draft.PRD.Frontmatter.Status != afspec.StatusDraft {
		t.Error("Transition modified original spec's status (must be immutable)")
	}
	if draft.PRD.Frontmatter.IntentHash != nil {
		t.Error("Transition modified original spec's IntentHash (must be immutable)")
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-7: Bootstrap end-to-end
// ---------------------------------------------------------------------------

func TestSmoke7(t *testing.T) {
	tmpdir := t.TempDir()
	specDir := filepath.Join(tmpdir, "05_new_feature")

	bs, err := afspec.NewBootstrap(specDir, "05", "new_feature")
	if err != nil {
		t.Fatalf("NewBootstrap: %v", err)
	}

	if err := bs.WritePRD(makeBootstrapPRD("05", "new_feature")); err != nil {
		t.Fatalf("WritePRD: %v", err)
	}
	if err := bs.WriteRequirements(makeBootstrapReq("05", "new_feature")); err != nil {
		t.Fatalf("WriteRequirements: %v", err)
	}
	if err := bs.WriteTestSpec(makeBootstrapTestSpec("05", "new_feature")); err != nil {
		t.Fatalf("WriteTestSpec: %v", err)
	}
	if err := bs.WriteTasks(makeBootstrapTasks("05", "new_feature")); err != nil {
		t.Fatalf("WriteTasks: %v", err)
	}

	spec, err := bs.Finalize()
	if err != nil {
		t.Fatalf("Finalize: %v", err)
	}
	if spec == nil {
		t.Fatal("Finalize returned nil spec")
	}

	// Validate the finalized spec
	errs, err := afspec.Validate(spec)
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}
	for _, e := range errs {
		if e.Severity == afspec.SeverityError {
			t.Errorf("Validate found error on bootstrapped spec: %+v", e)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-SMOKE-8: Discover specs end-to-end
// ---------------------------------------------------------------------------

func TestSmoke8(t *testing.T) {
	root := t.TempDir()

	// Create two complete specs: 01 (base), 02 (depends on 01)
	createSpecDir(t, root, "01", "base")
	createSpecDirWithDependency(t, root, "02", "dependent", "01")

	// Create an archive folder with an old spec (should be excluded)
	archiveDir := filepath.Join(root, "archive")
	if err := os.MkdirAll(archiveDir, 0755); err != nil {
		t.Fatalf("MkdirAll archive: %v", err)
	}
	createSpecDir(t, archiveDir, "03", "old")

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}
	if result == nil {
		t.Fatal("DiscoverSpecs returned nil")
	}

	// Must find exactly 2 entries (archive excluded)
	if len(result.Entries) != 2 {
		t.Errorf("DiscoverSpecs found %d entries, want 2", len(result.Entries))
	}

	// Graph must have edge 02 → 01
	if result.Graph == nil {
		t.Fatal("dependency graph is nil")
	}
	deps := result.Graph.Edges["02"]
	found := false
	for _, d := range deps {
		if d == "01" {
			found = true
		}
	}
	if !found {
		t.Errorf("graph edges['02'] should contain '01'; got %v", deps)
	}

	// Topological order must place 01 before 02
	order, err := result.Graph.TopologicalOrder()
	if err != nil {
		t.Fatalf("TopologicalOrder: %v", err)
	}

	i01, i02 := -1, -1
	for i, id := range order {
		switch id {
		case "01":
			i01 = i
		case "02":
			i02 = i
		}
	}
	if i01 < 0 || i02 < 0 {
		t.Errorf("TopologicalOrder missing '01' or '02': %v", order)
	} else if i01 >= i02 {
		t.Errorf("TopologicalOrder: '01' (pos %d) should come before '02' (pos %d)", i01, i02)
	}
}

// Note: createSpecDir, createSpecDirWithDependency, makeBootstrapPRD, etc. are
// defined in discover_test.go and bootstrap_test.go (same package afspec_test).
