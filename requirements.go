package afspec

// Requirements represents the top-level container for requirements.json.
type Requirements struct {
	Schema                string                `json:"$schema"`
	SpecID                string                `json:"spec_id"`
	SpecName              string                `json:"spec_name"`
	SchemaVersion         int                   `json:"schema_version"`
	Introduction          string                `json:"introduction"`
	Glossary              map[string]string     `json:"glossary"`
	Requirements          []Requirement         `json:"requirements"`
	CorrectnessProperties []CorrectnessProperty `json:"correctness_properties"`
	ExecutionPaths        []ExecutionPath       `json:"execution_paths"`
	ErrorHandling         []ErrorHandlingEntry  `json:"error_handling"`
}

// Requirement holds a single numbered requirement with its user story, acceptance
// criteria, and edge cases.
type Requirement struct {
	ID                 string      `json:"id"`    // {spec_id}-REQ-{N}
	Title              string      `json:"title"`
	UserStory          UserStory   `json:"user_story"`
	AcceptanceCriteria []Criterion `json:"acceptance_criteria"`
	EdgeCases          []Criterion `json:"edge_cases"`
}

// UserStory captures the role/goal/benefit triple for a requirement.
type UserStory struct {
	Role    string `json:"role"`
	Goal    string `json:"goal"`
	Benefit string `json:"benefit"`
}

// Criterion is the EARS discriminated union. EarsPattern determines which
// pattern-specific fields are populated. Common fields are always present.
// ReturnContract is always serialized (as null or string), never omitted.
type Criterion struct {
	// Common fields (all patterns)
	ID             string  `json:"id"`
	EarsPattern    string  `json:"ears_pattern"`
	System         string  `json:"system"`
	Action         string  `json:"action"`
	ReturnContract *string `json:"return_contract"` // always serialized (null or string)

	// Pattern-specific fields (omitted when not applicable)
	Trigger        string `json:"trigger,omitempty"`         // event_driven, complex_event
	Condition      string `json:"condition,omitempty"`       // complex_event
	ErrorCondition string `json:"error_condition,omitempty"` // unwanted
	State          string `json:"state,omitempty"`           // state_driven
	Feature        string `json:"feature,omitempty"`         // optional
}

// CorrectnessProperty expresses an invariant that must hold for any valid input.
type CorrectnessProperty struct {
	ID        string   `json:"id"`        // {spec_id}-PROP-{N}
	Title     string   `json:"title"`
	ForAny    string   `json:"for_any"`
	Invariant string   `json:"invariant"`
	Validates []string `json:"validates"` // criterion IDs
}

// ExecutionPath describes a named sequence of steps through the system.
type ExecutionPath struct {
	ID    string              `json:"id"` // {spec_id}-PATH-{N}
	Title string              `json:"title"`
	Steps []ExecutionPathStep `json:"steps"`
}

// ExecutionPathStep is a single actor-action pair within an execution path.
type ExecutionPathStep struct {
	Actor  string `json:"actor"`
	Action string `json:"action"`
}

// ErrorHandlingEntry maps an error condition to a requirement.
type ErrorHandlingEntry struct {
	ID            string `json:"id"` // {spec_id}-ERR-{N}
	Condition     string `json:"condition"`
	Behavior      string `json:"behavior"`
	RequirementID string `json:"requirement_id"`
}
