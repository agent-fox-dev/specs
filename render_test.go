package afspec_test

// render_test.go covers:
//   TS-01-25  (Per-file render determinism)
//   TS-01-26  (EARS template rendering — all 6 patterns)
//   TS-01-27  (Per-file render API)
//   TS-01-28  (Combined render includes PRD verbatim)
//   TS-01-E13 (EARS render with empty required field)
//   TS-01-E14 (EARS render with null or empty return_contract)
//   TS-01-P2  (EARS rendering determinism property)

import (
	"bytes"
	"strings"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-25: Per-file render determinism
// ---------------------------------------------------------------------------

func TestTS01_25(t *testing.T) {
	req := makeRenderRequirements()

	out1, err := afspec.RenderRequirements(req)
	if err != nil {
		t.Fatalf("RenderRequirements (1): %v", err)
	}
	out2, err := afspec.RenderRequirements(req)
	if err != nil {
		t.Fatalf("RenderRequirements (2): %v", err)
	}

	if !bytes.Equal(out1, out2) {
		t.Errorf("RenderRequirements is not deterministic: outputs differ")
	}
}

// ---------------------------------------------------------------------------
// TS-01-26: EARS template rendering — all 6 patterns
// ---------------------------------------------------------------------------

func TestTS01_26(t *testing.T) {
	cases := []struct {
		name     string
		c        afspec.Criterion
		contains []string
		exact    string
	}{
		{
			name: "ubiquitous",
			c: afspec.Criterion{
				ID:          "01-REQ-1.1",
				EarsPattern: "ubiquitous",
				System:      "the system",
				Action:      "do X",
			},
			exact: "THE the system SHALL do X",
		},
		{
			name: "event_driven",
			c: afspec.Criterion{
				ID:          "01-REQ-1.2",
				EarsPattern: "event_driven",
				Trigger:     "user clicks",
				System:      "the system",
				Action:      "respond",
			},
			exact: "WHEN user clicks, THE the system SHALL respond",
		},
		{
			name: "complex_event",
			c: afspec.Criterion{
				ID:          "01-REQ-1.3",
				EarsPattern: "complex_event",
				Trigger:     "t",
				Condition:   "c",
				System:      "s",
				Action:      "a",
			},
			exact: "WHEN t AND c, THE s SHALL a",
		},
		{
			name: "state_driven",
			c: afspec.Criterion{
				ID:          "01-REQ-1.4",
				EarsPattern: "state_driven",
				State:       "active",
				System:      "s",
				Action:      "a",
			},
			exact: "WHILE active, THE s SHALL a",
		},
		{
			name: "unwanted",
			c: afspec.Criterion{
				ID:             "01-REQ-1.5",
				EarsPattern:    "unwanted",
				ErrorCondition: "disk full",
				System:         "s",
				Action:         "alert",
			},
			exact: "IF disk full, THEN THE s SHALL alert",
		},
		{
			name: "optional",
			c: afspec.Criterion{
				ID:          "01-REQ-1.6",
				EarsPattern: "optional",
				Feature:     "debug mode",
				System:      "s",
				Action:      "log",
			},
			exact: "WHERE debug mode, THE s SHALL log",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			out, err := afspec.RenderEARS(&tc.c)
			if err != nil {
				t.Fatalf("RenderEARS: %v", err)
			}
			if out != tc.exact {
				t.Errorf("RenderEARS(%q) = %q, want %q", tc.name, out, tc.exact)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// TS-01-27: Per-file render API
// ---------------------------------------------------------------------------

func TestTS01_27(t *testing.T) {
	req := makeRenderRequirements()
	mdReq, err := afspec.RenderRequirements(req)
	if err != nil {
		t.Fatalf("RenderRequirements: %v", err)
	}
	if len(mdReq) == 0 {
		t.Error("RenderRequirements returned empty output")
	}
	if !strings.Contains(string(mdReq), "Requirements") {
		t.Errorf("RenderRequirements output should contain 'Requirements'; got %q", string(mdReq)[:min(100, len(mdReq))])
	}

	ts := makeRenderTestSpec()
	mdTS, err := afspec.RenderTestSpec(ts)
	if err != nil {
		t.Fatalf("RenderTestSpec: %v", err)
	}
	if len(mdTS) == 0 {
		t.Error("RenderTestSpec returned empty output")
	}

	tasks := makeRenderTasks()
	mdTasks, err := afspec.RenderTasks(tasks)
	if err != nil {
		t.Fatalf("RenderTasks: %v", err)
	}
	if len(mdTasks) == 0 {
		t.Error("RenderTasks returned empty output")
	}
}

// ---------------------------------------------------------------------------
// TS-01-28: Combined render includes PRD verbatim
// ---------------------------------------------------------------------------

func TestTS01_28(t *testing.T) {
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

	// PRD body must appear verbatim (first 50 chars at minimum)
	prdSnippet := spec.PRD.Body
	if len(prdSnippet) > 50 {
		prdSnippet = prdSnippet[:50]
	}
	if !strings.Contains(content, prdSnippet) {
		t.Errorf("RenderCombined output does not contain PRD body snippet %q", prdSnippet)
	}

	// Requirements section must come after PRD
	prdStart := strings.Index(content, spec.PRD.Body[:20])
	reqStart := strings.Index(content, "SHALL")
	if prdStart < 0 {
		t.Error("PRD body not found in combined output")
	}
	if reqStart < 0 {
		t.Error("EARS sentence (SHALL) not found in combined output")
	}
	if reqStart <= prdStart {
		t.Errorf("requirements section (%d) must come after PRD (%d) in combined output", reqStart, prdStart)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E13: EARS render with empty required field
// ---------------------------------------------------------------------------

func TestTS01_E13(t *testing.T) {
	c := afspec.Criterion{
		ID:          "01-REQ-1.1",
		EarsPattern: "ubiquitous",
		System:      "the system",
		Action:      "", // empty: must render as <missing>
	}

	out, err := afspec.RenderEARS(&c)
	if err != nil {
		t.Fatalf("RenderEARS: %v", err)
	}
	if out != "THE the system SHALL <missing>" {
		t.Errorf("RenderEARS with empty action = %q, want %q", out, "THE the system SHALL <missing>")
	}
}

// ---------------------------------------------------------------------------
// TS-01-E14: EARS render with null or empty return_contract
// ---------------------------------------------------------------------------

func TestTS01_E14(t *testing.T) {
	// Null return_contract: no "AND return" clause
	cNull := afspec.Criterion{
		ID:             "01-REQ-1.1",
		EarsPattern:    "ubiquitous",
		System:         "s",
		Action:         "a",
		ReturnContract: nil,
	}
	outNull, err := afspec.RenderEARS(&cNull)
	if err != nil {
		t.Fatalf("RenderEARS (null): %v", err)
	}
	if strings.Contains(outNull, "AND return") {
		t.Errorf("null return_contract should omit 'AND return'; got %q", outNull)
	}

	// Empty string return_contract: no "AND return" clause
	emptyStr := ""
	cEmpty := afspec.Criterion{
		ID:             "01-REQ-1.1",
		EarsPattern:    "ubiquitous",
		System:         "s",
		Action:         "a",
		ReturnContract: &emptyStr,
	}
	outEmpty, err := afspec.RenderEARS(&cEmpty)
	if err != nil {
		t.Fatalf("RenderEARS (empty): %v", err)
	}
	if strings.Contains(outEmpty, "AND return") {
		t.Errorf("empty return_contract should omit 'AND return'; got %q", outEmpty)
	}

	// Non-null, non-empty return_contract: append "AND return {value}"
	returnVal := "list of items"
	cVal := afspec.Criterion{
		ID:             "01-REQ-1.1",
		EarsPattern:    "ubiquitous",
		System:         "s",
		Action:         "a",
		ReturnContract: &returnVal,
	}
	outVal, err := afspec.RenderEARS(&cVal)
	if err != nil {
		t.Fatalf("RenderEARS (value): %v", err)
	}
	if !strings.Contains(outVal, "AND return list of items") {
		t.Errorf("non-empty return_contract should include 'AND return list of items'; got %q", outVal)
	}
}

// ---------------------------------------------------------------------------
// TS-01-P2: EARS rendering determinism (property test)
// ---------------------------------------------------------------------------

func TestPropertyP2(t *testing.T) {
	// Rendering the same criterion twice must produce identical output.
	patterns := []afspec.Criterion{
		{ID: "x", EarsPattern: "ubiquitous", System: "sys", Action: "act"},
		{ID: "x", EarsPattern: "event_driven", Trigger: "trig", System: "sys", Action: "act"},
		{ID: "x", EarsPattern: "complex_event", Trigger: "t", Condition: "c", System: "sys", Action: "act"},
		{ID: "x", EarsPattern: "state_driven", State: "st", System: "sys", Action: "act"},
		{ID: "x", EarsPattern: "unwanted", ErrorCondition: "err", System: "sys", Action: "act"},
		{ID: "x", EarsPattern: "optional", Feature: "feat", System: "sys", Action: "act"},
	}

	for _, c := range patterns {
		t.Run(c.EarsPattern, func(t *testing.T) {
			cr := c // capture range variable
			r1, err := afspec.RenderEARS(&cr)
			if err != nil {
				t.Fatalf("RenderEARS (1): %v", err)
			}
			r2, err := afspec.RenderEARS(&cr)
			if err != nil {
				t.Fatalf("RenderEARS (2): %v", err)
			}
			if r1 != r2 {
				t.Errorf("RenderEARS(%q) is not deterministic: %q vs %q", c.EarsPattern, r1, r2)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// Helpers for render tests
// ---------------------------------------------------------------------------

func makeRenderRequirements() *afspec.Requirements {
	return &afspec.Requirements{
		SpecID:   "01",
		SpecName: "render_test",
		Introduction: "Test requirements for rendering.",
		Glossary: map[string]string{"term": "definition"},
		Requirements: []afspec.Requirement{
			{
				ID:    "01-REQ-1",
				Title: "Test Requirement",
				UserStory: afspec.UserStory{
					Role: "consumer", Goal: "do something", Benefit: "get results",
				},
				AcceptanceCriteria: []afspec.Criterion{
					{ID: "01-REQ-1.1", EarsPattern: "ubiquitous", System: "the library", Action: "process input"},
					{ID: "01-REQ-1.2", EarsPattern: "event_driven", Trigger: "request arrives", System: "the library", Action: "respond"},
				},
				EdgeCases: []afspec.Criterion{
					{ID: "01-REQ-1.E1", EarsPattern: "unwanted", ErrorCondition: "input is nil", System: "the library", Action: "return error"},
				},
			},
		},
		CorrectnessProperties: []afspec.CorrectnessProperty{},
		ExecutionPaths:        []afspec.ExecutionPath{},
		ErrorHandling:         []afspec.ErrorHandlingEntry{},
		SchemaVersion:         1,
	}
}

func makeRenderTestSpec() *afspec.TestSpecDoc {
	return &afspec.TestSpecDoc{
		SpecID:   "01",
		SpecName: "render_test",
		TestCases: []afspec.TestCase{
			{
				ID:                  "TS-01-1",
				RequirementID:       "01-REQ-1.1",
				Kind:                "unit",
				Description:         "verify basic processing",
				Preconditions:       []string{"library is initialized"},
				AssertionPseudocode: "ASSERT result != nil",
			},
		},
		PropertyTests: []afspec.PropertyTest{},
		EdgeCaseTests: []afspec.EdgeCaseTest{},
		SmokeTests:    []afspec.SmokeTest{},
		Coverage:      afspec.Coverage{},
		SchemaVersion: 1,
	}
}

func makeRenderTasks() *afspec.Tasks {
	return &afspec.Tasks{
		SpecID:   "01",
		SpecName: "render_test",
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
				Title: "Write tests",
				Subtasks: []afspec.Subtask{
					{
						ID:              "1.1",
						Title:           "Write unit tests",
						Details:         []string{"Create test file"},
						TestSpecRefs:    []string{"TS-01-1"},
						RequirementRefs: []string{"01-REQ-1.1"},
						State:           afspec.StatePending,
						Optional:        false,
					},
				},
				Verification: afspec.VerificationSubtask{
					ID:     "1.V",
					Checks: []string{"All tests pass"},
				},
			},
			{
				ID:   2,
				Kind: "wiring_verification",
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
				RequirementID: "01-REQ-1.1",
				TestSpecID:    "TS-01-1",
				TaskID:        "1.1",
				TestPath:      nil,
			},
		},
		SchemaVersion: 1,
	}
}
