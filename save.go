package afspec

import "errors"

// SaveSpec writes all four spec files to dir deterministically.
// It sets updated_at to the current UTC timestamp and computes the coverage
// field before writing. Returns an error if dir does not exist or any write
// fails.
func SaveSpec(dir string, spec *Spec) error {
	return errors.New("not implemented")
}
