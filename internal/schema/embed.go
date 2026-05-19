// Package schema embeds the four JSON Schema files used to validate spec
// artifacts and exposes them as raw bytes for callers.
package schema

import _ "embed"

//go:embed prd-frontmatter.v1.json
var prdFrontmatterSchema []byte

//go:embed requirements.v1.json
var requirementsSchema []byte

//go:embed test_spec.v1.json
var testSpecSchema []byte

//go:embed tasks.v1.json
var tasksSchema []byte

// Schemas returns a map of schema file name → raw JSON bytes for all four
// bundled JSON Schema files. The bytes are the embedded file contents.
func Schemas() map[string][]byte {
	return map[string][]byte{
		"prd-frontmatter.v1.json": prdFrontmatterSchema,
		"requirements.v1.json":    requirementsSchema,
		"test_spec.v1.json":       testSpecSchema,
		"tasks.v1.json":           tasksSchema,
	}
}
