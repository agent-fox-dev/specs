package discovery

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"

	"github.com/agent-fox/afspec/internal/prd"
)

// requiredFiles lists the four artifacts a complete spec must have.
var requiredFiles = []string{"prd.md", "requirements.json", "test_spec.json", "tasks.json"}

// SpecMetadata is a lightweight representation of a discovered spec entry.
type SpecMetadata struct {
	Dir      string // absolute path to the spec folder
	SpecID   string
	SpecName string
	Status   string // raw status string from frontmatter
	Complete bool   // true when all four files are present
}

// frontmatterMinimal extracts only the fields we need without importing the
// root afspec package (which would create an import cycle).
type frontmatterMinimal struct {
	SpecID   string `yaml:"spec_id"`
	SpecName string `yaml:"spec_name"`
	Status   string `yaml:"status"`
}

// LoadMetadata reads only the PRD frontmatter from dir and returns a
// SpecMetadata. It does not parse or validate the other three artifacts.
func LoadMetadata(dir string) (*SpecMetadata, error) {
	absDir, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}

	// Check which files exist.
	complete := true
	for _, f := range requiredFiles {
		if _, err := os.Stat(filepath.Join(absDir, f)); os.IsNotExist(err) {
			complete = false
			break
		}
	}

	// Read and parse frontmatter from prd.md.
	data, err := os.ReadFile(filepath.Join(absDir, "prd.md"))
	if err != nil {
		return nil, err
	}

	yamlFM, _, err := prd.SplitFrontmatterBody(data)
	if err != nil {
		return nil, err
	}

	var fm frontmatterMinimal
	if err := yaml.Unmarshal(yamlFM, &fm); err != nil {
		return nil, err
	}

	return &SpecMetadata{
		Dir:      absDir,
		SpecID:   fm.SpecID,
		SpecName: fm.SpecName,
		Status:   fm.Status,
		Complete: complete,
	}, nil
}
