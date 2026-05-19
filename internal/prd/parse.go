// Package prd handles structural parsing and assembly of prd.md files.
// It works with raw bytes and strings; type conversion is done by callers.
package prd

import (
	"fmt"
	"strings"
)

// SplitFrontmatterBody splits the raw bytes of a prd.md file into the YAML
// frontmatter bytes (the content between the "---" delimiters, not including
// the delimiters themselves) and the body string (everything after the closing
// "---" line, including the leading newline).
//
// Returns an error if the file does not start with "---", or if the closing
// "---" delimiter is missing.
func SplitFrontmatterBody(data []byte) (yamlFM []byte, body string, err error) {
	content := string(data)
	lines := strings.Split(content, "\n")

	if len(lines) < 2 || strings.TrimRight(lines[0], "\r") != "---" {
		return nil, "", fmt.Errorf("missing opening '---' frontmatter delimiter")
	}

	// Find the closing "---" delimiter.
	closingIdx := -1
	for i := 1; i < len(lines); i++ {
		if strings.TrimRight(lines[i], "\r") == "---" {
			closingIdx = i
			break
		}
	}
	if closingIdx < 0 {
		return nil, "", fmt.Errorf("missing closing '---' frontmatter delimiter")
	}

	// YAML frontmatter is between line 1 and closingIdx (exclusive).
	yamlLines := lines[1:closingIdx]
	yamlContent := strings.Join(yamlLines, "\n")

	// Body is everything after the closing "---" line (as a single string).
	bodyLines := lines[closingIdx+1:]
	body = strings.Join(bodyLines, "\n")

	return []byte(yamlContent), body, nil
}

// AssemblePRDFile assembles the raw bytes of a prd.md file from the YAML
// frontmatter bytes (without "---" delimiters) and the body string.
func AssemblePRDFile(frontmatterYAML []byte, body string) []byte {
	var sb strings.Builder
	sb.WriteString("---\n")
	sb.Write(frontmatterYAML)
	sb.WriteString("---")

	// Body starts with a "\n" (the newline after the closing "---").
	if body != "" && !strings.HasPrefix(body, "\n") {
		sb.WriteByte('\n')
	}
	sb.WriteString(body)

	return []byte(sb.String())
}
