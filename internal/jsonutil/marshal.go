// Package jsonutil provides deterministic JSON marshaling and strict unmarshaling.
package jsonutil

import (
	"encoding/json"
)

// MarshalDeterministic marshals v to JSON with alphabetically sorted keys,
// 2-space indentation, and a trailing newline.
//
// It achieves sorted keys by marshaling to JSON, parsing into any
// (where objects become map[string]any which json.MarshalIndent sorts),
// and re-marshaling.
func MarshalDeterministic(v any) ([]byte, error) {
	// First pass: marshal the typed value to get all field values.
	raw, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}

	// Second pass: unmarshal into a generic any so that all JSON
	// objects become map[string]any (which json.MarshalIndent sorts
	// alphabetically) and all arrays become []any.
	var m any
	if err := json.Unmarshal(raw, &m); err != nil {
		return nil, err
	}

	// Third pass: marshal with sorted keys and 2-space indentation.
	out, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return nil, err
	}

	// Append trailing newline required by the spec.
	return append(out, '\n'), nil
}
