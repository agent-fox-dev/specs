package ioutil

import (
	"fmt"
	"os"
	"path/filepath"
)

// WriteAtomic writes data to path using a write-to-temp-file-then-rename
// strategy to prevent partial writes on failure.
//
// The temporary file is created in the same directory as path to ensure
// that the rename is an atomic operation on the same filesystem.
func WriteAtomic(path string, data []byte, perm os.FileMode) error {
	dir := filepath.Dir(path)

	// Create a temporary file in the same directory as the target.
	tmp, err := os.CreateTemp(dir, ".tmp-")
	if err != nil {
		return fmt.Errorf("create temp file for %s: %w", path, err)
	}
	tmpName := tmp.Name()

	// Ensure the temp file is removed if the operation fails.
	success := false
	defer func() {
		if !success {
			os.Remove(tmpName) //nolint:errcheck
		}
	}()

	// Write content.
	if _, err := tmp.Write(data); err != nil {
		tmp.Close() //nolint:errcheck
		return fmt.Errorf("write temp file for %s: %w", path, err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp file for %s: %w", path, err)
	}

	// Set permissions.
	if err := os.Chmod(tmpName, perm); err != nil {
		return fmt.Errorf("chmod temp file for %s: %w", path, err)
	}

	// Atomic rename.
	if err := os.Rename(tmpName, path); err != nil {
		return fmt.Errorf("rename temp file to %s: %w", path, err)
	}

	success = true
	return nil
}
