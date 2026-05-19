package afspec

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/agent-fox/afspec/internal/ioutil"
	"github.com/agent-fox/afspec/internal/jsonutil"
	"github.com/agent-fox/afspec/internal/lifecycle"
	prdpkg "github.com/agent-fox/afspec/internal/prd"
)

// SaveSpec writes all four spec files to dir deterministically.
// Before writing:
//   - updated_at is set to the current UTC timestamp (ISO 8601)
//   - coverage is computed from test cases vs. requirements
//
// Returns an error if dir does not exist or any write fails. On failure, any
// files successfully written before the failure are removed (all-or-nothing).
func SaveSpec(dir string, spec *Spec) error {
	// Verify the directory exists.
	info, err := os.Stat(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("target directory %q does not exist", dir)
		}
		return fmt.Errorf("stat %q: %w", dir, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("%q is not a directory", dir)
	}

	// Lifecycle guard: for active specs, verify the intent hash has not changed
	// since the draft→active transition. This detects unauthorized mutations to
	// the Intent section body (01-REQ-7.3, 01-REQ-7.E2).
	if spec.PRD != nil && spec.PRD.Frontmatter.Status == StatusActive {
		if err := checkActiveSpecIntegrity(spec); err != nil {
			return err
		}
	}

	// Make a shallow copy to avoid mutating the caller's struct.
	updatedSpec := *spec
	prdCopy := *spec.PRD
	fmCopy := spec.PRD.Frontmatter

	// Set updated_at to the current UTC timestamp with nanosecond precision.
	// RFC3339Nano ensures the saved value is always >= the time captured just
	// before SaveSpec was called (unlike RFC3339 which truncates to seconds).
	// Go's time.Parse(time.RFC3339, ...) accepts fractional seconds, so callers
	// that parse with RFC3339 still work correctly.
	fmCopy.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	prdCopy.Frontmatter = fmCopy
	updatedSpec.PRD = &prdCopy

	// Compute coverage for test_spec.json.
	tsCopy := *spec.TestSpec
	tsCopy.Coverage = computeCoverage(spec.Requirements, spec.TestSpec)
	updatedSpec.TestSpec = &tsCopy

	// Serialize all four files.
	prdBytes, err := serializePRD(updatedSpec.PRD)
	if err != nil {
		return fmt.Errorf("serialize prd.md: %w", err)
	}

	reqBytes, err := jsonutil.MarshalDeterministic(updatedSpec.Requirements)
	if err != nil {
		return fmt.Errorf("serialize requirements.json: %w", err)
	}

	tsBytes, err := jsonutil.MarshalDeterministic(updatedSpec.TestSpec)
	if err != nil {
		return fmt.Errorf("serialize test_spec.json: %w", err)
	}

	tasksBytes, err := jsonutil.MarshalDeterministic(updatedSpec.Tasks)
	if err != nil {
		return fmt.Errorf("serialize tasks.json: %w", err)
	}

	// Write all four files atomically. Track successfully written paths so we
	// can roll back on failure (01-REQ-3.E2).
	type fileWrite struct {
		name string
		data []byte
	}
	writes := []fileWrite{
		{"prd.md", prdBytes},
		{"requirements.json", reqBytes},
		{"test_spec.json", tsBytes},
		{"tasks.json", tasksBytes},
	}

	var written []string
	for _, w := range writes {
		path := filepath.Join(dir, w.name)
		if err := ioutil.WriteAtomic(path, w.data, 0o644); err != nil {
			// Roll back: remove files already written.
			for _, p := range written {
				os.Remove(p) //nolint:errcheck
			}
			return fmt.Errorf("write %s: %w", w.name, err)
		}
		written = append(written, path)
	}

	return nil
}

// computeCoverage calculates the coverage field for test_spec.json by
// comparing the requirement/edge-case IDs in requirements against the
// test cases that reference them.
func computeCoverage(reqs *Requirements, ts *TestSpecDoc) Coverage {
	if reqs == nil || ts == nil {
		return Coverage{
			RequirementsCovered: []string{},
			PropertiesCovered:   []string{},
			PathsCovered:        []string{},
			Gaps:                []string{},
		}
	}

	// Collect all acceptance-criteria and edge-case IDs from requirements.
	allCriterionIDs := make(map[string]bool)
	for _, req := range reqs.Requirements {
		for _, ac := range req.AcceptanceCriteria {
			allCriterionIDs[ac.ID] = true
		}
		for _, ec := range req.EdgeCases {
			allCriterionIDs[ec.ID] = true
		}
	}

	// Collect all property IDs from correctness properties.
	allPropertyIDs := make(map[string]bool)
	for _, prop := range reqs.CorrectnessProperties {
		allPropertyIDs[prop.ID] = true
	}

	// Collect all execution path IDs.
	allPathIDs := make(map[string]bool)
	for _, path := range reqs.ExecutionPaths {
		allPathIDs[path.ID] = true
	}

	// Build sets of covered IDs from test cases.
	coveredCriteria := make(map[string]bool)
	for _, tc := range ts.TestCases {
		coveredCriteria[tc.RequirementID] = true
	}
	for _, ec := range ts.EdgeCaseTests {
		coveredCriteria[ec.RequirementID] = true
	}

	coveredProperties := make(map[string]bool)
	for _, pt := range ts.PropertyTests {
		coveredProperties[pt.PropertyID] = true
	}

	coveredPaths := make(map[string]bool)
	for _, st := range ts.SmokeTests {
		coveredPaths[st.ExecutionPathID] = true
	}

	// Compute covered and gap lists.
	var requirementsCovered, gaps []string
	for id := range allCriterionIDs {
		if coveredCriteria[id] {
			requirementsCovered = append(requirementsCovered, id)
		} else {
			gaps = append(gaps, id)
		}
	}

	var propertiesCovered []string
	for id := range allPropertyIDs {
		if coveredProperties[id] {
			propertiesCovered = append(propertiesCovered, id)
		}
	}

	var pathsCovered []string
	for id := range allPathIDs {
		if coveredPaths[id] {
			pathsCovered = append(pathsCovered, id)
		}
	}

	// Sort for deterministic output.
	sort.Strings(requirementsCovered)
	sort.Strings(gaps)
	sort.Strings(propertiesCovered)
	sort.Strings(pathsCovered)

	// Ensure slices are non-nil (serialize as [] not null).
	if requirementsCovered == nil {
		requirementsCovered = []string{}
	}
	if gaps == nil {
		gaps = []string{}
	}
	if propertiesCovered == nil {
		propertiesCovered = []string{}
	}
	if pathsCovered == nil {
		pathsCovered = []string{}
	}

	return Coverage{
		RequirementsCovered: requirementsCovered,
		PropertiesCovered:   propertiesCovered,
		PathsCovered:        pathsCovered,
		Gaps:                gaps,
	}
}

// checkActiveSpecIntegrity verifies that the Intent section in the PRD body
// has not been altered since the draft→active transition. It compares the
// recomputed hash against the stored IntentHash in the frontmatter.
//
// Returns a descriptive error if the hash does not match (tamper detected) or
// nil if the spec is intact.
func checkActiveSpecIntegrity(spec *Spec) error {
	fm := &spec.PRD.Frontmatter
	if fm.IntentHash == nil {
		// No hash stored yet — draft state or pre-hash spec, skip check.
		return nil
	}

	// Extract the Intent section body from the full PRD body.
	intentBody, err := prdpkg.ExtractIntent(spec.PRD.Body)
	if err != nil {
		return fmt.Errorf(
			"intent section check failed: cannot extract ## Intent from PRD body: %w", err)
	}

	// Recompute and compare.
	if err := lifecycle.CheckIntentHash(fm.IntentHash, intentBody); err != nil {
		return fmt.Errorf("intent hash mismatch — Intent section modified on active spec: %w", err)
	}
	return nil
}
