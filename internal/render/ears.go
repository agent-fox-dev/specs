package render

import "fmt"

// placeholder is used when a required EARS field is empty.
const placeholder = "<missing>"

// field returns the value if non-empty, or the placeholder string.
func field(s string) string {
	if s == "" {
		return placeholder
	}
	return s
}

// EARSCriterion is an interface over the Criterion fields needed for rendering.
// We use a plain struct to avoid importing the root afspec package.
type EARSCriterion struct {
	EarsPattern    string
	System         string
	Action         string
	ReturnContract *string
	Trigger        string
	Condition      string
	ErrorCondition string
	State          string
	Feature        string
}

// RenderEARS renders a single EARS criterion to its sentence form.
// Uses the six templates from spec-format.md §5.2.1.
// Empty required fields render as "<missing>".
// A null or empty return_contract omits the "AND return" clause.
func RenderEARS(c *EARSCriterion) (string, error) {
	var sentence string

	switch c.EarsPattern {
	case "ubiquitous":
		sentence = fmt.Sprintf("THE %s SHALL %s", field(c.System), field(c.Action))
	case "event_driven":
		sentence = fmt.Sprintf("WHEN %s, THE %s SHALL %s", field(c.Trigger), field(c.System), field(c.Action))
	case "complex_event":
		sentence = fmt.Sprintf("WHEN %s AND %s, THE %s SHALL %s", field(c.Trigger), field(c.Condition), field(c.System), field(c.Action))
	case "state_driven":
		sentence = fmt.Sprintf("WHILE %s, THE %s SHALL %s", field(c.State), field(c.System), field(c.Action))
	case "unwanted":
		sentence = fmt.Sprintf("IF %s, THEN THE %s SHALL %s", field(c.ErrorCondition), field(c.System), field(c.Action))
	case "optional":
		sentence = fmt.Sprintf("WHERE %s, THE %s SHALL %s", field(c.Feature), field(c.System), field(c.Action))
	default:
		return "", fmt.Errorf("unknown EARS pattern: %q", c.EarsPattern)
	}

	// Append return contract clause if non-null and non-empty.
	if c.ReturnContract != nil && *c.ReturnContract != "" {
		sentence += fmt.Sprintf(" AND return %s", *c.ReturnContract)
	}

	return sentence, nil
}
