package prd

import (
	"fmt"
	"strings"
)

// ExtractIntent extracts the body of the "## Intent" section from a PRD body.
// The section body is the text between "## Intent" and the next "##" heading
// or the end of the document.
// Returns an error if the section is missing.
func ExtractIntent(body string) (string, error) {
	inIntent := false
	var intentLines []string

	for rawLine := range strings.SplitSeq(body, "\n") {
		line := strings.TrimRight(rawLine, "\r")

		if line == "## Intent" || strings.HasPrefix(line, "## Intent ") {
			inIntent = true
			continue
		}

		if inIntent {
			// Stop at the next level-2 (or higher level) heading.
			if strings.HasPrefix(line, "## ") || strings.HasPrefix(line, "# ") {
				break
			}
			intentLines = append(intentLines, rawLine)
		}
	}

	if !inIntent {
		return "", fmt.Errorf("'## Intent' section not found")
	}

	return strings.Join(intentLines, "\n"), nil
}

// HasIntentSection reports whether the body contains a "## Intent" heading.
func HasIntentSection(body string) bool {
	for line := range strings.SplitSeq(body, "\n") {
		trimmed := strings.TrimRight(line, "\r")
		if trimmed == "## Intent" || strings.HasPrefix(trimmed, "## Intent ") {
			return true
		}
	}
	return false
}
