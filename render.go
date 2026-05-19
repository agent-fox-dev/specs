package afspec

import "errors"

// RenderEARS renders a single EARS criterion to its sentence form.
// Uses the six templates from spec-format.md §5.2.1.
// Empty required fields render as "<missing>".
// A null or empty return_contract omits the "AND return" clause.
func RenderEARS(c *Criterion) (string, error) {
	return "", errors.New("not implemented")
}

// RenderRequirements renders requirements.json to markdown.
func RenderRequirements(req *Requirements) ([]byte, error) {
	return nil, errors.New("not implemented")
}

// RenderTestSpec renders test_spec.json to markdown.
func RenderTestSpec(ts *TestSpecDoc) ([]byte, error) {
	return nil, errors.New("not implemented")
}

// RenderTasks renders tasks.json to markdown.
func RenderTasks(tasks *Tasks) ([]byte, error) {
	return nil, errors.New("not implemented")
}

// RenderCombined produces a single document: PRD verbatim + rendered JSON artifacts.
// Sections appear in order: PRD body, requirements, test_spec, tasks.
func RenderCombined(spec *Spec) ([]byte, error) {
	return nil, errors.New("not implemented")
}
