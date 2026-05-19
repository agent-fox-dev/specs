package afspec

import (
	"github.com/agent-fox/afspec/internal/render"
)

// RenderEARS renders a single EARS criterion to its sentence form.
// Uses the six templates from spec-format.md §5.2.1.
// Empty required fields render as "<missing>".
// A null or empty return_contract omits the "AND return" clause.
func RenderEARS(c *Criterion) (string, error) {
	ic := &render.EARSCriterion{
		EarsPattern:    c.EarsPattern,
		System:         c.System,
		Action:         c.Action,
		ReturnContract: c.ReturnContract,
		Trigger:        c.Trigger,
		Condition:      c.Condition,
		ErrorCondition: c.ErrorCondition,
		State:          c.State,
		Feature:        c.Feature,
	}
	return render.RenderEARS(ic)
}

// RenderRequirements renders requirements.json to markdown.
func RenderRequirements(req *Requirements) ([]byte, error) {
	doc := &render.RequirementsDoc{
		SpecID:       req.SpecID,
		SpecName:     req.SpecName,
		Introduction: req.Introduction,
		Glossary:     req.Glossary,
	}

	// Convert requirements.
	for _, r := range req.Requirements {
		ri := render.RequirementItem{
			ID:    r.ID,
			Title: r.Title,
			UserStory: render.UserStoryItem{
				Role:    r.UserStory.Role,
				Goal:    r.UserStory.Goal,
				Benefit: r.UserStory.Benefit,
			},
		}
		for _, ac := range r.AcceptanceCriteria {
			ri.AcceptanceCriteria = append(ri.AcceptanceCriteria, criterionToInternal(ac))
		}
		for _, ec := range r.EdgeCases {
			ri.EdgeCases = append(ri.EdgeCases, criterionToInternal(ec))
		}
		doc.Requirements = append(doc.Requirements, ri)
	}

	// Convert correctness properties.
	for _, cp := range req.CorrectnessProperties {
		doc.CorrectnessProperties = append(doc.CorrectnessProperties, render.CorrectnessPropertyItem{
			ID:        cp.ID,
			Title:     cp.Title,
			ForAny:    cp.ForAny,
			Invariant: cp.Invariant,
			Validates: cp.Validates,
		})
	}

	// Convert execution paths.
	for _, ep := range req.ExecutionPaths {
		pi := render.ExecutionPathItem{
			ID:    ep.ID,
			Title: ep.Title,
		}
		for _, step := range ep.Steps {
			pi.Steps = append(pi.Steps, render.ExecutionPathStepItem{
				Actor:  step.Actor,
				Action: step.Action,
			})
		}
		doc.ExecutionPaths = append(doc.ExecutionPaths, pi)
	}

	// Convert error handling.
	for _, eh := range req.ErrorHandling {
		doc.ErrorHandling = append(doc.ErrorHandling, render.ErrorHandlingItem{
			ID:            eh.ID,
			Condition:     eh.Condition,
			Behavior:      eh.Behavior,
			RequirementID: eh.RequirementID,
		})
	}

	return render.RenderRequirements(doc)
}

// RenderTestSpec renders test_spec.json to markdown.
func RenderTestSpec(ts *TestSpecDoc) ([]byte, error) {
	doc := &render.TestSpecDocRender{
		SpecID:   ts.SpecID,
		SpecName: ts.SpecName,
	}

	for _, tc := range ts.TestCases {
		doc.TestCases = append(doc.TestCases, render.TestCaseItem{
			ID:                  tc.ID,
			RequirementID:       tc.RequirementID,
			Kind:                tc.Kind,
			Description:         tc.Description,
			Preconditions:       tc.Preconditions,
			AssertionPseudocode: tc.AssertionPseudocode,
		})
	}

	for _, pt := range ts.PropertyTests {
		doc.PropertyTests = append(doc.PropertyTests, render.PropertyTestItem{
			ID:             pt.ID,
			PropertyID:     pt.PropertyID,
			Validates:      pt.Validates,
			Description:    pt.Description,
			ForAnyStrategy: pt.ForAnyStrategy,
			InvariantCheck: pt.InvariantCheck,
		})
	}

	for _, ec := range ts.EdgeCaseTests {
		doc.EdgeCaseTests = append(doc.EdgeCaseTests, render.EdgeCaseTestItem{
			ID:                  ec.ID,
			RequirementID:       ec.RequirementID,
			Kind:                ec.Kind,
			Description:         ec.Description,
			Preconditions:       ec.Preconditions,
			AssertionPseudocode: ec.AssertionPseudocode,
		})
	}

	for _, st := range ts.SmokeTests {
		doc.SmokeTests = append(doc.SmokeTests, render.SmokeTestItem{
			ID:              st.ID,
			ExecutionPathID: st.ExecutionPathID,
			Description:     st.Description,
			Trigger:         st.Trigger,
			RealComponents:  st.RealComponents,
			Mockable:        st.Mockable,
			ExpectedEffects: st.ExpectedEffects,
		})
	}

	doc.Coverage = render.CoverageItem{
		RequirementsCovered: ts.Coverage.RequirementsCovered,
		PropertiesCovered:   ts.Coverage.PropertiesCovered,
		PathsCovered:        ts.Coverage.PathsCovered,
		Gaps:                ts.Coverage.Gaps,
	}

	return render.RenderTestSpec(doc)
}

// RenderTasks renders tasks.json to markdown.
func RenderTasks(tasks *Tasks) ([]byte, error) {
	doc := &render.TasksDoc{
		SpecID:   tasks.SpecID,
		SpecName: tasks.SpecName,
		TestCommands: render.TestCommandsItem{
			SpecTests: tasks.TestCommands.SpecTests,
			AllTests:  tasks.TestCommands.AllTests,
			Linter:    tasks.TestCommands.Linter,
		},
	}

	for _, dep := range tasks.Dependencies {
		doc.Dependencies = append(doc.Dependencies, render.TaskDependencyItem{
			DependsOnSpec: dep.DependsOnSpec,
			FromGroup:     dep.FromGroup,
			ToGroup:       dep.ToGroup,
			Relationship:  dep.Relationship,
			Sentinel:      dep.Sentinel,
		})
	}

	for _, tg := range tasks.TaskGroups {
		tgi := render.TaskGroupItem{
			ID:    tg.ID,
			Kind:  tg.Kind,
			Title: tg.Title,
			Verification: render.VerificationSubtaskItem{
				ID:     tg.Verification.ID,
				Checks: tg.Verification.Checks,
			},
		}
		for _, st := range tg.Subtasks {
			tgi.Subtasks = append(tgi.Subtasks, render.SubtaskItem{
				ID:              st.ID,
				Title:           st.Title,
				Details:         st.Details,
				TestSpecRefs:    st.TestSpecRefs,
				RequirementRefs: st.RequirementRefs,
				State:           string(st.State),
				Optional:        st.Optional,
			})
		}
		doc.TaskGroups = append(doc.TaskGroups, tgi)
	}

	for _, tr := range tasks.Traceability {
		doc.Traceability = append(doc.Traceability, render.TraceabilityItem{
			RequirementID: tr.RequirementID,
			TestSpecID:    tr.TestSpecID,
			TaskID:        tr.TaskID,
			TestPath:      tr.TestPath,
		})
	}

	return render.RenderTasks(doc)
}

// RenderCombined produces a single document: PRD verbatim + rendered JSON artifacts.
// Sections appear in order: PRD body, requirements, test_spec, tasks.
func RenderCombined(spec *Spec) ([]byte, error) {
	var result []byte

	// PRD body verbatim.
	result = append(result, []byte(spec.PRD.Body)...)

	// Separator.
	result = append(result, []byte("\n---\n\n")...)

	// Rendered requirements.
	reqMD, err := RenderRequirements(spec.Requirements)
	if err != nil {
		return nil, err
	}
	result = append(result, reqMD...)

	// Separator.
	result = append(result, []byte("\n---\n\n")...)

	// Rendered test spec.
	tsMD, err := RenderTestSpec(spec.TestSpec)
	if err != nil {
		return nil, err
	}
	result = append(result, tsMD...)

	// Separator.
	result = append(result, []byte("\n---\n\n")...)

	// Rendered tasks.
	tasksMD, err := RenderTasks(spec.Tasks)
	if err != nil {
		return nil, err
	}
	result = append(result, tasksMD...)

	return result, nil
}

// criterionToInternal converts a Criterion to an internal render.EARSCriterion.
func criterionToInternal(c Criterion) render.EARSCriterion {
	return render.EARSCriterion{
		EarsPattern:    c.EarsPattern,
		System:         c.System,
		Action:         c.Action,
		ReturnContract: c.ReturnContract,
		Trigger:        c.Trigger,
		Condition:      c.Condition,
		ErrorCondition: c.ErrorCondition,
		State:          c.State,
		Feature:        c.Feature,
	}
}
