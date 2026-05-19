package afspec_test

// spec_test.go covers:
//   TS-01-1  (PRD frontmatter types)
//   TS-01-2  (Requirements container types)
//   TS-01-3  (TestSpec and Tasks container types)
//   TS-01-4  (EARS discriminated union)
//   TS-01-5  (Subtask state enum and transitions)
//   TS-01-6  (Concurrent read safety)
//   TS-01-E1 (Null JSON field representation)
//   TS-01-E2 (Empty array serialization)
//   TS-01-P10 (Null preservation round-trip)

import (
	"bytes"
	"encoding/json"
	"sync"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-1: PRD frontmatter types
// ---------------------------------------------------------------------------

func TestTS01_01(t *testing.T) {
	hash := "abc123def456"
	fm := afspec.Frontmatter{
		SpecID:        "01",
		SpecName:      "test",
		Title:         "Test",
		Status:        afspec.StatusDraft,
		CreatedAt:     "2026-01-01T00:00:00Z",
		UpdatedAt:     "2026-01-01T00:00:00Z",
		Owner:         "tester",
		Source:        "https://example.com",
		Supersedes:    []string{},
		Tags:          []string{"v1"},
		IntentHash:    nil,
		SchemaVersion: 1,
	}

	if fm.SpecID != "01" {
		t.Errorf("SpecID = %q, want %q", fm.SpecID, "01")
	}
	if fm.IntentHash != nil {
		t.Errorf("IntentHash should be nil, got %v", fm.IntentHash)
	}
	if fm.SchemaVersion != 1 {
		t.Errorf("SchemaVersion = %d, want 1", fm.SchemaVersion)
	}
	if fm.Supersedes == nil {
		t.Error("Supersedes must be a non-nil slice")
	}
	if fm.Tags == nil {
		t.Error("Tags must be a non-nil slice")
	}

	// Verify IntentHash is a *string (nullable)
	fm.IntentHash = &hash
	if fm.IntentHash == nil || *fm.IntentHash != hash {
		t.Errorf("IntentHash should be settable to a non-nil *string; got %v", fm.IntentHash)
	}

	// Verify PRD wraps Frontmatter + Body
	prd := afspec.PRD{
		Frontmatter: fm,
		Body:        "# Title\n\n## Intent\n\nSome intent.\n",
	}
	if prd.Frontmatter.SpecID != "01" {
		t.Errorf("PRD.Frontmatter.SpecID = %q, want %q", prd.Frontmatter.SpecID, "01")
	}
	if prd.Body == "" {
		t.Error("PRD.Body should not be empty")
	}
}

// ---------------------------------------------------------------------------
// TS-01-2: Requirements container types
// ---------------------------------------------------------------------------

func TestTS01_02(t *testing.T) {
	criterion := afspec.Criterion{
		ID:             "01-REQ-1.1",
		EarsPattern:    "ubiquitous",
		System:         "sys",
		Action:         "act",
		ReturnContract: nil,
	}
	req := afspec.Requirements{
		SpecID:   "01",
		Glossary: map[string]string{"term": "definition"},
		Requirements: []afspec.Requirement{
			{
				ID:    "01-REQ-1",
				Title: "R1",
				UserStory: afspec.UserStory{
					Role:    "operator",
					Goal:    "do X",
					Benefit: "get Y",
				},
				AcceptanceCriteria: []afspec.Criterion{criterion},
				EdgeCases:          []afspec.Criterion{},
			},
		},
		CorrectnessProperties: []afspec.CorrectnessProperty{
			{
				ID:        "01-PROP-1",
				Title:     "P1",
				ForAny:    "any input",
				Invariant: "holds",
				Validates: []string{"01-REQ-1.1"},
			},
		},
		ExecutionPaths: []afspec.ExecutionPath{
			{
				ID:    "01-PATH-1",
				Title: "Path",
				Steps: []afspec.ExecutionPathStep{
					{Actor: "consumer", Action: "call"},
					{Actor: "library", Action: "respond"},
				},
			},
		},
		ErrorHandling: []afspec.ErrorHandlingEntry{
			{
				ID:            "01-ERR-1",
				Condition:     "file missing",
				Behavior:      "return error",
				RequirementID: "01-REQ-1.E1",
			},
		},
	}

	if req.SpecID != "01" {
		t.Errorf("SpecID = %q, want %q", req.SpecID, "01")
	}
	if req.Glossary["term"] != "definition" {
		t.Errorf("Glossary[term] = %q, want %q", req.Glossary["term"], "definition")
	}
	if len(req.CorrectnessProperties) == 0 {
		t.Error("CorrectnessProperties should not be empty")
	}
	if req.CorrectnessProperties[0].ID != "01-PROP-1" {
		t.Errorf("CorrectnessProperties[0].ID = %q, want %q", req.CorrectnessProperties[0].ID, "01-PROP-1")
	}
	if len(req.ExecutionPaths[0].Steps) != 2 {
		t.Errorf("ExecutionPath steps count = %d, want 2", len(req.ExecutionPaths[0].Steps))
	}
}

// ---------------------------------------------------------------------------
// TS-01-3: TestSpec and Tasks container types
// ---------------------------------------------------------------------------

func TestTS01_03(t *testing.T) {
	ts := afspec.TestSpecDoc{
		SpecID:   "01",
		SpecName: "test",
		TestCases: []afspec.TestCase{
			{ID: "TS-01-1", RequirementID: "01-REQ-1.1", Kind: "unit"},
		},
		PropertyTests: []afspec.PropertyTest{
			{ID: "TS-01-P1", PropertyID: "01-PROP-1"},
		},
		EdgeCaseTests: []afspec.EdgeCaseTest{
			{ID: "TS-01-E1", RequirementID: "01-REQ-1.E1", Kind: "unit"},
		},
		SmokeTests: []afspec.SmokeTest{
			{ID: "TS-01-SMOKE-1", ExecutionPathID: "01-PATH-1"},
		},
		Coverage: afspec.Coverage{
			RequirementsCovered: []string{"01-REQ-1.1"},
			Gaps:                []string{},
		},
	}

	if ts.TestCases[0].Kind != "unit" {
		t.Errorf("TestCases[0].Kind = %q, want %q", ts.TestCases[0].Kind, "unit")
	}
	if ts.PropertyTests[0].PropertyID != "01-PROP-1" {
		t.Errorf("PropertyTests[0].PropertyID = %q, want %q", ts.PropertyTests[0].PropertyID, "01-PROP-1")
	}
	if ts.EdgeCaseTests[0].RequirementID != "01-REQ-1.E1" {
		t.Errorf("EdgeCaseTests[0].RequirementID = %q, want %q", ts.EdgeCaseTests[0].RequirementID, "01-REQ-1.E1")
	}
	if ts.SmokeTests[0].ExecutionPathID != "01-PATH-1" {
		t.Errorf("SmokeTests[0].ExecutionPathID = %q, want %q", ts.SmokeTests[0].ExecutionPathID, "01-PATH-1")
	}
	if ts.Coverage.RequirementsCovered[0] != "01-REQ-1.1" {
		t.Errorf("Coverage.RequirementsCovered[0] = %q, want %q", ts.Coverage.RequirementsCovered[0], "01-REQ-1.1")
	}

	tpath := "tests/foo_test.go::TestFoo"
	tasks := afspec.Tasks{
		SpecID:   "01",
		SpecName: "test",
		TaskGroups: []afspec.TaskGroup{
			{ID: 1, Kind: "tests", Title: "Write tests"},
		},
		Traceability: []afspec.TraceabilityEntry{
			{
				RequirementID: "01-REQ-1.1",
				TestSpecID:    "TS-01-1",
				TaskID:        "1.1",
				TestPath:      &tpath,
			},
		},
	}

	if tasks.TaskGroups[0].Kind != "tests" {
		t.Errorf("TaskGroups[0].Kind = %q, want %q", tasks.TaskGroups[0].Kind, "tests")
	}
	if tasks.Traceability[0].TestSpecID != "TS-01-1" {
		t.Errorf("Traceability[0].TestSpecID = %q, want %q", tasks.Traceability[0].TestSpecID, "TS-01-1")
	}
}

// ---------------------------------------------------------------------------
// TS-01-4: EARS discriminated union
// ---------------------------------------------------------------------------

func TestTS01_04(t *testing.T) {
	// ubiquitous — no pattern-specific fields
	cUb := afspec.Criterion{
		ID:          "01-REQ-1.1",
		EarsPattern: "ubiquitous",
		System:      "the system",
		Action:      "do X",
	}
	if cUb.Trigger != "" {
		t.Errorf("ubiquitous: Trigger should be empty, got %q", cUb.Trigger)
	}
	if cUb.Condition != "" {
		t.Errorf("ubiquitous: Condition should be empty, got %q", cUb.Condition)
	}
	if cUb.ErrorCondition != "" {
		t.Errorf("ubiquitous: ErrorCondition should be empty, got %q", cUb.ErrorCondition)
	}
	if cUb.State != "" {
		t.Errorf("ubiquitous: State should be empty, got %q", cUb.State)
	}
	if cUb.Feature != "" {
		t.Errorf("ubiquitous: Feature should be empty, got %q", cUb.Feature)
	}

	// event_driven — has trigger
	cEd := afspec.Criterion{
		ID:          "01-REQ-1.2",
		EarsPattern: "event_driven",
		Trigger:     "user clicks",
		System:      "the system",
		Action:      "respond",
	}
	if cEd.Trigger != "user clicks" {
		t.Errorf("event_driven: Trigger = %q, want %q", cEd.Trigger, "user clicks")
	}

	// complex_event — has trigger + condition
	cCe := afspec.Criterion{
		ID:          "01-REQ-1.3",
		EarsPattern: "complex_event",
		Trigger:     "t",
		Condition:   "c",
		System:      "s",
		Action:      "a",
	}
	if cCe.Condition != "c" {
		t.Errorf("complex_event: Condition = %q, want %q", cCe.Condition, "c")
	}

	// state_driven — has state
	cSd := afspec.Criterion{
		ID:          "01-REQ-1.4",
		EarsPattern: "state_driven",
		State:       "active",
		System:      "s",
		Action:      "a",
	}
	if cSd.State != "active" {
		t.Errorf("state_driven: State = %q, want %q", cSd.State, "active")
	}

	// unwanted — has error_condition
	cUw := afspec.Criterion{
		ID:             "01-REQ-1.5",
		EarsPattern:    "unwanted",
		ErrorCondition: "disk full",
		System:         "s",
		Action:         "alert",
	}
	if cUw.ErrorCondition != "disk full" {
		t.Errorf("unwanted: ErrorCondition = %q, want %q", cUw.ErrorCondition, "disk full")
	}

	// optional — has feature
	cOp := afspec.Criterion{
		ID:          "01-REQ-1.6",
		EarsPattern: "optional",
		Feature:     "debug mode",
		System:      "s",
		Action:      "log",
	}
	if cOp.Feature != "debug mode" {
		t.Errorf("optional: Feature = %q, want %q", cOp.Feature, "debug mode")
	}
}

// ---------------------------------------------------------------------------
// TS-01-5: Subtask state enum and transitions
// ---------------------------------------------------------------------------

func TestTS01_05(t *testing.T) {
	check := func(state afspec.SubtaskState, want []afspec.SubtaskState) {
		t.Helper()
		got := state.LegalTransitions()
		if len(got) != len(want) {
			t.Errorf("LegalTransitions(%q) len = %d, want %d; got %v", state, len(got), len(want), got)
			return
		}
		gotSet := make(map[afspec.SubtaskState]bool)
		for _, s := range got {
			gotSet[s] = true
		}
		for _, w := range want {
			if !gotSet[w] {
				t.Errorf("LegalTransitions(%q) missing %q; got %v", state, w, got)
			}
		}
	}

	check(afspec.StatePending, []afspec.SubtaskState{afspec.StateQueued, afspec.StateDropped})
	check(afspec.StateQueued, []afspec.SubtaskState{afspec.StateInProgress, afspec.StatePending, afspec.StateDropped})
	check(afspec.StateInProgress, []afspec.SubtaskState{afspec.StateDone, afspec.StatePendingReevaluation})
	check(afspec.StateDone, []afspec.SubtaskState{afspec.StatePendingReevaluation})
	check(afspec.StatePendingReevaluation, []afspec.SubtaskState{afspec.StatePending, afspec.StateDropped})
	check(afspec.StateDropped, []afspec.SubtaskState{})
}

// ---------------------------------------------------------------------------
// TS-01-6: Concurrent read safety
// ---------------------------------------------------------------------------

func TestTS01_06(t *testing.T) {
	spec := &afspec.Spec{
		PRD: &afspec.PRD{
			Frontmatter: afspec.Frontmatter{SpecID: "01"},
			Body:        "# Title\n\n## Intent\n\nTest.\n",
		},
		Requirements: &afspec.Requirements{
			Glossary:     map[string]string{"key": "val"},
			Requirements: []afspec.Requirement{},
		},
		TestSpec: &afspec.TestSpecDoc{
			TestCases: []afspec.TestCase{},
		},
		Tasks: &afspec.Tasks{
			TaskGroups: []afspec.TaskGroup{},
		},
	}

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = spec.PRD.Frontmatter.SpecID
			_ = spec.Requirements.Glossary
			_ = spec.TestSpec.TestCases
			_ = spec.Tasks.TaskGroups
		}()
	}
	wg.Wait()
	// No race detector failure = pass
}

// ---------------------------------------------------------------------------
// TS-01-E1: Null JSON field representation
// ---------------------------------------------------------------------------

func TestTS01_E01(t *testing.T) {
	c := afspec.Criterion{
		ID:             "01-REQ-1.1",
		EarsPattern:    "ubiquitous",
		System:         "s",
		Action:         "a",
		ReturnContract: nil,
	}

	data, err := json.Marshal(c)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}

	// return_contract must appear as null, not be omitted
	if !bytes.Contains(data, []byte(`"return_contract":null`)) {
		t.Errorf("JSON must contain \"return_contract\":null; got %s", data)
	}
	// Must NOT be an empty string
	if bytes.Contains(data, []byte(`"return_contract":""`)) {
		t.Errorf("JSON must not have empty-string return_contract; got %s", data)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E2: Empty array serialization
// ---------------------------------------------------------------------------

func TestTS01_E02(t *testing.T) {
	req := afspec.Requirement{
		ID:    "01-REQ-1",
		Title: "R",
		UserStory: afspec.UserStory{
			Role: "r", Goal: "g", Benefit: "b",
		},
		AcceptanceCriteria: []afspec.Criterion{
			{ID: "01-REQ-1.1", EarsPattern: "ubiquitous", System: "s", Action: "a"},
		},
		EdgeCases: []afspec.Criterion{}, // explicitly empty
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}

	// edge_cases must be [] not null
	if !bytes.Contains(data, []byte(`"edge_cases":[]`)) {
		t.Errorf("JSON must contain \"edge_cases\":[]; got %s", data)
	}
}

// ---------------------------------------------------------------------------
// TS-01-P10: Null preservation round-trip
// ---------------------------------------------------------------------------

func TestPropertyP10(t *testing.T) {
	cases := []struct {
		name string
		rc   *string
	}{
		{"nil return_contract", nil},
		{"non-nil return_contract", strPtr("list of items")},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			c := afspec.Criterion{
				ID:             "01-REQ-1.1",
				EarsPattern:    "ubiquitous",
				System:         "s",
				Action:         "a",
				ReturnContract: tc.rc,
			}

			data, err := json.Marshal(c)
			if err != nil {
				t.Fatalf("json.Marshal: %v", err)
			}

			var c2 afspec.Criterion
			if err := json.Unmarshal(data, &c2); err != nil {
				t.Fatalf("json.Unmarshal: %v", err)
			}

			if tc.rc == nil {
				if c2.ReturnContract != nil {
					t.Errorf("ReturnContract should be nil after round-trip; got %v", c2.ReturnContract)
				}
				if !bytes.Contains(data, []byte(`"return_contract":null`)) {
					t.Errorf("JSON must contain null for nil return_contract; got %s", data)
				}
			} else {
				if c2.ReturnContract == nil {
					t.Error("ReturnContract should not be nil after round-trip")
				} else if *c2.ReturnContract != *tc.rc {
					t.Errorf("ReturnContract = %q, want %q", *c2.ReturnContract, *tc.rc)
				}
			}
		})
	}
}

// strPtr is a helper to create a pointer to a string literal.
func strPtr(s string) *string { return &s }
