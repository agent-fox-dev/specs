package afspec_test

// load_test.go covers:
//   TS-01-7  (Load valid spec from disk)
//   TS-01-8  (PRD frontmatter and body parsing)
//   TS-01-9  (JSON file loading with type preservation)
//   TS-01-E3 (Missing files in spec folder)
//   TS-01-E4 (Malformed JSON file)
//   TS-01-E5 (Malformed YAML frontmatter)
//   TS-01-E6 (Missing Intent section)
//   TS-01-E7 (Non-existent spec folder)

import (
	"strings"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-7: Load valid spec from disk
// ---------------------------------------------------------------------------

func TestTS01_07(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}
	if spec == nil {
		t.Fatal("LoadSpec returned nil spec")
	}
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
	if spec.Dir == "" {
		t.Error("spec.Dir is empty")
	}
	if !strings.HasSuffix(spec.Dir, "testdata/valid_spec") && !strings.HasSuffix(spec.Dir, "testdata"+string([]byte{47})+"valid_spec") {
		t.Errorf("spec.Dir = %q, should end with testdata/valid_spec", spec.Dir)
	}
}

// ---------------------------------------------------------------------------
// TS-01-8: PRD frontmatter and body parsing
// ---------------------------------------------------------------------------

func TestTS01_08(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	fm := spec.PRD.Frontmatter
	if fm.SpecID != "99" {
		t.Errorf("Frontmatter.SpecID = %q, want %q", fm.SpecID, "99")
	}
	if fm.SpecName != "golden" {
		t.Errorf("Frontmatter.SpecName = %q, want %q", fm.SpecName, "golden")
	}
	if fm.Status != afspec.StatusActive {
		t.Errorf("Frontmatter.Status = %q, want %q", fm.Status, afspec.StatusActive)
	}

	body := spec.PRD.Body
	if !strings.Contains(body, "## Intent") {
		t.Error("PRD.Body does not contain '## Intent' section")
	}
	if !strings.Contains(body, "Build a golden fixture for testing.") {
		t.Errorf("PRD.Body does not contain expected Intent text; body = %q", body)
	}

	// Intent hash should be non-nil (spec is active)
	if fm.IntentHash == nil {
		t.Error("Frontmatter.IntentHash is nil for active spec")
	}
}

// ---------------------------------------------------------------------------
// TS-01-9: JSON file loading with type preservation
// ---------------------------------------------------------------------------

func TestTS01_09(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	reqs := spec.Requirements
	if len(reqs.Requirements) == 0 {
		t.Fatal("Requirements.Requirements is empty")
	}
	req := reqs.Requirements[0]
	if len(req.AcceptanceCriteria) == 0 {
		t.Fatal("AcceptanceCriteria is empty")
	}

	// The golden fixture has a criterion with return_contract: null
	ac := req.AcceptanceCriteria[0]
	if ac.ReturnContract != nil {
		t.Errorf("ReturnContract should be nil (null JSON), got %v", ac.ReturnContract)
	}

	// Edge case criterion also has return_contract: null
	if len(req.EdgeCases) == 0 {
		t.Fatal("EdgeCases is empty")
	}
	ec := req.EdgeCases[0]
	if ec.ReturnContract != nil {
		t.Errorf("EdgeCase ReturnContract should be nil, got %v", ec.ReturnContract)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E3: Missing files in spec folder
// ---------------------------------------------------------------------------

func TestTS01_E03(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/incomplete_spec")
	if err == nil {
		t.Fatal("expected error for incomplete spec folder, got nil")
	}
	if spec != nil {
		t.Errorf("spec should be nil on error, got non-nil")
	}

	errStr := err.Error()
	// Must mention each missing file
	for _, missing := range []string{"requirements.json", "test_spec.json", "tasks.json"} {
		if !strings.Contains(errStr, missing) {
			t.Errorf("error %q does not mention missing file %q", errStr, missing)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-E4: Malformed JSON file
// ---------------------------------------------------------------------------

func TestTS01_E04(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/malformed_json")
	if err == nil {
		t.Fatal("expected error for malformed JSON, got nil")
	}
	if spec != nil {
		t.Errorf("spec should be nil on error, got non-nil")
	}

	errStr := err.Error()
	if !strings.Contains(errStr, "requirements.json") {
		t.Errorf("error %q should mention 'requirements.json'", errStr)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E5: Malformed YAML frontmatter
// ---------------------------------------------------------------------------

func TestTS01_E05(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/bad_yaml")
	if err == nil {
		t.Fatal("expected error for malformed YAML, got nil")
	}
	if spec != nil {
		t.Errorf("spec should be nil on error, got non-nil")
	}

	errStr := strings.ToLower(err.Error())
	if !strings.Contains(errStr, "frontmatter") && !strings.Contains(errStr, "yaml") {
		t.Errorf("error %q should mention 'frontmatter' or 'yaml'", err.Error())
	}
}

// ---------------------------------------------------------------------------
// TS-01-E6: Missing Intent section
// ---------------------------------------------------------------------------

func TestTS01_E06(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/no_intent")
	if err == nil {
		t.Fatal("expected error for missing Intent section, got nil")
	}
	if spec != nil {
		t.Errorf("spec should be nil on error, got non-nil")
	}

	if !strings.Contains(err.Error(), "Intent") {
		t.Errorf("error %q should mention 'Intent'", err.Error())
	}
}

// ---------------------------------------------------------------------------
// TS-01-E7: Non-existent spec folder
// ---------------------------------------------------------------------------

func TestTS01_E07(t *testing.T) {
	spec, err := afspec.LoadSpec("/nonexistent/path/that/does/not/exist")
	if err == nil {
		t.Fatal("expected error for non-existent path, got nil")
	}
	if spec != nil {
		t.Errorf("spec should be nil for error case, got %v", spec)
	}
	// Error must indicate path was not found, not just "not implemented"
	errStr := err.Error()
	if errStr == "not implemented" {
		t.Errorf("error should describe path failure, got %q", errStr)
	}
}
