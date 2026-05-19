package afspec

import (
	"errors"
	"sync"
)

// Bootstrap provides an incremental spec-creation workflow. Files can be
// written one at a time; cross-file validation is deferred until Finalize.
type Bootstrap struct {
	dir      string
	specID   string
	specName string
	written  map[string]bool
	mu       sync.Mutex
}

// NewBootstrap creates a new spec folder and returns a Bootstrap handle
// for writing files one at a time.
// Returns an error if the folder already exists.
func NewBootstrap(dir string, specID string, specName string) (*Bootstrap, error) {
	return nil, errors.New("not implemented")
}

// WritePRD validates and writes prd.md to the bootstrap folder.
func (b *Bootstrap) WritePRD(prd *PRD) error {
	return errors.New("not implemented")
}

// WriteRequirements validates and writes requirements.json to the bootstrap folder.
func (b *Bootstrap) WriteRequirements(req *Requirements) error {
	return errors.New("not implemented")
}

// WriteTestSpec validates and writes test_spec.json to the bootstrap folder.
func (b *Bootstrap) WriteTestSpec(ts *TestSpecDoc) error {
	return errors.New("not implemented")
}

// WriteTasks validates and writes tasks.json to the bootstrap folder.
func (b *Bootstrap) WriteTasks(tasks *Tasks) error {
	return errors.New("not implemented")
}

// Finalize runs full validation (schema + cross-file integrity) and returns
// the completed Spec on success, or all validation errors on failure.
// Returns IncompleteSpecError if any of the four files have not been written.
func (b *Bootstrap) Finalize() (*Spec, error) {
	return nil, errors.New("not implemented")
}
