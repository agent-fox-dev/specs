# Test Specification: Python Spec-Format Library (afspec)

## Overview

This test specification translates every acceptance criterion, correctness property, and execution path from the Python afspec library specification into concrete, language-agnostic test contracts. Tests are organized by requirement, with separate sections for property tests, edge case tests, and integration smoke tests. All tests target the `afspec/tests/` directory using pytest.

## Test Cases

### TS-02-1: PRD frontmatter dataclass contains all 12 fields

**Requirement:** 02-REQ-1.1
**Type:** unit
**Description:** Verify the PRD frontmatter dataclass has all 12 fields and accepts valid data.

**Preconditions:**
- None.

**Input:**
- A dict with all 12 frontmatter fields: `spec_id="05"`, `spec_name="my_feature"`, `title="My Feature"`, `status="draft"`, `created_at="2026-05-18T12:00:00Z"`, `updated_at="2026-05-18T12:00:00Z"`, `owner="alice"`, `source="interactive"`, `supersedes=[]`, `tags=["v1"]`, `intent_hash=None`, `schema_version=1`.

**Expected:**
- A frozen `PRDFrontmatter` instance with all fields accessible.
- A `PRD` instance containing the frontmatter and a separate body string.

**Assertion pseudocode:**
```
fm = PRDFrontmatter(spec_id="05", spec_name="my_feature", ...)
ASSERT fm.spec_id == "05"
ASSERT fm.schema_version == 1
ASSERT fm.intent_hash IS None
prd = PRD(frontmatter=fm, body="# Title\n\n## Intent\n\nSome intent.")
ASSERT prd.body CONTAINS "## Intent"
```

---

### TS-02-2: Requirements container and nested types

**Requirement:** 02-REQ-1.2
**Type:** unit
**Description:** Verify the requirements top-level container and all nested types can be constructed.

**Preconditions:**
- None.

**Input:**
- A Requirements object with all fields populated: introduction, glossary, one requirement with user_story, one acceptance criterion, one edge case, one correctness property, one execution path, one error handling entry.

**Expected:**
- All nested types are accessible: Requirement, UserStory, CorrectnessProperty, ExecutionPath, ExecutionPathStep, ErrorHandlingEntry.

**Assertion pseudocode:**
```
req = Requirements(spec_id="05", spec_name="test", schema_version=1, introduction="...", glossary={"term": "def"}, requirements=[...], correctness_properties=[...], execution_paths=[...], error_handling=[...])
ASSERT req.requirements[0].user_story.role == "operator"
ASSERT req.correctness_properties[0].id == "05-PROP-1"
ASSERT req.execution_paths[0].steps[0].actor == "SpaceManager"
```

---

### TS-02-3: TestSpec and Tasks container types

**Requirement:** 02-REQ-1.3
**Type:** unit
**Description:** Verify test spec and tasks top-level containers with all nested types.

**Preconditions:**
- None.

**Input:**
- A TestSpec with test_cases, property_tests, edge_case_tests, smoke_tests, coverage.
- A Tasks with test_commands, dependencies, task_groups, traceability.

**Expected:**
- All nested types accessible: TestCase, PropertyTest, EdgeCaseTest, SmokeTest, Coverage, TaskGroup, Subtask, VerificationSubtask, Dependency, TraceabilityEntry.

**Assertion pseudocode:**
```
ts = TestSpec(spec_id="05", ..., test_cases=[TestCase(...)], property_tests=[PropertyTest(...)], ...)
ASSERT ts.test_cases[0].kind == "unit"
tasks = Tasks(spec_id="05", ..., task_groups=[TaskGroup(id=1, ...)], traceability=[TraceabilityEntry(...)])
ASSERT tasks.task_groups[0].subtasks[0].state == SubtaskState.PENDING
```

---

### TS-02-4: EARS discriminated union with factory method

**Requirement:** 02-REQ-1.4
**Type:** unit
**Description:** Verify the EARS criterion factory dispatches correctly for all six patterns.

**Preconditions:**
- None.

**Input:**
- Six dicts, each with a different `ears_pattern` and the correct fields for that pattern.

**Expected:**
- Each returns the correct subclass. Pattern-specific fields are accessible. Fields from other patterns are absent.

**Assertion pseudocode:**
```
ub = EARSCriterion.from_dict({"id": "05-REQ-1.1", "ears_pattern": "ubiquitous", "system": "the system", "action": "do X", "return_contract": None})
ASSERT isinstance(ub, UbiquitousCriterion)
ASSERT NOT hasattr(ub, "trigger")

ed = EARSCriterion.from_dict({"id": "05-REQ-1.2", "ears_pattern": "event_driven", "trigger": "a request", "system": "the system", "action": "respond", "return_contract": None})
ASSERT isinstance(ed, EventDrivenCriterion)
ASSERT ed.trigger == "a request"

ce = EARSCriterion.from_dict({..., "ears_pattern": "complex_event", "trigger": "T", "condition": "C", ...})
ASSERT isinstance(ce, ComplexEventCriterion)
ASSERT ce.condition == "C"

sd = EARSCriterion.from_dict({..., "ears_pattern": "state_driven", "state": "active", ...})
ASSERT isinstance(sd, StateDrivenCriterion)

uw = EARSCriterion.from_dict({..., "ears_pattern": "unwanted", "error_condition": "timeout", ...})
ASSERT isinstance(uw, UnwantedCriterion)

op = EARSCriterion.from_dict({..., "ears_pattern": "optional", "feature": "dark mode", ...})
ASSERT isinstance(op, OptionalCriterion)
```

---

### TS-02-5: Subtask state machine transitions

**Requirement:** 02-REQ-1.5
**Type:** unit
**Description:** Verify the subtask state enum enforces legal transitions and rejects illegal ones.

**Preconditions:**
- None.

**Input:**
- Legal transitions: pending→queued, pending→dropped, queued→in_progress, queued→pending, queued→dropped, in_progress→done, in_progress→pending_reevaluation, done→pending_reevaluation, pending_reevaluation→pending, pending_reevaluation→dropped.
- Illegal transitions: pending→done, done→pending, dropped→pending, in_progress→pending.

**Expected:**
- Legal transitions accepted (return True).
- Illegal transitions rejected (return False or raise error).

**Assertion pseudocode:**
```
ASSERT SubtaskState.PENDING.can_transition_to(SubtaskState.QUEUED) IS True
ASSERT SubtaskState.PENDING.can_transition_to(SubtaskState.DONE) IS False
ASSERT SubtaskState.DROPPED.can_transition_to(SubtaskState.PENDING) IS False
ASSERT SubtaskState.IN_PROGRESS.can_transition_to(SubtaskState.DONE) IS True
```

---

### TS-02-6: Load a valid spec folder

**Requirement:** 02-REQ-2.1
**Type:** integration
**Description:** Verify loading all four files from a valid spec folder returns populated dataclass instances.

**Preconditions:**
- A temporary directory containing all four valid spec files.

**Input:**
- Path to the temporary spec folder.

**Expected:**
- A `Spec` instance with populated `prd`, `requirements`, `test_spec`, `tasks` fields.

**Assertion pseudocode:**
```
spec = load_spec(tmp_spec_path)
ASSERT spec.prd.frontmatter.spec_id == "05"
ASSERT len(spec.requirements.requirements) >= 1
ASSERT len(spec.test_spec.test_cases) >= 1
ASSERT len(spec.tasks.task_groups) >= 1
```

---

### TS-02-7: Parse PRD frontmatter and Intent section

**Requirement:** 02-REQ-2.2
**Type:** unit
**Description:** Verify PRD loading parses YAML frontmatter and extracts the Intent section body.

**Preconditions:**
- A valid `prd.md` file with YAML frontmatter and `## Intent` section.

**Input:**
- Raw prd.md content with frontmatter and body containing `## Intent\n\nBuild a thing.`

**Expected:**
- Frontmatter fields parsed correctly.
- Body string contains the full markdown body.
- Intent section body extractable for hash computation.

**Assertion pseudocode:**
```
prd = _load_prd(prd_path)
ASSERT prd.frontmatter.spec_id == "05"
ASSERT "## Intent" IN prd.body
intent_body = extract_intent(prd.body)
ASSERT intent_body STARTS_WITH "Build a thing"
```

---

### TS-02-8: Load JSON files into typed dataclasses

**Requirement:** 02-REQ-2.3
**Type:** unit
**Description:** Verify JSON loading preserves all field values including nulls.

**Preconditions:**
- A valid `requirements.json` file with at least one requirement where `return_contract` is null.

**Input:**
- Path to requirements.json.

**Expected:**
- Deserialized Requirements dataclass with `return_contract` preserved as `None`.

**Assertion pseudocode:**
```
req = _load_json(req_path, Requirements)
ASSERT req.requirements[0].acceptance_criteria[0].return_contract IS None
```

---

### TS-02-9: Save spec produces deterministic JSON

**Requirement:** 02-REQ-3.2
**Type:** unit
**Description:** Verify saved JSON files have sorted keys, 2-space indentation, and trailing newline.

**Preconditions:**
- A valid in-memory Requirements dataclass.

**Input:**
- Requirements instance.

**Expected:**
- JSON output with keys sorted alphabetically, 2-space indentation, trailing newline.

**Assertion pseudocode:**
```
save_spec(spec, tmp_dir)
content = read_file(tmp_dir / "requirements.json")
ASSERT content ENDS_WITH "\n"
parsed = json.loads(content)
keys = list(parsed.keys())
ASSERT keys == sorted(keys)
lines = content.split("\n")
indented_line = first_line_with_indentation(lines)
ASSERT indented_line STARTS_WITH "  "  # 2-space indent
```

---

### TS-02-10: Save spec produces deterministic YAML frontmatter

**Requirement:** 02-REQ-3.3
**Type:** unit
**Description:** Verify saved PRD has YAML frontmatter fields in the fixed order.

**Preconditions:**
- A valid in-memory PRD dataclass.

**Input:**
- PRD instance.

**Expected:**
- YAML frontmatter with fields in order: spec_id, spec_name, title, status, created_at, updated_at, owner, source, supersedes, tags, intent_hash, schema_version.

**Assertion pseudocode:**
```
save_spec(spec, tmp_dir)
content = read_file(tmp_dir / "prd.md")
frontmatter_text = extract_yaml_block(content)
field_order = extract_field_names(frontmatter_text)
ASSERT field_order == ["spec_id", "spec_name", "title", "status", "created_at", "updated_at", "owner", "source", "supersedes", "tags", "intent_hash", "schema_version"]
```

---

### TS-02-11: Idempotent round-trip

**Requirement:** 02-REQ-3.4
**Type:** integration
**Description:** Verify load-save-load produces byte-identical files (except `updated_at`) and equivalent in-memory state.

**Preconditions:**
- A temporary spec folder with all four valid files.

**Input:**
- Path to the spec folder.

**Expected:**
- After load → save → load, JSON files are byte-identical.
- prd.md is identical except for the `updated_at` field (which is auto-set on save).
- In-memory state is equivalent ignoring `updated_at`.

**Assertion pseudocode:**
```
spec1 = load_spec(src_path)
save_spec(spec1, dst_path)
FOR file IN ["requirements.json", "test_spec.json", "tasks.json"]:
    ASSERT read_bytes(src_path / file) == read_bytes(dst_path / file)
# prd.md: compare with updated_at masked out
prd1 = read_text(src_path / "prd.md")
prd2 = read_text(dst_path / "prd.md")
ASSERT mask_updated_at(prd1) == mask_updated_at(prd2)
spec2 = load_spec(dst_path)
# Compare ignoring updated_at
ASSERT spec1.requirements == spec2.requirements
ASSERT spec1.test_spec == spec2.test_spec
ASSERT spec1.tasks == spec2.tasks
ASSERT spec1.prd.body == spec2.prd.body
```

---

### TS-02-12: Save auto-updates updated_at

**Requirement:** 02-REQ-3.5
**Type:** unit
**Description:** Verify saving a spec automatically sets updated_at to the current UTC timestamp.

**Preconditions:**
- A spec with an old `updated_at` value.

**Input:**
- Spec with `updated_at="2020-01-01T00:00:00Z"`.

**Expected:**
- After save, the written prd.md has `updated_at` set to approximately now (within a few seconds).

**Assertion pseudocode:**
```
before = datetime.utcnow()
save_spec(spec, tmp_dir)
after = datetime.utcnow()
prd = _load_prd(tmp_dir / "prd.md")
saved_time = parse_iso8601(prd.frontmatter.updated_at)
ASSERT before <= saved_time <= after
```

---

### TS-02-13: Save auto-computes coverage

**Requirement:** 02-REQ-3.6
**Type:** integration
**Description:** Verify saving a spec computes the coverage field in test_spec.json from actual test cases.

**Preconditions:**
- A spec with requirements containing IDs 05-REQ-1.1, 05-REQ-1.E1 and test_spec with a test case covering only 05-REQ-1.1.

**Input:**
- Spec with partial test coverage.

**Expected:**
- After save, coverage.requirements_covered includes 05-REQ-1.1.
- coverage.gaps includes 05-REQ-1.E1.

**Assertion pseudocode:**
```
save_spec(spec, tmp_dir)
ts = _load_json(tmp_dir / "test_spec.json", TestSpec)
ASSERT "05-REQ-1.1" IN ts.coverage.requirements_covered
ASSERT "05-REQ-1.E1" IN ts.coverage.gaps
```

---

### TS-02-14: Schema validation against bundled schemas

**Requirement:** 02-REQ-4.1
**Type:** unit
**Description:** Verify each JSON file is validated against its corresponding bundled schema.

**Preconditions:**
- A valid spec and an invalid spec (with missing required field in requirements.json).

**Input:**
- Valid spec, invalid spec (requirements.json missing `introduction` field).

**Expected:**
- Valid spec: empty error list.
- Invalid spec: error list with entry referencing `requirements.json` and the missing field.

**Assertion pseudocode:**
```
errors_valid = validate(valid_spec)
ASSERT len(errors_valid) == 0

errors_invalid = validate(invalid_spec)
ASSERT len(errors_invalid) >= 1
ASSERT errors_invalid[0].file == "requirements.json"
ASSERT "introduction" IN errors_invalid[0].message
```

---

### TS-02-15: PRD frontmatter schema validation

**Requirement:** 02-REQ-4.2
**Type:** unit
**Description:** Verify PRD YAML frontmatter is validated against prd-frontmatter.v1.json.

**Preconditions:**
- A PRD with invalid frontmatter (e.g., missing `spec_id`).

**Input:**
- PRD with `spec_id` omitted from frontmatter.

**Expected:**
- Validation error referencing `prd.md` and `spec_id`.

**Assertion pseudocode:**
```
errors = validate(spec_with_bad_prd)
ASSERT any(e.file == "prd.md" AND "spec_id" IN e.message FOR e IN errors)
```

---

### TS-02-16: Bundled schemas accessible via importlib.resources

**Requirement:** 02-REQ-4.3
**Type:** unit
**Description:** Verify all four schema files are loadable from the package.

**Preconditions:**
- afspec package installed.

**Input:**
- None (load schemas from package resources).

**Expected:**
- Four schema files loadable and parseable as JSON.
- Schema version information accessible.

**Assertion pseudocode:**
```
FOR name IN ["requirements.v1.json", "test_spec.v1.json", "tasks.v1.json", "prd-frontmatter.v1.json"]:
    schema = load_schema(name)
    ASSERT schema IS valid JSON
ASSERT schema_version() == 1
```

---

### TS-02-17: Schema validation reports all errors

**Requirement:** 02-REQ-4.4
**Type:** unit
**Description:** Verify schema validation collects all errors, not just the first.

**Preconditions:**
- A spec with multiple schema violations in the same file.

**Input:**
- requirements.json with two missing required fields (`introduction` and `glossary`).

**Expected:**
- Error list contains at least two errors, both referencing requirements.json.

**Assertion pseudocode:**
```
errors = validate(spec_with_multiple_errors)
req_errors = [e FOR e IN errors IF e.file == "requirements.json"]
ASSERT len(req_errors) >= 2
```

---

### TS-02-18: Cross-file integrity — all seven rules

**Requirement:** 02-REQ-5.1
**Type:** integration
**Description:** Verify cross-file validation checks all seven integrity rules.

**Preconditions:**
- A spec that violates at least one of each rule type.

**Input:**
- Spec with: orphan requirement_id in test_spec (rule 1), uncovered requirement (rule 2), uncovered property (rule 3), uncovered path (rule 4), orphan test_spec_id in tasks (rule 5), missing glossary term (rule 6), mismatched spec_id (rule 7).

**Expected:**
- At least seven errors, one per rule.

**Assertion pseudocode:**
```
errors = validate(spec_with_all_rule_violations)
ASSERT len(errors) >= 7
messages = [e.message FOR e IN errors]
ASSERT any("requirement_id" IN m FOR m IN messages)  # rule 1
ASSERT any("uncovered" IN m FOR m IN messages)         # rule 2
ASSERT any("property" IN m FOR m IN messages)           # rule 3
ASSERT any("execution path" IN m OR "smoke" IN m FOR m IN messages) # rule 4
ASSERT any("test_spec_id" IN m FOR m IN messages)      # rule 5
ASSERT any("glossary" IN m FOR m IN messages)           # rule 6
ASSERT any("spec_id" IN m OR "spec_name" IN m FOR m IN messages)  # rule 7
```

---

### TS-02-19: Cross-file — requirement_id reference check (rule 1)

**Requirement:** 02-REQ-5.2
**Type:** unit
**Description:** Verify that orphan requirement_id references in test_spec, tasks traceability, and error_handling are caught.

**Preconditions:**
- A spec where test_spec references a requirement_id that doesn't exist in requirements.

**Input:**
- test_spec.json with `requirement_id: "05-REQ-99.1"` that doesn't exist in requirements.json.

**Expected:**
- Validation error identifying the orphan reference.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_with_orphan_ref)
ASSERT any("05-REQ-99.1" IN e.message FOR e IN errors)
```

---

### TS-02-20: Cross-file — requirement coverage check (rule 2)

**Requirement:** 02-REQ-5.3
**Type:** unit
**Description:** Verify every acceptance criterion and edge case has a test case.

**Preconditions:**
- A spec with a requirement that has no corresponding test case.

**Input:**
- requirements.json with criterion `05-REQ-1.1`, test_spec.json with no test case for `05-REQ-1.1`.

**Expected:**
- Validation error identifying the uncovered criterion.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_missing_coverage)
ASSERT any("05-REQ-1.1" IN e.message AND "uncovered" IN e.message FOR e IN errors)
```

---

### TS-02-21: Cross-file — property and path coverage (rules 3, 4)

**Requirement:** 02-REQ-5.4
**Type:** unit
**Description:** Verify every correctness property has a property test and every execution path has a smoke test.

**Preconditions:**
- A spec with an uncovered correctness property and an uncovered execution path.

**Input:**
- requirements.json with `05-PROP-1` and `05-PATH-1`, test_spec.json with neither.

**Expected:**
- Two validation errors: one for the property, one for the path.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_missing_prop_path_coverage)
ASSERT any("05-PROP-1" IN e.message FOR e IN errors)
ASSERT any("05-PATH-1" IN e.message FOR e IN errors)
```

---

### TS-02-22: Cross-file — test_spec_id reference check (rule 5)

**Requirement:** 02-REQ-5.5
**Type:** unit
**Description:** Verify every test_spec_id referenced in tasks traceability and subtask refs exists in test_spec.

**Preconditions:**
- A spec where tasks.json references a test_spec_id that doesn't exist.

**Input:**
- tasks.json traceability with `test_spec_id: "TS-05-99"` not in test_spec.json.

**Expected:**
- Validation error identifying the orphan test_spec_id.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_with_orphan_ts_ref)
ASSERT any("TS-05-99" IN e.message FOR e IN errors)
```

---

### TS-02-23: Cross-file — glossary cross-check (rule 6)

**Requirement:** 02-REQ-5.6
**Type:** unit
**Description:** Verify backtick-wrapped terms in checked fields have glossary entries.

**Preconditions:**
- A spec where an acceptance criterion's `action` field contains `` `SpaceManager` `` but the glossary has no entry for `SpaceManager`.

**Input:**
- requirements.json with action containing `` `SpaceManager` ``, glossary without `SpaceManager`.

**Expected:**
- Validation error for missing glossary term.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_missing_glossary_term)
ASSERT any("SpaceManager" IN e.message AND "glossary" IN e.message FOR e IN errors)
```

---

### TS-02-24: Cross-file — spec_id/spec_name consistency (rule 7)

**Requirement:** 02-REQ-5.7
**Type:** unit
**Description:** Verify spec_id and spec_name are consistent across all four files.

**Preconditions:**
- A spec where requirements.json has a different spec_id from prd.md.

**Input:**
- prd.md with `spec_id: "05"`, requirements.json with `spec_id: "06"`.

**Expected:**
- Validation error identifying the mismatch.

**Assertion pseudocode:**
```
errors = _validate_cross_file(spec_with_id_mismatch)
ASSERT any("spec_id" IN e.message AND "inconsistent" IN e.message FOR e IN errors)
```

---

### TS-02-25: Deterministic per-file markdown rendering

**Requirement:** 02-REQ-6.1
**Type:** unit
**Description:** Verify rendering the same input twice produces byte-identical output.

**Preconditions:**
- A valid Requirements dataclass.

**Input:**
- Same Requirements instance rendered twice.

**Expected:**
- Byte-identical output strings.

**Assertion pseudocode:**
```
out1 = render_requirements(req)
out2 = render_requirements(req)
ASSERT out1 == out2
```

---

### TS-02-26: EARS sentence rendering for all six patterns

**Requirement:** 02-REQ-6.2
**Type:** unit
**Description:** Verify EARS criteria render using the correct sentence templates.

**Preconditions:**
- One criterion of each EARS pattern type.

**Input:**
- Six criteria (ubiquitous, event_driven, complex_event, state_driven, unwanted, optional).

**Expected:**
- Rendered sentences match templates: "THE {system} SHALL {action}", "WHEN {trigger}, THE {system} SHALL {action}", etc.

**Assertion pseudocode:**
```
ASSERT render_ears(ubiquitous_criterion) == "THE the system SHALL do X"
ASSERT render_ears(event_driven_criterion) == "WHEN a request, THE the system SHALL respond"
ASSERT render_ears(complex_event_criterion) == "WHEN T AND C, THE the system SHALL act"
ASSERT render_ears(state_driven_criterion) == "WHILE active, THE the system SHALL monitor"
ASSERT render_ears(unwanted_criterion) == "IF timeout, THEN THE the system SHALL retry"
ASSERT render_ears(optional_criterion) == "WHERE dark mode, THE the system SHALL adjust"
```

---

### TS-02-27: Per-file rendering

**Requirement:** 02-REQ-6.3
**Type:** unit
**Description:** Verify each JSON artifact type can be rendered to markdown individually.

**Preconditions:**
- Valid Requirements, TestSpec, and Tasks dataclasses.

**Input:**
- Each artifact type.

**Expected:**
- Non-empty markdown strings returned for each.

**Assertion pseudocode:**
```
req_md = render_requirements(requirements)
ASSERT len(req_md) > 0
ASSERT "REQ-" IN req_md

ts_md = render_test_spec(test_spec)
ASSERT len(ts_md) > 0

tasks_md = render_tasks(tasks)
ASSERT len(tasks_md) > 0
```

---

### TS-02-28: Combined rendering with section headlines

**Requirement:** 02-REQ-6.4
**Type:** integration
**Description:** Verify combined rendering produces PRD verbatim followed by rendered artifacts under headlines.

**Preconditions:**
- A valid Spec.

**Input:**
- Complete Spec.

**Expected:**
- Output starts with PRD body verbatim.
- Contains section headlines for Requirements, Test Specification, Tasks.
- Sections appear in order: PRD, Requirements, Test Specification, Tasks.

**Assertion pseudocode:**
```
combined = render_combined(spec)
ASSERT combined STARTS_WITH spec.prd.body
req_pos = combined.index("# Requirements")
ts_pos = combined.index("# Test Specification")
tasks_pos = combined.index("# Tasks")
ASSERT req_pos < ts_pos < tasks_pos
```

---

### TS-02-29: Lifecycle transition graph enforcement

**Requirement:** 02-REQ-7.1
**Type:** unit
**Description:** Verify all legal transitions are accepted and all illegal transitions raise LifecycleError.

**Preconditions:**
- Specs in each lifecycle state.

**Input:**
- Legal: draft→active, active→sealed, sealed→superseded, sealed→archived, draft→archived.
- Illegal: draft→sealed, active→draft, sealed→draft, superseded→active, archived→draft.

**Expected:**
- Legal transitions return updated Spec.
- Illegal transitions raise `LifecycleError`.

**Assertion pseudocode:**
```
spec_active = transition(draft_spec, "active")
ASSERT spec_active.prd.frontmatter.status == "active"

ASSERT_RAISES LifecycleError: transition(draft_spec, "sealed")
ASSERT_RAISES LifecycleError: transition(active_spec, "draft")
```

---

### TS-02-30: Intent hash computation at draft→active

**Requirement:** 02-REQ-7.2
**Type:** unit
**Description:** Verify draft→active computes and stores intent_hash.

**Preconditions:**
- A draft spec with `## Intent\n\nBuild a thing.` and `intent_hash=None`.

**Input:**
- Draft spec.

**Expected:**
- After transition, `intent_hash` is a 64-character lowercase hex SHA-256 digest.
- The hash matches manual computation of the normalized intent body.

**Assertion pseudocode:**
```
active_spec = transition(draft_spec, "active")
ASSERT active_spec.prd.frontmatter.intent_hash IS NOT None
ASSERT len(active_spec.prd.frontmatter.intent_hash) == 64
expected_hash = sha256(normalize_intent("Build a thing."))
ASSERT active_spec.prd.frontmatter.intent_hash == expected_hash
```

---

### TS-02-31: Active state rejects Intent and immutable field mutations

**Requirement:** 02-REQ-7.3
**Type:** unit
**Description:** Verify mutations to Intent section and immutable fields are rejected in active state.

**Preconditions:**
- An active spec.

**Input:**
- Attempt to save with modified Intent body.
- Attempt to save with modified `created_at`.

**Expected:**
- Both raise `LifecycleError` identifying the rejected field.

**Assertion pseudocode:**
```
modified_intent = replace_intent(active_spec, "New intent text")
ASSERT_RAISES LifecycleError: save_spec(modified_intent, path)

modified_created = replace_field(active_spec, created_at="2000-01-01T00:00:00Z")
ASSERT_RAISES LifecycleError: save_spec(modified_created, path)
```

---

### TS-02-32: Sealed/superseded/archived reject all mutations

**Requirement:** 02-REQ-7.4
**Type:** unit
**Description:** Verify specs in sealed, superseded, or archived state reject all mutations.

**Preconditions:**
- A sealed spec.

**Input:**
- Attempt to save sealed spec with modified title.

**Expected:**
- `LifecycleError` raised.

**Assertion pseudocode:**
```
FOR state IN ["sealed", "superseded", "archived"]:
    spec_in_state = make_spec_with_status(state)
    modified = replace_field(spec_in_state, title="New Title")
    ASSERT_RAISES LifecycleError: save_spec(modified, path)
```

---

### TS-02-33: Superseding adds deprecation banner

**Requirement:** 02-REQ-7.5
**Type:** integration
**Description:** Verify transitioning to superseded adds deprecation banner to all files.

**Preconditions:**
- A sealed spec and a new spec that supersedes it.

**Input:**
- Sealed spec transitioning to superseded.

**Expected:**
- All four files in the old spec folder contain a deprecation banner.
- The superseding spec's frontmatter `supersedes` field is set.

**Assertion pseudocode:**
```
superseded_spec = transition(sealed_spec, "superseded")
FOR file IN ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]:
    content = read_file(old_spec_path / file)
    ASSERT "SUPERSEDED" IN content
```

---

### TS-02-34: BootstrapSpec context manager creates spec folder

**Requirement:** 02-REQ-8.1
**Type:** integration
**Description:** Verify BootstrapSpec creates a spec folder and allows sequential file writes.

**Preconditions:**
- A spec root directory with no existing spec folder.

**Input:**
- BootstrapSpec with spec_id="05", spec_name="test_feature".

**Expected:**
- Folder `05_test_feature` created.
- Files writable one at a time.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test_feature") as bs:
    ASSERT (spec_root / "05_test_feature").is_dir()
    bs.write_prd(prd)
    bs.write_requirements(requirements)
    bs.write_test_spec(test_spec)
    bs.write_tasks(tasks)
spec = bs.result
ASSERT spec.prd.frontmatter.spec_id == "05"
```

---

### TS-02-35: Bootstrap defers cross-file validation

**Requirement:** 02-REQ-8.2
**Type:** unit
**Description:** Verify per-file schema validation runs on each write, but cross-file validation is deferred.

**Preconditions:**
- A bootstrap session.

**Input:**
- Write only prd.md and requirements.json (incomplete set), both valid per their schemas.

**Expected:**
- No errors during writing (cross-file not checked yet).
- Per-file schema errors raised immediately if a file is malformed.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_prd(valid_prd)  # OK - per-file valid
    bs.write_requirements(valid_requirements)  # OK - per-file valid
    ASSERT_RAISES SpecValidationError: bs.write_prd(invalid_prd)  # per-file schema fails
    # No cross-file error yet even though test_spec and tasks are missing
```

---

### TS-02-36: Bootstrap finalize runs full validation

**Requirement:** 02-REQ-8.3
**Type:** integration
**Description:** Verify finalize (context exit) runs full validation and returns completed Spec.

**Preconditions:**
- A bootstrap session with all four valid, cross-file-consistent files written.

**Input:**
- All four valid files.

**Expected:**
- Spec returned on context exit.
- All validation passes.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_prd(prd)
    bs.write_requirements(requirements)
    bs.write_test_spec(test_spec)
    bs.write_tasks(tasks)
spec = bs.result
ASSERT spec IS NOT None
errors = validate(spec)
ASSERT len(errors) == 0
```

---

### TS-02-37: Bootstrap allows individual file writes

**Requirement:** 02-REQ-8.4
**Type:** unit
**Description:** Verify writing any single file works without requiring other files to exist.

**Preconditions:**
- A bootstrap session.

**Input:**
- Write only requirements.json first, before any other file.

**Expected:**
- No error raised during the write.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_requirements(valid_requirements)  # OK — no other files needed yet
    ASSERT (spec_root / "05_test" / "requirements.json").exists()
```

---

### TS-02-38: Discover specs in root directory

**Requirement:** 02-REQ-9.1
**Type:** integration
**Description:** Verify discovery scans for spec folders matching the naming pattern.

**Preconditions:**
- A spec root with folders: `01_alpha`, `02_beta`, `not_a_spec`, `archive/03_old`.

**Input:**
- Path to spec root.

**Expected:**
- Discovery returns entries for `01_alpha` and `02_beta`.
- `not_a_spec` and `archive/03_old` are not included.

**Assertion pseudocode:**
```
result = discover(spec_root)
ids = [e.spec_id FOR e IN result.entries]
ASSERT "01" IN ids
ASSERT "02" IN ids
ASSERT "03" NOT IN ids  # archived
```

---

### TS-02-39: Discovery skips archive directory

**Requirement:** 02-REQ-9.2
**Type:** unit
**Description:** Verify discovery skips the archive/ subdirectory.

**Preconditions:**
- A spec root with `archive/03_old/` containing valid spec files.

**Input:**
- Spec root path.

**Expected:**
- No entries from archive/.

**Assertion pseudocode:**
```
result = discover(spec_root)
ASSERT all(e.spec_id != "03" FOR e IN result.entries)
```

---

### TS-02-40: Discovery loads metadata without full load

**Requirement:** 02-REQ-9.3
**Type:** unit
**Description:** Verify discovery loads only PRD frontmatter (spec_id, spec_name, status) without loading all artifacts.

**Preconditions:**
- A spec root with a spec folder where requirements.json is deliberately malformed (to prove it's not loaded).

**Input:**
- Spec root with malformed requirements.json.

**Expected:**
- Discovery succeeds (doesn't load requirements.json).
- Metadata fields (spec_id, spec_name, status) populated from prd.md frontmatter.

**Assertion pseudocode:**
```
result = discover(spec_root_with_bad_req)
ASSERT result.entries[0].spec_id == "05"
ASSERT result.entries[0].status == "draft"
# No error raised — malformed requirements.json was not loaded
```

---

### TS-02-41: Discovery builds dependency graph

**Requirement:** 02-REQ-9.4
**Type:** integration
**Description:** Verify discovery builds a dependency graph from tasks.json and returns it.

**Preconditions:**
- Two spec folders where spec 02's tasks.json declares a dependency on spec 01.

**Input:**
- Spec root with two specs.

**Expected:**
- Dependency graph has an edge from 01 to 02.
- Topological sort returns [01, 02].

**Assertion pseudocode:**
```
result = discover(spec_root)
ASSERT result.dependency_graph.has_edge("01", "02")
order = result.dependency_graph.topological_sort()
ASSERT order.index("01") < order.index("02")
```

---

### TS-02-42: Discovery defaults to current working directory

**Requirement:** 02-REQ-9.5
**Type:** unit
**Description:** Verify discover() with no argument defaults to the current working directory.

**Preconditions:**
- Current working directory contains spec folders.

**Input:**
- `discover()` called with no arguments, cwd is a valid spec root.

**Expected:**
- Returns entries from the current directory.

**Assertion pseudocode:**
```
os.chdir(spec_root)
result = discover()
ASSERT len(result.entries) > 0
```

---

### TS-02-43: ID format validation for all entity types

**Requirement:** 02-REQ-10.1
**Type:** unit
**Description:** Verify all ID formats are validated against spec-format patterns.

**Preconditions:**
- None.

**Input:**
- Valid IDs: `"05-REQ-1"`, `"05-REQ-1.1"`, `"05-REQ-1.E1"`, `"05-PROP-1"`, `"05-PATH-1"`, `"05-ERR-1"`, `"TS-05-1"`, `"TS-05-P1"`, `"TS-05-E1"`, `"TS-05-SMOKE-1"`, `"1.1"`, `"1.V"`.
- Invalid IDs: `"REQ-1"` (no spec_id), `"05-REQ-0"` (zero), `"05-REQ-"` (missing N).

**Expected:**
- Valid IDs accepted.
- Invalid IDs rejected with appropriate error messages.

**Assertion pseudocode:**
```
FOR valid_id IN valid_ids:
    ASSERT validate_id(valid_id, "05") HAS NO errors
FOR invalid_id IN invalid_ids:
    errors = validate_id(invalid_id, "05")
    ASSERT len(errors) >= 1
```

---

### TS-02-44: ID spec_id consistency

**Requirement:** 02-REQ-10.2
**Type:** unit
**Description:** Verify the spec_id component in IDs matches the file's declared spec_id.

**Preconditions:**
- None.

**Input:**
- Criterion with ID `"06-REQ-1.1"` in a file with `spec_id: "05"`.

**Expected:**
- Validation error for spec_id mismatch.

**Assertion pseudocode:**
```
errors = validate_id("06-REQ-1.1", expected_spec_id="05")
ASSERT len(errors) >= 1
ASSERT "mismatch" IN errors[0].message
```

---

### TS-02-45: ID numeric components are positive

**Requirement:** 02-REQ-10.3
**Type:** unit
**Description:** Verify numeric components in IDs are positive integers.

**Preconditions:**
- None.

**Input:**
- `"05-REQ-0"` (zero), `"05-REQ-1.0"` (zero criterion).

**Expected:**
- Validation errors for non-positive components.

**Assertion pseudocode:**
```
ASSERT len(validate_id("05-REQ-0", "05")) >= 1
ASSERT len(validate_id("05-REQ-1.0", "05")) >= 1
ASSERT len(validate_id("05-REQ-1.1", "05")) == 0  # valid
```

---

## Property Test Cases

### TS-02-P1: Idempotent round-trip for any valid spec

**Property:** Property 1 from design.md
**Validates:** 02-REQ-3.4
**Type:** property
**Description:** Loading and saving any valid spec produces byte-identical files (except `updated_at` which is auto-set on every save).

**For any:** Valid spec generated by Hypothesis (random frontmatter fields, random requirements with valid EARS criteria, random test cases, random tasks with valid subtask states).
**Invariant:** `load(save(load(path))) == load(path)` — JSON files are byte-identical; prd.md is identical except `updated_at`.

**Assertion pseudocode:**
```
FOR ANY spec IN valid_spec_generator:
    save_spec(spec, dir_a)
    spec_loaded = load_spec(dir_a)
    save_spec(spec_loaded, dir_b)
    FOR file IN ["requirements.json", "test_spec.json", "tasks.json"]:
        ASSERT read_bytes(dir_a / file) == read_bytes(dir_b / file)
    ASSERT mask_updated_at(read_text(dir_a / "prd.md")) == mask_updated_at(read_text(dir_b / "prd.md"))
```

---

### TS-02-P2: EARS factory returns correct subclass

**Property:** Property 2 from design.md
**Validates:** 02-REQ-1.4
**Type:** property
**Description:** The EARS factory always returns an instance of the correct subclass.

**For any:** EARS criterion dict sampled from a generator that produces random valid EARS dicts across all six patterns.
**Invariant:** `isinstance(EARSCriterion.from_dict(d), expected_subclass[d["ears_pattern"]])` is True.

**Assertion pseudocode:**
```
FOR ANY criterion_dict IN ears_criterion_generator:
    result = EARSCriterion.from_dict(criterion_dict)
    expected_class = SUBCLASS_MAP[criterion_dict["ears_pattern"]]
    ASSERT isinstance(result, expected_class)
    ASSERT result.ears_pattern == criterion_dict["ears_pattern"]
```

---

### TS-02-P3: Subtask state machine never allows illegal transitions

**Property:** Property 3 from design.md
**Validates:** 02-REQ-1.5
**Type:** property
**Description:** No sequence of transitions can reach a state via an illegal path.

**For any:** Random sequence of (state, target_state) pairs drawn from all 36 possible combinations (6×6).
**Invariant:** `can_transition_to` returns True only for transitions in the legal set.

**Assertion pseudocode:**
```
LEGAL = {(PENDING, QUEUED), (PENDING, DROPPED), (QUEUED, IN_PROGRESS), ...}
FOR ANY (from_state, to_state) IN product(SubtaskState, SubtaskState):
    result = from_state.can_transition_to(to_state)
    ASSERT result == ((from_state, to_state) IN LEGAL)
```

---

### TS-02-P4: Lifecycle transitions match the graph

**Property:** Property 4 from design.md
**Validates:** 02-REQ-7.1, 02-REQ-7.E1
**Type:** property
**Description:** Only transitions in the legal graph are accepted.

**For any:** Random (current_status, target_status) pairs drawn from all 25 possible combinations (5×5).
**Invariant:** Transition succeeds if and only if the pair is in {(draft, active), (active, sealed), (sealed, superseded), (sealed, archived), (draft, archived)}.

**Assertion pseudocode:**
```
LEGAL_TRANSITIONS = {("draft", "active"), ("active", "sealed"), ("sealed", "superseded"), ("sealed", "archived"), ("draft", "archived")}
FOR ANY (current, target) IN product(STATUSES, STATUSES):
    IF (current, target) IN LEGAL_TRANSITIONS:
        ASSERT transition(spec_with_status(current), target) SUCCEEDS
    ELSE:
        ASSERT_RAISES LifecycleError: transition(spec_with_status(current), target)
```

---

### TS-02-P5: Intent hash is stable across save cycles

**Property:** Property 5 from design.md
**Validates:** 02-REQ-7.2, 02-REQ-7.3, 02-REQ-7.E2
**Type:** property
**Description:** Intent hash computed at draft→active remains stable across saves when intent is unchanged.

**For any:** Random intent body text (ASCII printable strings with newlines).
**Invariant:** `compute_intent_hash(text) == compute_intent_hash(text)` across calls, and the hash changes when the text changes.

**Assertion pseudocode:**
```
FOR ANY intent_text IN text_generator:
    hash1 = _compute_intent_hash(intent_text)
    hash2 = _compute_intent_hash(intent_text)
    ASSERT hash1 == hash2
    ASSERT len(hash1) == 64
    modified = intent_text + " extra"
    hash3 = _compute_intent_hash(modified)
    ASSERT hash1 != hash3
```

---

### TS-02-P6: Cross-file references form a closed set

**Property:** Property 6 from design.md
**Validates:** 02-REQ-5.2, 02-REQ-5.3, 02-REQ-5.4, 02-REQ-5.5
**Type:** property
**Description:** In any valid spec, all cross-file references resolve.

**For any:** Valid spec generated to be cross-file consistent.
**Invariant:** `_validate_cross_file(spec)` returns an empty error list.

**Assertion pseudocode:**
```
FOR ANY spec IN valid_consistent_spec_generator:
    errors = _validate_cross_file(spec)
    ASSERT len(errors) == 0
```

---

### TS-02-P7: ID format matches expected pattern

**Property:** Property 7 from design.md
**Validates:** 02-REQ-10.1, 02-REQ-10.2, 02-REQ-10.3
**Type:** property
**Description:** All generated valid IDs pass validation, all generated invalid IDs fail.

**For any:** Random spec_id (1-3 digit string), random positive integer N, random positive integer C.
**Invariant:** Constructed IDs `{spec_id}-REQ-{N}.{C}` pass validation with matching spec_id, fail with mismatched spec_id.

**Assertion pseudocode:**
```
FOR ANY (spec_id, n, c) IN (digit_string, pos_int, pos_int):
    valid_id = f"{spec_id}-REQ-{n}.{c}"
    ASSERT validate_id(valid_id, spec_id) HAS NO errors
    other_id = f"{spec_id + '0'}-REQ-{n}.{c}"  # different spec_id
    ASSERT validate_id(other_id, spec_id) HAS errors
```

---

### TS-02-P8: Deterministic rendering across multiple calls

**Property:** Property 8 from design.md
**Validates:** 02-REQ-6.1
**Type:** property
**Description:** Rendering any valid spec multiple times always produces the same output.

**For any:** Valid spec with random but valid content.
**Invariant:** `render_combined(spec) == render_combined(spec)` for any number of calls.

**Assertion pseudocode:**
```
FOR ANY spec IN valid_spec_generator:
    outputs = [render_combined(spec) FOR _ IN range(3)]
    ASSERT all(o == outputs[0] FOR o IN outputs)
```

---

### TS-02-P9: Schema validation catches structural violations

**Property:** Property 9 from design.md
**Validates:** 02-REQ-4.1, 02-REQ-4.2, 02-REQ-4.4, 02-REQ-4.E1, 02-REQ-4.E2
**Type:** property
**Description:** Removing any required field from a valid spec artifact triggers a schema validation error.

**For any:** Valid spec JSON artifact (requirements, test_spec, or tasks) with one required field removed.
**Invariant:** Schema validation returns at least one error referencing the removed field.

**Assertion pseudocode:**
```
FOR ANY (artifact, field) IN required_field_generator:
    modified = remove_field(artifact, field)
    errors = _validate_schemas(modified)
    ASSERT len(errors) >= 1
    ASSERT any(field IN e.path FOR e IN errors)
```

---

### TS-02-P10: Atomic writes leave no partial state

**Property:** Property 10 from design.md
**Validates:** 02-REQ-3.1, 02-REQ-3.E2
**Type:** property
**Description:** A save that fails mid-write does not leave partial files.

**For any:** Save operation where writing file N of 4 fails (N sampled from 1-4).
**Invariant:** After the failed save, the target directory contains exactly the files that existed before the save (no new partial files).

**Assertion pseudocode:**
```
FOR ANY fail_at_file IN [1, 2, 3, 4]:
    files_before = set(list_files(target_dir))
    with inject_write_failure(file_number=fail_at_file):
        ASSERT_RAISES: save_spec(spec, target_dir)
    files_after = set(list_files(target_dir))
    ASSERT files_before == files_after
```

---

### TS-02-P11: Computed coverage matches actual test state

**Property:** Property 11 from design.md
**Validates:** 02-REQ-3.6
**Type:** property
**Description:** The computed coverage accurately reflects which requirements have test cases.

**For any:** Spec with a random subset of requirements covered by test cases.
**Invariant:** `coverage.requirements_covered ∪ coverage.gaps == all_requirement_ids` and `coverage.requirements_covered ∩ coverage.gaps == ∅`.

**Assertion pseudocode:**
```
FOR ANY (requirements, test_cases) IN partial_coverage_generator:
    spec = make_spec(requirements, test_cases)
    save_spec(spec, dir)
    ts = load_json(dir / "test_spec.json")
    all_ids = set(extract_all_criterion_ids(requirements))
    covered = set(ts.coverage.requirements_covered)
    gaps = set(ts.coverage.gaps)
    ASSERT covered | gaps == all_ids
    ASSERT covered & gaps == set()
```

---

## Edge Case Tests

### TS-02-E1: Null field round-trip preservation

**Requirement:** 02-REQ-1.E1
**Type:** unit
**Description:** Verify null JSON fields are preserved as None through round-trip.

**Preconditions:**
- None.

**Input:**
- EARS criterion with `return_contract: null` in JSON.

**Expected:**
- After load → serialize, the field is `null` (not omitted or empty string).

**Assertion pseudocode:**
```
criterion = EARSCriterion.from_dict({"id": "05-REQ-1.1", ..., "return_contract": None})
ASSERT criterion.return_contract IS None
serialized = criterion.to_dict()
ASSERT "return_contract" IN serialized
ASSERT serialized["return_contract"] IS None
```

---

### TS-02-E2: Empty array round-trip as []

**Requirement:** 02-REQ-1.E2
**Type:** unit
**Description:** Verify empty arrays serialize as [] not null.

**Preconditions:**
- None.

**Input:**
- Requirement with `edge_cases=[]`.

**Expected:**
- JSON output contains `"edge_cases": []`.

**Assertion pseudocode:**
```
req = Requirement(id="05-REQ-1", ..., edge_cases=[])
json_str = serialize_json(req)
ASSERT '"edge_cases": []' IN json_str
```

---

### TS-02-E3: Missing spec files raises IncompleteSpecError

**Requirement:** 02-REQ-2.E1
**Type:** unit
**Description:** Verify loading a folder with missing files raises IncompleteSpecError.

**Preconditions:**
- A directory with only prd.md and requirements.json.

**Input:**
- Path to the incomplete directory.

**Expected:**
- `IncompleteSpecError` raised listing `test_spec.json` and `tasks.json` as absent.

**Assertion pseudocode:**
```
ASSERT_RAISES IncompleteSpecError: load_spec(incomplete_dir)
error = caught_exception
ASSERT "test_spec.json" IN error.missing_files
ASSERT "tasks.json" IN error.missing_files
```

---

### TS-02-E4: Malformed JSON raises parse error

**Requirement:** 02-REQ-2.E2
**Type:** unit
**Description:** Verify malformed JSON produces an error identifying the file.

**Preconditions:**
- A spec folder where requirements.json contains `{invalid`.

**Input:**
- Path to the spec folder.

**Expected:**
- Parse error raised mentioning `requirements.json`.

**Assertion pseudocode:**
```
ASSERT_RAISES: load_spec(dir_with_bad_json)
error = caught_exception
ASSERT "requirements.json" IN str(error)
```

---

### TS-02-E5: Malformed YAML frontmatter raises error

**Requirement:** 02-REQ-2.E3
**Type:** unit
**Description:** Verify malformed YAML frontmatter raises a parse error.

**Preconditions:**
- A prd.md with `---\n  bad: yaml: :\n---`.

**Input:**
- Path to the spec folder.

**Expected:**
- Parse error raised.

**Assertion pseudocode:**
```
ASSERT_RAISES: load_spec(dir_with_bad_yaml)
```

---

### TS-02-E6: Missing Intent section raises validation error

**Requirement:** 02-REQ-2.E4
**Type:** unit
**Description:** Verify a PRD without ## Intent raises SpecValidationError.

**Preconditions:**
- A prd.md with valid frontmatter but no `## Intent` section.

**Input:**
- Path to spec folder.

**Expected:**
- `SpecValidationError` raised.

**Assertion pseudocode:**
```
ASSERT_RAISES SpecValidationError: load_spec(dir_with_no_intent)
```

---

### TS-02-E7: Non-existent spec folder path raises error

**Requirement:** 02-REQ-2.E5
**Type:** unit
**Description:** Verify loading a non-existent path raises FileNotFoundError.

**Preconditions:**
- None.

**Input:**
- A path that does not exist.

**Expected:**
- `FileNotFoundError` raised.

**Assertion pseudocode:**
```
ASSERT_RAISES FileNotFoundError: load_spec(Path("/nonexistent/path"))
```

---

### TS-02-E8: Save to non-existent directory raises error

**Requirement:** 02-REQ-3.E1
**Type:** unit
**Description:** Verify saving to a non-existent directory raises error without creating it.

**Preconditions:**
- None.

**Input:**
- A non-existent directory path.

**Expected:**
- Error raised.
- Directory still doesn't exist.

**Assertion pseudocode:**
```
bad_path = Path("/tmp/nonexistent_dir_xyz")
ASSERT_RAISES: save_spec(spec, bad_path)
ASSERT NOT bad_path.exists()
```

---

### TS-02-E9: Write failure cleans up temp files

**Requirement:** 02-REQ-3.E2
**Type:** unit
**Description:** Verify a write failure mid-save cleans up temporary files.

**Preconditions:**
- A target directory exists.

**Input:**
- Spec save where the third file write is injected to fail.

**Expected:**
- Error raised.
- No temporary files remain in the target directory.
- Previously existing files are unchanged.

**Assertion pseudocode:**
```
files_before = snapshot_dir(target_dir)
with inject_write_failure(file_index=2):
    ASSERT_RAISES: save_spec(spec, target_dir)
files_after = snapshot_dir(target_dir)
ASSERT files_before == files_after
temp_files = [f FOR f IN list_files(target_dir) IF ".tmp" IN f.name]
ASSERT len(temp_files) == 0
```

---

### TS-02-E10: Unknown JSON fields rejected by schema

**Requirement:** 02-REQ-4.E1
**Type:** unit
**Description:** Verify extra fields in JSON are rejected with field path.

**Preconditions:**
- A requirements.json with an extra field `"bogus_field": true`.

**Input:**
- Spec with the extra field.

**Expected:**
- Schema validation error identifying `bogus_field`.

**Assertion pseudocode:**
```
errors = _validate_schemas(spec_with_extra_field)
ASSERT any("bogus_field" IN e.path FOR e IN errors)
```

---

### TS-02-E11: EARS pattern field mismatch rejected

**Requirement:** 02-REQ-4.E2
**Type:** unit
**Description:** Verify a criterion with wrong fields for its pattern is rejected.

**Preconditions:**
- A criterion with `ears_pattern: "ubiquitous"` but also has a `trigger` field.

**Input:**
- Spec with the mismatched criterion.

**Expected:**
- Schema validation error identifying the criterion and invalid field.

**Assertion pseudocode:**
```
errors = _validate_schemas(spec_with_pattern_mismatch)
ASSERT any("trigger" IN e.message FOR e IN errors)
```

---

### TS-02-E12: Bootstrap with incomplete files on finalize

**Requirement:** 02-REQ-8.E1
**Type:** unit
**Description:** Verify finalize with missing files raises IncompleteSpecError.

**Preconditions:**
- A bootstrap session.

**Input:**
- Write only prd.md and requirements.json, then exit context.

**Expected:**
- `IncompleteSpecError` listing missing files.

**Assertion pseudocode:**
```
ASSERT_RAISES IncompleteSpecError:
    with BootstrapSpec(spec_root, "05", "test") as bs:
        bs.write_prd(prd)
        bs.write_requirements(requirements)
        # exits without test_spec and tasks
```

---

### TS-02-E13: Bootstrap allows file overwrite

**Requirement:** 02-REQ-8.E2
**Type:** unit
**Description:** Verify writing the same file twice during bootstrap overwrites without error.

**Preconditions:**
- A bootstrap session.

**Input:**
- Write prd.md, then write prd.md again with different content.

**Expected:**
- No error. Second write takes effect.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_prd(prd_v1)
    bs.write_prd(prd_v2)  # No error
    content = read_file(spec_root / "05_test" / "prd.md")
    ASSERT prd_v2.frontmatter.title IN content
```

---

### TS-02-E14: Bootstrap on existing folder raises error

**Requirement:** 02-REQ-8.E3
**Type:** unit
**Description:** Verify BootstrapSpec for an existing folder raises error.

**Preconditions:**
- A spec root with existing `05_test` folder.

**Input:**
- `BootstrapSpec(spec_root, "05", "test")`.

**Expected:**
- Error raised to prevent accidental overwrite.

**Assertion pseudocode:**
```
(spec_root / "05_test").mkdir()
ASSERT_RAISES: BootstrapSpec(spec_root, "05", "test").__enter__()
```

---

### TS-02-E15: Bootstrap cross-file validation during deferred mode

**Requirement:** 02-REQ-5.E1
**Type:** unit
**Description:** Verify cross-file validation is skipped for missing files during bootstrap.

**Preconditions:**
- A bootstrap session with only prd.md and requirements.json written.

**Input:**
- Validate the partially-written spec.

**Expected:**
- No cross-file errors related to test_spec or tasks (they don't exist yet).
- Per-file schema validation still runs on present files.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_prd(prd)
    bs.write_requirements(requirements)
    # Internal validation does not error on missing test_spec/tasks
```

---

### TS-02-E16: Illegal lifecycle transition

**Requirement:** 02-REQ-7.E1
**Type:** unit
**Description:** Verify illegal transitions raise LifecycleError with state names.

**Preconditions:**
- A draft spec.

**Input:**
- Attempt `draft → sealed`.

**Expected:**
- `LifecycleError` naming "draft" as current and "sealed" as target.

**Assertion pseudocode:**
```
error = ASSERT_RAISES LifecycleError: transition(draft_spec, "sealed")
ASSERT error.current_state == "draft"
ASSERT error.target_state == "sealed"
```

---

### TS-02-E17: Intent hash tamper detection

**Requirement:** 02-REQ-7.E2
**Type:** unit
**Description:** Verify saving an active spec with modified intent body raises LifecycleError.

**Preconditions:**
- An active spec with intent_hash set.

**Input:**
- Active spec with modified Intent section body.

**Expected:**
- `LifecycleError` raised for intent tamper.

**Assertion pseudocode:**
```
active_spec = transition(draft_spec, "active")
tampered = replace_intent_body(active_spec, "Completely different intent")
ASSERT_RAISES LifecycleError: save_spec(tampered, path)
```

---

### TS-02-E18: Non-existent spec root raises error

**Requirement:** 02-REQ-9.E1
**Type:** unit
**Description:** Verify discovery on a non-existent directory raises error.

**Preconditions:**
- None.

**Input:**
- Non-existent path.

**Expected:**
- Error raised.

**Assertion pseudocode:**
```
ASSERT_RAISES: discover(Path("/nonexistent"))
```

---

### TS-02-E19: Incomplete spec folder in discovery

**Requirement:** 02-REQ-9.E2
**Type:** unit
**Description:** Verify incomplete spec folders are included but marked as incomplete.

**Preconditions:**
- A spec root with `05_test/` containing only prd.md.

**Input:**
- Spec root path.

**Expected:**
- Entry with `complete=False`.

**Assertion pseudocode:**
```
result = discover(spec_root)
entry = find_entry(result, "05")
ASSERT entry.complete IS False
```

---

### TS-02-E20: Dependency graph cycle detection

**Requirement:** 02-REQ-9.E3
**Type:** unit
**Description:** Verify a circular dependency is detected and reported.

**Preconditions:**
- Spec 01 depends on spec 02, spec 02 depends on spec 01 (in tasks.json).

**Input:**
- Spec root with the circular dependency.

**Expected:**
- Error identifying specs "01" and "02" in the cycle.

**Assertion pseudocode:**
```
ASSERT_RAISES: discover(spec_root_with_cycle)
error = caught_exception
ASSERT "01" IN str(error)
ASSERT "02" IN str(error)
```

---

### TS-02-E21: EARS rendering with empty field uses placeholder

**Requirement:** 02-REQ-6.E1
**Type:** unit
**Description:** Verify empty string fields render as `<missing>`.

**Preconditions:**
- None.

**Input:**
- Ubiquitous criterion with `system=""`.

**Expected:**
- Rendered as `"THE <missing> SHALL do X"`.

**Assertion pseudocode:**
```
criterion = UbiquitousCriterion(id="05-REQ-1.1", ears_pattern="ubiquitous", system="", action="do X", return_contract=None)
rendered = render_ears(criterion)
ASSERT rendered == "THE <missing> SHALL do X"
```

---

### TS-02-E22: EARS rendering omits null or empty return_contract

**Requirement:** 02-REQ-6.E2
**Type:** unit
**Description:** Verify null or empty-string return_contract is omitted from rendered output.

**Preconditions:**
- None.

**Input:**
- Criterion with `return_contract=None`.
- Criterion with `return_contract=""`.
- Criterion with `return_contract="list of items"`.

**Expected:**
- None: no return contract clause in rendered sentence.
- Empty string: no return contract clause in rendered sentence.
- Non-empty: ends with "AND return list of items".

**Assertion pseudocode:**
```
c_none = EventDrivenCriterion(id="05-REQ-1.1", ..., return_contract=None)
rendered_none = render_ears(c_none)
ASSERT "return" NOT IN rendered_none.lower()

c_empty = EventDrivenCriterion(id="05-REQ-1.2", ..., return_contract="")
rendered_empty = render_ears(c_empty)
ASSERT "return" NOT IN rendered_empty.lower()

c_val = EventDrivenCriterion(id="05-REQ-1.3", ..., return_contract="list of items")
rendered_val = render_ears(c_val)
ASSERT "AND return list of items" IN rendered_val
```

---

### TS-02-E23: ID spec_id mismatch error

**Requirement:** 02-REQ-10.E1
**Type:** unit
**Description:** Verify mismatched spec_id in IDs is reported.

**Preconditions:**
- None.

**Input:**
- ID `"06-REQ-1.1"` validated against file with `spec_id="05"`.

**Expected:**
- Error identifying the mismatch and expected spec_id.

**Assertion pseudocode:**
```
errors = validate_id("06-REQ-1.1", expected_spec_id="05")
ASSERT any("06" IN e.message AND "05" IN e.message FOR e IN errors)
```

---

### TS-02-E24: Non-sequential IDs produce warning

**Requirement:** 02-REQ-10.E2
**Type:** unit
**Description:** Verify non-sequential requirement numbering produces a warning, not an error.

**Preconditions:**
- Requirements numbered 1, 2, 5 (gap at 3, 4).

**Input:**
- Spec with requirements 05-REQ-1, 05-REQ-2, 05-REQ-5.

**Expected:**
- Validation warning (severity="warning") about non-sequential IDs.

**Assertion pseudocode:**
```
errors = validate(spec_with_gaps)
warnings = [e FOR e IN errors IF e.severity == "warning"]
ASSERT any("sequential" IN w.message FOR w IN warnings)
```

---

## Integration Smoke Tests

### TS-02-SMOKE-1: Full load from disk

**Execution Path:** Path 1 from design.md
**Description:** Verify a spec folder is loaded end-to-end from disk into populated dataclass instances.

**Setup:** Write four valid spec files to a temporary directory.

**Trigger:** `load_spec(tmp_path)`

**Expected side effects:**
- Returns a `Spec` with populated prd, requirements, test_spec, tasks.
- All nested types are correctly instantiated.

**Must NOT satisfy with:** Mocking loader, filesystem, or any afspec internal module.

**Assertion pseudocode:**
```
spec = load_spec(fixture_path)
ASSERT spec.prd.frontmatter.spec_id IS NOT None
ASSERT len(spec.requirements.requirements) > 0
ASSERT len(spec.test_spec.test_cases) > 0
ASSERT len(spec.tasks.task_groups) > 0
```

---

### TS-02-SMOKE-2: Full save to disk with computed fields

**Execution Path:** Path 2 from design.md
**Description:** Verify a spec is saved end-to-end with computed coverage and updated_at.

**Setup:** Load a fixture spec, note original updated_at and coverage.

**Trigger:** `save_spec(spec, output_path)`

**Expected side effects:**
- Four files written atomically to output_path.
- `updated_at` is refreshed.
- `coverage` is computed.
- Files are loadable via `load_spec`.

**Must NOT satisfy with:** Mocking saver, filesystem writes, or computed field logic.

**Assertion pseudocode:**
```
spec = load_spec(fixture_path)
save_spec(spec, output_path)
ASSERT (output_path / "prd.md").exists()
ASSERT (output_path / "requirements.json").exists()
reloaded = load_spec(output_path)
ASSERT reloaded.test_spec.coverage IS NOT None
```

---

### TS-02-SMOKE-3: Full validation pipeline

**Execution Path:** Path 3 from design.md
**Description:** Verify validation runs schema, ID, and cross-file checks end-to-end.

**Setup:** A valid spec and a spec with known violations.

**Trigger:** `validate(spec)`

**Expected side effects:**
- Valid spec: empty error list.
- Invalid spec: errors from schema, ID, and cross-file layers.

**Must NOT satisfy with:** Mocking validator, schema loading, or any validation subroutine.

**Assertion pseudocode:**
```
ASSERT len(validate(valid_spec)) == 0
errors = validate(invalid_spec)
ASSERT len(errors) > 0
ASSERT any(e.file == "requirements.json" FOR e IN errors)
```

---

### TS-02-SMOKE-4: Combined rendering end-to-end

**Execution Path:** Path 4 from design.md
**Description:** Verify combined rendering produces a complete document from a loaded spec.

**Setup:** Load a valid fixture spec.

**Trigger:** `render_combined(spec)`

**Expected side effects:**
- Returns a string starting with the PRD body.
- Contains section headlines for Requirements, Test Specification, Tasks.
- All EARS sentences rendered correctly.

**Must NOT satisfy with:** Mocking renderer or any rendering subroutine.

**Assertion pseudocode:**
```
spec = load_spec(fixture_path)
combined = render_combined(spec)
ASSERT combined STARTS_WITH spec.prd.body
ASSERT "# Requirements" IN combined
ASSERT "SHALL" IN combined  # EARS keywords present
```

---

### TS-02-SMOKE-5: Lifecycle transition end-to-end (draft → active)

**Execution Path:** Path 5 from design.md
**Description:** Verify draft-to-active transition computes intent hash and updates status.

**Setup:** Load a draft spec from a fixture.

**Trigger:** `transition(spec, "active")`

**Expected side effects:**
- Returns Spec with status="active" and intent_hash set.
- Save the result and reload — status and hash persist.

**Must NOT satisfy with:** Mocking lifecycle module or hash computation.

**Assertion pseudocode:**
```
draft = load_spec(draft_fixture_path)
active = transition(draft, "active")
ASSERT active.prd.frontmatter.status == "active"
ASSERT active.prd.frontmatter.intent_hash IS NOT None
save_spec(active, output_path)
reloaded = load_spec(output_path)
ASSERT reloaded.prd.frontmatter.status == "active"
ASSERT reloaded.prd.frontmatter.intent_hash == active.prd.frontmatter.intent_hash
```

---

### TS-02-SMOKE-6: Bootstrap spec creation end-to-end

**Execution Path:** Path 6 from design.md
**Description:** Verify full bootstrap flow creates a valid spec from scratch.

**Setup:** Empty spec root directory.

**Trigger:** `with BootstrapSpec(spec_root, "05", "test") as bs: ...`

**Expected side effects:**
- Folder `05_test` created with all four files.
- All files pass validation.
- Loadable via `load_spec`.

**Must NOT satisfy with:** Mocking bootstrap, loader, or saver modules.

**Assertion pseudocode:**
```
with BootstrapSpec(spec_root, "05", "test") as bs:
    bs.write_prd(prd)
    bs.write_requirements(requirements)
    bs.write_test_spec(test_spec)
    bs.write_tasks(tasks)
spec = load_spec(spec_root / "05_test")
errors = validate(spec)
ASSERT len(errors) == 0
```

---

### TS-02-SMOKE-7: Spec discovery end-to-end

**Execution Path:** Path 7 from design.md
**Description:** Verify discovery scans a spec root, loads metadata, and builds a dependency graph.

**Setup:** Spec root with two specs (01 depends on nothing, 02 depends on 01) and an archive folder.

**Trigger:** `discover(spec_root)`

**Expected side effects:**
- Two entries returned (archive excluded).
- Dependency graph with edge from 01 to 02.
- Topological sort succeeds.

**Must NOT satisfy with:** Mocking discovery, loader, or graph construction.

**Assertion pseudocode:**
```
result = discover(spec_root)
ASSERT len(result.entries) == 2
ASSERT NOT result.dependency_graph.has_cycle()
order = result.dependency_graph.topological_sort()
ASSERT order == ["01", "02"]
```

---

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 02-REQ-1.1 | TS-02-1 | unit |
| 02-REQ-1.2 | TS-02-2 | unit |
| 02-REQ-1.3 | TS-02-3 | unit |
| 02-REQ-1.4 | TS-02-4 | unit |
| 02-REQ-1.5 | TS-02-5 | unit |
| 02-REQ-1.E1 | TS-02-E1 | unit |
| 02-REQ-1.E2 | TS-02-E2 | unit |
| 02-REQ-2.1 | TS-02-6 | integration |
| 02-REQ-2.2 | TS-02-7 | unit |
| 02-REQ-2.3 | TS-02-8 | unit |
| 02-REQ-2.E1 | TS-02-E3 | unit |
| 02-REQ-2.E2 | TS-02-E4 | unit |
| 02-REQ-2.E3 | TS-02-E5 | unit |
| 02-REQ-2.E4 | TS-02-E6 | unit |
| 02-REQ-2.E5 | TS-02-E7 | unit |
| 02-REQ-3.1 | TS-02-9 | unit |
| 02-REQ-3.2 | TS-02-9 | unit |
| 02-REQ-3.3 | TS-02-10 | unit |
| 02-REQ-3.4 | TS-02-11 | integration |
| 02-REQ-3.5 | TS-02-12 | unit |
| 02-REQ-3.6 | TS-02-13 | integration |
| 02-REQ-3.E1 | TS-02-E8 | unit |
| 02-REQ-3.E2 | TS-02-E9 | unit |
| 02-REQ-4.1 | TS-02-14 | unit |
| 02-REQ-4.2 | TS-02-15 | unit |
| 02-REQ-4.3 | TS-02-16 | unit |
| 02-REQ-4.4 | TS-02-17 | unit |
| 02-REQ-4.E1 | TS-02-E10 | unit |
| 02-REQ-4.E2 | TS-02-E11 | unit |
| 02-REQ-5.1 | TS-02-18 | integration |
| 02-REQ-5.2 | TS-02-19 | unit |
| 02-REQ-5.3 | TS-02-20 | unit |
| 02-REQ-5.4 | TS-02-21 | unit |
| 02-REQ-5.5 | TS-02-22 | unit |
| 02-REQ-5.6 | TS-02-23 | unit |
| 02-REQ-5.7 | TS-02-24 | unit |
| 02-REQ-5.E1 | TS-02-E15 | unit |
| 02-REQ-6.1 | TS-02-25 | unit |
| 02-REQ-6.2 | TS-02-26 | unit |
| 02-REQ-6.3 | TS-02-27 | unit |
| 02-REQ-6.4 | TS-02-28 | integration |
| 02-REQ-6.E1 | TS-02-E21 | unit |
| 02-REQ-6.E2 | TS-02-E22 | unit |
| 02-REQ-7.1 | TS-02-29 | unit |
| 02-REQ-7.2 | TS-02-30 | unit |
| 02-REQ-7.3 | TS-02-31 | unit |
| 02-REQ-7.4 | TS-02-32 | unit |
| 02-REQ-7.5 | TS-02-33 | integration |
| 02-REQ-7.E1 | TS-02-E16 | unit |
| 02-REQ-7.E2 | TS-02-E17 | unit |
| 02-REQ-8.1 | TS-02-34 | integration |
| 02-REQ-8.2 | TS-02-35 | unit |
| 02-REQ-8.3 | TS-02-36 | integration |
| 02-REQ-8.4 | TS-02-37 | unit |
| 02-REQ-8.E1 | TS-02-E12 | unit |
| 02-REQ-8.E2 | TS-02-E13 | unit |
| 02-REQ-8.E3 | TS-02-E14 | unit |
| 02-REQ-9.1 | TS-02-38 | integration |
| 02-REQ-9.2 | TS-02-39 | unit |
| 02-REQ-9.3 | TS-02-40 | unit |
| 02-REQ-9.4 | TS-02-41 | integration |
| 02-REQ-9.5 | TS-02-42 | unit |
| 02-REQ-9.E1 | TS-02-E18 | unit |
| 02-REQ-9.E2 | TS-02-E19 | unit |
| 02-REQ-9.E3 | TS-02-E20 | unit |
| 02-REQ-10.1 | TS-02-43 | unit |
| 02-REQ-10.2 | TS-02-44 | unit |
| 02-REQ-10.3 | TS-02-45 | unit |
| 02-REQ-10.E1 | TS-02-E23 | unit |
| 02-REQ-10.E2 | TS-02-E24 | unit |
| Property 1 | TS-02-P1 | property |
| Property 2 | TS-02-P2 | property |
| Property 3 | TS-02-P3 | property |
| Property 4 | TS-02-P4 | property |
| Property 5 | TS-02-P5 | property |
| Property 6 | TS-02-P6 | property |
| Property 7 | TS-02-P7 | property |
| Property 8 | TS-02-P8 | property |
| Property 9 | TS-02-P9 | property |
| Property 10 | TS-02-P10 | property |
| Property 11 | TS-02-P11 | property |
| Path 1 | TS-02-SMOKE-1 | integration |
| Path 2 | TS-02-SMOKE-2 | integration |
| Path 3 | TS-02-SMOKE-3 | integration |
| Path 4 | TS-02-SMOKE-4 | integration |
| Path 5 | TS-02-SMOKE-5 | integration |
| Path 6 | TS-02-SMOKE-6 | integration |
| Path 7 | TS-02-SMOKE-7 | integration |
