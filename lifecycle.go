package afspec

import (
	"errors"

	"github.com/agent-fox/afspec/internal/lifecycle"
	prdpkg "github.com/agent-fox/afspec/internal/prd"
)

// Transition applies a lifecycle state transition.
// Returns a new Spec with updated state (original is not modified).
// Returns an error if the transition is illegal or any guard is violated.
func Transition(spec *Spec, target Status) (*Spec, error) {
	return nil, errors.New("not implemented")
}

// ComputeIntentHash computes the SHA-256 hash of the normalised Intent section
// body extracted from the PRD body. The body passed should be the full PRD
// body (everything after the closing "---" delimiter); the Intent section is
// extracted automatically.
//
// Returns a 64-character lowercase hex string.
func ComputeIntentHash(body string) string {
	intentBody, err := prdpkg.ExtractIntent(body)
	if err != nil {
		// If there is no intent section, hash the empty normalized string.
		return lifecycle.ComputeIntentHash("")
	}
	return lifecycle.ComputeIntentHash(intentBody)
}
