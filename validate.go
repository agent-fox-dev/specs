package afspec

import "errors"

// Validate runs schema validation, cross-file integrity, and ID validation.
// Returns all errors found (empty slice means valid).
func Validate(spec *Spec) ([]ValidationError, error) {
	return nil, errors.New("not implemented")
}

// ValidateSchema runs only JSON Schema validation per file.
func ValidateSchema(spec *Spec) ([]ValidationError, error) {
	return nil, errors.New("not implemented")
}

// ValidateCrossFile runs only cross-file integrity checks (7 rules).
func ValidateCrossFile(spec *Spec) ([]ValidationError, error) {
	return nil, errors.New("not implemented")
}

// ValidateIDs validates all ID fields against the spec-format conventions.
func ValidateIDs(spec *Spec) ([]ValidationError, error) {
	return nil, errors.New("not implemented")
}

// GetEmbeddedSchemas returns a map of schema name to raw JSON bytes for all
// four bundled JSON Schema files.
func GetEmbeddedSchemas() map[string][]byte {
	return nil
}
