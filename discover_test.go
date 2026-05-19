package afspec_test

// discover_test.go covers:
//   TS-01-38  (Discover specs in root directory)
//   TS-01-39  (Discovery skips archive)
//   TS-01-40  (Discovery loads metadata from frontmatter)
//   TS-01-41  (Discovery builds dependency graph)
//   TS-01-42  (Discovery defaults to current directory)
//   TS-01-E20 (Spec root not found)
//   TS-01-E21 (Incomplete spec in discovery)
//   TS-01-E22 (Dependency cycle detection)
//   TS-01-P7  (Discovery completeness property)

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	afspec "github.com/agent-fox/afspec"
)

// ---------------------------------------------------------------------------
// TS-01-38: Discover specs in root directory
// ---------------------------------------------------------------------------

func TestTS01_38(t *testing.T) {
	root := t.TempDir()

	// Create two valid spec dirs and one non-matching dir
	createSpecDir(t, root, "01", "feature_a")
	createSpecDir(t, root, "02", "feature_b")
	if err := os.MkdirAll(filepath.Join(root, "not_a_spec"), 0755); err != nil {
		t.Fatalf("MkdirAll not_a_spec: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(root, "archive"), 0755); err != nil {
		t.Fatalf("MkdirAll archive: %v", err)
	}

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}
	if result == nil {
		t.Fatal("DiscoverSpecs returned nil result")
	}

	if len(result.Entries) != 2 {
		t.Errorf("DiscoverSpecs found %d entries, want 2", len(result.Entries))
	}

	ids := make(map[string]bool)
	for _, e := range result.Entries {
		ids[e.SpecID] = true
	}
	for _, want := range []string{"01", "02"} {
		if !ids[want] {
			t.Errorf("DiscoverSpecs missing entry for spec_id %q", want)
		}
	}
}

// ---------------------------------------------------------------------------
// TS-01-39: Discovery skips archive
// ---------------------------------------------------------------------------

func TestTS01_39(t *testing.T) {
	root := t.TempDir()

	// Create one active spec and one in archive/
	createSpecDir(t, root, "01", "active")
	archiveDir := filepath.Join(root, "archive")
	if err := os.MkdirAll(archiveDir, 0755); err != nil {
		t.Fatalf("MkdirAll archive: %v", err)
	}
	createSpecDir(t, archiveDir, "03", "old")

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}

	if len(result.Entries) != 1 {
		t.Errorf("DiscoverSpecs found %d entries, want 1 (archive excluded)", len(result.Entries))
	}
	if len(result.Entries) > 0 && result.Entries[0].SpecID != "01" {
		t.Errorf("DiscoverSpecs found unexpected spec %q (should be '01')", result.Entries[0].SpecID)
	}
}

// ---------------------------------------------------------------------------
// TS-01-40: Discovery loads metadata from frontmatter
// ---------------------------------------------------------------------------

func TestTS01_40(t *testing.T) {
	root := t.TempDir()
	createSpecDirWithStatus(t, root, "01", "feature_a", afspec.StatusActive)

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}
	if len(result.Entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result.Entries))
	}

	entry := result.Entries[0]
	if entry.SpecID != "01" {
		t.Errorf("SpecID = %q, want %q", entry.SpecID, "01")
	}
	if entry.SpecName != "feature_a" {
		t.Errorf("SpecName = %q, want %q", entry.SpecName, "feature_a")
	}
	if entry.Status != afspec.StatusActive {
		t.Errorf("Status = %q, want %q", entry.Status, afspec.StatusActive)
	}
}

// ---------------------------------------------------------------------------
// TS-01-41: Discovery builds dependency graph
// ---------------------------------------------------------------------------

func TestTS01_41(t *testing.T) {
	root := t.TempDir()

	// Create two specs: 01 has no deps, 02 depends on 01
	createSpecDir(t, root, "01", "base")
	createSpecDirWithDependency(t, root, "02", "dependent", "01")

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}
	if result.Graph == nil {
		t.Fatal("DiscoverSpecs returned nil dependency graph")
	}

	// 02 should depend on 01
	deps, ok := result.Graph.Edges["02"]
	if !ok {
		t.Errorf("graph should have edges for '02'; edges = %v", result.Graph.Edges)
	}
	found := false
	for _, dep := range deps {
		if dep == "01" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("'02' should depend on '01'; deps = %v", deps)
	}

	// Topological order: 01 before 02
	order, err := result.Graph.TopologicalOrder()
	if err != nil {
		t.Fatalf("TopologicalOrder: %v", err)
	}

	idx01 := indexOf(order, "01")
	idx02 := indexOf(order, "02")
	if idx01 < 0 || idx02 < 0 {
		t.Errorf("TopologicalOrder missing entries: %v", order)
	} else if idx01 >= idx02 {
		t.Errorf("'01' (pos %d) should come before '02' (pos %d) in topo order", idx01, idx02)
	}
}

func indexOf(ss []string, s string) int {
	for i, v := range ss {
		if v == s {
			return i
		}
	}
	return -1
}

// ---------------------------------------------------------------------------
// TS-01-42: Discovery defaults to current directory
// ---------------------------------------------------------------------------

func TestTS01_42(t *testing.T) {
	root := t.TempDir()
	createSpecDir(t, root, "01", "default_cwd")

	// Change working directory to root
	t.Chdir(root)

	result, err := afspec.DiscoverSpecs("")
	if err != nil {
		t.Fatalf("DiscoverSpecs (empty root): %v", err)
	}
	if result == nil {
		t.Fatal("DiscoverSpecs returned nil")
	}
	if len(result.Entries) == 0 {
		t.Error("DiscoverSpecs with empty root should discover specs in cwd")
	}
}

// ---------------------------------------------------------------------------
// TS-01-E20: Spec root not found
// ---------------------------------------------------------------------------

func TestTS01_E20(t *testing.T) {
	result, err := afspec.DiscoverSpecs("/nonexistent/spec/root")
	if err == nil {
		t.Fatal("DiscoverSpecs should fail for non-existent root, got nil error")
	}
	if result != nil {
		t.Errorf("DiscoverSpecs should return nil result on error, got %v", result)
	}
}

// ---------------------------------------------------------------------------
// TS-01-E21: Incomplete spec in discovery
// ---------------------------------------------------------------------------

func TestTS01_E21(t *testing.T) {
	root := t.TempDir()

	// Create a spec directory with only prd.md (missing 3 files)
	specDir := filepath.Join(root, "01_partial")
	if err := os.MkdirAll(specDir, 0755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	writePRDFile(t, specDir, "01", "partial", afspec.StatusDraft)

	result, err := afspec.DiscoverSpecs(root)
	if err != nil {
		t.Fatalf("DiscoverSpecs: %v", err)
	}
	if len(result.Entries) == 0 {
		t.Fatal("DiscoverSpecs should include incomplete spec in results")
	}

	var entry *afspec.SpecEntry
	for i := range result.Entries {
		if result.Entries[i].SpecID == "01" {
			entry = &result.Entries[i]
			break
		}
	}
	if entry == nil {
		t.Fatal("DiscoverSpecs should find spec '01'")
	}
	if entry.Complete {
		t.Errorf("spec '01' should be marked Complete=false (missing files)")
	}
}

// ---------------------------------------------------------------------------
// TS-01-E22: Dependency cycle detection
// ---------------------------------------------------------------------------

func TestTS01_E22(t *testing.T) {
	root := t.TempDir()

	// 01 depends on 02, 02 depends on 01 → cycle
	createSpecDirWithDependency(t, root, "01", "spec_a", "02")
	createSpecDirWithDependency(t, root, "02", "spec_b", "01")

	_, err := afspec.DiscoverSpecs(root)
	if err == nil {
		t.Fatal("DiscoverSpecs should detect dependency cycle, got nil error")
	}
	errStr := err.Error()
	if !containsSubstr(errStr, "cycle") && !containsSubstr(errStr, "circular") {
		t.Errorf("error %q should mention 'cycle' or 'circular'", errStr)
	}
	if !containsSubstr(errStr, "01") || !containsSubstr(errStr, "02") {
		t.Errorf("error %q should mention both cycle participants '01' and '02'", errStr)
	}
}

// ---------------------------------------------------------------------------
// TS-01-P7: Discovery completeness (property test)
// ---------------------------------------------------------------------------

func TestPropertyP7(t *testing.T) {
	// For any set of N spec dirs, DiscoverSpecs should return exactly N entries.
	scenarios := []struct {
		nSpecs   int
		nArchive int
		nInvalid int
	}{
		{nSpecs: 1, nArchive: 0, nInvalid: 0},
		{nSpecs: 3, nArchive: 2, nInvalid: 1},
		{nSpecs: 0, nArchive: 1, nInvalid: 2},
		{nSpecs: 5, nArchive: 0, nInvalid: 3},
	}

	for _, sc := range scenarios {
		t.Run(fmt.Sprintf("specs=%d,archive=%d,invalid=%d", sc.nSpecs, sc.nArchive, sc.nInvalid), func(t *testing.T) {
			root := t.TempDir()

			for i := 1; i <= sc.nSpecs; i++ {
				createSpecDir(t, root, fmt.Sprintf("%02d", i), fmt.Sprintf("spec_%d", i))
			}

			if sc.nArchive > 0 {
				archiveDir := filepath.Join(root, "archive")
				if err := os.MkdirAll(archiveDir, 0755); err != nil {
					t.Fatalf("MkdirAll archive: %v", err)
				}
				for i := 1; i <= sc.nArchive; i++ {
					createSpecDir(t, archiveDir, fmt.Sprintf("%02d", 90+i), fmt.Sprintf("archived_%d", i))
				}
			}

			for i := 1; i <= sc.nInvalid; i++ {
				invalidDir := filepath.Join(root, fmt.Sprintf("invalid_%d", i))
				if err := os.MkdirAll(invalidDir, 0755); err != nil {
					t.Fatalf("MkdirAll invalid: %v", err)
				}
			}

			result, err := afspec.DiscoverSpecs(root)
			if err != nil {
				t.Fatalf("DiscoverSpecs: %v", err)
			}
			if len(result.Entries) != sc.nSpecs {
				t.Errorf("DiscoverSpecs found %d entries, want %d", len(result.Entries), sc.nSpecs)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// Discovery test helpers
// ---------------------------------------------------------------------------

// createSpecDir creates a complete spec directory matching {NN}_{name} pattern.
func createSpecDir(t *testing.T, root, specID, specName string) {
	t.Helper()
	createSpecDirWithStatus(t, root, specID, specName, afspec.StatusDraft)
}

// createSpecDirWithStatus creates a complete spec dir with a specific status.
func createSpecDirWithStatus(t *testing.T, root, specID, specName string, status afspec.Status) {
	t.Helper()
	dirName := fmt.Sprintf("%s_%s", specID, specName)
	specDir := filepath.Join(root, dirName)
	if err := os.MkdirAll(specDir, 0755); err != nil {
		t.Fatalf("MkdirAll %s: %v", specDir, err)
	}

	writePRDFile(t, specDir, specID, specName, status)
	writeJSONFile(t, specDir, "requirements.json", makeDiscoveryReq(specID, specName))
	writeJSONFile(t, specDir, "test_spec.json", makeDiscoveryTestSpec(specID, specName))
	writeJSONFile(t, specDir, "tasks.json", makeDiscoveryTasks(specID, specName, ""))
}

// createSpecDirWithDependency creates a spec dir that depends on another spec.
func createSpecDirWithDependency(t *testing.T, root, specID, specName, dependsOn string) {
	t.Helper()
	dirName := fmt.Sprintf("%s_%s", specID, specName)
	specDir := filepath.Join(root, dirName)
	if err := os.MkdirAll(specDir, 0755); err != nil {
		t.Fatalf("MkdirAll %s: %v", specDir, err)
	}

	writePRDFile(t, specDir, specID, specName, afspec.StatusDraft)
	writeJSONFile(t, specDir, "requirements.json", makeDiscoveryReq(specID, specName))
	writeJSONFile(t, specDir, "test_spec.json", makeDiscoveryTestSpec(specID, specName))
	writeJSONFile(t, specDir, "tasks.json", makeDiscoveryTasks(specID, specName, dependsOn))
}

func writePRDFile(t *testing.T, dir, specID, specName string, status afspec.Status) {
	t.Helper()
	content := fmt.Sprintf(`---
spec_id: "%s"
spec_name: "%s"
title: "Test Spec"
status: "%s"
created_at: "2026-01-01T00:00:00Z"
updated_at: "2026-01-01T00:00:00Z"
owner: "test"
source: "test"
supersedes: []
tags: []
intent_hash: null
schema_version: 1
---
# Test Spec

## Intent

Test spec for discovery.

## Goals

- Test discovery
`, specID, specName, status)
	if err := os.WriteFile(filepath.Join(dir, "prd.md"), []byte(content), 0644); err != nil {
		t.Fatalf("WriteFile prd.md: %v", err)
	}
}

func writeJSONFile(t *testing.T, dir, filename string, v interface{}) {
	t.Helper()
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		t.Fatalf("json.MarshalIndent %s: %v", filename, err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(filepath.Join(dir, filename), data, 0644); err != nil {
		t.Fatalf("WriteFile %s: %v", filename, err)
	}
}

type discoveryReqDoc struct {
	Schema                string        `json:"$schema"`
	SpecID                string        `json:"spec_id"`
	SpecName              string        `json:"spec_name"`
	SchemaVersion         int           `json:"schema_version"`
	Introduction          string        `json:"introduction"`
	Glossary              interface{}   `json:"glossary"`
	Requirements          []interface{} `json:"requirements"`
	CorrectnessProperties []interface{} `json:"correctness_properties"`
	ExecutionPaths        []interface{} `json:"execution_paths"`
	ErrorHandling         []interface{} `json:"error_handling"`
}

func makeDiscoveryReq(specID, specName string) discoveryReqDoc {
	return discoveryReqDoc{
		Schema:                "",
		SpecID:                specID,
		SpecName:              specName,
		SchemaVersion:         1,
		Introduction:          "Test spec.",
		Glossary:              map[string]string{},
		Requirements:          []interface{}{},
		CorrectnessProperties: []interface{}{},
		ExecutionPaths:        []interface{}{},
		ErrorHandling:         []interface{}{},
	}
}

type discoveryTSDoc struct {
	Schema        string        `json:"$schema"`
	SpecID        string        `json:"spec_id"`
	SpecName      string        `json:"spec_name"`
	SchemaVersion int           `json:"schema_version"`
	TestCases     []interface{} `json:"test_cases"`
	PropertyTests []interface{} `json:"property_tests"`
	EdgeCaseTests []interface{} `json:"edge_case_tests"`
	SmokeTests    []interface{} `json:"smoke_tests"`
	Coverage      interface{}   `json:"coverage"`
}

func makeDiscoveryTestSpec(specID, specName string) discoveryTSDoc {
	return discoveryTSDoc{
		Schema:        "",
		SpecID:        specID,
		SpecName:      specName,
		SchemaVersion: 1,
		TestCases:     []interface{}{},
		PropertyTests: []interface{}{},
		EdgeCaseTests: []interface{}{},
		SmokeTests:    []interface{}{},
		Coverage: map[string]interface{}{
			"requirements_covered": []string{},
			"properties_covered":   []string{},
			"paths_covered":        []string{},
			"gaps":                 []string{},
		},
	}
}

type discoveryTasksDoc struct {
	Schema        string        `json:"$schema"`
	SpecID        string        `json:"spec_id"`
	SpecName      string        `json:"spec_name"`
	SchemaVersion int           `json:"schema_version"`
	TestCommands  interface{}   `json:"test_commands"`
	Dependencies  []interface{} `json:"dependencies"`
	TaskGroups    []interface{} `json:"task_groups"`
	Traceability  []interface{} `json:"traceability"`
}

func makeDiscoveryTasks(specID, specName, dependsOn string) discoveryTasksDoc {
	deps := []interface{}{}
	if dependsOn != "" {
		deps = []interface{}{
			map[string]interface{}{
				"depends_on_spec": dependsOn,
				"from_group":      1,
				"to_group":        1,
				"relationship":    "requires",
				"sentinel":        false,
			},
		}
	}
	return discoveryTasksDoc{
		Schema:        "",
		SpecID:        specID,
		SpecName:      specName,
		SchemaVersion: 1,
		TestCommands: map[string]string{
			"spec_tests": "go test ./...",
			"all_tests":  "go test ./...",
			"linter":     "go vet ./...",
		},
		Dependencies: deps,
		TaskGroups: []interface{}{
			map[string]interface{}{
				"id": 1, "kind": "tests", "title": "Tests",
				"subtasks": []interface{}{},
				"verification": map[string]interface{}{
					"id": "1.V", "checks": []string{},
				},
			},
			map[string]interface{}{
				"id": 2, "kind": "wiring_verification", "title": "Wiring",
				"subtasks": []interface{}{},
				"verification": map[string]interface{}{
					"id": "2.V", "checks": []string{},
				},
			},
		},
		Traceability: []interface{}{},
	}
}
