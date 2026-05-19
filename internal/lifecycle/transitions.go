package lifecycle

import "fmt"

// Status mirrors the afspec.Status type to avoid import cycles.
// The values must match exactly.
type Status string

const (
	StatusDraft      Status = "draft"
	StatusActive     Status = "active"
	StatusSealed     Status = "sealed"
	StatusSuperseded Status = "superseded"
	StatusArchived   Status = "archived"
)

// legalEdges defines the allowed lifecycle transitions.
// Terminal states (superseded, archived) have no outgoing edges.
var legalEdges = map[Status][]Status{
	StatusDraft:  {StatusActive, StatusArchived},
	StatusActive: {StatusSealed},
	StatusSealed: {StatusSuperseded, StatusArchived},
	// superseded and archived are terminal states
	StatusSuperseded: {},
	StatusArchived:   {},
}

// TransitionError is returned when an illegal transition is attempted.
type TransitionError struct {
	Current Status
	Target  Status
}

func (e *TransitionError) Error() string {
	return fmt.Sprintf("invalid lifecycle transition from %q to %q", e.Current, e.Target)
}

// ValidateTransition returns nil if the transition from current to target is
// legal, or a *TransitionError if it is not.
func ValidateTransition(current, target Status) error {
	allowed, ok := legalEdges[current]
	if !ok {
		// Unknown state — treat as terminal, no outgoing edges.
		return &TransitionError{Current: current, Target: target}
	}
	for _, s := range allowed {
		if s == target {
			return nil
		}
	}
	return &TransitionError{Current: current, Target: target}
}
