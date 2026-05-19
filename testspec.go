package afspec

// TestSpecDoc represents the top-level container for test_spec.json.
type TestSpecDoc struct {
	Comment       string         `json:"$comment,omitempty"` // deprecation banner (superseded specs)
	Schema        string         `json:"$schema"`
	SpecID        string         `json:"spec_id"`
	SpecName      string         `json:"spec_name"`
	SchemaVersion int            `json:"schema_version"`
	TestCases     []TestCase     `json:"test_cases"`
	PropertyTests []PropertyTest `json:"property_tests"`
	EdgeCaseTests []EdgeCaseTest `json:"edge_case_tests"`
	SmokeTests    []SmokeTest    `json:"smoke_tests"`
	Coverage      Coverage       `json:"coverage"`
}

// TestCase is a single unit or integration test contract.
type TestCase struct {
	ID                  string      `json:"id"` // TS-{spec_id}-{N}
	RequirementID       string      `json:"requirement_id"`
	Kind                string      `json:"kind"` // "unit" | "integration"
	Description         string      `json:"description"`
	Preconditions       []string    `json:"preconditions"`
	Input               any    `json:"input"`
	Expected            any    `json:"expected"`
	AssertionPseudocode string `json:"assertion_pseudocode"`
}

// PropertyTest expresses a property-based test contract tied to a correctness property.
type PropertyTest struct {
	ID             string   `json:"id"` // TS-{spec_id}-P{N}
	PropertyID     string   `json:"property_id"`
	Validates      []string `json:"validates"`
	Description    string   `json:"description"`
	ForAnyStrategy string   `json:"for_any_strategy"`
	InvariantCheck string   `json:"invariant_check"`
}

// EdgeCaseTest is a test contract for an edge case criterion.
type EdgeCaseTest struct {
	ID                  string      `json:"id"` // TS-{spec_id}-E{N}
	RequirementID       string      `json:"requirement_id"`
	Kind                string      `json:"kind"`
	Description         string      `json:"description"`
	Preconditions       []string    `json:"preconditions"`
	Input               any    `json:"input"`
	Expected            any    `json:"expected"`
	AssertionPseudocode string `json:"assertion_pseudocode"`
}

// SmokeTest exercises a full execution path with real components.
type SmokeTest struct {
	ID              string   `json:"id"` // TS-{spec_id}-SMOKE-{N}
	ExecutionPathID string   `json:"execution_path_id"`
	Description     string   `json:"description"`
	Trigger         string   `json:"trigger"`
	RealComponents  []string `json:"real_components"`
	Mockable        []string `json:"mockable"`
	ExpectedEffects []string `json:"expected_effects"`
}

// Coverage summarises which requirements and paths are covered by tests.
// It is computed automatically by SaveSpec on every save.
type Coverage struct {
	RequirementsCovered []string `json:"requirements_covered"`
	PropertiesCovered   []string `json:"properties_covered"`
	PathsCovered        []string `json:"paths_covered"`
	Gaps                []string `json:"gaps"`
}
