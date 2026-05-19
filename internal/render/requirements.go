package render

import (
	"fmt"
	"sort"
	"strings"
)

// RequirementsDoc contains the data needed to render requirements.json as markdown.
// We use plain types here to avoid importing the root afspec package.
type RequirementsDoc struct {
	SpecID                string
	SpecName              string
	Introduction          string
	Glossary              map[string]string
	Requirements          []RequirementItem
	CorrectnessProperties []CorrectnessPropertyItem
	ExecutionPaths        []ExecutionPathItem
	ErrorHandling         []ErrorHandlingItem
}

// RequirementItem mirrors afspec.Requirement.
type RequirementItem struct {
	ID                 string
	Title              string
	UserStory          UserStoryItem
	AcceptanceCriteria []EARSCriterion
	EdgeCases          []EARSCriterion
}

// UserStoryItem mirrors afspec.UserStory.
type UserStoryItem struct {
	Role    string
	Goal    string
	Benefit string
}

// CorrectnessPropertyItem mirrors afspec.CorrectnessProperty.
type CorrectnessPropertyItem struct {
	ID        string
	Title     string
	ForAny    string
	Invariant string
	Validates []string
}

// ExecutionPathItem mirrors afspec.ExecutionPath.
type ExecutionPathItem struct {
	ID    string
	Title string
	Steps []ExecutionPathStepItem
}

// ExecutionPathStepItem mirrors afspec.ExecutionPathStep.
type ExecutionPathStepItem struct {
	Actor  string
	Action string
}

// ErrorHandlingItem mirrors afspec.ErrorHandlingEntry.
type ErrorHandlingItem struct {
	ID            string
	Condition     string
	Behavior      string
	RequirementID string
}

// RenderRequirements renders a RequirementsDoc to markdown bytes.
func RenderRequirements(doc *RequirementsDoc) ([]byte, error) {
	var sb strings.Builder

	fmt.Fprintf(&sb, "# Requirements\n\n")

	if doc.Introduction != "" {
		fmt.Fprintf(&sb, "%s\n\n", doc.Introduction)
	}

	// Glossary
	if len(doc.Glossary) > 0 {
		fmt.Fprintf(&sb, "## Glossary\n\n")
		keys := make([]string, 0, len(doc.Glossary))
		for k := range doc.Glossary {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		fmt.Fprintf(&sb, "| Term | Definition |\n")
		fmt.Fprintf(&sb, "|------|------------|\n")
		for _, k := range keys {
			fmt.Fprintf(&sb, "| %s | %s |\n", k, doc.Glossary[k])
		}
		fmt.Fprintf(&sb, "\n")
	}

	// Requirements
	if len(doc.Requirements) > 0 {
		fmt.Fprintf(&sb, "## Requirements\n\n")
		for _, req := range doc.Requirements {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", req.ID, req.Title)

			// User story
			fmt.Fprintf(&sb, "**As a** %s, **I want** %s, **so that** %s.\n\n",
				req.UserStory.Role, req.UserStory.Goal, req.UserStory.Benefit)

			// Acceptance criteria
			if len(req.AcceptanceCriteria) > 0 {
				fmt.Fprintf(&sb, "#### Acceptance Criteria\n\n")
				for _, ac := range req.AcceptanceCriteria {
					sentence, err := RenderEARS(&ac)
					if err != nil {
						return nil, fmt.Errorf("rendering criterion %s: %w", ac.EarsPattern, err)
					}
					fmt.Fprintf(&sb, "[%s] %s\n\n", ac.EarsPattern, sentence)
				}
			}

			// Edge cases
			if len(req.EdgeCases) > 0 {
				fmt.Fprintf(&sb, "#### Edge Cases\n\n")
				for _, ec := range req.EdgeCases {
					sentence, err := RenderEARS(&ec)
					if err != nil {
						return nil, fmt.Errorf("rendering edge case %s: %w", ec.EarsPattern, err)
					}
					fmt.Fprintf(&sb, "[%s] %s\n\n", ec.EarsPattern, sentence)
				}
			}
		}
	}

	// Correctness Properties
	if len(doc.CorrectnessProperties) > 0 {
		fmt.Fprintf(&sb, "## Correctness Properties\n\n")
		for _, prop := range doc.CorrectnessProperties {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", prop.ID, prop.Title)
			fmt.Fprintf(&sb, "**For any:** %s\n\n", prop.ForAny)
			fmt.Fprintf(&sb, "**Invariant:** %s\n\n", prop.Invariant)
			if len(prop.Validates) > 0 {
				fmt.Fprintf(&sb, "**Validates:** %s\n\n", strings.Join(prop.Validates, ", "))
			}
		}
	}

	// Execution Paths
	if len(doc.ExecutionPaths) > 0 {
		fmt.Fprintf(&sb, "## Execution Paths\n\n")
		for _, path := range doc.ExecutionPaths {
			fmt.Fprintf(&sb, "### [%s] %s\n\n", path.ID, path.Title)
			for i, step := range path.Steps {
				fmt.Fprintf(&sb, "%d. **%s**: %s\n", i+1, step.Actor, step.Action)
			}
			fmt.Fprintf(&sb, "\n")
		}
	}

	// Error Handling
	if len(doc.ErrorHandling) > 0 {
		fmt.Fprintf(&sb, "## Error Handling\n\n")
		for _, eh := range doc.ErrorHandling {
			fmt.Fprintf(&sb, "### [%s]\n\n", eh.ID)
			fmt.Fprintf(&sb, "**Condition:** %s\n\n", eh.Condition)
			fmt.Fprintf(&sb, "**Behavior:** %s\n\n", eh.Behavior)
			fmt.Fprintf(&sb, "**Requirement:** %s\n\n", eh.RequirementID)
		}
	}

	return []byte(sb.String()), nil
}
