package render

import (
	"fmt"
	"strings"
)

// TasksDoc contains the data needed to render tasks.json as markdown.
type TasksDoc struct {
	SpecID       string
	SpecName     string
	TestCommands TestCommandsItem
	Dependencies []TaskDependencyItem
	TaskGroups   []TaskGroupItem
	Traceability []TraceabilityItem
}

// TestCommandsItem mirrors afspec.TestCommands.
type TestCommandsItem struct {
	SpecTests string
	AllTests  string
	Linter    string
}

// TaskDependencyItem mirrors afspec.TaskDependency.
type TaskDependencyItem struct {
	DependsOnSpec string
	FromGroup     int
	ToGroup       int
	Relationship  string
	Sentinel      bool
}

// TaskGroupItem mirrors afspec.TaskGroup.
type TaskGroupItem struct {
	ID           int
	Kind         string
	Title        string
	Subtasks     []SubtaskItem
	Verification VerificationSubtaskItem
}

// SubtaskItem mirrors afspec.Subtask.
type SubtaskItem struct {
	ID              string
	Title           string
	Details         []string
	TestSpecRefs    []string
	RequirementRefs []string
	State           string
	Optional        bool
}

// VerificationSubtaskItem mirrors afspec.VerificationSubtask.
type VerificationSubtaskItem struct {
	ID     string
	Checks []string
}

// TraceabilityItem mirrors afspec.TraceabilityEntry.
type TraceabilityItem struct {
	RequirementID string
	TestSpecID    string
	TaskID        string
	TestPath      *string
}

// RenderTasks renders a TasksDoc to markdown bytes.
func RenderTasks(doc *TasksDoc) ([]byte, error) {
	var sb strings.Builder

	fmt.Fprintf(&sb, "# Implementation Plan\n\n")

	// Test Commands
	fmt.Fprintf(&sb, "## Test Commands\n\n")
	fmt.Fprintf(&sb, "- **Spec tests:** `%s`\n", doc.TestCommands.SpecTests)
	fmt.Fprintf(&sb, "- **All tests:** `%s`\n", doc.TestCommands.AllTests)
	fmt.Fprintf(&sb, "- **Linter:** `%s`\n\n", doc.TestCommands.Linter)

	// Dependencies
	if len(doc.Dependencies) > 0 {
		fmt.Fprintf(&sb, "## Dependencies\n\n")
		for _, dep := range doc.Dependencies {
			sentinel := ""
			if dep.Sentinel {
				sentinel = " (sentinel)"
			}
			fmt.Fprintf(&sb, "- Spec `%s` group %d → this group %d [%s]%s\n",
				dep.DependsOnSpec, dep.FromGroup, dep.ToGroup, dep.Relationship, sentinel)
		}
		fmt.Fprintf(&sb, "\n")
	}

	// Task Groups
	if len(doc.TaskGroups) > 0 {
		fmt.Fprintf(&sb, "## Tasks\n\n")
		for _, tg := range doc.TaskGroups {
			fmt.Fprintf(&sb, "### Group %d: %s (%s)\n\n", tg.ID, tg.Title, tg.Kind)

			for _, st := range tg.Subtasks {
				var checkbox string
				switch st.State {
				case "done":
					checkbox = "[x]"
				case "in_progress":
					checkbox = "[-]"
				case "dropped":
					checkbox = "[~]"
				default:
					checkbox = "[ ]"
				}
				optional := ""
				if st.Optional {
					optional = " (optional)"
				}
				fmt.Fprintf(&sb, "- %s **%s** %s%s\n", checkbox, st.ID, st.Title, optional)
				for _, d := range st.Details {
					fmt.Fprintf(&sb, "  - %s\n", d)
				}
				if len(st.TestSpecRefs) > 0 {
					fmt.Fprintf(&sb, "  - _Test Spec: %s_\n", strings.Join(st.TestSpecRefs, ", "))
				}
			}

			// Verification
			fmt.Fprintf(&sb, "- **%s** Verification\n", tg.Verification.ID)
			for _, check := range tg.Verification.Checks {
				fmt.Fprintf(&sb, "  - %s\n", check)
			}
			fmt.Fprintf(&sb, "\n")
		}
	}

	// Traceability
	if len(doc.Traceability) > 0 {
		fmt.Fprintf(&sb, "## Traceability\n\n")
		fmt.Fprintf(&sb, "| Requirement | Test Spec | Task | Test Path |\n")
		fmt.Fprintf(&sb, "|-------------|-----------|------|-----------|\n")
		for _, tr := range doc.Traceability {
			testPath := "—"
			if tr.TestPath != nil {
				testPath = *tr.TestPath
			}
			fmt.Fprintf(&sb, "| %s | %s | %s | %s |\n",
				tr.RequirementID, tr.TestSpecID, tr.TaskID, testPath)
		}
		fmt.Fprintf(&sb, "\n")
	}

	return []byte(sb.String()), nil
}
