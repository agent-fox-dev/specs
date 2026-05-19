package afspec

import "errors"

// LoadSpec reads all four spec files from dir and returns a populated Spec.
// Returns an error if dir does not exist, any file is missing, or any file
// contains malformed content.
func LoadSpec(dir string) (*Spec, error) {
	return nil, errors.New("not implemented")
}
