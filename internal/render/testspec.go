package render

import (
	"fmt"
	"strings"
)

// TestSpecDocRender contains the data needed to render test_spec.json as markdown.
type TestSpecDocRender struct {
	SpecID    string
	SpecName  string
	TestCases []TestCaseItem
	PropertyTests []PropertyTestItem
	EdgeCaseTests []EdgeCaseTestItem
	SmokeTests    []SmokeTestItem
	Coverage      CoverageItem
}

// TestCaseItem mirrors afspec.TestCase.
type TestCaseItem struct {
	ID                  string
	RequirementID       string
	Kind                string
	Description         string
	Preconditions       []string
	AssertionPseudocode string
}

// PropertyTestItem mirrors afspec.PropertyTest.
type PropertyTestItem struct {
	ID             string
	PropertyID     string
	Validates      []string
	Description    string
	ForAnyStrategy string
	InvariantCheck string
}

// EdgeCaseTestItem mirrors afspec.EdgeCaseTest.
type EdgeCaseTestItem struct {
	ID                  string
	RequirementID       string
	Kind                string
	Description         string
	Preconditions       []string
	AssertionPseudocode string
}

// SmokeTestItem mirrors afspec.SmokeTest.
type SmokeTestItem struct {
	ID              string
	ExecutionPathID string
	Description     string
	Trigger         string
	RealComponents  []string
	Mockable        []string
	ExpectedEffects []string
}

// CoverageItem mirrors afspec.Coverage.
type CoverageItem struct {
	RequirementsCovered []string
	PropertiesCovered   []string
	PathsCovered        []string
	Gaps                []string
}

// RenderTestSpec renders a TestSpecDocRender to markdown bytes.
func RenderTestSpec(doc *TestSpecDocRender) ([]byte, error) {
	var sb strings.Builder

	fmt.Fprintf(&sb, "# Test Specification\n\n")

	// Test Cases
	if len(doc.TestCases) > 0 {
		fmt.Fprintf(&sb, "## Test Cases\n\n")
		for _, tc := range doc.TestCases {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", tc.ID, tc.Description)
			fmt.Fprintf(&sb, "**Kind:** %s | **Requirement:** %s\n\n", tc.Kind, tc.RequirementID)
			if len(tc.Preconditions) > 0 {
				fmt.Fprintf(&sb, "**Preconditions:**\n\n")
				for _, p := range tc.Preconditions {
					fmt.Fprintf(&sb, "- %s\n", p)
				}
				fmt.Fprintf(&sb, "\n")
			}
			if tc.AssertionPseudocode != "" {
				fmt.Fprintf(&sb, "**Assertion:**\n\n```\n%s\n```\n\n", tc.AssertionPseudocode)
			}
		}
	}

	// Property Tests
	if len(doc.PropertyTests) > 0 {
		fmt.Fprintf(&sb, "## Property Tests\n\n")
		for _, pt := range doc.PropertyTests {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", pt.ID, pt.Description)
			fmt.Fprintf(&sb, "**Property:** %s\n\n", pt.PropertyID)
			fmt.Fprintf(&sb, "**For any:** %s\n\n", pt.ForAnyStrategy)
			fmt.Fprintf(&sb, "**Invariant:** %s\n\n", pt.InvariantCheck)
			if len(pt.Validates) > 0 {
				fmt.Fprintf(&sb, "**Validates:** %s\n\n", strings.Join(pt.Validates, ", "))
			}
		}
	}

	// Edge Case Tests
	if len(doc.EdgeCaseTests) > 0 {
		fmt.Fprintf(&sb, "## Edge Case Tests\n\n")
		for _, ec := range doc.EdgeCaseTests {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", ec.ID, ec.Description)
			fmt.Fprintf(&sb, "**Kind:** %s | **Requirement:** %s\n\n", ec.Kind, ec.RequirementID)
			if len(ec.Preconditions) > 0 {
				fmt.Fprintf(&sb, "**Preconditions:**\n\n")
				for _, p := range ec.Preconditions {
					fmt.Fprintf(&sb, "- %s\n", p)
				}
				fmt.Fprintf(&sb, "\n")
			}
			if ec.AssertionPseudocode != "" {
				fmt.Fprintf(&sb, "**Assertion:**\n\n```\n%s\n```\n\n", ec.AssertionPseudocode)
			}
		}
	}

	// Smoke Tests
	if len(doc.SmokeTests) > 0 {
		fmt.Fprintf(&sb, "## Smoke Tests\n\n")
		for _, st := range doc.SmokeTests {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", st.ID, st.Description)
			fmt.Fprintf(&sb, "**Execution Path:** %s\n\n", st.ExecutionPathID)
			fmt.Fprintf(&sb, "**Trigger:** %s\n\n", st.Trigger)
			if len(st.RealComponents) > 0 {
				fmt.Fprintf(&sb, "**Real Components:** %s\n\n", strings.Join(st.RealComponents, ", "))
			}
			if len(st.ExpectedEffects) > 0 {
				fmt.Fprintf(&sb, "**Expected Effects:**\n\n")
				for _, e := range st.ExpectedEffects {
					fmt.Fprintf(&sb, "- %s\n", e)
				}
				fmt.Fprintf(&sb, "\n")
			}
		}
	}

	// Coverage
	fmt.Fprintf(&sb, "## Coverage\n\n")
	if len(doc.Coverage.RequirementsCovered) > 0 {
		fmt.Fprintf(&sb, "**Requirements Covered:** %s\n\n", strings.Join(doc.Coverage.RequirementsCovered, ", "))
	}
	if len(doc.Coverage.PropertiesCovered) > 0 {
		fmt.Fprintf(&sb, "**Properties Covered:** %s\n\n", strings.Join(doc.Coverage.PropertiesCovered, ", "))
	}
	if len(doc.Coverage.PathsCovered) > 0 {
		fmt.Fprintf(&sb, "**Paths Covered:** %s\n\n", strings.Join(doc.Coverage.PathsCovered, ", "))
	}
	if len(doc.Coverage.Gaps) > 0 {
		fmt.Fprintf(&sb, "**Gaps:** %s\n\n", strings.Join(doc.Coverage.Gaps, ", "))
	}

	return []byte(sb.String()), nil
}
