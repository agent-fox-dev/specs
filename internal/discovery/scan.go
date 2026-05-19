// Package discovery provides spec root scanning, metadata loading, and
// dependency-graph construction for the afspec library.
package discovery

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
)

// specDirPattern matches directory names like "01_feature_name" or "99_my_spec".
var specDirPattern = regexp.MustCompile(`^(\d+)_([a-z][a-z0-9_]*)$`)

// ScanRoot scans root for directories matching {NN}_{snake_case_name} and
// returns their absolute paths. The "archive" subdirectory is always skipped.
// If root is empty, the current working directory is used.
func ScanRoot(root string) ([]string, error) {
	if root == "" {
		var err error
		root, err = os.Getwd()
		if err != nil {
			return nil, fmt.Errorf("getwd: %w", err)
		}
	}

	info, err := os.Stat(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("spec root %q not found", root)
		}
		return nil, fmt.Errorf("stat %q: %w", root, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("%q is not a directory", root)
	}

	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, fmt.Errorf("read dir %q: %w", root, err)
	}

	var dirs []string
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		name := e.Name()
		// Skip the archive subdirectory regardless of case (exact match).
		if name == "archive" {
			continue
		}
		if specDirPattern.MatchString(name) {
			dirs = append(dirs, filepath.Join(root, name))
		}
	}
	return dirs, nil
}

// ParseSpecDir extracts specID and specName from a directory name matching
// {NN}_{snake_case_name}. Returns an error if the name does not match.
func ParseSpecDir(name string) (specID, specName string, err error) {
	m := specDirPattern.FindStringSubmatch(name)
	if m == nil {
		return "", "", fmt.Errorf("directory name %q does not match spec pattern", name)
	}
	return m[1], m[2], nil
}
