package afspec

import "errors"

// Transition applies a lifecycle state transition.
// Returns a new Spec with updated state (original is not modified).
// Returns an error if the transition is illegal or any guard is violated.
func Transition(spec *Spec, target Status) (*Spec, error) {
	return nil, errors.New("not implemented")
}

// ComputeIntentHash computes the SHA-256 hash of the normalised Intent section body.
// Normalisation: trim leading and trailing whitespace.
// Returns a 64-character lowercase hex string.
func ComputeIntentHash(body string) string {
	return ""
}
