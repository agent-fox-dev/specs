// Package validate provides cross-file integrity checks, ID format validation,
// and glossary cross-check helpers for the afspec library.
//
// Functions in this package operate on primitive Go types (strings, maps,
// slices) to avoid circular import dependencies with the root afspec package.
// The root package is responsible for extracting the relevant data from Spec
// structs and calling these helpers.
package validate

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// ─────────────────────────────────────────────────────────────────────────────
// ID format regexes (Appendix A of spec-format.md)
// ─────────────────────────────────────────────────────────────────────────────

var (
	// RequirementIDRe matches {spec_id}-REQ-{N}
	RequirementIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)$`)
	// CriterionIDRe matches {spec_id}-REQ-{N}.{C} (acceptance criteria)
	CriterionIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)\.(\d+)$`)
	// EdgeCaseIDRe matches {spec_id}-REQ-{N}.E{C} (edge cases)
	EdgeCaseIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)\.E(\d+)$`)
	// PropIDRe matches {spec_id}-PROP-{N}
	PropIDRe = regexp.MustCompile(`^(\w+)-PROP-(\d+)$`)
	// PathIDRe matches {spec_id}-PATH-{N}
	PathIDRe = regexp.MustCompile(`^(\w+)-PATH-(\d+)$`)
	// ErrIDRe matches {spec_id}-ERR-{N}
	ErrIDRe = regexp.MustCompile(`^(\w+)-ERR-(\d+)$`)
	// TestCaseIDRe matches TS-{spec_id}-{N}
	TestCaseIDRe = regexp.MustCompile(`^TS-(\w+)-(\d+)$`)
	// PropTestIDRe matches TS-{spec_id}-P{N}
	PropTestIDRe = regexp.MustCompile(`^TS-(\w+)-P(\d+)$`)
	// EdgeCaseTestIDRe matches TS-{spec_id}-E{N}
	EdgeCaseTestIDRe = regexp.MustCompile(`^TS-(\w+)-E(\d+)$`)
	// SmokeTestIDRe matches TS-{spec_id}-SMOKE-{N}
	SmokeTestIDRe = regexp.MustCompile(`^TS-(\w+)-SMOKE-(\d+)$`)
	// SubtaskIDRe matches {group}.{N}
	SubtaskIDRe = regexp.MustCompile(`^(\d+)\.(\d+)$`)
	// VerificationIDRe matches {group}.V
	VerificationIDRe = regexp.MustCompile(`^(\d+)\.V$`)
)

// backtickTermRe matches backtick-wrapped terms in a string.
var backtickTermRe = regexp.MustCompile("`([^`]+)`")

// ExtractBacktickTerms returns all terms wrapped in backticks within s.
func ExtractBacktickTerms(s string) []string {
	matches := backtickTermRe.FindAllStringSubmatch(s, -1)
	var terms []string
	for _, m := range matches {
		if len(m) > 1 {
			terms = append(terms, m[1])
		}
	}
	return terms
}

// CheckSequentiality returns a human-readable description of any gaps in the
// sorted list of positive integers. It returns nil if there are no gaps or if
// there are fewer than two numbers to compare. This is used to emit ID
// sequentiality warnings.
func CheckSequentiality(nums []int) []string {
	if len(nums) < 2 {
		return nil
	}
	sorted := make([]int, len(nums))
	copy(sorted, nums)
	sort.Ints(sorted)

	var gaps []string
	for i := 1; i < len(sorted); i++ {
		for g := sorted[i-1] + 1; g < sorted[i]; g++ {
			gaps = append(gaps, strconv.Itoa(g))
		}
	}
	return gaps
}

// ParseNumericComponents extracts and validates the numeric subgroup matches
// from a regex result slice (m[offset:]). Returns true if all components are
// positive integers, along with the parsed integers.
func ParseNumericComponents(m []string, offset int) (nums []int, valid bool) {
	valid = true
	for _, s := range m[offset:] {
		n, err := strconv.Atoi(s)
		if err != nil || n <= 0 {
			valid = false
		}
		nums = append(nums, n)
	}
	return nums, valid
}

// SpecIDFromRequirementID extracts the spec_id component from an ID matching
// RequirementIDRe, CriterionIDRe, etc. Returns "" if the ID doesn't match.
func SpecIDFromRequirementID(id string) string {
	patterns := []*regexp.Regexp{
		CriterionIDRe, EdgeCaseIDRe, RequirementIDRe,
		PropIDRe, PathIDRe, ErrIDRe,
	}
	for _, re := range patterns {
		if m := re.FindStringSubmatch(id); m != nil {
			return m[1]
		}
	}
	return ""
}

// SpecIDFromTestID extracts the spec_id component from a test ID matching
// TestCaseIDRe, PropTestIDRe, EdgeCaseTestIDRe, or SmokeTestIDRe.
func SpecIDFromTestID(id string) string {
	patterns := []*regexp.Regexp{
		SmokeTestIDRe, EdgeCaseTestIDRe, PropTestIDRe, TestCaseIDRe,
	}
	for _, re := range patterns {
		if m := re.FindStringSubmatch(id); m != nil {
			return m[1]
		}
	}
	return ""
}

// JoinGaps formats a list of gap positions as a comma-separated string.
func JoinGaps(gaps []string) string {
	return strings.Join(gaps, ", ")
}
