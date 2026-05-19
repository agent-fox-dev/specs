package afspec

// Tasks represents the top-level container for tasks.json.
type Tasks struct {
	Comment      string             `json:"$comment,omitempty"` // deprecation banner (superseded specs)
	Schema       string             `json:"$schema"`
	SpecID       string             `json:"spec_id"`
	SpecName     string             `json:"spec_name"`
	SchemaVersion int               `json:"schema_version"`
	TestCommands TestCommands       `json:"test_commands"`
	Dependencies []TaskDependency   `json:"dependencies"`
	TaskGroups   []TaskGroup        `json:"task_groups"`
	Traceability []TraceabilityEntry `json:"traceability"`
}

// TestCommands holds the shell commands for running tests and the linter.
type TestCommands struct {
	SpecTests string `json:"spec_tests"`
	AllTests  string `json:"all_tests"`
	Linter    string `json:"linter"`
}

// TaskDependency declares a cross-spec dependency between task groups.
type TaskDependency struct {
	DependsOnSpec string `json:"depends_on_spec"`
	FromGroup     int    `json:"from_group"`
	ToGroup       int    `json:"to_group"`
	Relationship  string `json:"relationship"`
	Sentinel      bool   `json:"sentinel"`
}

// TaskGroup is a cohesive set of subtasks sharing a single verification step.
type TaskGroup struct {
	ID           int                 `json:"id"`
	Kind         string              `json:"kind"` // tests | standard | checkpoint | wiring_verification
	Title        string              `json:"title"`
	Subtasks     []Subtask           `json:"subtasks"`
	Verification VerificationSubtask `json:"verification"`
}

// Subtask is a single work item within a task group.
type Subtask struct {
	ID              string       `json:"id"`   // {group}.{N}
	Title           string       `json:"title"`
	Details         []string     `json:"details"`
	TestSpecRefs    []string     `json:"test_spec_refs"`
	RequirementRefs []string     `json:"requirement_refs"`
	State           SubtaskState `json:"state"`
	Optional        bool         `json:"optional"`
}

// SubtaskState represents the execution state of a subtask.
type SubtaskState string

const (
	StatePending             SubtaskState = "pending"
	StateQueued              SubtaskState = "queued"
	StateInProgress          SubtaskState = "in_progress"
	StateDone                SubtaskState = "done"
	StatePendingReevaluation SubtaskState = "pending_reevaluation"
	StateDropped             SubtaskState = "dropped"
)

// LegalTransitions returns the allowed next states for a given subtask state.
func (s SubtaskState) LegalTransitions() []SubtaskState {
	switch s {
	case StatePending:
		return []SubtaskState{StateQueued, StateDropped}
	case StateQueued:
		return []SubtaskState{StateInProgress, StatePending, StateDropped}
	case StateInProgress:
		return []SubtaskState{StateDone, StatePendingReevaluation}
	case StateDone:
		return []SubtaskState{StatePendingReevaluation}
	case StatePendingReevaluation:
		return []SubtaskState{StatePending, StateDropped}
	case StateDropped:
		return []SubtaskState{}
	default:
		return nil
	}
}

// VerificationSubtask is the final verification step for a task group.
type VerificationSubtask struct {
	ID     string   `json:"id"` // {group}.V
	Checks []string `json:"checks"`
}

// TraceabilityEntry links a requirement to its test spec entry and task.
type TraceabilityEntry struct {
	RequirementID string  `json:"requirement_id"`
	TestSpecID    string  `json:"test_spec_id"`
	TaskID        string  `json:"task_id"`
	TestPath      *string `json:"test_path"` // nullable until test is written
}
