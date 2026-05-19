package afspec

import (
	"bytes"
	"fmt"

	"github.com/agent-fox/afspec/internal/prd"
	"gopkg.in/yaml.v3"
)

// serializePRD serializes a PRD to its prd.md file bytes.
// The YAML frontmatter is written with the canonical field order and the body
// is appended verbatim.
func serializePRD(p *PRD) ([]byte, error) {
	fmYAML, err := marshalFrontmatterOrdered(&p.Frontmatter)
	if err != nil {
		return nil, fmt.Errorf("serialize frontmatter: %w", err)
	}
	return prd.AssemblePRDFile(fmYAML, p.Body), nil
}

// marshalFrontmatterOrdered marshals a Frontmatter in the canonical 12-field
// order using yaml.Node to preserve field ordering.
// Order: spec_id, spec_name, title, status, created_at, updated_at, owner,
// source, supersedes, tags, intent_hash, schema_version.
func marshalFrontmatterOrdered(fm *Frontmatter) ([]byte, error) {
	root := &yaml.Node{Kind: yaml.DocumentNode}
	mapping := &yaml.Node{Kind: yaml.MappingNode, Tag: "!!map"}
	root.Content = append(root.Content, mapping)

	addScalar := func(key, val, tag string) {
		mapping.Content = append(mapping.Content,
			&yaml.Node{Kind: yaml.ScalarNode, Value: key},
			&yaml.Node{Kind: yaml.ScalarNode, Tag: tag, Value: val},
		)
	}
	addStr := func(key, val string) {
		// Always double-quote string values for deterministic, round-trip-safe output.
		n := &yaml.Node{Kind: yaml.ScalarNode, Value: val, Style: yaml.DoubleQuotedStyle}
		mapping.Content = append(mapping.Content,
			&yaml.Node{Kind: yaml.ScalarNode, Value: key},
			n,
		)
	}
	addStrSlice := func(key string, vals []string) {
		seq := &yaml.Node{Kind: yaml.SequenceNode, Tag: "!!seq", Style: yaml.FlowStyle}
		for _, v := range vals {
			// Always double-quote string values in sequences too.
			n := &yaml.Node{Kind: yaml.ScalarNode, Value: v, Style: yaml.DoubleQuotedStyle}
			seq.Content = append(seq.Content, n)
		}
		mapping.Content = append(mapping.Content,
			&yaml.Node{Kind: yaml.ScalarNode, Value: key},
			seq,
		)
	}
	addNullableStr := func(key string, val *string) {
		if val == nil {
			addScalar(key, "null", "!!null")
		} else {
			addStr(key, *val)
		}
	}
	addInt := func(key string, val int) {
		addScalar(key, fmt.Sprintf("%d", val), "!!int")
	}

	addStr("spec_id", fm.SpecID)
	addStr("spec_name", fm.SpecName)
	addStr("title", fm.Title)
	addStr("status", string(fm.Status))
	addStr("created_at", fm.CreatedAt)
	addStr("updated_at", fm.UpdatedAt)
	addStr("owner", fm.Owner)
	addStr("source", fm.Source)
	addStrSlice("supersedes", fm.Supersedes)
	addStrSlice("tags", fm.Tags)
	addNullableStr("intent_hash", fm.IntentHash)
	addInt("schema_version", fm.SchemaVersion)

	var buf bytes.Buffer
	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	if err := enc.Encode(root); err != nil {
		return nil, err
	}
	if err := enc.Close(); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

