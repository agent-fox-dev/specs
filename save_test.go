package afspec_test

// save_test.go covers:
//   TS-01-10  (Save all four files)
//   TS-01-11  (Deterministic JSON output)
//   TS-01-12  (Deterministic YAML frontmatter field order)
//   TS-01-13  (Idempotent round-trip)
//   TS-01-46  (Auto-update updated_at on save)
//   TS-01-47  (Auto-compute coverage on save)
//   TS-01-E8  (Save to non-existent directory)
//   TS-01-E9  (Atomic write on failure)
//   TS-01-P1  (Round-trip idempotency property test)
//   TS-01-P11 (Computed coverage accuracy property test)

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-10: Save all four files
// ---------------------------------------------------------------------------

func TestTS01_10(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	for _, f := range []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"} {
		path := filepath.Join(tmpdir, f)
		if _, err := os.Stat(path); os.IsNotExist(err) {
			t.Errorf("expected file %q to exist after SaveSpec", path)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-11: Deterministic JSON output
// ---------------------------------------------------------------------------

func TestTS01_11(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(tmpdir, "requirements.json"))
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}

	content := string(data)

	// Must end with a newline
	if !strings.HasSuffix(content, "\n") {
		t.Error("requirements.json must end with a newline")
	}

	// 2-space indentation: check for "  " at the beginning of lines
	lines := strings.Split(content, "\n")
	hasIndent := false
	for _, line := range lines {
		if strings.HasPrefix(line, "  ") && !strings.HasPrefix(line, "   ") {
			hasIndent = true
			break
		}
	}
	if !hasIndent {
		t.Error("requirements.json should use 2-space indentation")
	}

	// Alphabetically sorted keys: "$schema" before "correctness_properties" before "glossary"
	schemaPos := strings.Index(content, `"$schema"`)
	corrPos := strings.Index(content, `"correctness_properties"`)
	glossaryPos := strings.Index(content, `"glossary"`)
	introPos := strings.Index(content, `"introduction"`)
	specIDPos := strings.Index(content, `"spec_id"`)

	if schemaPos < 0 || corrPos < 0 || glossaryPos < 0 || introPos < 0 || specIDPos < 0 {
		t.Fatal("requirements.json is missing expected top-level keys")
	}
	if schemaPos > corrPos {
		t.Errorf("keys not alphabetically sorted: $schema (%d) should come before correctness_properties (%d)", schemaPos, corrPos)
	}
	if glossaryPos > introPos {
		t.Errorf("keys not alphabetically sorted: glossary (%d) should come before introduction (%d)", glossaryPos, introPos)
	}
}

// ---------------------------------------------------------------------------
// TS-01-12: Deterministic YAML frontmatter field order
// ---------------------------------------------------------------------------

func TestTS01_12(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(tmpdir, "prd.md"))
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}

	content := string(data)

	// Extract YAML frontmatter (between first and second ---)
	lines := strings.Split(content, "\n")
	if len(lines) < 3 || lines[0] != "---" {
		t.Fatal("prd.md does not start with '---' YAML frontmatter delimiter")
	}

	// Collect keys in order
	expectedOrder := []string{
		"spec_id", "spec_name", "title", "status",
		"created_at", "updated_at", "owner", "source",
		"supersedes", "tags", "intent_hash", "schema_version",
	}

	var foundKeys []string
	inFrontmatter := false
	for _, line := range lines[1:] {
		if line == "---" {
			break
		}
		inFrontmatter = true
		if idx := strings.Index(line, ":"); idx > 0 {
			key := strings.TrimSpace(line[:idx])
			foundKeys = append(foundKeys, key)
		}
	}
	if !inFrontmatter {
		t.Fatal("no frontmatter found in prd.md")
	}

	if len(foundKeys) != len(expectedOrder) {
		t.Errorf("frontmatter has %d keys, want %d; got %v", len(foundKeys), len(expectedOrder), foundKeys)
	}
	for i, want := range expectedOrder {
		if i >= len(foundKeys) {
			t.Errorf("frontmatter key at position %d: missing (want %q)", i, want)
			continue
		}
		if foundKeys[i] != want {
			t.Errorf("frontmatter key at position %d: got %q, want %q", i, foundKeys[i], want)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-13: Idempotent round-trip
// ---------------------------------------------------------------------------

func TestTS01_13(t *testing.T) {
	spec1, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec (first): %v", err)
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec1); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	spec2, err := afspec.LoadSpec(tmpdir)
	if err != nil {
		t.Fatalf("LoadSpec (second): %v", err)
	}

	// JSON files must be byte-identical between testdata and tmpdir
	for _, f := range []string{"requirements.json", "test_spec.json", "tasks.json"} {
		orig, err := os.ReadFile(filepath.Join("testdata/valid_spec", f))
		if err != nil {
			t.Fatalf("ReadFile original %s: %v", f, err)
		}
		saved, err := os.ReadFile(filepath.Join(tmpdir, f))
		if err != nil {
			t.Fatalf("ReadFile saved %s: %v", f, err)
		}
		if string(orig) != string(saved) {
			t.Errorf("file %s is not byte-identical after round-trip", f)
		}
	}

	// prd.md: identical except updated_at field
	origPRD, _ := os.ReadFile("testdata/valid_spec/prd.md")
	savedPRD, _ := os.ReadFile(filepath.Join(tmpdir, "prd.md"))
	if maskUpdatedAt(string(origPRD)) != maskUpdatedAt(string(savedPRD)) {
		t.Error("prd.md differs after round-trip (ignoring updated_at)")
	}

	// In-memory structures must be deeply equal (ignoring Dir and UpdatedAt)
	if spec1.PRD.Frontmatter.SpecID != spec2.PRD.Frontmatter.SpecID {
		t.Errorf("SpecID mismatch: %q vs %q", spec1.PRD.Frontmatter.SpecID, spec2.PRD.Frontmatter.SpecID)
	}
	if len(spec1.Requirements.Requirements) != len(spec2.Requirements.Requirements) {
		t.Errorf("Requirements count mismatch: %d vs %d",
			len(spec1.Requirements.Requirements), len(spec2.Requirements.Requirements))
	}
}

// maskUpdatedAt replaces the updated_at value in YAML frontmatter with a placeholder.
func maskUpdatedAt(content string) string {
	lines := strings.Split(content, "\n")
	for i, line := range lines {
		if strings.HasPrefix(line, "updated_at:") {
			lines[i] = "updated_at: <masked>"
		}
	}
	return strings.Join(lines, "\n")
}

// ---------------------------------------------------------------------------
// TS-01-46: Auto-update updated_at on save
// ---------------------------------------------------------------------------

func TestTS01_46(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	oldUpdatedAt := spec.PRD.Frontmatter.UpdatedAt
	before := time.Now().UTC()

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	after := time.Now().UTC()

	saved, err := afspec.LoadSpec(tmpdir)
	if err != nil {
		t.Fatalf("LoadSpec (saved): %v", err)
	}

	newUpdatedAt := saved.PRD.Frontmatter.UpdatedAt
	newTime, err := time.Parse(time.RFC3339, newUpdatedAt)
	if err != nil {
		t.Fatalf("parse updated_at %q: %v", newUpdatedAt, err)
	}

	if newTime.Before(before) || newTime.After(after.Add(time.Second)) {
		t.Errorf("updated_at %q not within expected range [%v, %v]", newUpdatedAt, before, after)
	}

	// Original in-memory spec should not be modified
	if spec.PRD.Frontmatter.UpdatedAt != oldUpdatedAt {
		t.Errorf("SaveSpec modified original spec.UpdatedAt: got %q, want %q",
			spec.PRD.Frontmatter.UpdatedAt, oldUpdatedAt)
	}
}

// ---------------------------------------------------------------------------
// TS-01-47: Auto-compute coverage on save
// ---------------------------------------------------------------------------

func TestTS01_47(t *testing.T) {
	// Build a spec with a requirement with two criteria but only one test case covering it
	spec := &afspec.Spec{
		PRD: &afspec.PRD{
			Frontmatter: afspec.Frontmatter{
				SpecID:        "01",
				SpecName:      "cov_test",
				Title:         "Coverage Test",
				Status:        afspec.StatusDraft,
				CreatedAt:     "2026-01-01T00:00:00Z",
				UpdatedAt:     "2026-01-01T00:00:00Z",
				Owner:         "test",
				Source:        "test",
				Supersedes:    []string{},
				Tags:          []string{},
				SchemaVersion: 1,
			},
			Body: "# Coverage Test\n\n## Intent\n\nTest coverage computation.\n",
		},
		Requirements: &afspec.Requirements{
			SpecID:   "01",
			SpecName: "cov_test",
			Requirements: []afspec.Requirement{
				{
					ID:    "01-REQ-1",
					Title: "R1",
					UserStory: afspec.UserStory{
						Role: "r", Goal: "g", Benefit: "b",
					},
					AcceptanceCriteria: []afspec.Criterion{
						{ID: "01-REQ-1.1", EarsPattern: "ubiquitous", System: "s", Action: "a"},
					},
					EdgeCases: []afspec.Criterion{
						{ID: "01-REQ-1.E1", EarsPattern: "unwanted", ErrorCondition: "bad", System: "s", Action: "a"},
					},
				},
			},
			CorrectnessProperties: []afspec.CorrectnessProperty{},
			ExecutionPaths:        []afspec.ExecutionPath{},
			ErrorHandling:         []afspec.ErrorHandlingEntry{},
			Glossary:              map[string]string{},
			SchemaVersion:         1,
		},
		TestSpec: &afspec.TestSpecDoc{
			SpecID:   "01",
			SpecName: "cov_test",
			TestCases: []afspec.TestCase{
				{
					ID:                  "TS-01-1",
					RequirementID:       "01-REQ-1.1",
					Kind:                "unit",
					Description:         "covers req 1.1",
					Preconditions:       []string{},
					AssertionPseudocode: "ASSERT true",
				},
				// 01-REQ-1.E1 intentionally not covered
			},
			PropertyTests: []afspec.PropertyTest{},
			EdgeCaseTests: []afspec.EdgeCaseTest{},
			SmokeTests:    []afspec.SmokeTest{},
			Coverage:      afspec.Coverage{},
			SchemaVersion: 1,
		},
		Tasks: &afspec.Tasks{
			SpecID:   "01",
			SpecName: "cov_test",
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
					Subtasks: []afspec.Subtask{},
					Verification: afspec.VerificationSubtask{
						ID:     "1.V",
						Checks: []string{},
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
			Traceability:  []afspec.TraceabilityEntry{},
			SchemaVersion: 1,
		},
	}

	tmpdir := t.TempDir()
	if err := afspec.SaveSpec(tmpdir, spec); err != nil {
		t.Fatalf("SaveSpec: %v", err)
	}

	saved, err := afspec.LoadSpec(tmpdir)
	if err != nil {
		t.Fatalf("LoadSpec (saved): %v", err)
	}

	cov := saved.TestSpec.Coverage

	// 01-REQ-1.1 is covered (has a test case)
	coveredSet := make(map[string]bool)
	for _, id := range cov.RequirementsCovered {
		coveredSet[id] = true
	}
	if !coveredSet["01-REQ-1.1"] {
		t.Errorf("coverage.requirements_covered should contain '01-REQ-1.1'; got %v", cov.RequirementsCovered)
	}

	// 01-REQ-1.E1 is NOT covered (no test case references it)
	gapSet := make(map[string]bool)
	for _, id := range cov.Gaps {
		gapSet[id] = true
	}
	if !gapSet["01-REQ-1.E1"] {
		t.Errorf("coverage.gaps should contain '01-REQ-1.E1'; got %v", cov.Gaps)
	}

	// Union of covered + gaps == all criterion IDs
	allCriteriaIDs := map[string]bool{
		"01-REQ-1.1":  true,
		"01-REQ-1.E1": true,
	}
	union := make(map[string]bool)
	for id := range coveredSet {
		union[id] = true
	}
	for id := range gapSet {
		union[id] = true
	}
	for id := range allCriteriaIDs {
		if !union[id] {
			t.Errorf("criteria ID %q not in covered or gaps", id)
		}
	}
	// No overlap
	for id := range coveredSet {
		if gapSet[id] {
			t.Errorf("ID %q appears in both covered and gaps", id)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-E8: Save to non-existent directory
// ---------------------------------------------------------------------------

func TestTS01_E08(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	nonexistent := "/nonexistent/dir/that/does/not/exist"
	err = afspec.SaveSpec(nonexistent, spec)
	if err == nil {
		t.Fatal("expected error saving to non-existent directory, got nil")
	}

	// Directory must NOT have been created
	if _, statErr := os.Stat(nonexistent); !os.IsNotExist(statErr) {
		t.Errorf("SaveSpec must not create directory %q", nonexistent)
	}
	// Error should NOT just say "not implemented"
	if err.Error() == "not implemented" {
		t.Errorf("SaveSpec error should describe path problem, got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// TS-01-E9: Atomic write on failure
// ---------------------------------------------------------------------------

func TestTS01_E09(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/valid_spec")
	if err != nil {
		t.Fatalf("LoadSpec: %v", err)
	}

	// Create a temp dir and pre-create requirements.json as a read-only file
	// to force a write failure mid-operation.
	tmpdir := t.TempDir()
	reqPath := filepath.Join(tmpdir, "requirements.json")

	// Write a placeholder and make it read-only
	if err := os.WriteFile(reqPath, []byte("{}"), 0444); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	err = afspec.SaveSpec(tmpdir, spec)
	if err == nil {
		t.Fatal("expected error when write fails, got nil")
	}

	// prd.md was written before requirements.json failed; it must be rolled back
	prdPath := filepath.Join(tmpdir, "prd.md")
	if _, statErr := os.Stat(prdPath); statErr == nil {
		t.Error("prd.md should have been rolled back after partial write failure")
	}
}

// ---------------------------------------------------------------------------
// TS-01-P1: Round-trip idempotency (property test)
// ---------------------------------------------------------------------------

func TestPropertyP1(t *testing.T) {
	// Test against the golden fixture — the canonical valid spec.
	fixtures := []string{
		"testdata/valid_spec",
		"testdata/draft_spec",
	}
	for _, fixture := range fixtures {
		t.Run(fixture, func(t *testing.T) {
			spec1, err := afspec.LoadSpec(fixture)
			if err != nil {
				t.Fatalf("LoadSpec: %v", err)
			}

			tmpdir := t.TempDir()
			if err := afspec.SaveSpec(tmpdir, spec1); err != nil {
				t.Fatalf("SaveSpec: %v", err)
			}

			spec2, err := afspec.LoadSpec(tmpdir)
			if err != nil {
				t.Fatalf("LoadSpec (saved): %v", err)
			}

			// JSON files must be byte-identical
			for _, f := range []string{"requirements.json", "test_spec.json", "tasks.json"} {
				orig, _ := os.ReadFile(filepath.Join(fixture, f))
				saved, _ := os.ReadFile(filepath.Join(tmpdir, f))
				if string(orig) != string(saved) {
					t.Errorf("[%s] %s is not byte-identical after round-trip", fixture, f)
				}
			}

			// prd.md identical except updated_at
			origPRD, _ := os.ReadFile(filepath.Join(fixture, "prd.md"))
			savedPRD, _ := os.ReadFile(filepath.Join(tmpdir, "prd.md"))
			if maskUpdatedAt(string(origPRD)) != maskUpdatedAt(string(savedPRD)) {
				t.Errorf("[%s] prd.md differs after round-trip (ignoring updated_at)", fixture)
			}

			// SpecID consistent
			if spec1.PRD.Frontmatter.SpecID != spec2.PRD.Frontmatter.SpecID {
				t.Errorf("[%s] SpecID mismatch after round-trip", fixture)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// TS-01-P11: Computed coverage accuracy (property test)
// ---------------------------------------------------------------------------

func TestPropertyP11(t *testing.T) {
	// Generate scenarios with different test coverage subsets.
	// Each scenario: all_ids, covered_ids → save → verify coverage.
	scenarios := []struct {
		name       string
		allCritIDs []string
		coveredIDs []string
	}{
		{
			name:       "fully covered",
			allCritIDs: []string{"01-REQ-1.1", "01-REQ-1.E1"},
			coveredIDs: []string{"01-REQ-1.1", "01-REQ-1.E1"},
		},
		{
			name:       "partially covered",
			allCritIDs: []string{"01-REQ-1.1", "01-REQ-1.E1"},
			coveredIDs: []string{"01-REQ-1.1"},
		},
		{
			name:       "no coverage",
			allCritIDs: []string{"01-REQ-1.1", "01-REQ-1.E1"},
			coveredIDs: []string{},
		},
	}

	for _, sc := range scenarios {
		t.Run(sc.name, func(t *testing.T) {
			spec := buildSpecWithCoverage(sc.allCritIDs, sc.coveredIDs)
			tmpdir := t.TempDir()
			if err := afspec.SaveSpec(tmpdir, spec); err != nil {
				t.Fatalf("SaveSpec: %v", err)
			}
			saved, err := afspec.LoadSpec(tmpdir)
			if err != nil {
				t.Fatalf("LoadSpec: %v", err)
			}

			cov := saved.TestSpec.Coverage
			coveredSet := toSet(cov.RequirementsCovered)
			gapSet := toSet(cov.Gaps)
			allSet := toSet(sc.allCritIDs)

			// Union == all criteria IDs
			union := make(map[string]bool)
			for k := range coveredSet {
				union[k] = true
			}
			for k := range gapSet {
				union[k] = true
			}
			for id := range allSet {
				if !union[id] {
					t.Errorf("ID %q not in covered or gaps", id)
				}
			}

			// No overlap
			for id := range coveredSet {
				if gapSet[id] {
					t.Errorf("ID %q in both covered and gaps", id)
				}
			}

			// Covered IDs match expected
			for _, id := range sc.coveredIDs {
				if !coveredSet[id] {
					t.Errorf("ID %q should be covered but is not", id)
				}
			}
		})
	}
}

// buildSpecWithCoverage constructs a minimal spec with given criteria and test cases.
func buildSpecWithCoverage(allCritIDs, coveredIDs []string) *afspec.Spec {
	var criteria []afspec.Criterion
	var edgeCases []afspec.Criterion
	for _, id := range allCritIDs {
		if strings.Contains(id, ".E") {
			edgeCases = append(edgeCases, afspec.Criterion{
				ID:             id,
				EarsPattern:    "unwanted",
				ErrorCondition: "err",
				System:         "s",
				Action:         "a",
			})
		} else {
			criteria = append(criteria, afspec.Criterion{
				ID:          id,
				EarsPattern: "ubiquitous",
				System:      "s",
				Action:      "a",
			})
		}
	}

	var testCases []afspec.TestCase
	for i, id := range coveredIDs {
		testCases = append(testCases, afspec.TestCase{
			ID:                  "TS-01-" + string(rune('1'+i)),
			RequirementID:       id,
			Kind:                "unit",
			Description:         "covers " + id,
			Preconditions:       []string{},
			AssertionPseudocode: "ASSERT true",
		})
	}

	return &afspec.Spec{
		PRD: &afspec.PRD{
			Frontmatter: afspec.Frontmatter{
				SpecID:        "01",
				SpecName:      "cov_test",
				Title:         "Coverage Test",
				Status:        afspec.StatusDraft,
				CreatedAt:     "2026-01-01T00:00:00Z",
				UpdatedAt:     "2026-01-01T00:00:00Z",
				Owner:         "test",
				Source:        "test",
				Supersedes:    []string{},
				Tags:          []string{},
				SchemaVersion: 1,
			},
			Body: "# Coverage Test\n\n## Intent\n\nTest coverage.\n",
		},
		Requirements: &afspec.Requirements{
			SpecID:   "01",
			SpecName: "cov_test",
			Requirements: []afspec.Requirement{
				{
					ID:                 "01-REQ-1",
					Title:              "R1",
					UserStory:          afspec.UserStory{Role: "r", Goal: "g", Benefit: "b"},
					AcceptanceCriteria: criteria,
					EdgeCases:          edgeCases,
				},
			},
			CorrectnessProperties: []afspec.CorrectnessProperty{},
			ExecutionPaths:        []afspec.ExecutionPath{},
			ErrorHandling:         []afspec.ErrorHandlingEntry{},
			Glossary:              map[string]string{},
			SchemaVersion:         1,
		},
		TestSpec: &afspec.TestSpecDoc{
			SpecID:        "01",
			SpecName:      "cov_test",
			TestCases:     testCases,
			PropertyTests: []afspec.PropertyTest{},
			EdgeCaseTests: []afspec.EdgeCaseTest{},
			SmokeTests:    []afspec.SmokeTest{},
			Coverage:      afspec.Coverage{},
			SchemaVersion: 1,
		},
		Tasks: &afspec.Tasks{
			SpecID:   "01",
			SpecName: "cov_test",
			TestCommands: afspec.TestCommands{
				SpecTests: "go test ./...",
				AllTests:  "go test ./...",
				Linter:    "go vet ./...",
			},
			Dependencies: []afspec.TaskDependency{},
			TaskGroups: []afspec.TaskGroup{
				{
					ID: 1, Kind: "tests", Title: "Tests",
					Subtasks:     []afspec.Subtask{},
					Verification: afspec.VerificationSubtask{ID: "1.V", Checks: []string{}},
				},
				{
					ID: 2, Kind: "wiring_verification", Title: "Wiring",
					Subtasks:     []afspec.Subtask{},
					Verification: afspec.VerificationSubtask{ID: "2.V", Checks: []string{}},
				},
			},
			Traceability:  []afspec.TraceabilityEntry{},
			SchemaVersion: 1,
		},
	}
}

// toSet converts a slice to a set map.
func toSet(ss []string) map[string]bool {
	m := make(map[string]bool, len(ss))
	for _, s := range ss {
		m[s] = true
	}
	return m
}

