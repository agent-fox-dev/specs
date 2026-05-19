// Package afspec provides data structures, file I/O, validation, rendering,
// lifecycle management, and discovery for the agent-fox specification format.
package afspec

// Status represents the lifecycle state of a spec.
type Status string

const (
	StatusDraft      Status = "draft"
	StatusActive     Status = "active"
	StatusSealed     Status = "sealed"
	StatusSuperseded Status = "superseded"
	StatusArchived   Status = "archived"
)

// Spec is the complete in-memory representation of a four-artifact spec package.
type Spec struct {
	PRD          *PRD
	Requirements *Requirements
	TestSpec     *TestSpecDoc
	Tasks        *Tasks
	Dir          string // absolute path to spec folder on disk
}

// PRD represents prd.md: YAML frontmatter + markdown body.
type PRD struct {
	Frontmatter Frontmatter
	Body        string // full markdown body (everything after frontmatter)
}

// Frontmatter contains the 12 YAML frontmatter fields with fixed serialization order.
type Frontmatter struct {
	SpecID        string   `yaml:"spec_id"        json:"spec_id"`
	SpecName      string   `yaml:"spec_name"      json:"spec_name"`
	Title         string   `yaml:"title"          json:"title"`
	Status        Status   `yaml:"status"         json:"status"`
	CreatedAt     string   `yaml:"created_at"     json:"created_at"`   // ISO 8601
	UpdatedAt     string   `yaml:"updated_at"     json:"updated_at"`   // ISO 8601
	Owner         string   `yaml:"owner"          json:"owner"`
	Source        string   `yaml:"source"         json:"source"`
	Supersedes    []string `yaml:"supersedes"     json:"supersedes"`
	Tags          []string `yaml:"tags"           json:"tags"`
	IntentHash    *string  `yaml:"intent_hash"    json:"intent_hash"` // nullable
	SchemaVersion int      `yaml:"schema_version" json:"schema_version"`
}
