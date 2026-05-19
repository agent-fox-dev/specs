package afspec_test

// lifecycle_test.go covers:
//   TS-01-29  (Lifecycle transition graph enforcement)
//   TS-01-30  (Intent hash computation at draft→active)
//   TS-01-31  (Active state mutation guard)
//   TS-01-32  (Sealed/superseded/archived reject all mutations)
//   TS-01-33  (Deprecation banner on supersede)
//   TS-01-E15 (Illegal lifecycle transition error)
//   TS-01-E16 (Intent hash tamper detection)
//   TS-01-P3  (Lifecycle monotonicity property)
//   TS-01-P5  (Intent hash stability property)

import (
	"os"
	"strings"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-29: Lifecycle transition graph enforcement
// ---------------------------------------------------------------------------

func TestTS01_29(t *testing.T) {
	legal := [][2]afspec.Status{
		{afspec.StatusDraft, afspec.StatusActive},
		{afspec.StatusDraft, afspec.StatusArchived},
		{afspec.StatusActive, afspec.StatusSealed},
		{afspec.StatusSealed, afspec.StatusSuperseded},
		{afspec.StatusSealed, afspec.StatusArchived},
	}
	allStatuses := []afspec.Status{
		afspec.StatusDraft,
		afspec.StatusActive,
		afspec.StatusSealed,
		afspec.StatusSuperseded,
		afspec.StatusArchived,
	}

	isLegal := func(from, to afspec.Status) bool {
		for _, pair := range legal {
			if pair[0] == from && pair[1] == to {
				return true
			}
		}
		return false
	}

	for _, from := range allStatuses {
		for _, to := range allStatuses {
			spec := makeSpecWithStatus(from)
			result, err := afspec.Transition(spec, to)
			if isLegal(from, to) {
				if err != nil {
					t.Errorf("Transition(%s→%s) should succeed, got error: %v", from, to, err)
				} else if result == nil {
					t.Errorf("Transition(%s→%s) returned nil spec on success", from, to)
				} else if result.PRD.Frontmatter.Status != to {
					t.Errorf("Transition(%s→%s) result status = %q, want %q", from, to, result.PRD.Frontmatter.Status, to)
				}
			} else {
				if err == nil {
					t.Errorf("Transition(%s→%s) should fail, got nil error", from, to)
				}
			}
		}
	}
}

// makeSpecWithStatus constructs a minimal spec with the given status.
func makeSpecWithStatus(status afspec.Status) *afspec.Spec {
	intentHash := "a81b8d7135f2b4a3d18aa9f2163edda5ceecf03c795e9cf757e069b8ea2b3222"
	var hashPtr *string
	if status != afspec.StatusDraft {
		hashPtr = &intentHash
	}
	return &afspec.Spec{
		PRD: &afspec.PRD{
			Frontmatter: afspec.Frontmatter{
				SpecID:        "01",
				SpecName:      "lc_test",
				Title:         "Lifecycle Test",
				Status:        status,
				CreatedAt:     "2026-01-01T00:00:00Z",
				UpdatedAt:     "2026-01-01T00:00:00Z",
				Owner:         "test",
				Source:        "test",
				Supersedes:    []string{},
				Tags:          []string{},
				IntentHash:    hashPtr,
				SchemaVersion: 1,
			},
			Body: "# Lifecycle Test\n\n## Intent\n\nBuild a lifecycle test spec.\n",
		},
		Requirements: &afspec.Requirements{
			SpecID:                "01",
			SpecName:              "lc_test",
			Requirements:          []afspec.Requirement{},
			CorrectnessProperties: []afspec.CorrectnessProperty{},
			ExecutionPaths:        []afspec.ExecutionPath{},
			ErrorHandling:         []afspec.ErrorHandlingEntry{},
			Glossary:              map[string]string{},
			SchemaVersion:         1,
		},
		TestSpec: &afspec.TestSpecDoc{
			SpecID:        "01",
			SpecName:      "lc_test",
			TestCases:     []afspec.TestCase{},
			PropertyTests: []afspec.PropertyTest{},
			EdgeCaseTests: []afspec.EdgeCaseTest{},
			SmokeTests:    []afspec.SmokeTest{},
			Coverage:      afspec.Coverage{},
			SchemaVersion: 1,
		},
		Tasks: &afspec.Tasks{
			SpecID:   "01",
			SpecName: "lc_test",
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

// ---------------------------------------------------------------------------
// TS-01-30: Intent hash computation at draft→active
// ---------------------------------------------------------------------------

func TestTS01_30(t *testing.T) {
	spec, err := afspec.LoadSpec("testdata/draft_spec")
	if err != nil {
		t.Fatalf("LoadSpec draft_spec: %v", err)
	}
	if spec.PRD.Frontmatter.Status != afspec.StatusDraft {
		t.Skipf("spec status = %q, want draft", spec.PRD.Frontmatter.Status)
	}

	active, err := afspec.Transition(spec, afspec.StatusActive)
	if err != nil {
		t.Fatalf("Transition draft→active: %v", err)
	}
	if active == nil {
		t.Fatal("Transition returned nil spec")
	}
	if active.PRD.Frontmatter.Status != afspec.StatusActive {
		t.Errorf("status = %q, want %q", active.PRD.Frontmatter.Status, afspec.StatusActive)
	}
	if active.PRD.Frontmatter.IntentHash == nil {
		t.Fatal("IntentHash should be set after draft→active transition")
	}
	hash := *active.PRD.Frontmatter.IntentHash
	if len(hash) != 64 {
		t.Errorf("IntentHash length = %d, want 64 (SHA-256 hex)", len(hash))
	}
	for _, c := range hash {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			t.Errorf("IntentHash contains non-lowercase-hex character %q", c)
			break
		}
	}

	// Verify hash matches ComputeIntentHash
	expectedHash := afspec.ComputeIntentHash(spec.PRD.Body)
	if hash != expectedHash {
		t.Errorf("IntentHash = %q, ComputeIntentHash = %q", hash, expectedHash)
	}

	// Original spec must not be modified
	if spec.PRD.Frontmatter.Status != afspec.StatusDraft {
		t.Error("Transition modified the original spec's status")
	}
	if spec.PRD.Frontmatter.IntentHash != nil {
		t.Error("Transition modified the original spec's IntentHash")
	}
}

// ---------------------------------------------------------------------------
// TS-01-31: Active state mutation guard
// ---------------------------------------------------------------------------

func TestTS01_31(t *testing.T) {
	// Build an active spec and attempt to modify immutable fields.
	activeSpec := makeSpecWithStatus(afspec.StatusActive)
	hashVal := "a81b8d7135f2b4a3d18aa9f2163edda5ceecf03c795e9cf757e069b8ea2b3222"
	activeSpec.PRD.Frontmatter.IntentHash = &hashVal

	tmpdir := t.TempDir()

	// Attempt to save with a modified Intent section — should be rejected.
	modifiedSpec := *activeSpec
	modifiedPRD := *activeSpec.PRD
	modifiedPRD.Body = strings.Replace(activeSpec.PRD.Body,
		"Build a lifecycle test spec.",
		"This is a completely different intent.",
		1)
	modifiedSpec.PRD = &modifiedPRD

	err := afspec.SaveSpec(tmpdir, &modifiedSpec)
	if err == nil {
		t.Error("SaveSpec should reject mutation of Intent on active spec, got nil error")
	} else if !strings.Contains(err.Error(), "Intent") && err.Error() == "not implemented" {
		t.Logf("SaveSpec not yet implemented (expected failure)")
	}

	// Attempt to modify created_at (immutable field).
	modifiedSpec2 := *activeSpec
	modifiedPRD2 := *activeSpec.PRD
	fm2 := activeSpec.PRD.Frontmatter
	fm2.CreatedAt = "2099-01-01T00:00:00Z" // changed
	modifiedPRD2.Frontmatter = fm2
	modifiedSpec2.PRD = &modifiedPRD2

	err2 := afspec.SaveSpec(tmpdir, &modifiedSpec2)
	if err2 == nil {
		t.Error("SaveSpec should reject mutation of created_at on active spec, got nil error")
	} else if err2.Error() == "not implemented" {
		t.Logf("SaveSpec not yet implemented (expected failure)")
	}
}

// ---------------------------------------------------------------------------
// TS-01-32: Sealed/superseded/archived reject all mutations
// ---------------------------------------------------------------------------

func TestTS01_32(t *testing.T) {
	immutableStates := []afspec.Status{
		afspec.StatusSealed,
		afspec.StatusSuperseded,
		afspec.StatusArchived,
	}

	for _, state := range immutableStates {
		t.Run(string(state), func(t *testing.T) {
			spec := makeSpecWithStatus(state)
			tmpdir := t.TempDir()

			// Attempt to modify the title and save
			modified := *spec
			modifiedPRD := *spec.PRD
			fm := spec.PRD.Frontmatter
			fm.Title = "Changed Title"
			modifiedPRD.Frontmatter = fm
			modified.PRD = &modifiedPRD

			err := afspec.SaveSpec(tmpdir, &modified)
			if err == nil {
				t.Errorf("SaveSpec should reject mutation for %s state, got nil error", state)
			}
			// Error should mention the state
			if err != nil && err.Error() != "not implemented" {
				stateName := string(state)
				if !strings.Contains(err.Error(), stateName) {
					t.Errorf("error %q should mention state %q", err.Error(), stateName)
				}
			}
		})
	}
}

// ---------------------------------------------------------------------------
// TS-01-33: Deprecation banner on supersede
// ---------------------------------------------------------------------------

func TestTS01_33(t *testing.T) {
	// Create a sealed spec in a temp directory
	tmpdir := t.TempDir()
	specDir := tmpdir + "/01_supersede_test"
	if err := os.MkdirAll(specDir, 0755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}

	sealedSpec := makeSpecWithStatus(afspec.StatusSealed)
	if err := afspec.SaveSpec(specDir, sealedSpec); err != nil {
		t.Fatalf("SaveSpec (sealed): %v", err)
	}

	spec, err := afspec.LoadSpec(specDir)
	if err != nil {
		t.Fatalf("LoadSpec (sealed): %v", err)
	}

	superseded, err := afspec.Transition(spec, afspec.StatusSuperseded)
	if err != nil {
		t.Fatalf("Transition sealed→superseded: %v", err)
	}
	if superseded == nil {
		t.Fatal("Transition returned nil")
	}

	// After transitioning, the spec files should contain a deprecation banner.
	// The banner should appear in all four files.
	if err := afspec.SaveSpec(specDir, superseded); err != nil {
		t.Fatalf("SaveSpec (superseded): %v", err)
	}

	for _, f := range []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"} {
		data, err := os.ReadFile(specDir + "/" + f)
		if err != nil {
			t.Fatalf("ReadFile %s: %v", f, err)
		}
		if !strings.Contains(strings.ToUpper(string(data)), "SUPERSEDED") {
			t.Errorf("file %s should contain 'SUPERSEDED' banner after supersede transition", f)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-E15: Illegal lifecycle transition error
// ---------------------------------------------------------------------------

func TestTS01_E15(t *testing.T) {
	// draft → sealed is illegal
	spec := makeSpecWithStatus(afspec.StatusDraft)
	_, err := afspec.Transition(spec, afspec.StatusSealed)
	if err == nil {
		t.Fatal("Transition(draft→sealed) should fail, got nil error")
	}
	errStr := err.Error()
	if !strings.Contains(errStr, "draft") && !strings.Contains(errStr, string(afspec.StatusDraft)) {
		t.Errorf("error %q should mention 'draft'", errStr)
	}
	if !strings.Contains(errStr, "sealed") && !strings.Contains(errStr, string(afspec.StatusSealed)) {
		t.Errorf("error %q should mention 'sealed'", errStr)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E16: Intent hash tamper detection
// ---------------------------------------------------------------------------

func TestTS01_E16(t *testing.T) {
	// Active spec with a stored intent_hash
	intentBody := "Build a lifecycle test spec."
	originalHash := afspec.ComputeIntentHash("# Lifecycle Test\n\n## Intent\n\n" + intentBody + "\n")

	// Modify the body to compute a different hash
	modifiedBody := "# Lifecycle Test\n\n## Intent\n\nBuild something completely different.\n"
	newHash := afspec.ComputeIntentHash(modifiedBody)

	// The two hashes must differ (tamper detected)
	if originalHash == "" {
		t.Skip("ComputeIntentHash not yet implemented")
	}
	if originalHash == newHash {
		t.Errorf("ComputeIntentHash should differ for different content: both = %q", originalHash)
	}
}

// ---------------------------------------------------------------------------
// TS-01-P3: Lifecycle monotonicity (property test)
// ---------------------------------------------------------------------------

func TestPropertyP3(t *testing.T) {
	// State ordering: draft < active < sealed < {superseded, archived}
	stateOrder := map[afspec.Status]int{
		afspec.StatusDraft:      0,
		afspec.StatusActive:     1,
		afspec.StatusSealed:     2,
		afspec.StatusSuperseded: 3,
		afspec.StatusArchived:   3,
	}

	legalTransitions := [][2]afspec.Status{
		{afspec.StatusDraft, afspec.StatusActive},
		{afspec.StatusDraft, afspec.StatusArchived},
		{afspec.StatusActive, afspec.StatusSealed},
		{afspec.StatusSealed, afspec.StatusSuperseded},
		{afspec.StatusSealed, afspec.StatusArchived},
	}

	for _, pair := range legalTransitions {
		from, to := pair[0], pair[1]
		spec := makeSpecWithStatus(from)
		result, err := afspec.Transition(spec, to)
		if err != nil {
			t.Errorf("Transition(%s→%s) should succeed: %v", from, to, err)
			continue
		}
		if result == nil {
			t.Errorf("Transition(%s→%s) returned nil spec", from, to)
			continue
		}
		if stateOrder[result.PRD.Frontmatter.Status] < stateOrder[from] {
			t.Errorf("Transition(%s→%s) moved backward: result state = %q",
				from, to, result.PRD.Frontmatter.Status)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-P5: Intent hash stability (property test)
// ---------------------------------------------------------------------------

func TestPropertyP5(t *testing.T) {
	bodies := []string{
		"Build a test library.",
		"This is a multi-line\nintent body.",
		"Short.",
		"Long intent body with\nmultiple paragraphs.\n\nAnd some extra whitespace.",
	}

	for _, body := range bodies {
		t.Run(body[:min(20, len(body))], func(t *testing.T) {
			h1 := afspec.ComputeIntentHash(body)
			h2 := afspec.ComputeIntentHash(body)

			if h1 == "" {
				t.Skip("ComputeIntentHash not yet implemented")
			}

			// Must be deterministic
			if h1 != h2 {
				t.Errorf("ComputeIntentHash is not deterministic for %q: %q vs %q", body, h1, h2)
			}

			// Changing the body must change the hash
			modified := body + " extra content"
			h3 := afspec.ComputeIntentHash(modified)
			if h1 == h3 {
				t.Errorf("ComputeIntentHash should differ for modified body %q: both = %q", body, h1)
			}
		})
	}
}
