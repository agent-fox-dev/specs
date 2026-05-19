package afspec

import "fmt"

// Severity indicates how critical a validation error is.
type Severity string

const (
	SeverityError   Severity = "error"
	SeverityWarning Severity = "warning"
)

// ValidationError describes a single validation violation found during spec checking.
type ValidationError struct {
	File     string   `json:"file"`     // e.g., "requirements.json"
	Path     string   `json:"path"`     // JSON path, e.g., "/requirements/0/acceptance_criteria/1"
	Rule     string   `json:"rule"`     // e.g., "schema", "integrity-1", "id-format"
	Message  string   `json:"message"`  // human-readable description
	Severity Severity `json:"severity"` // "error" or "warning"
}

// LifecycleError is returned when a lifecycle transition is rejected.
type LifecycleError struct {
	Current Status
	Target  Status
	Reason  string
}

// Error implements the error interface.
func (e *LifecycleError) Error() string {
	return fmt.Sprintf("invalid lifecycle transition from %q to %q: %s", e.Current, e.Target, e.Reason)
}

// IncompleteSpecError is returned when Finalize() is called on a partial spec.
type IncompleteSpecError struct {
	MissingFiles []string
}

// Error implements the error interface.
func (e *IncompleteSpecError) Error() string {
	return fmt.Sprintf("incomplete spec: missing files: %v", e.MissingFiles)
}
