package lifecycle

import (
	"errors"
	"fmt"
)

// CheckIntentHash verifies that the intent hash stored in intentHash (the
// value from Frontmatter.IntentHash) matches the hash computed from intentBody
// (the raw text of the ## Intent section, already extracted from the PRD body).
//
// Returns nil if:
//   - intentHash is nil (no hash was stored yet — draft state)
//   - The computed hash matches the stored hash
//
// Returns an error if the computed hash differs from the stored hash.
func CheckIntentHash(storedHash *string, intentBody string) error {
	if storedHash == nil {
		// No hash stored — spec is probably in draft, nothing to verify.
		return nil
	}
	computed := ComputeIntentHash(intentBody)
	if computed != *storedHash {
		return fmt.Errorf(
			"intent section has been modified since the draft→active transition "+
				"(stored hash %s, computed hash %s)",
			*storedHash, computed,
		)
	}
	return nil
}

// ErrImmutableState is a sentinel error type for mutation-rejection on
// sealed/superseded/archived specs.
type ErrImmutableState struct {
	State Status
}

func (e *ErrImmutableState) Error() string {
	return fmt.Sprintf("cannot mutate spec in %q state: all mutations are rejected", e.State)
}

// Is implements errors.Is so callers can use errors.Is(err, &ErrImmutableState{}).
func (e *ErrImmutableState) Is(target error) bool {
	var t *ErrImmutableState
	return errors.As(target, &t)
}
