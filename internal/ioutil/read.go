// Package ioutil provides atomic file writing and file reading helpers.
package ioutil

import (
	"fmt"
	"os"
)

// ReadFile reads the contents of the file at path.
// Returns a descriptive error on failure.
func ReadFile(path string) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	return data, nil
}
