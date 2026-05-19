# Implementation Plan: Python Spec-Format Library (afspec)

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

The implementation follows a test-first approach. Task group 1 writes all failing tests from test_spec.md. Subsequent groups implement the library modules to make those tests pass, starting with the foundational data models and building up through I/O, validation, rendering, lifecycle, bootstrap, and discovery. The final group performs wiring verification to ensure all execution paths are live.

The dependency order is: models → exceptions → IDs → schemas → loader → saver → validator → renderer → lifecycle → bootstrap → discovery. Each module builds on the previous ones.

## Test Commands

- Spec tests: `uv run pytest -q afspec/tests/`
- Unit tests: `uv run pytest -q afspec/tests/ -k "not smoke and not property"`
- Property tests: `uv run pytest -q afspec/tests/ -k "property"`
- Integration tests: `uv run pytest -q afspec/tests/ -k "smoke"`
- All tests: `uv run pytest -q`
- Linter: `uv run ruff check`
- Type check: `uv run mypy afspec/`

## Tasks

- [x] 1. Write failing spec tests
  - [x] 1.1 Set up test file structure and fixtures
    - Create `afspec/tests/` directory with `__init__.py` and `conftest.py`
    - Create shared test fixtures: valid spec folders (tmpdir-based), valid/invalid dataclass instances
    - Create golden fixture directory structure at `testdata/golden/` (with at least one complete spec)
    - Set up pytest configuration in `pyproject.toml`
    - Add `hypothesis` to dev dependencies for property tests
    - _Test Spec: all_

  - [x] 1.2 Translate data model tests (TS-02-1 through TS-02-5)
    - `afspec/tests/test_models.py`: frozen dataclass construction, EARS factory dispatch, subtask state transitions
    - Tests MUST fail (assert against not-yet-implemented types)
    - _Test Spec: TS-02-1, TS-02-2, TS-02-3, TS-02-4, TS-02-5_

  - [x] 1.3 Translate loading and saving tests (TS-02-6 through TS-02-13)
    - `afspec/tests/test_loader.py`: load spec, parse PRD, load JSON
    - `afspec/tests/test_saver.py`: deterministic JSON, deterministic YAML, round-trip, auto updated_at, auto coverage
    - Tests MUST fail
    - _Test Spec: TS-02-6, TS-02-7, TS-02-8, TS-02-9, TS-02-10, TS-02-11, TS-02-12, TS-02-13_

  - [x] 1.4 Translate validation tests (TS-02-14 through TS-02-24)
    - `afspec/tests/test_validator.py`: schema validation, cross-file integrity rules 1-7
    - `afspec/tests/test_ids.py`: ID format patterns, spec_id consistency, positive integers
    - Tests MUST fail
    - _Test Spec: TS-02-14, TS-02-15, TS-02-16, TS-02-17, TS-02-18, TS-02-19, TS-02-20, TS-02-21, TS-02-22, TS-02-23, TS-02-24, TS-02-43, TS-02-44, TS-02-45_

  - [x] 1.5 Translate rendering, lifecycle, bootstrap, and discovery tests
    - `afspec/tests/test_renderer.py`: deterministic rendering, EARS templates, per-file, combined (TS-02-25 through TS-02-28)
    - `afspec/tests/test_lifecycle.py`: transition graph, intent hash, mutation guards (TS-02-29 through TS-02-33)
    - `afspec/tests/test_bootstrap.py`: context manager, deferred validation, finalize (TS-02-34 through TS-02-37)
    - `afspec/tests/test_discovery.py`: scan, skip archive, metadata, dependency graph (TS-02-38 through TS-02-42)
    - Tests MUST fail
    - _Test Spec: TS-02-25 through TS-02-45_

  - [x] 1.6 Translate edge case and property tests
    - Edge case tests in their respective test files (TS-02-E1 through TS-02-E24)
    - `afspec/tests/test_properties.py`: Hypothesis-based property tests (TS-02-P1 through TS-02-P11)
    - Smoke tests in `afspec/tests/test_smoke.py` (TS-02-SMOKE-1 through TS-02-SMOKE-7)
    - Tests MUST fail
    - _Test Spec: TS-02-E1 through TS-02-E24, TS-02-P1 through TS-02-P11, TS-02-SMOKE-1 through TS-02-SMOKE-7_

  - [x] 1.V Verify task group 1
    - [x] All spec tests exist and are syntactically valid
    - [x] All spec tests FAIL (red) — no implementation yet
    - [x] No linter warnings introduced: `uv run ruff check`
    - [x] Type stubs/imports are minimal — just enough for tests to be parseable

---

- [x] 2. Implement data models and exceptions
  - [x] 2.1 Create package structure and exceptions module
    - Create `afspec/__init__.py` (empty initially), `afspec/py.typed` marker
    - Create `afspec/exceptions.py` with `AfspecError`, `SpecValidationError`, `LifecycleError`, `IncompleteSpecError`
    - Create `afspec/models.py` stub
    - _Requirements: 02-REQ-1.1, 02-REQ-1.2, 02-REQ-1.3_

  - [x] 2.2 Implement PRD and Requirements data models
    - `PRDFrontmatter` frozen dataclass with all 12 fields
    - `PRD` frozen dataclass with frontmatter and body
    - `Requirements` container with all nested types: `Requirement`, `UserStory`, `CorrectnessProperty`, `ExecutionPath`, `ExecutionPathStep`, `ErrorHandlingEntry`
    - Null-safe field handling (None for optional fields, empty list for empty arrays)
    - _Requirements: 02-REQ-1.1, 02-REQ-1.2, 02-REQ-1.E1, 02-REQ-1.E2_

  - [x] 2.3 Implement EARS discriminated union
    - Base `EARSCriterion` frozen dataclass with common fields
    - Six subclasses: `UbiquitousCriterion`, `EventDrivenCriterion`, `ComplexEventCriterion`, `StateDrivenCriterion`, `UnwantedCriterion`, `OptionalCriterion`
    - `from_dict()` class method factory dispatching on `ears_pattern`
    - `to_dict()` method for serialization
    - _Requirements: 02-REQ-1.4_

  - [x] 2.4 Implement TestSpec, Tasks, and SubtaskState
    - `TestSpec` container with `TestCase`, `PropertyTest`, `EdgeCaseTest`, `SmokeTest`, `Coverage`
    - `Tasks` container with `TaskGroup`, `Subtask`, `VerificationSubtask`, `Dependency`, `TraceabilityEntry`, `TestCommands`
    - `SubtaskState` enum with `can_transition_to()` enforcing legal transitions
    - `Spec` top-level frozen dataclass aggregating `PRD`, `Requirements`, `TestSpec`, `Tasks`
    - _Requirements: 02-REQ-1.3, 02-REQ-1.5_

  - [x] 2.V Verify task group 2
    - [x] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_models.py`
    - [x] Edge case tests TS-02-E1, TS-02-E2 pass
    - [x] Property tests TS-02-P2, TS-02-P3 pass
    - [x] All existing tests still pass: `uv run pytest -q`
    - [x] No linter warnings: `uv run ruff check`
    - [x] Type check passes: `uv run mypy afspec/`
    - [x] Requirements 02-REQ-1.1 through 02-REQ-1.5, 02-REQ-1.E1, 02-REQ-1.E2 acceptance criteria met

---

- [x] 3. Implement JSON schemas and ID validation
  - [x] 3.1 Create bundled JSON Schema files
    - Create `afspec/schemas/` package with `__init__.py`
    - Author `requirements.v1.json` from spec-format.md §5 (EARS discriminated union via `oneOf`)
    - Author `test_spec.v1.json` from spec-format.md §6
    - Author `tasks.v1.json` from spec-format.md §7 (subtask state enum, verification subtask)
    - Author `prd-frontmatter.v1.json` from spec-format.md §4.1 (all 12 fields)
    - _Requirements: 02-REQ-4.3_

  - [x] 3.2 Implement schema loading via importlib.resources
    - Load schemas from `afspec/schemas/` using `importlib.resources`
    - Expose `schema_version()` function
    - _Requirements: 02-REQ-4.3_

  - [x] 3.3 Implement ID format validation
    - Create `afspec/ids.py` with regex patterns for all 12 ID formats
    - `validate_id(id_str, expected_spec_id)` → list of ValidationError
    - Spec_id consistency check, positive integer check, sequential numbering warning
    - _Requirements: 02-REQ-10.1, 02-REQ-10.2, 02-REQ-10.3_

  - [x] 3.V Verify task group 3
    - [x] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_ids.py afspec/tests/test_validator.py -k "schema or id_format"`
    - [x] Edge case tests TS-02-E23, TS-02-E24 (check_sequential part) pass; TS-02-E10, TS-02-E11 pending task group 7 (require load_spec+validate)
    - [x] Property tests TS-02-P7, TS-02-P9 pass
    - [x] Test TS-02-16 (bundled schemas accessible) passes
    - [x] All existing tests still pass: `uv run pytest -q` (96 failures are all stubs from later groups, 39 pass)
    - [x] No linter warnings: `uv run ruff check`
    - [x] Requirements 02-REQ-4.3, 02-REQ-10.1 through 02-REQ-10.3 acceptance criteria met

---

- [x] 4. Checkpoint — Data models and schemas complete
  - Ensure all model, exception, ID, and schema tests pass.
  - Ask the user if questions arise.
  - The foundational types are now available for I/O, validation, and rendering modules.

---

- [ ] 5. Implement spec loading
  - [ ] 5.1 Implement PRD loading
    - Create `afspec/loader.py`
    - `_load_prd(path)` → `PRD`: parse YAML frontmatter (delimited by `---`), extract markdown body, extract `## Intent` section
    - Handle malformed YAML, missing Intent section
    - _Requirements: 02-REQ-2.2, 02-REQ-2.E3, 02-REQ-2.E4_

  - [ ] 5.2 Implement JSON loading
    - `_load_json(path, target_type)` → dataclass: deserialize JSON, construct typed instances, preserve nulls
    - Handle malformed JSON with file-name-in-error
    - _Requirements: 02-REQ-2.3, 02-REQ-2.E2_

  - [ ] 5.3 Implement load_spec entry point
    - `load_spec(path)` → `Spec`: check all four files exist, load each, assemble Spec
    - Handle missing files (IncompleteSpecError), non-existent path
    - _Requirements: 02-REQ-2.1, 02-REQ-2.E1, 02-REQ-2.E5_

  - [ ] 5.V Verify task group 5
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_loader.py`
    - [ ] Edge case tests TS-02-E3 through TS-02-E7 pass
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Requirements 02-REQ-2.1 through 02-REQ-2.3, 02-REQ-2.E1 through 02-REQ-2.E5 acceptance criteria met

---

- [ ] 6. Implement spec saving
  - [ ] 6.1 Implement deterministic serialization
    - Create `afspec/saver.py`
    - `_serialize_json(data)` → `str`: `json.dumps` with `sort_keys=True, indent=2`, trailing newline
    - `_serialize_prd(prd)` → `str`: YAML frontmatter in fixed field order + body
    - _Requirements: 02-REQ-3.2, 02-REQ-3.3_

  - [ ] 6.2 Implement atomic file writes
    - `_atomic_write(path, content)`: write to tempfile in same directory, then `os.replace`
    - Clean up temp files on failure
    - _Requirements: 02-REQ-3.1, 02-REQ-3.E2_

  - [ ] 6.3 Implement computed fields and save_spec entry point
    - `_update_computed_fields(spec)` → `Spec`: set `updated_at` to UTC now, compute `coverage`
    - `_compute_coverage(requirements, test_spec)` → `Coverage`: scan test cases against requirements
    - `save_spec(spec, path)` → `None`: compute fields, validate directory exists, write all four files atomically
    - _Requirements: 02-REQ-3.1, 02-REQ-3.4, 02-REQ-3.5, 02-REQ-3.6, 02-REQ-3.E1_

  - [ ] 6.V Verify task group 6
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_saver.py`
    - [ ] Edge case tests TS-02-E8, TS-02-E9 pass
    - [ ] Property tests TS-02-P1, TS-02-P10, TS-02-P11 pass
    - [ ] Round-trip test TS-02-11 passes
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Requirements 02-REQ-3.1 through 02-REQ-3.6, 02-REQ-3.E1, 02-REQ-3.E2 acceptance criteria met

---

- [ ] 7. Implement validation
  - [ ] 7.1 Implement schema validation
    - Create `afspec/validator.py`
    - `_validate_schemas(spec)` → `list[ValidationError]`: validate each file against bundled schema
    - PRD frontmatter: parse YAML to dict, validate against prd-frontmatter.v1.json
    - Collect all errors with file name, JSON path, description
    - _Requirements: 02-REQ-4.1, 02-REQ-4.2, 02-REQ-4.4_

  - [ ] 7.2 Implement cross-file integrity validation
    - `_validate_cross_file(spec)` → `list[ValidationError]`: all seven rules
    - Rule 1: requirement_id existence check
    - Rule 2: criterion/edge case coverage check
    - Rule 3: property test coverage
    - Rule 4: smoke test coverage
    - Rule 5: test_spec_id existence
    - Rule 6: glossary term check (backtick-wrapped terms in checked fields)
    - Rule 7: spec_id/spec_name consistency
    - _Requirements: 02-REQ-5.1 through 02-REQ-5.7_

  - [ ] 7.3 Implement validate entry point
    - `validate(spec)` → `list[ValidationError]`: run schema validation, then ID validation, then cross-file
    - Aggregate all errors from all layers
    - _Requirements: 02-REQ-5.1, 02-REQ-4.1_

  - [ ] 7.V Verify task group 7
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_validator.py`
    - [ ] Edge case tests TS-02-E10, TS-02-E11, TS-02-E15 pass
    - [ ] Property tests TS-02-P6, TS-02-P9 pass
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Requirements 02-REQ-4.1 through 02-REQ-4.4, 02-REQ-4.E1, 02-REQ-4.E2, 02-REQ-5.1 through 02-REQ-5.7, 02-REQ-5.E1 acceptance criteria met

---

- [ ] 8. Checkpoint — Core I/O and validation complete
  - Ensure all loader, saver, and validator tests pass.
  - Verify idempotent round-trip with golden fixtures.
  - Ask the user if questions arise.

---

- [ ] 9. Implement markdown rendering
  - [ ] 9.1 Implement EARS sentence rendering
    - Create `afspec/renderer.py`
    - `render_ears(criterion)` → `str`: dispatch on `ears_pattern`, apply template, handle empty fields (`<missing>`), omit null or empty-string `return_contract`
    - _Requirements: 02-REQ-6.2, 02-REQ-6.E1, 02-REQ-6.E2_

  - [ ] 9.2 Implement per-file rendering
    - `render_requirements(requirements)` → `str`: requirements with EARS sentences, glossary, properties, paths, error handling
    - `render_test_spec(test_spec)` → `str`: test cases, property tests, edge cases, smoke tests, coverage
    - `render_tasks(tasks)` → `str`: task groups with subtasks, traceability
    - All output deterministic
    - _Requirements: 02-REQ-6.1, 02-REQ-6.3_

  - [ ] 9.3 Implement combined rendering
    - `render_combined(spec)` → `str`: PRD body verbatim, then requirements, test_spec, tasks each under a `#` headline
    - _Requirements: 02-REQ-6.4_

  - [ ] 9.V Verify task group 9
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_renderer.py`
    - [ ] Edge case tests TS-02-E21, TS-02-E22 pass
    - [ ] Property test TS-02-P8 passes
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Requirements 02-REQ-6.1 through 02-REQ-6.4, 02-REQ-6.E1, 02-REQ-6.E2 acceptance criteria met

---

- [ ] 10. Implement lifecycle management
  - [ ] 10.1 Implement lifecycle state machine
    - Create `afspec/lifecycle.py`
    - Legal transition graph: draft→active, active→sealed, sealed→superseded, sealed→archived, draft→archived
    - `_check_transition(current, target)`: validate or raise `LifecycleError`
    - _Requirements: 02-REQ-7.1, 02-REQ-7.E1_

  - [ ] 10.2 Implement intent hash computation
    - `_compute_intent_hash(body)` → `str`: extract `## Intent` section, normalize (LF, collapse blanks, lowercase, trim), SHA-256
    - `_verify_intent_hash(spec)`: compare stored hash vs recomputed, raise on mismatch
    - _Requirements: 02-REQ-7.2, 02-REQ-7.E2_

  - [ ] 10.3 Implement transition and mutation guards
    - `transition(spec, target_status)` → `Spec`: check transition, compute intent hash on draft→active, apply deprecation banner on superseded, return new Spec
    - Mutation guards: reject Intent/immutable field changes in active, reject all changes in sealed/superseded/archived
    - _Requirements: 02-REQ-7.3, 02-REQ-7.4, 02-REQ-7.5_

  - [ ] 10.V Verify task group 10
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_lifecycle.py`
    - [ ] Edge case tests TS-02-E16, TS-02-E17 pass
    - [ ] Property tests TS-02-P4, TS-02-P5 pass
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Requirements 02-REQ-7.1 through 02-REQ-7.5, 02-REQ-7.E1, 02-REQ-7.E2 acceptance criteria met

---

- [ ] 11. Implement bootstrap mode and discovery
  - [ ] 11.1 Implement BootstrapSpec context manager
    - Create `afspec/bootstrap.py`
    - `BootstrapSpec(spec_root, spec_id, spec_name)`: context manager creating spec folder
    - `write_prd()`, `write_requirements()`, `write_test_spec()`, `write_tasks()`: per-file schema validation on each write
    - `__exit__()` / `finalize()`: run full validation, return completed Spec or raise
    - Handle existing folder (error), incomplete finalize (IncompleteSpecError), file overwrite (allow)
    - _Requirements: 02-REQ-8.1 through 02-REQ-8.4, 02-REQ-8.E1 through 02-REQ-8.E3_

  - [ ] 11.2 Implement spec discovery
    - Create `afspec/discovery.py`
    - `_scan_folders(spec_root)` → `list[Path]`: find `{NN}_{snake_case}` dirs, skip `archive/`
    - `_load_metadata(folder)` → `SpecEntry`: read only PRD frontmatter
    - `_build_dependency_graph(entries)` → `DependencyGraph`: read tasks.json dependencies, detect cycles
    - `discover(spec_root)` → `DiscoveryResult`: default to cwd if None
    - _Requirements: 02-REQ-9.1 through 02-REQ-9.5_

  - [ ] 11.3 Wire public API in __init__.py
    - Export all public functions: `load_spec`, `save_spec`, `validate`, `render_requirements`, `render_test_spec`, `render_tasks`, `render_combined`, `transition`, `discover`, `schema_version`
    - Export all public types: `Spec`, `PRD`, `PRDFrontmatter`, `Requirements`, `TestSpec`, `Tasks`, `EARSCriterion`, subclasses, `SubtaskState`, `BootstrapSpec`, `DiscoveryResult`, `SpecEntry`, `DependencyGraph`, `ValidationError`
    - Export exception types
    - _Requirements: all_

  - [ ] 11.V Verify task group 11
    - [ ] Spec tests for this group pass: `uv run pytest -q afspec/tests/test_bootstrap.py afspec/tests/test_discovery.py`
    - [ ] Edge case tests TS-02-E12 through TS-02-E15, TS-02-E18 through TS-02-E20 pass
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check`
    - [ ] Type check passes: `uv run mypy afspec/`
    - [ ] Requirements 02-REQ-8.1 through 02-REQ-8.4, 02-REQ-8.E1 through 02-REQ-8.E3, 02-REQ-9.1 through 02-REQ-9.5, 02-REQ-9.E1 through 02-REQ-9.E3 acceptance criteria met

---

- [ ] 12. Checkpoint — Full library complete
  - Ensure all unit, property, edge case, and integration tests pass.
  - Run golden fixture round-trip tests against `testdata/golden/`.
  - Run `uv run mypy afspec/` — no errors.
  - Run `uv run ruff check` — no warnings.
  - Create or update documentation (README.md updates, docstrings on public API).

---

- [ ] 13. Wiring verification

  - [ ] 13.1 Trace every execution path from design.md end-to-end
    - For each of the 7 execution paths, verify the entry point in `afspec/__init__.py` actually calls the next function in the chain (read the calling code, do not assume)
    - Confirm no function in the chain is a stub (`return []`, `return None`, `pass`, `raise NotImplementedError`) that was never replaced
    - Every path must be live in production code — errata or deferrals do not satisfy this check
    - _Requirements: all_

  - [ ] 13.2 Verify return values propagate correctly
    - For every function that returns data consumed by a caller, confirm the caller receives and uses the return value
    - Key chains: `_load_prd` → `load_spec`, `_compute_coverage` → `save_spec`, `_compute_intent_hash` → `transition`, `_scan_folders` → `discover`
    - Grep for callers of each function; confirm none discards the return
    - _Requirements: all_

  - [ ] 13.3 Run the integration smoke tests
    - All `TS-02-SMOKE-*` tests pass using real components (no stub bypass)
    - _Test Spec: TS-02-SMOKE-1 through TS-02-SMOKE-7_

  - [ ] 13.4 Stub / dead-code audit
    - Search all files in `afspec/` for: `return []`, `return None` on non-Optional returns, `pass` in non-abstract methods, `# TODO`, `# stub`, `NotImplementedError`
    - Each hit must be either: (a) justified with a comment explaining why it is intentional, or (b) replaced with a real implementation
    - Document any intentional stubs here with rationale

  - [ ] 13.5 Cross-spec entry point verification
    - For each execution path whose entry point is a public API function in `afspec/__init__.py`, confirm the function is importable and callable from external code
    - Verify `BootstrapSpec` is usable as a context manager from consumer code
    - Since this is a library (no upstream callers within this repo), verify via the smoke tests that all entry points are exercised
    - _Requirements: all_

  - [ ] 13.V Verify wiring group
    - [ ] All smoke tests pass: `uv run pytest -q afspec/tests/test_smoke.py`
    - [ ] No unjustified stubs remain in `afspec/`
    - [ ] All execution paths from design.md are live (traceable in code)
    - [ ] All public API functions are importable and callable
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] Type check clean: `uv run mypy afspec/`
    - [ ] Linter clean: `uv run ruff check`

### Checkbox States

| Syntax   | Meaning                |
|----------|------------------------|
| `- [ ]`  | Not started (required) |
| `- [ ]*` | Not started (optional) |
| `- [x]`  | Completed              |
| `- [-]`  | In progress            |
| `- [~]`  | Queued                 |

Tasks are **required by default**. Mark optional tasks with `*` after checkbox: `- [ ]* Optional task`

## Traceability

| Requirement | Test Spec Entry | Implemented By Task | Verified By Test |
|-------------|-----------------|---------------------|------------------|
| 02-REQ-1.1 | TS-02-1 | 2.2 | afspec/tests/test_models.py::test_prd_frontmatter_fields |
| 02-REQ-1.2 | TS-02-2 | 2.2 | afspec/tests/test_models.py::test_requirements_container |
| 02-REQ-1.3 | TS-02-3 | 2.4 | afspec/tests/test_models.py::test_testspec_tasks_containers |
| 02-REQ-1.4 | TS-02-4 | 2.3 | afspec/tests/test_models.py::test_ears_factory_dispatch |
| 02-REQ-1.5 | TS-02-5 | 2.4 | afspec/tests/test_models.py::test_subtask_state_transitions |
| 02-REQ-1.E1 | TS-02-E1 | 2.2 | afspec/tests/test_models.py::test_null_field_roundtrip |
| 02-REQ-1.E2 | TS-02-E2 | 2.2 | afspec/tests/test_models.py::test_empty_array_roundtrip |
| 02-REQ-2.1 | TS-02-6 | 5.3 | afspec/tests/test_loader.py::test_load_valid_spec |
| 02-REQ-2.2 | TS-02-7 | 5.1 | afspec/tests/test_loader.py::test_parse_prd_frontmatter |
| 02-REQ-2.3 | TS-02-8 | 5.2 | afspec/tests/test_loader.py::test_load_json_preserves_nulls |
| 02-REQ-2.E1 | TS-02-E3 | 5.3 | afspec/tests/test_loader.py::test_missing_files_error |
| 02-REQ-2.E2 | TS-02-E4 | 5.2 | afspec/tests/test_loader.py::test_malformed_json_error |
| 02-REQ-2.E3 | TS-02-E5 | 5.1 | afspec/tests/test_loader.py::test_malformed_yaml_error |
| 02-REQ-2.E4 | TS-02-E6 | 5.1 | afspec/tests/test_loader.py::test_missing_intent_error |
| 02-REQ-2.E5 | TS-02-E7 | 5.3 | afspec/tests/test_loader.py::test_nonexistent_path_error |
| 02-REQ-3.1 | TS-02-9 | 6.2, 6.3 | afspec/tests/test_saver.py::test_atomic_write |
| 02-REQ-3.2 | TS-02-9 | 6.1 | afspec/tests/test_saver.py::test_deterministic_json |
| 02-REQ-3.3 | TS-02-10 | 6.1 | afspec/tests/test_saver.py::test_deterministic_yaml |
| 02-REQ-3.4 | TS-02-11 | 6.3 | afspec/tests/test_saver.py::test_idempotent_roundtrip |
| 02-REQ-3.5 | TS-02-12 | 6.3 | afspec/tests/test_saver.py::test_auto_updated_at |
| 02-REQ-3.6 | TS-02-13 | 6.3 | afspec/tests/test_saver.py::test_auto_computed_coverage |
| 02-REQ-3.E1 | TS-02-E8 | 6.3 | afspec/tests/test_saver.py::test_nonexistent_dir_error |
| 02-REQ-3.E2 | TS-02-E9 | 6.2 | afspec/tests/test_saver.py::test_write_failure_cleanup |
| 02-REQ-4.1 | TS-02-14 | 7.1 | afspec/tests/test_validator.py::test_schema_validation |
| 02-REQ-4.2 | TS-02-15 | 7.1 | afspec/tests/test_validator.py::test_prd_frontmatter_validation |
| 02-REQ-4.3 | TS-02-16 | 3.1, 3.2 | afspec/tests/test_validator.py::test_bundled_schemas |
| 02-REQ-4.4 | TS-02-17 | 7.1 | afspec/tests/test_validator.py::test_all_errors_reported |
| 02-REQ-4.E1 | TS-02-E10 | 7.1 | afspec/tests/test_validator.py::test_unknown_fields_rejected |
| 02-REQ-4.E2 | TS-02-E11 | 7.1 | afspec/tests/test_validator.py::test_ears_pattern_mismatch |
| 02-REQ-5.1 | TS-02-18 | 7.2, 7.3 | afspec/tests/test_validator.py::test_cross_file_all_rules |
| 02-REQ-5.2 | TS-02-19 | 7.2 | afspec/tests/test_validator.py::test_orphan_requirement_id |
| 02-REQ-5.3 | TS-02-20 | 7.2 | afspec/tests/test_validator.py::test_uncovered_requirement |
| 02-REQ-5.4 | TS-02-21 | 7.2 | afspec/tests/test_validator.py::test_uncovered_property_path |
| 02-REQ-5.5 | TS-02-22 | 7.2 | afspec/tests/test_validator.py::test_orphan_test_spec_id |
| 02-REQ-5.6 | TS-02-23 | 7.2 | afspec/tests/test_validator.py::test_glossary_crosscheck |
| 02-REQ-5.7 | TS-02-24 | 7.2 | afspec/tests/test_validator.py::test_spec_id_consistency |
| 02-REQ-5.E1 | TS-02-E15 | 7.2 | afspec/tests/test_validator.py::test_bootstrap_skip_missing |
| 02-REQ-6.1 | TS-02-25 | 9.2 | afspec/tests/test_renderer.py::test_deterministic_rendering |
| 02-REQ-6.2 | TS-02-26 | 9.1 | afspec/tests/test_renderer.py::test_ears_templates |
| 02-REQ-6.3 | TS-02-27 | 9.2 | afspec/tests/test_renderer.py::test_per_file_rendering |
| 02-REQ-6.4 | TS-02-28 | 9.3 | afspec/tests/test_renderer.py::test_combined_rendering |
| 02-REQ-6.E1 | TS-02-E21 | 9.1 | afspec/tests/test_renderer.py::test_empty_field_placeholder |
| 02-REQ-6.E2 | TS-02-E22 | 9.1 | afspec/tests/test_renderer.py::test_null_return_contract |
| 02-REQ-7.1 | TS-02-29 | 10.1 | afspec/tests/test_lifecycle.py::test_transition_graph |
| 02-REQ-7.2 | TS-02-30 | 10.2 | afspec/tests/test_lifecycle.py::test_intent_hash_computation |
| 02-REQ-7.3 | TS-02-31 | 10.3 | afspec/tests/test_lifecycle.py::test_active_mutation_guards |
| 02-REQ-7.4 | TS-02-32 | 10.3 | afspec/tests/test_lifecycle.py::test_sealed_reject_mutations |
| 02-REQ-7.5 | TS-02-33 | 10.3 | afspec/tests/test_lifecycle.py::test_supersede_deprecation |
| 02-REQ-7.E1 | TS-02-E16 | 10.1 | afspec/tests/test_lifecycle.py::test_illegal_transition |
| 02-REQ-7.E2 | TS-02-E17 | 10.2 | afspec/tests/test_lifecycle.py::test_intent_tamper |
| 02-REQ-8.1 | TS-02-34 | 11.1 | afspec/tests/test_bootstrap.py::test_bootstrap_creates_folder |
| 02-REQ-8.2 | TS-02-35 | 11.1 | afspec/tests/test_bootstrap.py::test_bootstrap_defers_validation |
| 02-REQ-8.3 | TS-02-36 | 11.1 | afspec/tests/test_bootstrap.py::test_bootstrap_finalize |
| 02-REQ-8.4 | TS-02-37 | 11.1 | afspec/tests/test_bootstrap.py::test_bootstrap_individual_writes |
| 02-REQ-8.E1 | TS-02-E12 | 11.1 | afspec/tests/test_bootstrap.py::test_incomplete_finalize |
| 02-REQ-8.E2 | TS-02-E13 | 11.1 | afspec/tests/test_bootstrap.py::test_file_overwrite |
| 02-REQ-8.E3 | TS-02-E14 | 11.1 | afspec/tests/test_bootstrap.py::test_existing_folder_error |
| 02-REQ-9.1 | TS-02-38 | 11.2 | afspec/tests/test_discovery.py::test_discover_specs |
| 02-REQ-9.2 | TS-02-39 | 11.2 | afspec/tests/test_discovery.py::test_skip_archive |
| 02-REQ-9.3 | TS-02-40 | 11.2 | afspec/tests/test_discovery.py::test_load_metadata_only |
| 02-REQ-9.4 | TS-02-41 | 11.2 | afspec/tests/test_discovery.py::test_dependency_graph |
| 02-REQ-9.5 | TS-02-42 | 11.2 | afspec/tests/test_discovery.py::test_default_cwd |
| 02-REQ-9.E1 | TS-02-E18 | 11.2 | afspec/tests/test_discovery.py::test_nonexistent_root |
| 02-REQ-9.E2 | TS-02-E19 | 11.2 | afspec/tests/test_discovery.py::test_incomplete_spec_entry |
| 02-REQ-9.E3 | TS-02-E20 | 11.2 | afspec/tests/test_discovery.py::test_cycle_detection |
| 02-REQ-10.1 | TS-02-43 | 3.3 | afspec/tests/test_ids.py::test_id_format_patterns |
| 02-REQ-10.2 | TS-02-44 | 3.3 | afspec/tests/test_ids.py::test_spec_id_consistency |
| 02-REQ-10.3 | TS-02-45 | 3.3 | afspec/tests/test_ids.py::test_positive_integers |
| 02-REQ-10.E1 | TS-02-E23 | 3.3 | afspec/tests/test_ids.py::test_spec_id_mismatch |
| 02-REQ-10.E2 | TS-02-E24 | 3.3 | afspec/tests/test_ids.py::test_nonsequential_warning |

## Notes

- **Test framework**: pytest with hypothesis for property tests. Tests live in `afspec/tests/`.
- **Golden fixtures**: Shared fixtures in `testdata/golden/` are used by both Go and Python test suites for cross-library consistency verification. These are created as part of task group 1.
- **Dependency on spec 01**: The JSON Schema files may already exist if spec 01 (Go library) is implemented first. If they exist, reuse them. If not, create them in task group 3.
- **pyproject.toml**: Must be created/updated in task group 1 to configure pytest, ruff, mypy, and dependencies.
- **`from __future__ import annotations`**: Include in every source file for Python 3.10+ type hint syntax.
