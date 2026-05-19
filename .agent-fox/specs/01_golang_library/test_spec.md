# Test Specification: Go Spec-Format Library (afspec)

## Overview

This document defines test contracts for every acceptance criterion, correctness property, edge case, and execution path in the afspec library specification. Tests are organized by requirement and map 1:1 to the criteria in `requirements.md` and properties in `design.md`. The coding agent translates these into executable Go tests using the `testing` package and `testing/quick` for property tests.

Test fixtures live in `testdata/` as golden files. Temporary directories are used for I/O tests.

---

## Test Cases

### TS-01-1: PRD frontmatter types

**Requirement:** 01-REQ-1.1
**Type:** unit
**Description:** Verify Go PRD types represent all 12 frontmatter fields.

**Preconditions:**
- None (compile-time check).

**Input:**
- Construct a `Frontmatter` struct with all 12 fields populated.

**Expected:**
- All fields are accessible and have correct types.
- `IntentHash` is a `*string` (nullable).
- `Supersedes` and `Tags` are `[]string`.

**Assertion pseudocode:**
```
fm = Frontmatter{SpecID: "01", SpecName: "test", Title: "Test", ...all 12 fields...}
ASSERT fm.SpecID == "01"
ASSERT fm.IntentHash == nil OR *fm.IntentHash == "abc..."
ASSERT len(fm.Supersedes) >= 0
ASSERT fm.SchemaVersion == 1
```

---

### TS-01-2: Requirements container types

**Requirement:** 01-REQ-1.2
**Type:** unit
**Description:** Verify Go Requirements types contain all top-level fields and nested types.

**Preconditions:**
- None.

**Input:**
- Construct a `Requirements` struct with all fields, including nested `Requirement`, `UserStory`, `CorrectnessProperty`, `ExecutionPath`, `ExecutionPathStep`, `ErrorHandlingEntry`.

**Expected:**
- All fields accessible and correctly typed.
- `Glossary` is `map[string]string`.
- Arrays default to empty slices.

**Assertion pseudocode:**
```
req = Requirements{SpecID: "01", Glossary: map[string]string{"term": "def"}, Requirements: []Requirement{...}}
ASSERT req.SpecID == "01"
ASSERT req.Glossary["term"] == "def"
ASSERT len(req.CorrectnessProperties) >= 0
```

---

### TS-01-3: TestSpec and Tasks container types

**Requirement:** 01-REQ-1.3
**Type:** unit
**Description:** Verify Go TestSpecDoc and Tasks types contain all fields and nested types.

**Preconditions:**
- None.

**Input:**
- Construct `TestSpecDoc` and `Tasks` structs with all nested types populated.

**Expected:**
- All nested types (TestCase, PropertyTest, SmokeTest, TaskGroup, Subtask, etc.) accessible.

**Assertion pseudocode:**
```
ts = TestSpecDoc{TestCases: []TestCase{{ID: "TS-01-1", Kind: "unit"}}}
tasks = Tasks{TaskGroups: []TaskGroup{{ID: 1, Kind: "tests"}}}
ASSERT ts.TestCases[0].Kind == "unit"
ASSERT tasks.TaskGroups[0].Kind == "tests"
```

---

### TS-01-4: EARS discriminated union

**Requirement:** 01-REQ-1.4
**Type:** unit
**Description:** Verify six EARS criterion variants have correct field sets.

**Preconditions:**
- None.

**Input:**
- Construct one `Criterion` per EARS pattern: ubiquitous, event_driven, complex_event, state_driven, unwanted, optional.

**Expected:**
- Each variant has `id`, `ears_pattern`, `system`, `action`, `return_contract`.
- Pattern-specific fields populated for correct pattern, empty/zero for others.

**Assertion pseudocode:**
```
c_ub = Criterion{EarsPattern: "ubiquitous", System: "the system", Action: "do X"}
ASSERT c_ub.Trigger == ""  // not applicable
c_ed = Criterion{EarsPattern: "event_driven", Trigger: "user clicks", System: "the system", Action: "do X"}
ASSERT c_ed.Trigger == "user clicks"
c_ce = Criterion{EarsPattern: "complex_event", Trigger: "t", Condition: "c", System: "s", Action: "a"}
ASSERT c_ce.Condition == "c"
c_sd = Criterion{EarsPattern: "state_driven", State: "active", System: "s", Action: "a"}
ASSERT c_sd.State == "active"
c_uw = Criterion{EarsPattern: "unwanted", ErrorCondition: "disk full", System: "s", Action: "a"}
ASSERT c_uw.ErrorCondition == "disk full"
c_op = Criterion{EarsPattern: "optional", Feature: "debug mode", System: "s", Action: "a"}
ASSERT c_op.Feature == "debug mode"
```

---

### TS-01-5: Subtask state enum and transitions

**Requirement:** 01-REQ-1.5
**Type:** unit
**Description:** Verify subtask state enum values and legal transitions.

**Preconditions:**
- None.

**Input:**
- Each of the six `SubtaskState` values.

**Expected:**
- `pending` → `[queued, dropped]`
- `queued` → `[in_progress, pending, dropped]`
- `in_progress` → `[done, pending_reevaluation]`
- `done` → `[pending_reevaluation]`
- `pending_reevaluation` → `[pending, dropped]`
- `dropped` → `[]` (terminal)

**Assertion pseudocode:**
```
ASSERT StatePending.LegalTransitions() == [StateQueued, StateDropped]
ASSERT StateQueued.LegalTransitions() == [StateInProgress, StatePending, StateDropped]
ASSERT StateInProgress.LegalTransitions() == [StateDone, StatePendingReevaluation]
ASSERT StateDone.LegalTransitions() == [StatePendingReevaluation]
ASSERT StatePendingReevaluation.LegalTransitions() == [StatePending, StateDropped]
ASSERT StateDropped.LegalTransitions() == []
```

---

### TS-01-6: Concurrent read safety

**Requirement:** 01-REQ-1.6
**Type:** integration
**Description:** Verify exported types can be read concurrently without data races.

**Preconditions:**
- A valid Spec loaded from testdata.

**Input:**
- Launch 100 goroutines, each reading fields from the same `*Spec`.

**Expected:**
- No race detector failures. All goroutines complete successfully.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
wg = WaitGroup{}
FOR i IN 0..99:
    wg.Add(1)
    GO func():
        _ = spec.PRD.Frontmatter.SpecID
        _ = spec.Requirements.Glossary
        _ = spec.TestSpec.TestCases
        _ = spec.Tasks.TaskGroups
        wg.Done()
wg.Wait()
// test passes if no race detector panic
```

---

### TS-01-7: Load valid spec from disk

**Requirement:** 01-REQ-2.1
**Type:** integration
**Description:** Verify LoadSpec reads all four files and returns populated Spec.

**Preconditions:**
- `testdata/valid_spec/` contains all four valid files.

**Input:**
- `dir = "testdata/valid_spec"`

**Expected:**
- Returned `*Spec` has non-nil PRD, Requirements, TestSpec, Tasks.
- `Spec.Dir` is the absolute path to the testdata directory.

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/valid_spec")
ASSERT err == nil
ASSERT spec.PRD != nil
ASSERT spec.Requirements != nil
ASSERT spec.TestSpec != nil
ASSERT spec.Tasks != nil
ASSERT spec.Dir ends with "testdata/valid_spec"
```

---

### TS-01-8: PRD frontmatter and body parsing

**Requirement:** 01-REQ-2.2
**Type:** unit
**Description:** Verify PRD parsing separates frontmatter from body and extracts Intent section.

**Preconditions:**
- A prd.md string with YAML frontmatter and a `## Intent` section.

**Input:**
```
---
spec_id: "01"
spec_name: "test"
...
---
# Test

## Intent

Build a test library.

## Goals

- Goal 1
```

**Expected:**
- `Frontmatter.SpecID == "01"`
- `Body` contains everything after the closing `---`
- Intent section body is `"Build a test library."` (trimmed).

**Assertion pseudocode:**
```
prd = ParsePRD(input_bytes)
ASSERT prd.Frontmatter.SpecID == "01"
ASSERT strings.Contains(prd.Body, "## Intent")
intent = ExtractIntent(prd.Body)
ASSERT strings.TrimSpace(intent) == "Build a test library."
```

---

### TS-01-9: JSON file loading with type preservation

**Requirement:** 01-REQ-2.3
**Type:** unit
**Description:** Verify JSON files unmarshal into typed structs preserving all values including nulls.

**Preconditions:**
- A requirements.json with a criterion having `return_contract: null`.

**Input:**
- JSON with `"return_contract": null` and `"return_contract": "list of items"`.

**Expected:**
- Null value: `ReturnContract == nil`
- String value: `*ReturnContract == "list of items"`

**Assertion pseudocode:**
```
req = UnmarshalStrict(json_bytes, &Requirements{})
ASSERT req.Requirements[0].AcceptanceCriteria[0].ReturnContract == nil
ASSERT *req.Requirements[0].AcceptanceCriteria[1].ReturnContract == "list of items"
```

---

### TS-01-10: Save all four files

**Requirement:** 01-REQ-3.1
**Type:** integration
**Description:** Verify SaveSpec writes all four files to the directory.

**Preconditions:**
- A valid in-memory `*Spec` and an existing empty temp directory.

**Input:**
- `spec` loaded from testdata, `dir` = temp directory.

**Expected:**
- Four files exist: `prd.md`, `requirements.json`, `test_spec.json`, `tasks.json`.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
tmpdir = TempDir()
err = SaveSpec(tmpdir, spec)
ASSERT err == nil
ASSERT FileExists(tmpdir + "/prd.md")
ASSERT FileExists(tmpdir + "/requirements.json")
ASSERT FileExists(tmpdir + "/test_spec.json")
ASSERT FileExists(tmpdir + "/tasks.json")
```

---

### TS-01-11: Deterministic JSON output

**Requirement:** 01-REQ-3.2
**Type:** unit
**Description:** Verify JSON output has sorted keys, 2-space indent, and trailing newline.

**Preconditions:**
- A Requirements struct with multiple fields.

**Input:**
- `Requirements{SpecID: "01", SpecName: "test", Introduction: "Intro", Glossary: {"b": "B", "a": "A"}}`

**Expected:**
- Keys in alphabetical order at all levels.
- 2-space indentation.
- File ends with `\n`.

**Assertion pseudocode:**
```
bytes = MarshalDeterministic(requirements)
ASSERT bytes ends with "}\n"
ASSERT indexOf(bytes, "\"$schema\"") < indexOf(bytes, "\"glossary\"")
ASSERT indexOf(bytes, "\"glossary\"") < indexOf(bytes, "\"introduction\"")
// within glossary object: "a" before "b"
ASSERT indexOf(bytes, "\"a\"") < indexOf(bytes, "\"b\"")
```

---

### TS-01-12: Deterministic YAML frontmatter field order

**Requirement:** 01-REQ-3.3
**Type:** unit
**Description:** Verify YAML frontmatter serializes with fixed field order.

**Preconditions:**
- A Frontmatter struct with all fields populated.

**Input:**
- Frontmatter with all 12 fields.

**Expected:**
- Fields appear in order: spec_id, spec_name, title, status, created_at, updated_at, owner, source, supersedes, tags, intent_hash, schema_version.

**Assertion pseudocode:**
```
bytes = SerializePRD(prd)
lines = split(bytes, "\n")
field_order = extract_yaml_keys(lines)
ASSERT field_order == ["spec_id", "spec_name", "title", "status", "created_at", "updated_at", "owner", "source", "supersedes", "tags", "intent_hash", "schema_version"]
```

---

### TS-01-13: Idempotent round-trip

**Requirement:** 01-REQ-3.4
**Type:** integration
**Description:** Verify load → save → load produces identical files and structures (except `updated_at` which is auto-set on save).

**Preconditions:**
- `testdata/valid_spec/` with all four files.

**Input:**
- Load from testdata, save to tmpdir, load from tmpdir.

**Expected:**
- JSON files (requirements.json, test_spec.json, tasks.json) in tmpdir are byte-identical to testdata.
- prd.md in tmpdir is identical to testdata except for the `updated_at` field.
- Second load produces deeply equal in-memory structures (ignoring `updated_at`).

**Assertion pseudocode:**
```
spec1 = LoadSpec("testdata/valid_spec")
tmpdir = TempDir()
SaveSpec(tmpdir, spec1)
spec2 = LoadSpec(tmpdir)
FOR file IN ["requirements.json", "test_spec.json", "tasks.json"]:
    ASSERT ReadFile(tmpdir + "/" + file) == ReadFile("testdata/valid_spec/" + file)
// prd.md: compare with updated_at masked out
prd1 = ReadFile("testdata/valid_spec/prd.md")
prd2 = ReadFile(tmpdir + "/prd.md")
ASSERT mask_updated_at(prd1) == mask_updated_at(prd2)
// In-memory: compare ignoring Dir and updated_at
ASSERT DeepEqual(spec1, spec2, ignoring Dir, ignoring Frontmatter.UpdatedAt)
```

---

### TS-01-14: Schema validation per JSON file

**Requirement:** 01-REQ-4.1
**Type:** unit
**Description:** Verify JSON files are validated against bundled schemas.

**Preconditions:**
- A valid requirements.json and an invalid one (missing required field).

**Input:**
- Valid JSON: passes schema.
- Invalid JSON: missing `spec_id` field.

**Expected:**
- Valid: no errors.
- Invalid: error with file "requirements.json" and path to missing field.

**Assertion pseudocode:**
```
valid_spec = LoadSpec("testdata/valid_spec")
errs = ValidateSchema(valid_spec)
ASSERT len(errs) == 0

invalid_spec = /* spec with missing spec_id in requirements */
errs = ValidateSchema(invalid_spec)
ASSERT len(errs) > 0
ASSERT errs[0].File == "requirements.json"
```

---

### TS-01-15: PRD frontmatter schema validation

**Requirement:** 01-REQ-4.2
**Type:** unit
**Description:** Verify YAML frontmatter is validated against prd-frontmatter schema.

**Preconditions:**
- A PRD with valid frontmatter and one with invalid status value.

**Input:**
- Valid: `status: "draft"`.
- Invalid: `status: "invalid_status"`.

**Expected:**
- Valid: no errors.
- Invalid: error on `status` field.

**Assertion pseudocode:**
```
valid_prd = ParsePRD(valid_prd_bytes)
errs = validateFrontmatter(valid_prd.Frontmatter)
ASSERT len(errs) == 0

invalid_prd = ParsePRD(invalid_prd_bytes)
errs = validateFrontmatter(invalid_prd.Frontmatter)
ASSERT len(errs) > 0
ASSERT errs[0].File == "prd.md"
ASSERT contains(errs[0].Message, "status")
```

---

### TS-01-16: Embedded JSON schemas

**Requirement:** 01-REQ-4.3
**Type:** unit
**Description:** Verify four JSON Schema files are embedded and accessible.

**Preconditions:**
- None.

**Input:**
- Read each embedded schema.

**Expected:**
- Four schemas exist: requirements.v1.json, test_spec.v1.json, tasks.v1.json, prd-frontmatter.v1.json.
- Each is valid JSON.
- Each contains `"$schema"` or schema metadata.

**Assertion pseudocode:**
```
schemas = GetEmbeddedSchemas()
ASSERT len(schemas) == 4
FOR name IN ["requirements.v1.json", "test_spec.v1.json", "tasks.v1.json", "prd-frontmatter.v1.json"]:
    data = schemas[name]
    ASSERT len(data) > 0
    ASSERT json.Valid(data)
```

---

### TS-01-17: Schema validation returns all errors

**Requirement:** 01-REQ-4.4
**Type:** unit
**Description:** Verify schema validation collects all errors, not just the first.

**Preconditions:**
- A requirements.json with multiple schema violations.

**Input:**
- JSON missing `spec_id`, `spec_name`, and having invalid `schema_version` type.

**Expected:**
- At least 3 errors returned, each with file, path, and description.

**Assertion pseudocode:**
```
spec = /* spec with 3+ schema violations */
errs = ValidateSchema(spec)
ASSERT len(errs) >= 3
FOR err IN errs:
    ASSERT err.File != ""
    ASSERT err.Message != ""
```

---

### TS-01-18: Cross-file validation — all seven rules

**Requirement:** 01-REQ-5.1
**Type:** integration
**Description:** Verify cross-file validation runs all seven integrity rules.

**Preconditions:**
- A spec that passes schema validation but has cross-file violations.

**Input:**
- Spec where test_spec references a non-existent requirement_id, a requirement has no test case, etc.

**Expected:**
- Errors returned referencing rules 1-7 as applicable.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/crossfile_errors")
errs = ValidateCrossFile(spec)
ASSERT len(errs) > 0
rules_found = {err.Rule for err in errs}
ASSERT "integrity-1" IN rules_found OR "integrity-2" IN rules_found  // at least some rules triggered
```

---

### TS-01-19: Requirement ID references exist (rule 1)

**Requirement:** 01-REQ-5.2
**Type:** unit
**Description:** Verify every requirement_id in test_spec, tasks traceability, and error_handling resolves.

**Preconditions:**
- A spec where test_spec references "01-REQ-99.1" which doesn't exist.

**Input:**
- Spec with dangling reference in test_spec.json.

**Expected:**
- Validation error with rule "integrity-1" naming the dangling ID.

**Assertion pseudocode:**
```
spec = /* test_spec references "01-REQ-99.1" not in requirements */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-1" AND contains(err.Message, "01-REQ-99.1") for err in errs)
```

---

### TS-01-20: Requirement test coverage (rule 2)

**Requirement:** 01-REQ-5.3
**Type:** unit
**Description:** Verify every acceptance criterion and edge case has a test case.

**Preconditions:**
- A spec with a requirement missing its test case in test_spec.json.

**Input:**
- Requirement "01-REQ-1.1" exists but no TestCase with `requirement_id: "01-REQ-1.1"`.

**Expected:**
- Validation error with rule "integrity-2" naming the uncovered criterion.

**Assertion pseudocode:**
```
spec = /* requirement 01-REQ-1.1 has no test case */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-2" AND contains(err.Message, "01-REQ-1.1") for err in errs)
```

---

### TS-01-21: Property and path test coverage (rules 3-4)

**Requirement:** 01-REQ-5.4
**Type:** unit
**Description:** Verify every correctness property has a property test and every path has a smoke test.

**Preconditions:**
- A spec with a correctness property missing its property test and a path missing its smoke test.

**Input:**
- Property "01-PROP-1" has no TS-01-P1 entry. Path "01-PATH-1" has no TS-01-SMOKE-1 entry.

**Expected:**
- Two errors: rule "integrity-3" for property, rule "integrity-4" for path.

**Assertion pseudocode:**
```
spec = /* property and path without tests */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-3" for err in errs)
ASSERT any(err.Rule == "integrity-4" for err in errs)
```

---

### TS-01-22: Test spec ID references (rule 5)

**Requirement:** 01-REQ-5.5
**Type:** unit
**Description:** Verify every test_spec_id in tasks.json exists in test_spec.json.

**Preconditions:**
- A spec where tasks.json references "TS-01-99" which doesn't exist in test_spec.json.

**Input:**
- Tasks traceability entry with `test_spec_id: "TS-01-99"`.

**Expected:**
- Validation error with rule "integrity-5" naming "TS-01-99".

**Assertion pseudocode:**
```
spec = /* tasks references TS-01-99 not in test_spec */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-5" AND contains(err.Message, "TS-01-99") for err in errs)
```

---

### TS-01-23: Glossary cross-check (rule 6)

**Requirement:** 01-REQ-5.6
**Type:** unit
**Description:** Verify backtick-wrapped terms in checked fields have glossary entries.

**Preconditions:**
- A requirement with `` `SpaceManager` `` in its action field but no glossary entry for "SpaceManager".

**Input:**
- Criterion action: ``"create a `SpaceManager` instance"``. Glossary: empty.

**Expected:**
- Validation error with rule "integrity-6" naming "SpaceManager".

**Assertion pseudocode:**
```
spec = /* action references `SpaceManager` not in glossary */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-6" AND contains(err.Message, "SpaceManager") for err in errs)
```

---

### TS-01-24: Spec ID/name consistency (rule 7)

**Requirement:** 01-REQ-5.7
**Type:** unit
**Description:** Verify spec_id and spec_name match across all four files.

**Preconditions:**
- A spec where requirements.json has `spec_id: "02"` but prd.md has `spec_id: "01"`.

**Input:**
- Mismatched spec_id between files.

**Expected:**
- Validation error with rule "integrity-7".

**Assertion pseudocode:**
```
spec = /* requirements.json spec_id "02", prd.md spec_id "01" */
errs = ValidateCrossFile(spec)
ASSERT any(err.Rule == "integrity-7" for err in errs)
```

---

### TS-01-25: Per-file render determinism

**Requirement:** 01-REQ-6.1
**Type:** unit
**Description:** Verify rendering the same artifact twice produces byte-identical output.

**Preconditions:**
- A populated Requirements struct.

**Input:**
- Same `*Requirements` rendered twice.

**Expected:**
- Two byte slices are identical.

**Assertion pseudocode:**
```
req = /* populated requirements */
out1 = RenderRequirements(req)
out2 = RenderRequirements(req)
ASSERT bytes.Equal(out1, out2)
```

---

### TS-01-26: EARS template rendering

**Requirement:** 01-REQ-6.2
**Type:** unit
**Description:** Verify all six EARS templates render correctly.

**Preconditions:**
- One criterion per EARS pattern.

**Input:**
- Ubiquitous: system="the system", action="do X"
- Event-driven: trigger="user clicks", system="the system", action="respond"
- Complex-event: trigger="t", condition="c", system="s", action="a"
- State-driven: state="active", system="s", action="a"
- Unwanted: error_condition="disk full", system="s", action="alert"
- Optional: feature="debug mode", system="s", action="log"

**Expected:**
- "THE the system SHALL do X"
- "WHEN user clicks, THE the system SHALL respond"
- "WHEN t AND c, THE s SHALL a"
- "WHILE active, THE s SHALL a"
- "IF disk full, THEN THE s SHALL alert"
- "WHERE debug mode, THE s SHALL log"

**Assertion pseudocode:**
```
ASSERT RenderEARS(ubiquitous_criterion) == "THE the system SHALL do X"
ASSERT RenderEARS(event_driven_criterion) == "WHEN user clicks, THE the system SHALL respond"
// ... (all six patterns)
```

---

### TS-01-27: Per-file render API

**Requirement:** 01-REQ-6.3
**Type:** unit
**Description:** Verify per-file rendering works for each JSON artifact type.

**Preconditions:**
- Populated Requirements, TestSpecDoc, Tasks structs.

**Input:**
- Each struct individually.

**Expected:**
- Each returns non-empty `[]byte` containing valid markdown.

**Assertion pseudocode:**
```
md_req = RenderRequirements(requirements)
ASSERT len(md_req) > 0
ASSERT contains(string(md_req), "# Requirements")

md_ts = RenderTestSpec(testspec)
ASSERT len(md_ts) > 0

md_tasks = RenderTasks(tasks)
ASSERT len(md_tasks) > 0
```

---

### TS-01-28: Combined render includes PRD verbatim

**Requirement:** 01-REQ-6.4
**Type:** integration
**Description:** Verify combined rendering includes PRD as-is followed by rendered JSON artifacts.

**Preconditions:**
- A complete valid spec.

**Input:**
- A `*Spec` with PRD body containing `"## Intent\n\nBuild a test."`.

**Expected:**
- Output starts with the PRD body (verbatim).
- Output contains rendered requirements section after PRD.
- Sections appear in order: PRD, requirements, test_spec, tasks.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
combined = RenderCombined(spec)
prd_end = indexOf(combined, spec.PRD.Body) + len(spec.PRD.Body)
ASSERT prd_end > 0  // PRD is present
req_start = indexOf(combined, "# Requirements")
ASSERT req_start > prd_end  // requirements after PRD
ts_start = indexOf(combined, "# Test Specification")
ASSERT ts_start > req_start
tasks_start = indexOf(combined, "# Implementation Plan")
ASSERT tasks_start > ts_start
```

---

### TS-01-29: Lifecycle transition graph enforcement

**Requirement:** 01-REQ-7.1
**Type:** unit
**Description:** Verify only legal lifecycle transitions are allowed.

**Preconditions:**
- Specs in each lifecycle state.

**Input:**
- All possible (current, target) pairs.

**Expected:**
- Legal: (draft,active), (draft,archived), (active,sealed), (sealed,superseded), (sealed,archived) → succeed.
- Illegal: all other pairs → error.

**Assertion pseudocode:**
```
legal = [(draft,active), (draft,archived), (active,sealed), (sealed,superseded), (sealed,archived)]
FOR (current, target) IN all_pairs:
    spec = make_spec_with_status(current)
    result, err = Transition(spec, target)
    IF (current, target) IN legal:
        ASSERT err == nil
        ASSERT result.PRD.Frontmatter.Status == target
    ELSE:
        ASSERT err != nil
```

---

### TS-01-30: Intent hash computation at draft→active

**Requirement:** 01-REQ-7.2
**Type:** unit
**Description:** Verify intent hash is computed and stored during draft→active transition.

**Preconditions:**
- A spec in draft state with an Intent section.

**Input:**
- Draft spec with `## Intent` body "Build a test library."

**Expected:**
- After transition, `IntentHash` is non-nil.
- Hash matches SHA-256 of normalized intent body.

**Assertion pseudocode:**
```
spec = make_draft_spec(intent_body="Build a test library.")
active_spec, err = Transition(spec, StatusActive)
ASSERT err == nil
ASSERT active_spec.PRD.Frontmatter.IntentHash != nil
expected_hash = sha256(normalize("Build a test library."))
ASSERT *active_spec.PRD.Frontmatter.IntentHash == expected_hash
```

---

### TS-01-31: Active state mutation guard

**Requirement:** 01-REQ-7.3
**Type:** unit
**Description:** Verify active state rejects Intent and immutable field mutations.

**Preconditions:**
- A spec in active state.

**Input:**
- Attempt to change Intent body, created_at, spec_id, spec_name.

**Expected:**
- Each mutation attempt returns an error identifying the rejected field.

**Assertion pseudocode:**
```
spec = make_active_spec()
// Modify intent
modified = copy(spec)
modified.PRD.Body = replace_intent(modified.PRD.Body, "New intent")
err = SaveSpec(tmpdir, modified)  // or lifecycle check
ASSERT err != nil AND contains(err.Message, "Intent")
```

---

### TS-01-32: Sealed/superseded/archived reject all mutations

**Requirement:** 01-REQ-7.4
**Type:** unit
**Description:** Verify sealed, superseded, and archived specs reject all mutations.

**Preconditions:**
- Specs in sealed, superseded, and archived states.

**Input:**
- Attempt to modify any field on each.

**Expected:**
- Error returned identifying the state as immutable.

**Assertion pseudocode:**
```
FOR state IN [StatusSealed, StatusSuperseded, StatusArchived]:
    spec = make_spec_with_status(state)
    modified = copy(spec)
    modified.PRD.Frontmatter.Title = "Changed"
    // attempt to validate mutation
    ASSERT lifecycle_check returns error with state name
```

---

### TS-01-33: Deprecation banner on supersede

**Requirement:** 01-REQ-7.5
**Type:** integration
**Description:** Verify transitioning to superseded adds deprecation banner.

**Preconditions:**
- A sealed spec and a new spec that supersedes it.

**Input:**
- Transition sealed spec to superseded.

**Expected:**
- All four files in the superseded spec folder contain a deprecation banner.

**Assertion pseudocode:**
```
spec = make_sealed_spec(dir=tmpdir)
superseded_spec, err = Transition(spec, StatusSuperseded)
ASSERT err == nil
FOR file IN ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]:
    content = ReadFile(tmpdir + "/" + file)
    ASSERT contains(content, "SUPERSEDED")
```

---

### TS-01-34: BootstrapSpec API creation

**Requirement:** 01-REQ-8.1
**Type:** integration
**Description:** Verify BootstrapSpec creates a folder and returns a handle.

**Preconditions:**
- A temp directory exists.

**Input:**
- `NewBootstrap(tmpdir + "/05_my_feature", "05", "my_feature")`

**Expected:**
- Directory `05_my_feature/` created.
- Bootstrap handle returned.

**Assertion pseudocode:**
```
bs, err = NewBootstrap(tmpdir + "/05_my_feature", "05", "my_feature")
ASSERT err == nil
ASSERT bs != nil
ASSERT DirExists(tmpdir + "/05_my_feature")
```

---

### TS-01-35: Bootstrap defers cross-file validation

**Requirement:** 01-REQ-8.2
**Type:** integration
**Description:** Verify bootstrap allows writing single files without cross-file errors.

**Preconditions:**
- Bootstrap handle created.

**Input:**
- Write only prd.md (no other files).

**Expected:**
- Schema validation runs on prd.md (per-file).
- No cross-file errors raised.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
err = bs.WritePRD(valid_prd)
ASSERT err == nil  // no cross-file validation yet
ASSERT FileExists(bs.dir + "/prd.md")
ASSERT NOT FileExists(bs.dir + "/requirements.json")
```

---

### TS-01-36: Bootstrap Finalize runs full validation

**Requirement:** 01-REQ-8.3
**Type:** integration
**Description:** Verify Finalize runs complete validation and returns Spec on success.

**Preconditions:**
- Bootstrap with all four valid files written.

**Input:**
- Write all four files, then call Finalize().

**Expected:**
- Returns `*Spec` with all four artifacts populated.
- No errors.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
bs.WritePRD(valid_prd)
bs.WriteRequirements(valid_req)
bs.WriteTestSpec(valid_ts)
bs.WriteTasks(valid_tasks)
spec, err = bs.Finalize()
ASSERT err == nil
ASSERT spec.PRD != nil
ASSERT spec.Requirements != nil
ASSERT spec.TestSpec != nil
ASSERT spec.Tasks != nil
```

---

### TS-01-37: Bootstrap write files independently

**Requirement:** 01-REQ-8.4
**Type:** integration
**Description:** Verify files can be written in any order during bootstrap.

**Preconditions:**
- Bootstrap handle.

**Input:**
- Write tasks.json first, then requirements.json, then test_spec.json, then prd.md.

**Expected:**
- No errors during writes.
- Finalize succeeds.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
ASSERT bs.WriteTasks(tasks) == nil
ASSERT bs.WriteRequirements(req) == nil
ASSERT bs.WriteTestSpec(ts) == nil
ASSERT bs.WritePRD(prd) == nil
spec, err = bs.Finalize()
ASSERT err == nil
```

---

### TS-01-38: Discover specs in root directory

**Requirement:** 01-REQ-9.1
**Type:** integration
**Description:** Verify DiscoverSpecs finds directories matching the naming pattern.

**Preconditions:**
- Temp root with `01_feature_a/`, `02_feature_b/`, `not_a_spec/`, `archive/`.

**Input:**
- `DiscoverSpecs(root)`

**Expected:**
- Exactly 2 entries: spec_id "01" and "02".
- `not_a_spec` excluded.

**Assertion pseudocode:**
```
// setup: create 01_feature_a/ and 02_feature_b/ with prd.md, plus not_a_spec/ and archive/
result, err = DiscoverSpecs(root)
ASSERT err == nil
ASSERT len(result.Entries) == 2
ids = {e.SpecID for e in result.Entries}
ASSERT "01" IN ids
ASSERT "02" IN ids
```

---

### TS-01-39: Discovery skips archive

**Requirement:** 01-REQ-9.2
**Type:** integration
**Description:** Verify archive/ directory is excluded from discovery.

**Preconditions:**
- Root with `01_active/` and `archive/03_old/`.

**Input:**
- `DiscoverSpecs(root)`

**Expected:**
- Only `01_active` returned. `03_old` in archive excluded.

**Assertion pseudocode:**
```
result, err = DiscoverSpecs(root)
ASSERT len(result.Entries) == 1
ASSERT result.Entries[0].SpecID == "01"
```

---

### TS-01-40: Discovery loads metadata from frontmatter

**Requirement:** 01-REQ-9.3
**Type:** integration
**Description:** Verify discovery loads spec_id, spec_name, status from PRD frontmatter only.

**Preconditions:**
- Root with spec folders containing prd.md with frontmatter.

**Input:**
- `DiscoverSpecs(root)` on root with spec whose PRD has `status: "active"`.

**Expected:**
- Entry has `Status == StatusActive`.
- Requirements, TestSpec, Tasks are NOT loaded (metadata-only).

**Assertion pseudocode:**
```
result, err = DiscoverSpecs(root)
entry = result.Entries[0]
ASSERT entry.SpecID == "01"
ASSERT entry.SpecName == "feature_a"
ASSERT entry.Status == StatusActive
```

---

### TS-01-41: Discovery builds dependency graph

**Requirement:** 01-REQ-9.4
**Type:** integration
**Description:** Verify dependency graph is built from tasks.json declarations.

**Preconditions:**
- Root with two specs: 01 has no dependencies, 02 depends on 01.

**Input:**
- `DiscoverSpecs(root)` where 02's tasks.json has `depends_on_spec: "01"`.

**Expected:**
- Graph has edge "02" → "01".
- TopologicalOrder returns ["01", "02"].

**Assertion pseudocode:**
```
result, err = DiscoverSpecs(root)
ASSERT result.Graph != nil
ASSERT "01" IN result.Graph.Edges["02"]
order, err = result.Graph.TopologicalOrder()
ASSERT err == nil
ASSERT indexOf(order, "01") < indexOf(order, "02")
```

---

### TS-01-42: Discovery defaults to current directory

**Requirement:** 01-REQ-9.5
**Type:** integration
**Description:** Verify empty root defaults to current working directory.

**Preconditions:**
- Current directory contains spec folders.

**Input:**
- `DiscoverSpecs("")`

**Expected:**
- Discovers specs in cwd.

**Assertion pseudocode:**
```
os.Chdir(root_with_specs)
result, err = DiscoverSpecs("")
ASSERT err == nil
ASSERT len(result.Entries) > 0
```

---

### TS-01-43: ID format validation — all patterns

**Requirement:** 01-REQ-10.1
**Type:** unit
**Description:** Verify all ID formats from Appendix A are validated.

**Preconditions:**
- A spec with correctly and incorrectly formatted IDs.

**Input:**
- Valid: `"01-REQ-1"`, `"01-REQ-1.1"`, `"01-REQ-1.E1"`, `"01-PROP-1"`, `"01-PATH-1"`, `"01-ERR-1"`, `"TS-01-1"`, `"TS-01-P1"`, `"TS-01-E1"`, `"TS-01-SMOKE-1"`, `"1.1"`, `"1.V"`.
- Invalid: `"REQ-1"` (missing spec_id), `"01-REQ-"` (missing N), `"TS01-1"` (missing dash).

**Expected:**
- Valid IDs pass.
- Invalid IDs produce validation errors.

**Assertion pseudocode:**
```
valid_spec = /* spec with all valid IDs */
errs = ValidateIDs(valid_spec)
ASSERT len(filter(errs, severity=error)) == 0

invalid_spec = /* spec with malformed IDs */
errs = ValidateIDs(invalid_spec)
ASSERT len(errs) > 0
```

---

### TS-01-44: ID spec_id component matching

**Requirement:** 01-REQ-10.2
**Type:** unit
**Description:** Verify embedded spec_id in IDs matches file's declared spec_id.

**Preconditions:**
- A spec where spec_id is "01" but a requirement ID is "02-REQ-1".

**Input:**
- Mismatched ID.

**Expected:**
- Validation error identifying the mismatched ID.

**Assertion pseudocode:**
```
spec = /* requirements.json spec_id "01", but requirement id "02-REQ-1" */
errs = ValidateIDs(spec)
ASSERT any(contains(err.Message, "02-REQ-1") AND contains(err.Message, "01") for err in errs)
```

---

### TS-01-45: ID numeric components are positive

**Requirement:** 01-REQ-10.3
**Type:** unit
**Description:** Verify N and C in IDs are positive integers.

**Preconditions:**
- A spec with ID `"01-REQ-0"` (zero) and `"01-REQ--1"` (negative).

**Input:**
- IDs with zero and negative numeric components.

**Expected:**
- Validation errors for each.

**Assertion pseudocode:**
```
spec = /* requirement id "01-REQ-0" */
errs = ValidateIDs(spec)
ASSERT any(contains(err.Message, "positive") for err in errs)
```

---

### TS-01-46: Auto-update updated_at on save

**Requirement:** 01-REQ-3.5
**Type:** integration
**Description:** Verify SaveSpec sets the `updated_at` frontmatter field to the current UTC timestamp.

**Preconditions:**
- A valid in-memory `*Spec` with a known `updated_at` value (e.g., "2020-01-01T00:00:00Z").

**Input:**
- Save the spec to a temp directory.

**Expected:**
- The written prd.md has `updated_at` set to a timestamp close to `time.Now().UTC()` (within 5 seconds).
- The original in-memory spec's `updated_at` is NOT modified (save returns/uses a copy).

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
old_updated_at = spec.PRD.Frontmatter.UpdatedAt
before = time.Now().UTC()
tmpdir = TempDir()
SaveSpec(tmpdir, spec)
after = time.Now().UTC()
saved_spec = LoadSpec(tmpdir)
new_updated_at = parseISO8601(saved_spec.PRD.Frontmatter.UpdatedAt)
ASSERT new_updated_at >= before
ASSERT new_updated_at <= after
ASSERT new_updated_at != parseISO8601(old_updated_at) // unless test runs at exact same second
```

---

### TS-01-47: Auto-compute coverage on save

**Requirement:** 01-REQ-3.6
**Type:** integration
**Description:** Verify SaveSpec computes the `coverage` field in test_spec.json from requirements and test data.

**Preconditions:**
- A valid spec where requirements have IDs "01-REQ-1.1", "01-REQ-1.E1", and test_spec has test cases covering only "01-REQ-1.1" but not "01-REQ-1.E1".

**Input:**
- Save the spec to a temp directory.

**Expected:**
- The written test_spec.json has `coverage.requirements_covered` containing "01-REQ-1.1".
- `coverage.gaps` contains "01-REQ-1.E1".
- `coverage.requirements_covered` + `coverage.gaps` == all criterion/edge case IDs in requirements.

**Assertion pseudocode:**
```
spec = make_spec_with_partial_coverage()
tmpdir = TempDir()
SaveSpec(tmpdir, spec)
saved = LoadSpec(tmpdir)
ASSERT "01-REQ-1.1" IN saved.TestSpec.Coverage.RequirementsCovered
ASSERT "01-REQ-1.E1" IN saved.TestSpec.Coverage.Gaps
all_ids = get_all_criterion_ids(spec.Requirements)
ASSERT set(saved.TestSpec.Coverage.RequirementsCovered) | set(saved.TestSpec.Coverage.Gaps) == set(all_ids)
```

---

## Property Test Cases

### TS-01-P1: Round-trip idempotency

**Property:** Property 1 from design.md
**Validates:** 01-REQ-3.4
**Type:** property
**Description:** Loading a valid spec, saving, and reloading produces identical results (except `updated_at` which is auto-set on every save).

**For any:** valid spec fixture from testdata (iterate all golden files)
**Invariant:** LoadSpec(dir) → SaveSpec(tmpdir) → LoadSpec(tmpdir) produces DeepEqual Spec (ignoring `updated_at`) and byte-identical JSON files. prd.md is identical except for `updated_at`.

**Assertion pseudocode:**
```
FOR ANY fixture IN testdata/valid_specs:
    spec1 = LoadSpec(fixture)
    tmpdir = TempDir()
    SaveSpec(tmpdir, spec1)
    spec2 = LoadSpec(tmpdir)
    ASSERT DeepEqual(spec1, spec2, ignoring Dir, ignoring Frontmatter.UpdatedAt)
    FOR file IN ["requirements.json", "test_spec.json", "tasks.json"]:
        ASSERT ReadFile(fixture/file) == ReadFile(tmpdir/file)
    ASSERT mask_updated_at(ReadFile(fixture/"prd.md")) == mask_updated_at(ReadFile(tmpdir/"prd.md"))
```

---

### TS-01-P2: EARS rendering determinism

**Property:** Property 2 from design.md
**Validates:** 01-REQ-6.1, 01-REQ-6.2
**Type:** property
**Description:** Rendering the same criterion always produces identical output.

**For any:** criterion generated with random valid fields for each EARS pattern
**Invariant:** RenderEARS(c) == RenderEARS(c) for all valid criteria c.

**Assertion pseudocode:**
```
FOR ANY criterion IN generate_valid_criteria():
    r1 = RenderEARS(criterion)
    r2 = RenderEARS(criterion)
    ASSERT r1 == r2
```

---

### TS-01-P3: Lifecycle monotonicity

**Property:** Property 3 from design.md
**Validates:** 01-REQ-7.1, 01-REQ-7.E1
**Type:** property
**Description:** Sequential transitions never move backward in the lifecycle graph.

**For any:** sequence of (state, target) transition attempts starting from draft
**Invariant:** Successful transitions only advance through draft→active→sealed→{superseded,archived} or draft→archived. No backward moves.

**Assertion pseudocode:**
```
state_order = {draft: 0, active: 1, sealed: 2, superseded: 3, archived: 3}
FOR ANY transitions IN generate_transition_sequences():
    current = draft
    FOR target IN transitions:
        result, err = Transition(make_spec(current), target)
        IF err == nil:
            ASSERT state_order[target] > state_order[current]
            current = target
```

---

### TS-01-P4: Cross-file referential integrity

**Property:** Property 4 from design.md
**Validates:** 01-REQ-5.1, 01-REQ-5.2, 01-REQ-5.3, 01-REQ-5.4, 01-REQ-5.5
**Type:** property
**Description:** A spec passing cross-file validation has no dangling references.

**For any:** spec that passes ValidateCrossFile with zero errors
**Invariant:** Every requirement_id in test_spec exists in requirements, and every requirement has test coverage.

**Assertion pseudocode:**
```
FOR ANY spec IN valid_specs:
    errs = ValidateCrossFile(spec)
    IF len(errs) == 0:
        FOR tc IN spec.TestSpec.TestCases:
            ASSERT tc.RequirementID exists in spec.Requirements (all criteria IDs)
        FOR req IN spec.Requirements:
            FOR ac IN req.AcceptanceCriteria:
                ASSERT ac.ID has a corresponding TestCase
```

---

### TS-01-P5: Intent hash stability

**Property:** Property 5 from design.md
**Validates:** 01-REQ-7.2, 01-REQ-7.E2
**Type:** property
**Description:** Intent hash is deterministic and detects changes.

**For any:** intent body string
**Invariant:** ComputeIntentHash(body) is deterministic; changing any character in body changes the hash.

**Assertion pseudocode:**
```
FOR ANY body IN generate_intent_bodies():
    h1 = ComputeIntentHash(body)
    h2 = ComputeIntentHash(body)
    ASSERT h1 == h2  // deterministic
    
    modified = body + " extra"
    h3 = ComputeIntentHash(modified)
    ASSERT h3 != h1  // detects change
```

---

### TS-01-P6: Schema validation soundness

**Property:** Property 6 from design.md
**Validates:** 01-REQ-4.1, 01-REQ-4.2, 01-REQ-4.4, 01-REQ-4.E1, 01-REQ-4.E2
**Type:** property
**Description:** Schema validation rejects structurally invalid data.

**For any:** JSON with a randomly removed required field or added unknown field
**Invariant:** ValidateSchema returns at least one error.

**Assertion pseudocode:**
```
FOR ANY mutation IN [remove_required_field, add_unknown_field, wrong_type]:
    invalid_json = apply_mutation(valid_json)
    spec = parse(invalid_json)
    errs = ValidateSchema(spec)
    ASSERT len(errs) > 0
```

---

### TS-01-P7: Discovery completeness

**Property:** Property 7 from design.md
**Validates:** 01-REQ-9.1, 01-REQ-9.2, 01-REQ-9.3
**Type:** property
**Description:** Discovery finds all valid spec dirs, skips archive.

**For any:** set of directories with N matching pattern and M in archive
**Invariant:** DiscoverSpecs returns exactly N entries.

**Assertion pseudocode:**
```
FOR ANY (n_specs, n_archived, n_invalid) IN generate_dir_configs():
    root = create_temp_root(n_specs, n_archived, n_invalid)
    result = DiscoverSpecs(root)
    ASSERT len(result.Entries) == n_specs
```

---

### TS-01-P8: Bootstrap deferred validation

**Property:** Property 8 from design.md
**Validates:** 01-REQ-8.2, 01-REQ-8.4, 01-REQ-5.E1
**Type:** property
**Description:** No cross-file errors during bootstrap until Finalize.

**For any:** subset of files written during bootstrap (1 to 3 files)
**Invariant:** Writing any file individually succeeds without cross-file errors.

**Assertion pseudocode:**
```
FOR ANY file_subset IN subsets_of([prd, req, ts, tasks], size=1..3):
    bs = NewBootstrap(...)
    FOR file IN file_subset:
        err = bs.WriteFile(file)
        ASSERT err == nil  // no cross-file validation
```

---

### TS-01-P9: ID format consistency

**Property:** Property 9 from design.md
**Validates:** 01-REQ-10.1, 01-REQ-10.2, 01-REQ-10.3, 01-REQ-10.E1
**Type:** property
**Description:** Valid IDs parse to correct components.

**For any:** valid ID string matching any Appendix A pattern
**Invariant:** Parsing extracts the correct spec_id, entity type, and numeric components.

**Assertion pseudocode:**
```
FOR ANY id IN generate_valid_ids():
    parsed = ParseID(id)
    ASSERT parsed.SpecID matches the spec_id portion
    ASSERT parsed.N > 0
    reconstructed = FormatID(parsed)
    ASSERT reconstructed == id  // round-trip
```

---

### TS-01-P10: Null preservation

**Property:** Property 10 from design.md
**Validates:** 01-REQ-1.E1, 01-REQ-3.4
**Type:** property
**Description:** Null fields survive round-trip serialization.

**For any:** criterion with return_contract set to null or non-null
**Invariant:** Marshal → Unmarshal preserves null vs non-null distinction.

**Assertion pseudocode:**
```
FOR ANY rc IN [nil, ptr("value")]:
    c = Criterion{ReturnContract: rc, ...}
    json_bytes = MarshalDeterministic(c)
    c2 = UnmarshalStrict(json_bytes)
    IF rc == nil:
        ASSERT c2.ReturnContract == nil
        ASSERT contains(json_bytes, "\"return_contract\": null")
    ELSE:
        ASSERT *c2.ReturnContract == *rc
```

---

### TS-01-P11: Computed coverage accuracy

**Property:** Property 11 from design.md
**Validates:** 01-REQ-3.6
**Type:** property
**Description:** Coverage field accurately reflects test-to-requirement mapping.

**For any:** spec with a random subset of requirements covered by test cases
**Invariant:** After save, `requirements_covered` lists exactly the IDs with test cases, `gaps` lists exactly the IDs without, and their union equals all criterion/edge case IDs.

**Assertion pseudocode:**
```
FOR ANY (requirements, test_cases) IN generate_coverage_scenarios():
    spec = build_spec(requirements, test_cases)
    tmpdir = TempDir()
    SaveSpec(tmpdir, spec)
    saved = LoadSpec(tmpdir)
    covered = set(saved.TestSpec.Coverage.RequirementsCovered)
    gaps = set(saved.TestSpec.Coverage.Gaps)
    all_ids = set(get_all_criterion_ids(spec.Requirements))
    ASSERT covered | gaps == all_ids
    ASSERT covered & gaps == {} // no overlap
    FOR tc IN test_cases:
        ASSERT tc.RequirementID IN covered
```

---

## Edge Case Tests

### TS-01-E1: Null JSON field representation

**Requirement:** 01-REQ-1.E1
**Type:** unit
**Description:** Null fields serialize as JSON null, not omitted.

**Preconditions:**
- Criterion with `return_contract: null`.

**Input:**
- `Criterion{ReturnContract: nil}`

**Expected:**
- JSON contains `"return_contract": null` (not missing).

**Assertion pseudocode:**
```
c = Criterion{ID: "01-REQ-1.1", EarsPattern: "ubiquitous", System: "s", Action: "a", ReturnContract: nil}
bytes = MarshalDeterministic(c)
ASSERT contains(string(bytes), "\"return_contract\": null")
ASSERT NOT contains(string(bytes), "\"return_contract\": \"\"")
```

---

### TS-01-E2: Empty array serialization

**Requirement:** 01-REQ-1.E2
**Type:** unit
**Description:** Empty slices serialize as [] not null.

**Preconditions:**
- Requirement with empty `edge_cases` slice.

**Input:**
- `Requirement{EdgeCases: []Criterion{}}`

**Expected:**
- JSON contains `"edge_cases": []`.

**Assertion pseudocode:**
```
req = Requirement{ID: "01-REQ-1", EdgeCases: []Criterion{}}
bytes = MarshalDeterministic(req)
ASSERT contains(string(bytes), "\"edge_cases\": []")
```

---

### TS-01-E3: Missing files in spec folder

**Requirement:** 01-REQ-2.E1
**Type:** unit
**Description:** LoadSpec returns error listing missing files.

**Preconditions:**
- Directory with only `prd.md` (missing 3 files).

**Input:**
- `LoadSpec(dir_with_only_prd)`

**Expected:**
- Error mentioning `requirements.json`, `test_spec.json`, `tasks.json`.

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/incomplete_spec")
ASSERT err != nil
ASSERT contains(err.Error(), "requirements.json")
ASSERT contains(err.Error(), "test_spec.json")
ASSERT contains(err.Error(), "tasks.json")
```

---

### TS-01-E4: Malformed JSON file

**Requirement:** 01-REQ-2.E2
**Type:** unit
**Description:** LoadSpec returns parse error for malformed JSON.

**Preconditions:**
- Spec folder where requirements.json has invalid JSON (missing closing brace).

**Input:**
- `LoadSpec(dir_with_bad_json)`

**Expected:**
- Error mentioning "requirements.json" and parse failure.

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/malformed_json")
ASSERT err != nil
ASSERT contains(err.Error(), "requirements.json")
```

---

### TS-01-E5: Malformed YAML frontmatter

**Requirement:** 01-REQ-2.E3
**Type:** unit
**Description:** LoadSpec returns parse error for bad YAML.

**Preconditions:**
- prd.md with invalid YAML between `---` delimiters.

**Input:**
- prd.md content: `---\nspec_id: [invalid\n---\n# Title`

**Expected:**
- Parse error mentioning YAML/frontmatter.

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/bad_yaml")
ASSERT err != nil
ASSERT contains(err.Error(), "frontmatter") OR contains(err.Error(), "yaml")
```

---

### TS-01-E6: Missing Intent section

**Requirement:** 01-REQ-2.E4
**Type:** unit
**Description:** LoadSpec returns error when prd.md has no ## Intent section.

**Preconditions:**
- Valid prd.md frontmatter but body has no `## Intent`.

**Input:**
- prd.md with body: `# Title\n\n## Goals\n\n- Goal 1`

**Expected:**
- Validation error mentioning "Intent".

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/no_intent")
ASSERT err != nil
ASSERT contains(err.Error(), "Intent")
```

---

### TS-01-E7: Non-existent spec folder

**Requirement:** 01-REQ-2.E5
**Type:** unit
**Description:** LoadSpec returns error for non-existent path.

**Preconditions:**
- Path does not exist.

**Input:**
- `LoadSpec("/nonexistent/path")`

**Expected:**
- Error indicating path not found.

**Assertion pseudocode:**
```
spec, err = LoadSpec("/nonexistent/path")
ASSERT err != nil
ASSERT spec == nil
```

---

### TS-01-E8: Save to non-existent directory

**Requirement:** 01-REQ-3.E1
**Type:** unit
**Description:** SaveSpec returns error without creating directory.

**Preconditions:**
- Target path does not exist.

**Input:**
- `SaveSpec("/nonexistent/dir", spec)`

**Expected:**
- Error returned.
- Directory NOT created.

**Assertion pseudocode:**
```
err = SaveSpec("/nonexistent/dir", valid_spec)
ASSERT err != nil
ASSERT NOT DirExists("/nonexistent/dir")
```

---

### TS-01-E9: Atomic write on failure

**Requirement:** 01-REQ-3.E2
**Type:** integration
**Description:** Partial write failure leaves no half-written files.

**Preconditions:**
- A directory where one file path is not writable (simulate with read-only permissions).

**Input:**
- SaveSpec to a directory where one target file cannot be written.

**Expected:**
- Error returned.
- No new files left in the directory from the failed operation.

**Assertion pseudocode:**
```
tmpdir = TempDir()
make_readonly(tmpdir + "/requirements.json")  // prevent write
err = SaveSpec(tmpdir, spec)
ASSERT err != nil
// partial files from this save attempt should not exist
```

---

### TS-01-E10: Unknown JSON field rejection

**Requirement:** 01-REQ-4.E1
**Type:** unit
**Description:** Schema validation rejects unknown fields.

**Preconditions:**
- requirements.json with an extra field `"unknown_field": "value"`.

**Input:**
- Spec with additional property not in schema.

**Expected:**
- Validation error identifying the unknown field.

**Assertion pseudocode:**
```
spec = /* requirements.json with "unknown_field" */
errs = ValidateSchema(spec)
ASSERT any(contains(err.Message, "unknown") OR contains(err.Message, "additional") for err in errs)
```

---

### TS-01-E11: EARS pattern-field mismatch

**Requirement:** 01-REQ-4.E2
**Type:** unit
**Description:** Schema rejects criterion with wrong fields for its pattern.

**Preconditions:**
- A criterion with `ears_pattern: "ubiquitous"` but a `trigger` field present.

**Input:**
- Ubiquitous criterion with trigger field.

**Expected:**
- Validation error identifying the pattern-field mismatch.

**Assertion pseudocode:**
```
spec = /* ubiquitous criterion with trigger="something" */
errs = ValidateSchema(spec)
ASSERT any(contains(err.Message, "trigger") OR contains(err.Message, "ubiquitous") for err in errs)
```

---

### TS-01-E12: Bootstrap mode skips cross-file rules

**Requirement:** 01-REQ-5.E1
**Type:** integration
**Description:** Cross-file validation is skipped for missing files during bootstrap.

**Preconditions:**
- Bootstrap with only prd.md and requirements.json written.

**Input:**
- Validate the partial spec during bootstrap.

**Expected:**
- No cross-file errors for rules that reference test_spec.json or tasks.json.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
bs.WritePRD(prd)
bs.WriteRequirements(req)
// implicit: no cross-file validation runs during bootstrap
// only on Finalize
```

---

### TS-01-E13: EARS render with empty required field

**Requirement:** 01-REQ-6.E1
**Type:** unit
**Description:** Empty required field renders as placeholder.

**Preconditions:**
- A criterion with `action: ""`.

**Input:**
- `Criterion{EarsPattern: "ubiquitous", System: "the system", Action: ""}`

**Expected:**
- Rendered as `"THE the system SHALL <missing>"`.

**Assertion pseudocode:**
```
c = Criterion{EarsPattern: "ubiquitous", System: "the system", Action: ""}
rendered = RenderEARS(c)
ASSERT rendered == "THE the system SHALL <missing>"
```

---

### TS-01-E14: EARS render with null or empty return_contract

**Requirement:** 01-REQ-6.E2
**Type:** unit
**Description:** Null or empty-string return_contract omits the return clause.

**Preconditions:**
- A criterion with `return_contract: null`, one with an empty string, and one with a value.

**Input:**
- Null: `Criterion{ReturnContract: nil, ...}`
- Empty: `Criterion{ReturnContract: ptr(""), ...}`
- Non-null: `Criterion{ReturnContract: ptr("list of items"), ...}`

**Expected:**
- Null: no "AND return" in output.
- Empty string: no "AND return" in output.
- Non-null non-empty: ends with "AND return list of items".

**Assertion pseudocode:**
```
c_null = Criterion{EarsPattern: "ubiquitous", System: "s", Action: "a", ReturnContract: nil}
ASSERT NOT contains(RenderEARS(c_null), "AND return")

c_empty = Criterion{EarsPattern: "ubiquitous", System: "s", Action: "a", ReturnContract: ptr("")}
ASSERT NOT contains(RenderEARS(c_empty), "AND return")

c_val = Criterion{EarsPattern: "ubiquitous", System: "s", Action: "a", ReturnContract: ptr("list of items")}
ASSERT contains(RenderEARS(c_val), "AND return list of items")
```

---

### TS-01-E15: Illegal lifecycle transition error

**Requirement:** 01-REQ-7.E1
**Type:** unit
**Description:** Illegal transitions return error with state names.

**Preconditions:**
- Spec in draft state.

**Input:**
- `Transition(draft_spec, StatusSealed)` — illegal (draft→sealed not allowed).

**Expected:**
- Error mentioning "draft" and "sealed".

**Assertion pseudocode:**
```
spec = make_spec_with_status(StatusDraft)
_, err = Transition(spec, StatusSealed)
ASSERT err != nil
ASSERT contains(err.Error(), "draft")
ASSERT contains(err.Error(), "sealed")
```

---

### TS-01-E16: Intent hash tamper detection

**Requirement:** 01-REQ-7.E2
**Type:** unit
**Description:** Altered Intent body detected via hash mismatch.

**Preconditions:**
- Active spec with stored intent_hash.

**Input:**
- Modify the Intent section body text.

**Expected:**
- Recomputed hash differs from stored hash.
- Mutation rejected with intent-tamper error.

**Assertion pseudocode:**
```
spec = make_active_spec(intent="Build a library.")
modified_spec = copy(spec)
modified_spec.PRD.Body = replace_intent(spec.PRD.Body, "Build something else.")
// verify hash mismatch
new_hash = ComputeIntentHash(modified_spec.PRD.Body)
ASSERT new_hash != *spec.PRD.Frontmatter.IntentHash
```

---

### TS-01-E17: Finalize before all files written

**Requirement:** 01-REQ-8.E1
**Type:** integration
**Description:** Finalize with missing files returns incompleteness error.

**Preconditions:**
- Bootstrap with only prd.md written.

**Input:**
- `bs.Finalize()`

**Expected:**
- `IncompleteSpecError` listing missing files.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
bs.WritePRD(prd)
spec, err = bs.Finalize()
ASSERT spec == nil
ASSERT err is IncompleteSpecError
ASSERT "requirements.json" IN err.MissingFiles
ASSERT "test_spec.json" IN err.MissingFiles
ASSERT "tasks.json" IN err.MissingFiles
```

---

### TS-01-E18: Bootstrap overwrites duplicate file

**Requirement:** 01-REQ-8.E2
**Type:** integration
**Description:** Writing same file twice overwrites without error.

**Preconditions:**
- Bootstrap handle.

**Input:**
- Write prd.md with content A, then write prd.md with content B.

**Expected:**
- No error. Second write replaces first. File on disk has content B.

**Assertion pseudocode:**
```
bs = NewBootstrap(...)
bs.WritePRD(prd_a)
bs.WritePRD(prd_b)
content = ReadFile(bs.dir + "/prd.md")
ASSERT content matches prd_b serialization
```

---

### TS-01-E19: Bootstrap on existing folder

**Requirement:** 01-REQ-8.E3
**Type:** integration
**Description:** NewBootstrap errors if folder already exists.

**Preconditions:**
- Spec folder already exists.

**Input:**
- `NewBootstrap(existing_dir, "01", "existing")`

**Expected:**
- Error indicating folder exists.

**Assertion pseudocode:**
```
os.MkdirAll(tmpdir + "/01_existing", 0755)
bs, err = NewBootstrap(tmpdir + "/01_existing", "01", "existing")
ASSERT err != nil
ASSERT bs == nil
```

---

### TS-01-E20: Spec root not found

**Requirement:** 01-REQ-9.E1
**Type:** unit
**Description:** DiscoverSpecs errors on non-existent root.

**Preconditions:**
- Path does not exist.

**Input:**
- `DiscoverSpecs("/nonexistent")`

**Expected:**
- Error returned.

**Assertion pseudocode:**
```
result, err = DiscoverSpecs("/nonexistent")
ASSERT err != nil
ASSERT result == nil
```

---

### TS-01-E21: Incomplete spec in discovery

**Requirement:** 01-REQ-9.E2
**Type:** integration
**Description:** Discovered spec with missing files is marked incomplete.

**Preconditions:**
- Root with `01_partial/` containing only `prd.md`.

**Input:**
- `DiscoverSpecs(root)`

**Expected:**
- Entry for "01" has `Complete == false`.

**Assertion pseudocode:**
```
// setup: 01_partial/ with only prd.md
result, err = DiscoverSpecs(root)
ASSERT err == nil
entry = find(result.Entries, SpecID="01")
ASSERT entry.Complete == false
```

---

### TS-01-E22: Dependency cycle detection

**Requirement:** 01-REQ-9.E3
**Type:** integration
**Description:** Cycle in dependency graph is reported.

**Preconditions:**
- Root with specs 01 and 02 where 01 depends on 02 and 02 depends on 01.

**Input:**
- `DiscoverSpecs(root)`

**Expected:**
- Error identifying cycle participants (01, 02).

**Assertion pseudocode:**
```
// setup: 01 depends_on_spec "02", 02 depends_on_spec "01"
result, err = DiscoverSpecs(root)
// graph building may succeed, but TopologicalOrder detects cycle
order, err = result.Graph.TopologicalOrder()
ASSERT err != nil
ASSERT contains(err.Error(), "cycle")
```

---

### TS-01-E23: ID spec_id mismatch

**Requirement:** 01-REQ-10.E1
**Type:** unit
**Description:** ID with wrong spec_id component is flagged.

**Preconditions:**
- requirements.json with spec_id "01" but criterion ID "02-REQ-1.1".

**Input:**
- Spec with mismatched ID.

**Expected:**
- Validation error identifying "02-REQ-1.1" and expected spec_id "01".

**Assertion pseudocode:**
```
spec = /* spec_id "01", criterion id "02-REQ-1.1" */
errs = ValidateIDs(spec)
ASSERT any(contains(err.Message, "02-REQ-1.1") for err in errs)
```

---

### TS-01-E24: Non-sequential IDs produce warning

**Requirement:** 01-REQ-10.E2
**Type:** unit
**Description:** Gaps in ID sequences produce warnings, not errors.

**Preconditions:**
- Requirements numbered 1, 2, 5 (skipping 3, 4).

**Input:**
- Spec with non-sequential requirement IDs.

**Expected:**
- Warning (not error) about non-sequential IDs.

**Assertion pseudocode:**
```
spec = /* requirements: 01-REQ-1, 01-REQ-2, 01-REQ-5 */
errs = ValidateIDs(spec)
warnings = filter(errs, severity=warning)
ASSERT any(contains(w.Message, "sequential") for w in warnings)
errors = filter(errs, severity=error)
ASSERT len(errors) == 0  // gaps are warnings, not errors
```

---

## Integration Smoke Tests

### TS-01-SMOKE-1: Load spec from disk end-to-end

**Execution Path:** Path 1 from design.md
**Description:** Full load path from directory to populated Spec struct.

**Setup:** testdata/valid_spec/ with all four valid files. No mocks.

**Trigger:** `LoadSpec("testdata/valid_spec")`

**Expected side effects:**
- Returns non-nil `*Spec` with all four artifacts populated.
- PRD frontmatter fields match file content.
- Requirements contain expected number of entries.
- No errors.

**Must NOT satisfy with:** Mocking file reads, hardcoding struct values.

**Assertion pseudocode:**
```
spec, err = LoadSpec("testdata/valid_spec")
ASSERT err == nil
ASSERT spec.PRD.Frontmatter.SpecID != ""
ASSERT len(spec.Requirements.Requirements) > 0
ASSERT len(spec.TestSpec.TestCases) > 0
ASSERT len(spec.Tasks.TaskGroups) > 0
```

---

### TS-01-SMOKE-2: Save spec to disk end-to-end

**Execution Path:** Path 2 from design.md
**Description:** Full save path from Spec struct to files on disk.

**Setup:** Loaded spec + empty temp directory. No mocks.

**Trigger:** `SaveSpec(tmpdir, spec)`

**Expected side effects:**
- Four files written to tmpdir.
- Each file is valid (parseable, schema-valid).
- Files are byte-identical to source on round-trip.

**Must NOT satisfy with:** Mocking file writes, skipping actual disk I/O.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
tmpdir = TempDir()
err = SaveSpec(tmpdir, spec)
ASSERT err == nil
spec2 = LoadSpec(tmpdir)
ASSERT DeepEqual(spec, spec2, ignoring Dir)
```

---

### TS-01-SMOKE-3: Validate spec end-to-end

**Execution Path:** Path 3 from design.md
**Description:** Full validation pipeline: schema + cross-file + ID checks.

**Setup:** testdata/valid_spec. No mocks.

**Trigger:** `Validate(spec)`

**Expected side effects:**
- Returns empty error list for valid spec.
- All three validation stages run (schema, cross-file, ID).

**Must NOT satisfy with:** Skipping any validation stage.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
errs = Validate(spec)
ASSERT len(errs) == 0
```

---

### TS-01-SMOKE-4: Render per-file end-to-end

**Execution Path:** Path 4 from design.md
**Description:** Render requirements to markdown through the full rendering pipeline.

**Setup:** Loaded spec with requirements containing all six EARS patterns. No mocks.

**Trigger:** `RenderRequirements(spec.Requirements)`

**Expected side effects:**
- Returns non-empty markdown bytes.
- Contains rendered EARS sentences for each pattern.
- Output is valid markdown.

**Must NOT satisfy with:** Returning hardcoded markdown strings.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/all_ears_patterns")
md = RenderRequirements(spec.Requirements)
ASSERT len(md) > 0
ASSERT contains(string(md), "SHALL")
ASSERT contains(string(md), "WHEN")
ASSERT contains(string(md), "WHILE")
```

---

### TS-01-SMOKE-5: Render combined end-to-end

**Execution Path:** Path 5 from design.md
**Description:** Combined rendering includes PRD verbatim + all three rendered artifacts.

**Setup:** Complete valid spec. No mocks.

**Trigger:** `RenderCombined(spec)`

**Expected side effects:**
- Returns non-empty bytes containing PRD body, requirements, test spec, and tasks sections.
- PRD body appears verbatim (not re-rendered).
- Sections appear in correct order.

**Must NOT satisfy with:** Mocking render functions or returning concatenated mock strings.

**Assertion pseudocode:**
```
spec = LoadSpec("testdata/valid_spec")
combined = RenderCombined(spec)
ASSERT contains(string(combined), spec.PRD.Body[:50])  // PRD verbatim
ASSERT contains(string(combined), "SHALL")  // rendered requirements
```

---

### TS-01-SMOKE-6: Lifecycle transition end-to-end

**Execution Path:** Path 6 from design.md
**Description:** Draft → active transition computes intent hash and updates status.

**Setup:** Draft spec with Intent section. No mocks.

**Trigger:** `Transition(draft_spec, StatusActive)`

**Expected side effects:**
- Returned spec has Status == "active".
- IntentHash is non-nil and is a 64-char hex string.
- Original spec is NOT modified.

**Must NOT satisfy with:** Hardcoding hash, skipping guard checks.

**Assertion pseudocode:**
```
draft = LoadSpec("testdata/draft_spec")
ASSERT draft.PRD.Frontmatter.Status == StatusDraft
active, err = Transition(draft, StatusActive)
ASSERT err == nil
ASSERT active.PRD.Frontmatter.Status == StatusActive
ASSERT active.PRD.Frontmatter.IntentHash != nil
ASSERT len(*active.PRD.Frontmatter.IntentHash) == 64
ASSERT draft.PRD.Frontmatter.Status == StatusDraft  // original unchanged
```

---

### TS-01-SMOKE-7: Bootstrap end-to-end

**Execution Path:** Path 7 from design.md
**Description:** Create spec from scratch via bootstrap: create folder, write files, finalize.

**Setup:** Empty temp directory. No mocks.

**Trigger:** `NewBootstrap(dir, "05", "new_feature")` → write all files → `Finalize()`

**Expected side effects:**
- Directory created with all four files.
- Finalize returns valid Spec.
- Spec passes Validate.

**Must NOT satisfy with:** Pre-creating files, skipping Finalize validation.

**Assertion pseudocode:**
```
tmpdir = TempDir()
bs, err = NewBootstrap(tmpdir + "/05_new_feature", "05", "new_feature")
ASSERT err == nil
bs.WritePRD(make_prd("05", "new_feature"))
bs.WriteRequirements(make_requirements("05", "new_feature"))
bs.WriteTestSpec(make_testspec("05", "new_feature"))
bs.WriteTasks(make_tasks("05", "new_feature"))
spec, err = bs.Finalize()
ASSERT err == nil
errs = Validate(spec)
ASSERT len(errs) == 0
```

---

### TS-01-SMOKE-8: Discover specs end-to-end

**Execution Path:** Path 8 from design.md
**Description:** Scan root, load metadata, build dependency graph.

**Setup:** Temp root with two complete specs (02 depends on 01) and an archive folder. No mocks.

**Trigger:** `DiscoverSpecs(root)`

**Expected side effects:**
- Returns 2 entries with correct metadata.
- Graph has edge from 02 to 01.
- TopologicalOrder succeeds.

**Must NOT satisfy with:** Mocking directory reads or graph construction.

**Assertion pseudocode:**
```
root = create_test_root(specs=["01_base", "02_dependent"], archive=["03_old"])
result, err = DiscoverSpecs(root)
ASSERT err == nil
ASSERT len(result.Entries) == 2
ASSERT result.Graph.Edges["02"] contains "01"
order, err = result.Graph.TopologicalOrder()
ASSERT err == nil
ASSERT indexOf(order, "01") < indexOf(order, "02")
```

---

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|---|---|---|
| 01-REQ-1.1 | TS-01-1 | unit |
| 01-REQ-1.2 | TS-01-2 | unit |
| 01-REQ-1.3 | TS-01-3 | unit |
| 01-REQ-1.4 | TS-01-4 | unit |
| 01-REQ-1.5 | TS-01-5 | unit |
| 01-REQ-1.6 | TS-01-6 | integration |
| 01-REQ-1.E1 | TS-01-E1 | unit |
| 01-REQ-1.E2 | TS-01-E2 | unit |
| 01-REQ-2.1 | TS-01-7 | integration |
| 01-REQ-2.2 | TS-01-8 | unit |
| 01-REQ-2.3 | TS-01-9 | unit |
| 01-REQ-2.E1 | TS-01-E3 | unit |
| 01-REQ-2.E2 | TS-01-E4 | unit |
| 01-REQ-2.E3 | TS-01-E5 | unit |
| 01-REQ-2.E4 | TS-01-E6 | unit |
| 01-REQ-2.E5 | TS-01-E7 | unit |
| 01-REQ-3.1 | TS-01-10 | integration |
| 01-REQ-3.2 | TS-01-11 | unit |
| 01-REQ-3.3 | TS-01-12 | unit |
| 01-REQ-3.4 | TS-01-13 | integration |
| 01-REQ-3.5 | TS-01-46 | integration |
| 01-REQ-3.6 | TS-01-47 | integration |
| 01-REQ-3.E1 | TS-01-E8 | unit |
| 01-REQ-3.E2 | TS-01-E9 | integration |
| 01-REQ-4.1 | TS-01-14 | unit |
| 01-REQ-4.2 | TS-01-15 | unit |
| 01-REQ-4.3 | TS-01-16 | unit |
| 01-REQ-4.4 | TS-01-17 | unit |
| 01-REQ-4.E1 | TS-01-E10 | unit |
| 01-REQ-4.E2 | TS-01-E11 | unit |
| 01-REQ-5.1 | TS-01-18 | integration |
| 01-REQ-5.2 | TS-01-19 | unit |
| 01-REQ-5.3 | TS-01-20 | unit |
| 01-REQ-5.4 | TS-01-21 | unit |
| 01-REQ-5.5 | TS-01-22 | unit |
| 01-REQ-5.6 | TS-01-23 | unit |
| 01-REQ-5.7 | TS-01-24 | unit |
| 01-REQ-5.E1 | TS-01-E12 | integration |
| 01-REQ-6.1 | TS-01-25 | unit |
| 01-REQ-6.2 | TS-01-26 | unit |
| 01-REQ-6.3 | TS-01-27 | unit |
| 01-REQ-6.4 | TS-01-28 | integration |
| 01-REQ-6.E1 | TS-01-E13 | unit |
| 01-REQ-6.E2 | TS-01-E14 | unit |
| 01-REQ-7.1 | TS-01-29 | unit |
| 01-REQ-7.2 | TS-01-30 | unit |
| 01-REQ-7.3 | TS-01-31 | unit |
| 01-REQ-7.4 | TS-01-32 | unit |
| 01-REQ-7.5 | TS-01-33 | integration |
| 01-REQ-7.E1 | TS-01-E15 | unit |
| 01-REQ-7.E2 | TS-01-E16 | unit |
| 01-REQ-8.1 | TS-01-34 | integration |
| 01-REQ-8.2 | TS-01-35 | integration |
| 01-REQ-8.3 | TS-01-36 | integration |
| 01-REQ-8.4 | TS-01-37 | integration |
| 01-REQ-8.E1 | TS-01-E17 | integration |
| 01-REQ-8.E2 | TS-01-E18 | integration |
| 01-REQ-8.E3 | TS-01-E19 | integration |
| 01-REQ-9.1 | TS-01-38 | integration |
| 01-REQ-9.2 | TS-01-39 | integration |
| 01-REQ-9.3 | TS-01-40 | integration |
| 01-REQ-9.4 | TS-01-41 | integration |
| 01-REQ-9.5 | TS-01-42 | integration |
| 01-REQ-9.E1 | TS-01-E20 | unit |
| 01-REQ-9.E2 | TS-01-E21 | integration |
| 01-REQ-9.E3 | TS-01-E22 | integration |
| 01-REQ-10.1 | TS-01-43 | unit |
| 01-REQ-10.2 | TS-01-44 | unit |
| 01-REQ-10.3 | TS-01-45 | unit |
| 01-REQ-10.E1 | TS-01-E23 | unit |
| 01-REQ-10.E2 | TS-01-E24 | unit |
| Property 1 | TS-01-P1 | property |
| Property 2 | TS-01-P2 | property |
| Property 3 | TS-01-P3 | property |
| Property 4 | TS-01-P4 | property |
| Property 5 | TS-01-P5 | property |
| Property 6 | TS-01-P6 | property |
| Property 7 | TS-01-P7 | property |
| Property 8 | TS-01-P8 | property |
| Property 9 | TS-01-P9 | property |
| Property 10 | TS-01-P10 | property |
| Property 11 | TS-01-P11 | property |
| Path 1 | TS-01-SMOKE-1 | integration |
| Path 2 | TS-01-SMOKE-2 | integration |
| Path 3 | TS-01-SMOKE-3 | integration |
| Path 4 | TS-01-SMOKE-4 | integration |
| Path 5 | TS-01-SMOKE-5 | integration |
| Path 6 | TS-01-SMOKE-6 | integration |
| Path 7 | TS-01-SMOKE-7 | integration |
| Path 8 | TS-01-SMOKE-8 | integration |
