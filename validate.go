package afspec

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/agent-fox/afspec/internal/schema"
)

// GetEmbeddedSchemas returns a map of schema file name → raw JSON bytes for
// all four bundled JSON Schema files.
func GetEmbeddedSchemas() map[string][]byte {
	return schema.Schemas()
}

// Validate runs schema validation, cross-file integrity checks, and ID
// format validation. Returns all errors found (empty slice means valid).
func Validate(spec *Spec) ([]ValidationError, error) {
	var all []ValidationError

	schemaErrs, err := ValidateSchema(spec)
	if err != nil {
		return nil, err
	}
	all = append(all, schemaErrs...)

	xfileErrs, err := ValidateCrossFile(spec)
	if err != nil {
		return nil, err
	}
	all = append(all, xfileErrs...)

	idErrs, err := ValidateIDs(spec)
	if err != nil {
		return nil, err
	}
	all = append(all, idErrs...)

	return all, nil
}

// ValidateSchema runs per-file JSON Schema validation on all four spec
// artifacts. Returns all errors found (empty slice means schema-valid).
func ValidateSchema(spec *Spec) ([]ValidationError, error) {
	var errs []ValidationError

	if spec.PRD != nil {
		errs = append(errs, validateFrontmatter(&spec.PRD.Frontmatter)...)
	}
	if spec.Requirements != nil {
		errs = append(errs, validateRequirementsSchema(spec.Requirements)...)
	}
	if spec.TestSpec != nil {
		errs = append(errs, validateTestSpecSchema(spec.TestSpec)...)
	}
	if spec.Tasks != nil {
		errs = append(errs, validateTasksSchema(spec.Tasks)...)
	}

	return errs, nil
}

// ValidateCrossFile runs only cross-file integrity checks (seven rules from
// spec-format.md §9.2). Returns all violations found.
func ValidateCrossFile(spec *Spec) ([]ValidationError, error) {
	if spec == nil {
		return nil, nil
	}
	var errs []ValidationError
	errs = append(errs, crossFileRule1(spec)...)
	errs = append(errs, crossFileRule2(spec)...)
	errs = append(errs, crossFileRule3(spec)...)
	errs = append(errs, crossFileRule4(spec)...)
	errs = append(errs, crossFileRule5(spec)...)
	errs = append(errs, crossFileRule6(spec)...)
	errs = append(errs, crossFileRule7(spec)...)
	return errs, nil
}

// ValidateIDs validates all ID fields in the spec against the format patterns
// defined in spec-format.md Appendix A.
func ValidateIDs(spec *Spec) ([]ValidationError, error) {
	if spec == nil {
		return nil, nil
	}

	var errs []ValidationError

	specID := ""
	if spec.PRD != nil {
		specID = spec.PRD.Frontmatter.SpecID
	} else if spec.Requirements != nil {
		specID = spec.Requirements.SpecID
	}

	if spec.Requirements != nil {
		errs = append(errs, validateRequirementIDs(spec.Requirements, specID)...)
	}
	if spec.TestSpec != nil {
		errs = append(errs, validateTestSpecIDs(spec.TestSpec, specID)...)
	}
	if spec.Tasks != nil {
		errs = append(errs, validateTasksIDs(spec.Tasks, specID)...)
	}

	return errs, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Schema validation helpers
// ─────────────────────────────────────────────────────────────────────────────

var validStatuses = map[Status]bool{
	StatusDraft:      true,
	StatusActive:     true,
	StatusSealed:     true,
	StatusSuperseded: true,
	StatusArchived:   true,
}

func validateFrontmatter(fm *Frontmatter) []ValidationError {
	var errs []ValidationError
	add := func(path, msg string) {
		errs = append(errs, ValidationError{
			File:     "prd.md",
			Path:     path,
			Rule:     "schema",
			Message:  msg,
			Severity: SeverityError,
		})
	}
	if fm.SpecID == "" {
		add("/spec_id", "spec_id is required and must be non-empty")
	}
	if fm.SpecName == "" {
		add("/spec_name", "spec_name is required and must be non-empty")
	}
	if fm.Title == "" {
		add("/title", "title is required and must be non-empty")
	}
	if !validStatuses[fm.Status] {
		add("/status", fmt.Sprintf(
			"status %q is not valid; must be one of: draft, active, sealed, superseded, archived",
			fm.Status,
		))
	}
	if fm.SchemaVersion < 1 {
		add("/schema_version", fmt.Sprintf("schema_version must be >= 1, got %d", fm.SchemaVersion))
	}
	return errs
}

func validateRequirementsSchema(req *Requirements) []ValidationError {
	var errs []ValidationError
	add := func(path, msg string) {
		errs = append(errs, ValidationError{
			File:     "requirements.json",
			Path:     path,
			Rule:     "schema",
			Message:  msg,
			Severity: SeverityError,
		})
	}
	if req.SpecID == "" {
		add("/spec_id", "spec_id is required and must be non-empty")
	}
	if req.SpecName == "" {
		add("/spec_name", "spec_name is required and must be non-empty")
	}
	if req.SchemaVersion < 1 {
		add("/schema_version", fmt.Sprintf("schema_version must be >= 1, got %d", req.SchemaVersion))
	}
	// Validate EARS criteria in all requirements
	for ri, r := range req.Requirements {
		for ci, c := range r.AcceptanceCriteria {
			path := fmt.Sprintf("/requirements/%d/acceptance_criteria/%d", ri, ci)
			errs = append(errs, validateEARSPattern(c, "requirements.json", path)...)
		}
		for ci, c := range r.EdgeCases {
			path := fmt.Sprintf("/requirements/%d/edge_cases/%d", ri, ci)
			errs = append(errs, validateEARSPattern(c, "requirements.json", path)...)
		}
	}
	return errs
}

// validateEARSPattern checks that the criterion only has fields valid for its
// declared ears_pattern. It also catches invalid (unknown) pattern values.
func validateEARSPattern(c Criterion, file, path string) []ValidationError {
	var errs []ValidationError
	add := func(msg string) {
		errs = append(errs, ValidationError{
			File:     file,
			Path:     path,
			Rule:     "schema",
			Message:  msg,
			Severity: SeverityError,
		})
	}

	switch c.EarsPattern {
	case "ubiquitous":
		if c.Trigger != "" {
			add(fmt.Sprintf("criterion %q (ubiquitous): trigger field is not valid for ubiquitous pattern", c.ID))
		}
		if c.Condition != "" {
			add(fmt.Sprintf("criterion %q (ubiquitous): condition field is not valid for ubiquitous pattern", c.ID))
		}
		if c.ErrorCondition != "" {
			add(fmt.Sprintf("criterion %q (ubiquitous): error_condition field is not valid for ubiquitous pattern", c.ID))
		}
		if c.State != "" {
			add(fmt.Sprintf("criterion %q (ubiquitous): state field is not valid for ubiquitous pattern", c.ID))
		}
		if c.Feature != "" {
			add(fmt.Sprintf("criterion %q (ubiquitous): feature field is not valid for ubiquitous pattern", c.ID))
		}
	case "event_driven":
		if c.Trigger == "" {
			add(fmt.Sprintf("criterion %q (event_driven): trigger field is required", c.ID))
		}
		if c.Condition != "" {
			add(fmt.Sprintf("criterion %q (event_driven): condition field is not valid for event_driven pattern", c.ID))
		}
		if c.ErrorCondition != "" {
			add(fmt.Sprintf("criterion %q (event_driven): error_condition field is not valid for event_driven pattern", c.ID))
		}
		if c.State != "" {
			add(fmt.Sprintf("criterion %q (event_driven): state field is not valid for event_driven pattern", c.ID))
		}
		if c.Feature != "" {
			add(fmt.Sprintf("criterion %q (event_driven): feature field is not valid for event_driven pattern", c.ID))
		}
	case "complex_event":
		if c.Trigger == "" {
			add(fmt.Sprintf("criterion %q (complex_event): trigger field is required", c.ID))
		}
		if c.Condition == "" {
			add(fmt.Sprintf("criterion %q (complex_event): condition field is required", c.ID))
		}
		if c.ErrorCondition != "" {
			add(fmt.Sprintf("criterion %q (complex_event): error_condition field is not valid for complex_event pattern", c.ID))
		}
		if c.State != "" {
			add(fmt.Sprintf("criterion %q (complex_event): state field is not valid for complex_event pattern", c.ID))
		}
		if c.Feature != "" {
			add(fmt.Sprintf("criterion %q (complex_event): feature field is not valid for complex_event pattern", c.ID))
		}
	case "state_driven":
		if c.State == "" {
			add(fmt.Sprintf("criterion %q (state_driven): state field is required", c.ID))
		}
		if c.Trigger != "" {
			add(fmt.Sprintf("criterion %q (state_driven): trigger field is not valid for state_driven pattern", c.ID))
		}
		if c.Condition != "" {
			add(fmt.Sprintf("criterion %q (state_driven): condition field is not valid for state_driven pattern", c.ID))
		}
		if c.ErrorCondition != "" {
			add(fmt.Sprintf("criterion %q (state_driven): error_condition field is not valid for state_driven pattern", c.ID))
		}
		if c.Feature != "" {
			add(fmt.Sprintf("criterion %q (state_driven): feature field is not valid for state_driven pattern", c.ID))
		}
	case "unwanted":
		if c.ErrorCondition == "" {
			add(fmt.Sprintf("criterion %q (unwanted): error_condition field is required", c.ID))
		}
		if c.Trigger != "" {
			add(fmt.Sprintf("criterion %q (unwanted): trigger field is not valid for unwanted pattern", c.ID))
		}
		if c.Condition != "" {
			add(fmt.Sprintf("criterion %q (unwanted): condition field is not valid for unwanted pattern", c.ID))
		}
		if c.State != "" {
			add(fmt.Sprintf("criterion %q (unwanted): state field is not valid for unwanted pattern", c.ID))
		}
		if c.Feature != "" {
			add(fmt.Sprintf("criterion %q (unwanted): feature field is not valid for unwanted pattern", c.ID))
		}
	case "optional":
		if c.Feature == "" {
			add(fmt.Sprintf("criterion %q (optional): feature field is required", c.ID))
		}
		if c.Trigger != "" {
			add(fmt.Sprintf("criterion %q (optional): trigger field is not valid for optional pattern", c.ID))
		}
		if c.Condition != "" {
			add(fmt.Sprintf("criterion %q (optional): condition field is not valid for optional pattern", c.ID))
		}
		if c.ErrorCondition != "" {
			add(fmt.Sprintf("criterion %q (optional): error_condition field is not valid for optional pattern", c.ID))
		}
		if c.State != "" {
			add(fmt.Sprintf("criterion %q (optional): state field is not valid for optional pattern", c.ID))
		}
	default:
		add(fmt.Sprintf("criterion %q: ears_pattern %q is not a valid EARS pattern", c.ID, c.EarsPattern))
	}
	return errs
}

func validateTestSpecSchema(ts *TestSpecDoc) []ValidationError {
	var errs []ValidationError
	add := func(path, msg string) {
		errs = append(errs, ValidationError{
			File:     "test_spec.json",
			Path:     path,
			Rule:     "schema",
			Message:  msg,
			Severity: SeverityError,
		})
	}
	if ts.SpecID == "" {
		add("/spec_id", "spec_id is required and must be non-empty")
	}
	if ts.SpecName == "" {
		add("/spec_name", "spec_name is required and must be non-empty")
	}
	if ts.SchemaVersion < 1 {
		add("/schema_version", fmt.Sprintf("schema_version must be >= 1, got %d", ts.SchemaVersion))
	}
	for i, tc := range ts.TestCases {
		if tc.Kind != "unit" && tc.Kind != "integration" {
			add(fmt.Sprintf("/test_cases/%d/kind", i),
				fmt.Sprintf("test case kind %q must be 'unit' or 'integration'", tc.Kind))
		}
	}
	for i, ec := range ts.EdgeCaseTests {
		if ec.Kind != "unit" && ec.Kind != "integration" {
			add(fmt.Sprintf("/edge_case_tests/%d/kind", i),
				fmt.Sprintf("edge case test kind %q must be 'unit' or 'integration'", ec.Kind))
		}
	}
	return errs
}

func validateTasksSchema(tasks *Tasks) []ValidationError {
	var errs []ValidationError
	add := func(path, msg string) {
		errs = append(errs, ValidationError{
			File:     "tasks.json",
			Path:     path,
			Rule:     "schema",
			Message:  msg,
			Severity: SeverityError,
		})
	}
	if tasks.SpecID == "" {
		add("/spec_id", "spec_id is required and must be non-empty")
	}
	if tasks.SpecName == "" {
		add("/spec_name", "spec_name is required and must be non-empty")
	}
	if tasks.SchemaVersion < 1 {
		add("/schema_version", fmt.Sprintf("schema_version must be >= 1, got %d", tasks.SchemaVersion))
	}
	validGroupKinds := map[string]bool{
		"tests": true, "standard": true, "checkpoint": true, "wiring_verification": true,
	}
	validSubtaskStates := map[SubtaskState]bool{
		StatePending: true, StateQueued: true, StateInProgress: true,
		StateDone: true, StatePendingReevaluation: true, StateDropped: true,
	}
	for i, g := range tasks.TaskGroups {
		if !validGroupKinds[g.Kind] {
			add(fmt.Sprintf("/task_groups/%d/kind", i),
				fmt.Sprintf("task group kind %q is not valid; must be tests|standard|checkpoint|wiring_verification", g.Kind))
		}
		for j, s := range g.Subtasks {
			if !validSubtaskStates[s.State] {
				add(fmt.Sprintf("/task_groups/%d/subtasks/%d/state", i, j),
					fmt.Sprintf("subtask state %q is not valid", s.State))
			}
		}
	}
	return errs
}

// ─────────────────────────────────────────────────────────────────────────────
// Cross-file integrity rules
// ─────────────────────────────────────────────────────────────────────────────

// buildCriterionIDSet collects all acceptance criterion and edge case IDs
// from requirements.json into a set.
func buildCriterionIDSet(req *Requirements) map[string]bool {
	ids := make(map[string]bool)
	if req == nil {
		return ids
	}
	for _, r := range req.Requirements {
		for _, ac := range r.AcceptanceCriteria {
			ids[ac.ID] = true
		}
		for _, ec := range r.EdgeCases {
			ids[ec.ID] = true
		}
	}
	return ids
}

// buildTestSpecIDSet collects all test IDs from test_spec.json into a set.
func buildTestSpecIDSet(ts *TestSpecDoc) map[string]bool {
	ids := make(map[string]bool)
	if ts == nil {
		return ids
	}
	for _, tc := range ts.TestCases {
		ids[tc.ID] = true
	}
	for _, pt := range ts.PropertyTests {
		ids[pt.ID] = true
	}
	for _, ec := range ts.EdgeCaseTests {
		ids[ec.ID] = true
	}
	for _, st := range ts.SmokeTests {
		ids[st.ID] = true
	}
	return ids
}

// Rule 1: every requirement_id referenced in test_spec, tasks traceability,
// and requirements error_handling resolves to a criterion/edge-case ID.
func crossFileRule1(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Requirements == nil {
		return errs
	}
	criterionIDs := buildCriterionIDSet(spec.Requirements)

	check := func(file, path, rid string) {
		if rid != "" && !criterionIDs[rid] {
			errs = append(errs, ValidationError{
				File:     file,
				Path:     path,
				Rule:     "integrity-1",
				Message:  fmt.Sprintf("requirement_id %q not found in requirements.json", rid),
				Severity: SeverityError,
			})
		}
	}

	if spec.TestSpec != nil {
		for i, tc := range spec.TestSpec.TestCases {
			check("test_spec.json", fmt.Sprintf("/test_cases/%d/requirement_id", i), tc.RequirementID)
		}
		for i, ec := range spec.TestSpec.EdgeCaseTests {
			check("test_spec.json", fmt.Sprintf("/edge_case_tests/%d/requirement_id", i), ec.RequirementID)
		}
	}
	if spec.Tasks != nil {
		for i, tr := range spec.Tasks.Traceability {
			check("tasks.json", fmt.Sprintf("/traceability/%d/requirement_id", i), tr.RequirementID)
		}
	}
	for i, eh := range spec.Requirements.ErrorHandling {
		check("requirements.json", fmt.Sprintf("/error_handling/%d/requirement_id", i), eh.RequirementID)
	}
	return errs
}

// Rule 2: every acceptance criterion and edge case has a corresponding test case.
func crossFileRule2(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Requirements == nil || spec.TestSpec == nil {
		return errs
	}

	// Build set of requirement_ids covered by TestCases and EdgeCaseTests.
	covered := make(map[string]bool)
	for _, tc := range spec.TestSpec.TestCases {
		covered[tc.RequirementID] = true
	}
	for _, ec := range spec.TestSpec.EdgeCaseTests {
		covered[ec.RequirementID] = true
	}

	for ri, r := range spec.Requirements.Requirements {
		for ci, ac := range r.AcceptanceCriteria {
			if !covered[ac.ID] {
				errs = append(errs, ValidationError{
					File:     "requirements.json",
					Path:     fmt.Sprintf("/requirements/%d/acceptance_criteria/%d", ri, ci),
					Rule:     "integrity-2",
					Message:  fmt.Sprintf("acceptance criterion %q has no test case in test_spec.json", ac.ID),
					Severity: SeverityError,
				})
			}
		}
		for ci, ec := range r.EdgeCases {
			if !covered[ec.ID] {
				errs = append(errs, ValidationError{
					File:     "requirements.json",
					Path:     fmt.Sprintf("/requirements/%d/edge_cases/%d", ri, ci),
					Rule:     "integrity-2",
					Message:  fmt.Sprintf("edge case %q has no test case in test_spec.json", ec.ID),
					Severity: SeverityError,
				})
			}
		}
	}
	return errs
}

// Rule 3: every correctness property has a corresponding property test.
func crossFileRule3(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Requirements == nil || spec.TestSpec == nil {
		return errs
	}

	covered := make(map[string]bool)
	for _, pt := range spec.TestSpec.PropertyTests {
		covered[pt.PropertyID] = true
	}

	for i, prop := range spec.Requirements.CorrectnessProperties {
		if !covered[prop.ID] {
			errs = append(errs, ValidationError{
				File:     "requirements.json",
				Path:     fmt.Sprintf("/correctness_properties/%d", i),
				Rule:     "integrity-3",
				Message:  fmt.Sprintf("correctness property %q has no property test in test_spec.json", prop.ID),
				Severity: SeverityError,
			})
		}
	}
	return errs
}

// Rule 4: every execution path has a corresponding smoke test.
func crossFileRule4(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Requirements == nil || spec.TestSpec == nil {
		return errs
	}

	covered := make(map[string]bool)
	for _, st := range spec.TestSpec.SmokeTests {
		covered[st.ExecutionPathID] = true
	}

	for i, path := range spec.Requirements.ExecutionPaths {
		if !covered[path.ID] {
			errs = append(errs, ValidationError{
				File:     "requirements.json",
				Path:     fmt.Sprintf("/execution_paths/%d", i),
				Rule:     "integrity-4",
				Message:  fmt.Sprintf("execution path %q has no smoke test in test_spec.json", path.ID),
				Severity: SeverityError,
			})
		}
	}
	return errs
}

// Rule 5: every test_spec_id in tasks traceability and subtask test_spec_refs
// exists in test_spec.json.
func crossFileRule5(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Tasks == nil || spec.TestSpec == nil {
		return errs
	}

	tsIDs := buildTestSpecIDSet(spec.TestSpec)

	check := func(file, path, tsid string) {
		if tsid != "" && !tsIDs[tsid] {
			errs = append(errs, ValidationError{
				File:     file,
				Path:     path,
				Rule:     "integrity-5",
				Message:  fmt.Sprintf("test_spec_id %q not found in test_spec.json", tsid),
				Severity: SeverityError,
			})
		}
	}

	for i, tr := range spec.Tasks.Traceability {
		check("tasks.json", fmt.Sprintf("/traceability/%d/test_spec_id", i), tr.TestSpecID)
	}
	for gi, g := range spec.Tasks.TaskGroups {
		for si, s := range g.Subtasks {
			for ri, ref := range s.TestSpecRefs {
				check("tasks.json",
					fmt.Sprintf("/task_groups/%d/subtasks/%d/test_spec_refs/%d", gi, si, ri),
					ref)
			}
		}
	}
	return errs
}

// backtickTermRe matches backtick-wrapped terms in a string.
var backtickTermRe = regexp.MustCompile("`([^`]+)`")

// extractBacktickTerms returns all terms wrapped in backticks within s.
func extractBacktickTerms(s string) []string {
	matches := backtickTermRe.FindAllStringSubmatch(s, -1)
	var terms []string
	for _, m := range matches {
		if len(m) > 1 {
			terms = append(terms, m[1])
		}
	}
	return terms
}

// Rule 6: every backtick-wrapped term in checked fields has a glossary entry.
func crossFileRule6(spec *Spec) []ValidationError {
	var errs []ValidationError
	if spec.Requirements == nil {
		return errs
	}

	glossary := spec.Requirements.Glossary

	checkField := func(file, path, fieldName, value string) {
		for _, term := range extractBacktickTerms(value) {
			if _, ok := glossary[term]; !ok {
				errs = append(errs, ValidationError{
					File:     file,
					Path:     path + "/" + fieldName,
					Rule:     "integrity-6",
					Message:  fmt.Sprintf("backtick term %q in field %q not found in glossary", term, fieldName),
					Severity: SeverityError,
				})
			}
		}
	}

	for ri, r := range spec.Requirements.Requirements {
		for ci, c := range r.AcceptanceCriteria {
			base := fmt.Sprintf("/requirements/%d/acceptance_criteria/%d", ri, ci)
			checkField("requirements.json", base, "action", c.Action)
			checkField("requirements.json", base, "trigger", c.Trigger)
			checkField("requirements.json", base, "condition", c.Condition)
			checkField("requirements.json", base, "error_condition", c.ErrorCondition)
			checkField("requirements.json", base, "state", c.State)
			checkField("requirements.json", base, "feature", c.Feature)
		}
		for ci, c := range r.EdgeCases {
			base := fmt.Sprintf("/requirements/%d/edge_cases/%d", ri, ci)
			checkField("requirements.json", base, "action", c.Action)
			checkField("requirements.json", base, "trigger", c.Trigger)
			checkField("requirements.json", base, "condition", c.Condition)
			checkField("requirements.json", base, "error_condition", c.ErrorCondition)
			checkField("requirements.json", base, "state", c.State)
			checkField("requirements.json", base, "feature", c.Feature)
		}
	}
	for pi, prop := range spec.Requirements.CorrectnessProperties {
		base := fmt.Sprintf("/correctness_properties/%d", pi)
		checkField("requirements.json", base, "for_any", prop.ForAny)
		checkField("requirements.json", base, "invariant", prop.Invariant)
	}
	return errs
}

// Rule 7: spec_id and spec_name are identical across all four files.
func crossFileRule7(spec *Spec) []ValidationError {
	var errs []ValidationError

	var prdSpecID, prdSpecName string
	if spec.PRD != nil {
		prdSpecID = spec.PRD.Frontmatter.SpecID
		prdSpecName = spec.PRD.Frontmatter.SpecName
	}

	check := func(file, field, got, want string) {
		if got != want {
			errs = append(errs, ValidationError{
				File:     file,
				Path:     "/" + field,
				Rule:     "integrity-7",
				Message: fmt.Sprintf(
					"%s mismatch: %s has %q but prd.md has %q",
					field, file, got, want,
				),
				Severity: SeverityError,
			})
		}
	}

	if spec.Requirements != nil {
		check("requirements.json", "spec_id", spec.Requirements.SpecID, prdSpecID)
		check("requirements.json", "spec_name", spec.Requirements.SpecName, prdSpecName)
	}
	if spec.TestSpec != nil {
		check("test_spec.json", "spec_id", spec.TestSpec.SpecID, prdSpecID)
		check("test_spec.json", "spec_name", spec.TestSpec.SpecName, prdSpecName)
	}
	if spec.Tasks != nil {
		check("tasks.json", "spec_id", spec.Tasks.SpecID, prdSpecID)
		check("tasks.json", "spec_name", spec.Tasks.SpecName, prdSpecName)
	}
	return errs
}

// ─────────────────────────────────────────────────────────────────────────────
// ID format validation
// ─────────────────────────────────────────────────────────────────────────────

var (
	// {spec_id}-REQ-{N}
	reqIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)$`)
	// {spec_id}-REQ-{N}.{C} (acceptance criteria)
	criterionIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)\.(\d+)$`)
	// {spec_id}-REQ-{N}.E{C} (edge cases)
	edgeCaseIDRe = regexp.MustCompile(`^(\w+)-REQ-(\d+)\.E(\d+)$`)
	// {spec_id}-PROP-{N}
	propIDRe = regexp.MustCompile(`^(\w+)-PROP-(\d+)$`)
	// {spec_id}-PATH-{N}
	pathIDRe = regexp.MustCompile(`^(\w+)-PATH-(\d+)$`)
	// {spec_id}-ERR-{N}
	errIDRe = regexp.MustCompile(`^(\w+)-ERR-(\d+)$`)
	// TS-{spec_id}-{N}
	testCaseIDRe = regexp.MustCompile(`^TS-(\w+)-(\d+)$`)
	// TS-{spec_id}-P{N}
	propTestIDRe = regexp.MustCompile(`^TS-(\w+)-P(\d+)$`)
	// TS-{spec_id}-E{N}
	edgeCaseTestIDRe = regexp.MustCompile(`^TS-(\w+)-E(\d+)$`)
	// TS-{spec_id}-SMOKE-{N}
	smokeTestIDRe = regexp.MustCompile(`^TS-(\w+)-SMOKE-(\d+)$`)
	// {group}.{N}
	subtaskIDRe = regexp.MustCompile(`^(\d+)\.(\d+)$`)
	// {group}.V
	verificationIDRe = regexp.MustCompile(`^(\d+)\.V$`)
)

// checkIDFormat validates an ID against a regex pattern and checks that the
// spec_id component matches the declared specID. Returns zero or more errors.
func checkIDFormat(file, path, id, declaredSpecID string, re *regexp.Regexp, idType string) []ValidationError {
	var errs []ValidationError
	add := func(sev Severity, msg string) {
		errs = append(errs, ValidationError{
			File:     file,
			Path:     path,
			Rule:     "id-format",
			Message:  msg,
			Severity: sev,
		})
	}

	m := re.FindStringSubmatch(id)
	if m == nil {
		add(SeverityError, fmt.Sprintf("%s ID %q does not match the required format", idType, id))
		return errs
	}

	// m[1] is always the spec_id component for all patterns except subtask/verification.
	parsedSpecID := m[1]
	if declaredSpecID != "" && parsedSpecID != declaredSpecID {
		add(SeverityError, fmt.Sprintf(
			"%s ID %q has spec_id %q but file declares spec_id %q",
			idType, id, parsedSpecID, declaredSpecID,
		))
	}

	// Validate numeric components are positive (> 0).
	for i := 2; i < len(m); i++ {
		n, err := strconv.Atoi(m[i])
		if err != nil {
			add(SeverityError, fmt.Sprintf("%s ID %q: component %q is not a valid integer", idType, id, m[i]))
		} else if n <= 0 {
			add(SeverityError, fmt.Sprintf("%s ID %q: numeric component %d must be a positive integer (> 0)", idType, id, n))
		}
	}
	return errs
}

// checkTestIDFormat validates test spec IDs (TS-{specID}-...). The spec_id
// is the second group in these patterns (m[1]).
func checkTestIDFormat(file, path, id, declaredSpecID string, re *regexp.Regexp, idType string) []ValidationError {
	var errs []ValidationError
	add := func(sev Severity, msg string) {
		errs = append(errs, ValidationError{
			File:     file,
			Path:     path,
			Rule:     "id-format",
			Message:  msg,
			Severity: sev,
		})
	}

	m := re.FindStringSubmatch(id)
	if m == nil {
		add(SeverityError, fmt.Sprintf("%s ID %q does not match the required format", idType, id))
		return errs
	}

	parsedSpecID := m[1]
	if declaredSpecID != "" && parsedSpecID != declaredSpecID {
		add(SeverityError, fmt.Sprintf(
			"%s ID %q has spec_id %q but file declares spec_id %q",
			idType, id, parsedSpecID, declaredSpecID,
		))
	}
	// Validate numeric component(s)
	for i := 2; i < len(m); i++ {
		n, err := strconv.Atoi(m[i])
		if err != nil {
			add(SeverityError, fmt.Sprintf("%s ID %q: component %q is not a valid integer", idType, id, m[i]))
		} else if n <= 0 {
			add(SeverityError, fmt.Sprintf("%s ID %q: numeric component %d must be a positive integer (> 0)", idType, id, n))
		}
	}
	return errs
}

func validateRequirementIDs(req *Requirements, specID string) []ValidationError {
	var errs []ValidationError
	file := "requirements.json"

	// Collect requirement N values to check sequentiality.
	var reqNums []int

	for ri, r := range req.Requirements {
		path := fmt.Sprintf("/requirements/%d/id", ri)
		errs = append(errs, checkIDFormat(file, path, r.ID, specID, reqIDRe, "requirement")...)

		// Extract N for sequentiality check.
		if m := reqIDRe.FindStringSubmatch(r.ID); m != nil {
			if n, err := strconv.Atoi(m[2]); err == nil && n > 0 {
				reqNums = append(reqNums, n)
			}
		}

		for ci, ac := range r.AcceptanceCriteria {
			path := fmt.Sprintf("/requirements/%d/acceptance_criteria/%d/id", ri, ci)
			errs = append(errs, checkIDFormat(file, path, ac.ID, specID, criterionIDRe, "criterion")...)
		}
		for ci, ec := range r.EdgeCases {
			path := fmt.Sprintf("/requirements/%d/edge_cases/%d/id", ri, ci)
			errs = append(errs, checkIDFormat(file, path, ec.ID, specID, edgeCaseIDRe, "edge case")...)
		}
	}

	for i, prop := range req.CorrectnessProperties {
		path := fmt.Sprintf("/correctness_properties/%d/id", i)
		errs = append(errs, checkIDFormat(file, path, prop.ID, specID, propIDRe, "correctness property")...)
	}
	for i, ep := range req.ExecutionPaths {
		path := fmt.Sprintf("/execution_paths/%d/id", i)
		errs = append(errs, checkIDFormat(file, path, ep.ID, specID, pathIDRe, "execution path")...)
	}
	for i, eh := range req.ErrorHandling {
		path := fmt.Sprintf("/error_handling/%d/id", i)
		errs = append(errs, checkIDFormat(file, path, eh.ID, specID, errIDRe, "error handling")...)
	}

	// Sequentiality warning for requirements.
	errs = append(errs, checkSequentiality(file, "/requirements", reqNums, "requirement")...)

	return errs
}

// checkSequentiality emits a warning if there are gaps in a slice of positive integers.
func checkSequentiality(file, path string, nums []int, entityType string) []ValidationError {
	if len(nums) < 2 {
		return nil
	}
	sort.Ints(nums)
	var gaps []string
	for i := 1; i < len(nums); i++ {
		if nums[i] != nums[i-1]+1 {
			for g := nums[i-1] + 1; g < nums[i]; g++ {
				gaps = append(gaps, strconv.Itoa(g))
			}
		}
	}
	if len(gaps) == 0 {
		return nil
	}
	return []ValidationError{{
		File:     file,
		Path:     path,
		Rule:     "id-sequence",
		Message: fmt.Sprintf(
			"%s IDs are not sequential; missing positions: %s",
			entityType, strings.Join(gaps, ", "),
		),
		Severity: SeverityWarning,
	}}
}

func validateTestSpecIDs(ts *TestSpecDoc, specID string) []ValidationError {
	var errs []ValidationError
	file := "test_spec.json"

	for i, tc := range ts.TestCases {
		path := fmt.Sprintf("/test_cases/%d/id", i)
		errs = append(errs, checkTestIDFormat(file, path, tc.ID, specID, testCaseIDRe, "test case")...)
	}
	for i, pt := range ts.PropertyTests {
		path := fmt.Sprintf("/property_tests/%d/id", i)
		errs = append(errs, checkTestIDFormat(file, path, pt.ID, specID, propTestIDRe, "property test")...)
	}
	for i, ec := range ts.EdgeCaseTests {
		path := fmt.Sprintf("/edge_case_tests/%d/id", i)
		errs = append(errs, checkTestIDFormat(file, path, ec.ID, specID, edgeCaseTestIDRe, "edge case test")...)
	}
	for i, st := range ts.SmokeTests {
		path := fmt.Sprintf("/smoke_tests/%d/id", i)
		errs = append(errs, checkTestIDFormat(file, path, st.ID, specID, smokeTestIDRe, "smoke test")...)
	}
	return errs
}

func validateTasksIDs(tasks *Tasks, _ string) []ValidationError {
	var errs []ValidationError
	file := "tasks.json"

	for gi, g := range tasks.TaskGroups {
		for si, s := range g.Subtasks {
			path := fmt.Sprintf("/task_groups/%d/subtasks/%d/id", gi, si)
			m := subtaskIDRe.FindStringSubmatch(s.ID)
			if m == nil {
				errs = append(errs, ValidationError{
					File:     file,
					Path:     path,
					Rule:     "id-format",
					Message:  fmt.Sprintf("subtask ID %q does not match required format {group}.{N}", s.ID),
					Severity: SeverityError,
				})
			}
		}
		// Verification ID
		vpath := fmt.Sprintf("/task_groups/%d/verification/id", gi)
		if !verificationIDRe.MatchString(g.Verification.ID) {
			errs = append(errs, ValidationError{
				File:     file,
				Path:     vpath,
				Rule:     "id-format",
				Message:  fmt.Sprintf("verification ID %q does not match required format {group}.V", g.Verification.ID),
				Severity: SeverityError,
			})
		}
	}
	return errs
}
