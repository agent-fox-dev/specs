package afspec

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"github.com/agent-fox/afspec/internal/ioutil"
	"github.com/agent-fox/afspec/internal/jsonutil"
	"github.com/agent-fox/afspec/internal/prd"
)

// Bootstrap provides an incremental spec-creation workflow. Files can be
// written one at a time; cross-file validation is deferred until Finalize.
type Bootstrap struct {
	dir      string
	specID   string
	specName string
	written  map[string]bool // tracks which files have been written
	mu       sync.Mutex      // guards concurrent access
}

// NewBootstrap creates a new spec folder and returns a Bootstrap handle
// for writing files one at a time.
// Returns an error if the folder already exists.
func NewBootstrap(dir string, specID string, specName string) (*Bootstrap, error) {
	// Check if the directory already exists.
	if _, err := os.Stat(dir); err == nil {
		return nil, fmt.Errorf("spec folder %q already exists; use LoadSpec to open an existing spec", dir)
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("stat %q: %w", dir, err)
	}

	// Create the directory.
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("create spec folder %q: %w", dir, err)
	}

	return &Bootstrap{
		dir:      dir,
		specID:   specID,
		specName: specName,
		written:  make(map[string]bool),
	}, nil
}

// WritePRD validates (per-file schema only) and writes prd.md to the bootstrap
// folder. May be called multiple times; the last write wins.
func (b *Bootstrap) WritePRD(p *PRD) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Per-file schema validation only — no cross-file checks.
	schemaErrs := validateFrontmatter(&p.Frontmatter)
	if len(schemaErrs) > 0 {
		return fmt.Errorf("prd.md schema validation failed: %v", schemaErrs[0].Message)
	}

	// Verify the Intent section is present.
	if !prd.HasIntentSection(p.Body) {
		return fmt.Errorf("prd.md validation failed: ## Intent section is required")
	}

	data, err := serializePRD(p)
	if err != nil {
		return fmt.Errorf("serialize prd.md: %w", err)
	}

	if err := ioutil.WriteAtomic(filepath.Join(b.dir, "prd.md"), data, 0o644); err != nil {
		return fmt.Errorf("write prd.md: %w", err)
	}

	b.written["prd.md"] = true
	return nil
}

// WriteRequirements validates (per-file schema only) and writes requirements.json
// to the bootstrap folder. May be called multiple times; the last write wins.
func (b *Bootstrap) WriteRequirements(req *Requirements) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	schemaErrs := validateRequirementsSchema(req)
	if len(schemaErrs) > 0 {
		return fmt.Errorf("requirements.json schema validation failed: %v", schemaErrs[0].Message)
	}

	data, err := jsonutil.MarshalDeterministic(req)
	if err != nil {
		return fmt.Errorf("serialize requirements.json: %w", err)
	}

	if err := ioutil.WriteAtomic(filepath.Join(b.dir, "requirements.json"), data, 0o644); err != nil {
		return fmt.Errorf("write requirements.json: %w", err)
	}

	b.written["requirements.json"] = true
	return nil
}

// WriteTestSpec validates (per-file schema only) and writes test_spec.json
// to the bootstrap folder. May be called multiple times; the last write wins.
func (b *Bootstrap) WriteTestSpec(ts *TestSpecDoc) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	schemaErrs := validateTestSpecSchema(ts)
	if len(schemaErrs) > 0 {
		return fmt.Errorf("test_spec.json schema validation failed: %v", schemaErrs[0].Message)
	}

	data, err := jsonutil.MarshalDeterministic(ts)
	if err != nil {
		return fmt.Errorf("serialize test_spec.json: %w", err)
	}

	if err := ioutil.WriteAtomic(filepath.Join(b.dir, "test_spec.json"), data, 0o644); err != nil {
		return fmt.Errorf("write test_spec.json: %w", err)
	}

	b.written["test_spec.json"] = true
	return nil
}

// WriteTasks validates (per-file schema only) and writes tasks.json to the
// bootstrap folder. May be called multiple times; the last write wins.
func (b *Bootstrap) WriteTasks(tasks *Tasks) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	schemaErrs := validateTasksSchema(tasks)
	if len(schemaErrs) > 0 {
		return fmt.Errorf("tasks.json schema validation failed: %v", schemaErrs[0].Message)
	}

	data, err := jsonutil.MarshalDeterministic(tasks)
	if err != nil {
		return fmt.Errorf("serialize tasks.json: %w", err)
	}

	if err := ioutil.WriteAtomic(filepath.Join(b.dir, "tasks.json"), data, 0o644); err != nil {
		return fmt.Errorf("write tasks.json: %w", err)
	}

	b.written["tasks.json"] = true
	return nil
}

// Finalize runs full validation (schema + cross-file integrity) and returns
// the completed Spec on success, or all validation errors on failure.
// Returns IncompleteSpecError if any of the four files have not been written.
func (b *Bootstrap) Finalize() (*Spec, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	required := []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"}
	var missing []string
	for _, f := range required {
		if !b.written[f] {
			missing = append(missing, f)
		}
	}
	if len(missing) > 0 {
		return nil, &IncompleteSpecError{MissingFiles: missing}
	}

	// Load the complete spec from disk.
	spec, err := LoadSpec(b.dir)
	if err != nil {
		return nil, fmt.Errorf("finalize: load spec: %w", err)
	}

	// Run full validation (schema + cross-file + IDs).
	errs, err := Validate(spec)
	if err != nil {
		return nil, fmt.Errorf("finalize: validation error: %w", err)
	}
	// Only block on errors, not warnings.
	var blockingErrs []ValidationError
	for _, e := range errs {
		if e.Severity == SeverityError {
			blockingErrs = append(blockingErrs, e)
		}
	}
	if len(blockingErrs) > 0 {
		return nil, fmt.Errorf("finalize: spec has %d validation error(s): first error: %v",
			len(blockingErrs), blockingErrs[0].Message)
	}

	return spec, nil
}
