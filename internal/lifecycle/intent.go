// Package lifecycle implements lifecycle state machine logic for specs.
package lifecycle

import (
	"crypto/sha256"
	"fmt"
	"regexp"
	"strings"
)

// NormalizeIntent applies the five-step normalization pipeline to the raw
// ## Intent section body before hashing:
//  1. Normalize line endings to LF
//  2. Collapse multiple consecutive blank lines into one blank line
//  3. Lower-case entire text
//  4. Trim leading and trailing whitespace
func NormalizeIntent(body string) string {
	// Step 1: normalize line endings to LF
	s := strings.ReplaceAll(body, "\r\n", "\n")
	s = strings.ReplaceAll(s, "\r", "\n")

	// Step 2: collapse multiple consecutive blank lines into one
	s = collapseBlankLines(s)

	// Step 3: lower-case
	s = strings.ToLower(s)

	// Step 4: trim leading and trailing whitespace
	s = strings.TrimSpace(s)

	return s
}

// multiBlankLine matches two or more consecutive newlines (blank lines).
var multiBlankLine = regexp.MustCompile(`\n{3,}`)

// collapseBlankLines replaces sequences of 3 or more newlines with exactly two
// (one blank line between paragraphs).
func collapseBlankLines(s string) string {
	return multiBlankLine.ReplaceAllString(s, "\n\n")
}

// ComputeIntentHash computes the SHA-256 hash of the normalized Intent body.
// The input should be the raw text of the ## Intent section (not the full PRD
// body). Returns a 64-character lowercase hex string.
func ComputeIntentHash(body string) string {
	normalized := NormalizeIntent(body)
	sum := sha256.Sum256([]byte(normalized))
	return fmt.Sprintf("%x", sum)
}
