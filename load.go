package afspec

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/agent-fox/afspec/internal/ioutil"
	"github.com/agent-fox/afspec/internal/jsonutil"
	prdpkg "github.com/agent-fox/afspec/internal/prd"
	"gopkg.in/yaml.v3"
)

// LoadSpec reads all four spec files from dir and returns a populated Spec.
// Returns an error if dir does not exist, any file is missing, or any file
// contains malformed content.
func LoadSpec(dir string) (*Spec, error) {
	// Verify the directory exists and is a directory.
	info, err := os.Stat(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("spec folder %q not found", dir)
		}
		return nil, fmt.Errorf("stat %q: %w", dir, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("%q is not a directory", dir)
	}

	// Check which of the four required files are present.
	required := []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"}
	var missing []string
	for _, f := range required {
		if _, err := os.Stat(filepath.Join(dir, f)); os.IsNotExist(err) {
			missing = append(missing, f)
		}
	}
	if len(missing) > 0 {
		return nil, fmt.Errorf("spec folder %q is missing required files: %v", dir, missing)
	}

	// --- prd.md ---
	prdData, err := ioutil.ReadFile(filepath.Join(dir, "prd.md"))
	if err != nil {
		return nil, err
	}
	parsedPRD, err := loadPRD(prdData)
	if err != nil {
		return nil, fmt.Errorf("prd.md: %w", err)
	}

	// --- requirements.json ---
	reqData, err := ioutil.ReadFile(filepath.Join(dir, "requirements.json"))
	if err != nil {
		return nil, err
	}
	var reqs Requirements
	if err := jsonutil.UnmarshalStrict(reqData, &reqs); err != nil {
		return nil, fmt.Errorf("requirements.json: %w", err)
	}

	// --- test_spec.json ---
	tsData, err := ioutil.ReadFile(filepath.Join(dir, "test_spec.json"))
	if err != nil {
		return nil, err
	}
	var testSpec TestSpecDoc
	if err := jsonutil.UnmarshalStrict(tsData, &testSpec); err != nil {
		return nil, fmt.Errorf("test_spec.json: %w", err)
	}

	// --- tasks.json ---
	tasksData, err := ioutil.ReadFile(filepath.Join(dir, "tasks.json"))
	if err != nil {
		return nil, err
	}
	var tasks Tasks
	if err := jsonutil.UnmarshalStrict(tasksData, &tasks); err != nil {
		return nil, fmt.Errorf("tasks.json: %w", err)
	}

	absDir, err := filepath.Abs(dir)
	if err != nil {
		return nil, fmt.Errorf("abs path for %q: %w", dir, err)
	}

	return &Spec{
		PRD:          parsedPRD,
		Requirements: &reqs,
		TestSpec:     &testSpec,
		Tasks:        &tasks,
		Dir:          absDir,
	}, nil
}

// loadPRD parses the raw bytes of a prd.md file into a PRD struct.
func loadPRD(data []byte) (*PRD, error) {
	yamlFM, body, err := prdpkg.SplitFrontmatterBody(data)
	if err != nil {
		return nil, err
	}

	var fm Frontmatter
	if err := yaml.Unmarshal(yamlFM, &fm); err != nil {
		return nil, fmt.Errorf("malformed YAML frontmatter: %w", err)
	}

	if !prdpkg.HasIntentSection(body) {
		return nil, fmt.Errorf("missing '## Intent' section")
	}

	return &PRD{
		Frontmatter: fm,
		Body:        body,
	}, nil
}
