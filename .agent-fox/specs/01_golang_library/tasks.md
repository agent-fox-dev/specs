# Implementation Plan: Go Spec-Format Library (afspec)

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

The implementation follows a test-first approach: group 1 writes all failing tests, subsequent groups implement features to make them pass. The groups are ordered by dependency: data model → serialization → I/O → validation → rendering → lifecycle → bootstrap → discovery. Checkpoints verify end-to-end integration at key milestones.

## Test Commands

- Spec tests: `go test -count=1 -run 'TestSpec' ./...`
- Unit tests: `go test -count=1 -run 'TestUnit' ./...`
- Property tests: `go test -count=1 -run 'TestProperty' ./...`
- All tests: `go test -count=1 ./...`
- Linter: `go vet ./...`

## Tasks

- [x] 1. Write failing spec tests
  - [x] 1.1 Set up test file structure and testdata fixtures
    - Create test files: `spec_test.go`, `load_test.go`, `save_test.go`, `validate_test.go`, `render_test.go`, `lifecycle_test.go`, `bootstrap_test.go`, `discover_test.go`
    - Create `testdata/valid_spec/` with all four golden files (prd.md, requirements.json, test_spec.json, tasks.json)
    - Create `testdata/` directories for error cases: `incomplete_spec/`, `malformed_json/`, `bad_yaml/`, `no_intent/`, `crossfile_errors/`, `all_ears_patterns/`, `draft_spec/`
    - _Test Spec: TS-01-1 through TS-01-45_

  - [x] 1.2 Translate acceptance-criterion tests (TS-01-1 through TS-01-47)
    - Data model tests (TS-01-1 through TS-01-6) in `spec_test.go`
    - Load tests (TS-01-7 through TS-01-9) in `load_test.go`
    - Save tests (TS-01-10 through TS-01-13) in `save_test.go`
    - Auto-computed field tests (TS-01-46, TS-01-47) in `save_test.go`
    - Schema validation tests (TS-01-14 through TS-01-17) in `validate_test.go`
    - Cross-file tests (TS-01-18 through TS-01-24) in `validate_test.go`
    - Render tests (TS-01-25 through TS-01-28) in `render_test.go`
    - Lifecycle tests (TS-01-29 through TS-01-33) in `lifecycle_test.go`
    - Bootstrap tests (TS-01-34 through TS-01-37) in `bootstrap_test.go`
    - Discovery tests (TS-01-38 through TS-01-42) in `discover_test.go`
    - ID validation tests (TS-01-43 through TS-01-45) in `validate_test.go`
    - _Test Spec: TS-01-1 through TS-01-47_

  - [x] 1.3 Translate edge-case tests (TS-01-E1 through TS-01-E24)
    - Serialization edge cases (TS-01-E1, TS-01-E2)
    - Load edge cases (TS-01-E3 through TS-01-E7)
    - Save edge cases (TS-01-E8, TS-01-E9)
    - Schema edge cases (TS-01-E10, TS-01-E11)
    - Cross-file edge cases (TS-01-E12)
    - Render edge cases (TS-01-E13, TS-01-E14)
    - Lifecycle edge cases (TS-01-E15, TS-01-E16)
    - Bootstrap edge cases (TS-01-E17 through TS-01-E19)
    - Discovery edge cases (TS-01-E20 through TS-01-E22)
    - ID edge cases (TS-01-E23, TS-01-E24)
    - _Test Spec: TS-01-E1 through TS-01-E24_

  - [x] 1.4 Translate property tests (TS-01-P1 through TS-01-P11)
    - Round-trip idempotency (TS-01-P1) in `save_test.go`
    - EARS determinism (TS-01-P2) in `render_test.go`
    - Lifecycle monotonicity (TS-01-P3) in `lifecycle_test.go`
    - Cross-file integrity (TS-01-P4) in `validate_test.go`
    - Intent hash stability (TS-01-P5) in `lifecycle_test.go`
    - Schema soundness (TS-01-P6) in `validate_test.go`
    - Discovery completeness (TS-01-P7) in `discover_test.go`
    - Bootstrap deferred validation (TS-01-P8) in `bootstrap_test.go`
    - ID format consistency (TS-01-P9) in `validate_test.go`
    - Null preservation (TS-01-P10) in `spec_test.go`
    - Computed coverage accuracy (TS-01-P11) in `save_test.go`
    - _Test Spec: TS-01-P1 through TS-01-P11_

  - [x] 1.5 Translate smoke tests (TS-01-SMOKE-1 through TS-01-SMOKE-8)
    - All smoke tests in `smoke_test.go`
    - _Test Spec: TS-01-SMOKE-1 through TS-01-SMOKE-8_

  - [x] 1.V Verify task group 1
    - [x] All spec tests exist and are syntactically valid: `go build ./...`
    - [x] All spec tests FAIL (red) — no implementation yet: `go test -count=1 ./...` shows failures
    - [x] No linter warnings introduced: `go vet ./...`

- [x] 2. Core data model types
  - [x] 2.1 Define core types and status enum
    - Create `spec.go`: `Spec`, `PRD`, `Frontmatter`, `Status` constants
    - Create `errors.go`: `ValidationError`, `Severity`, `LifecycleError`, `IncompleteSpecError`
    - _Requirements: 01-REQ-1.1, 01-REQ-1.6_

  - [x] 2.2 Define requirements types
    - Create `requirements.go`: `Requirements`, `Requirement`, `UserStory`, `Criterion`, `CorrectnessProperty`, `ExecutionPath`, `ExecutionPathStep`, `ErrorHandlingEntry`
    - Implement EARS discriminated union: `Criterion` struct with pattern-specific fields using `omitempty` for non-applicable fields, `return_contract` always serialized
    - _Requirements: 01-REQ-1.2, 01-REQ-1.4_

  - [x] 2.3 Define test spec and tasks types
    - Create `testspec.go`: `TestSpecDoc`, `TestCase`, `PropertyTest`, `EdgeCaseTest`, `SmokeTest`, `Coverage`
    - Create `tasks.go`: `Tasks`, `TestCommands`, `TaskDependency`, `TaskGroup`, `Subtask`, `SubtaskState`, `VerificationSubtask`, `TraceabilityEntry`
    - Implement `SubtaskState.LegalTransitions()` method
    - _Requirements: 01-REQ-1.3, 01-REQ-1.5_

  - [x] 2.4 Define discovery types
    - Create `discover.go` (type definitions only): `DiscoveryResult`, `SpecEntry`, `DependencyGraph`, `TopologicalOrder()` method
    - Create `bootstrap.go` (type definitions only): `Bootstrap` struct
    - _Requirements: 01-REQ-9.1, 01-REQ-8.1_

  - [x] 2.V Verify task group 2
    - [x] Spec tests TS-01-1 through TS-01-5 pass: `go test -count=1 -run 'TS01_0[1-5]' ./...`
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-1.1 through 01-REQ-1.6 acceptance criteria met

- [x] 3. Serialization and PRD parsing
  - [x] 3.1 Implement deterministic JSON marshaling
    - Create `internal/jsonutil/marshal.go`: `MarshalDeterministic()` — sorted keys, 2-space indent, trailing newline
    - Create `internal/jsonutil/unmarshal.go`: `UnmarshalStrict()` — reject unknown fields
    - Ensure `null` for nil pointers, `[]` for empty slices
    - _Requirements: 01-REQ-3.2, 01-REQ-1.E1, 01-REQ-1.E2_

  - [x] 3.2 Implement YAML frontmatter serialization
    - Created `serialize.go` (root package, not internal/prd) to avoid import cycle: `serializePRD()` + `marshalFrontmatterOrdered()` — fixed field order, `---` delimiters via `internal/prd.AssemblePRDFile`
    - Use `gopkg.in/yaml.v3` encoder with ordered fields via yaml.Node
    - _Requirements: 01-REQ-3.3_

  - [x] 3.3 Implement PRD parsing
    - Create `internal/prd/parse.go`: `SplitFrontmatterBody()` — split on `---` delimiters, return raw YAML + body
    - Create `internal/prd/intent.go`: `ExtractIntent()` — find `## Intent` section, extract body between it and next `##` or EOF; `HasIntentSection()`
    - Root package `load.go` does YAML unmarshal into `Frontmatter` (avoids import cycle)
    - _Requirements: 01-REQ-2.2_

  - [x] 3.4 Implement intent hash normalization
    - In `internal/lifecycle/intent.go`: `NormalizeIntent()` and `ComputeIntentHash()`
    - Pipeline: LF normalization → collapse blank lines → lower-case → trim → SHA-256
    - Root package `lifecycle.go` re-exports `ComputeIntentHash` using internal package
    - _Requirements: 01-REQ-7.2_

  - [x] 3.V Verify task group 3
    - [x] Spec tests TS-01-8, TS-01-9, TS-01-11, TS-01-12, TS-01-E1, TS-01-E2 pass
    - [x] Property test TS-01-P10 (null preservation) passes
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-2.2, 01-REQ-3.2, 01-REQ-3.3, 01-REQ-1.E1, 01-REQ-1.E2 met

- [x] 4. File I/O (Load and Save)
  - [x] 4.1 Implement LoadSpec
    - Create `load.go`: `LoadSpec(dir)` — validate dir, read all four files, parse each, return `*Spec`
    - Create `internal/ioutil/read.go`: file reading helpers
    - Handle missing files, malformed JSON, malformed YAML, missing Intent
    - _Requirements: 01-REQ-2.1, 01-REQ-2.3_

  - [x] 4.2 Implement SaveSpec with computed fields
    - Create `save.go`: `SaveSpec(dir, spec)` — validate dir exists, compute fields, serialize all four, write atomically
    - Compute `updated_at` to current UTC timestamp (ISO 8601/RFC3339Nano) before writing prd.md
    - Compute `coverage` field by cross-referencing test cases against requirements before writing test_spec.json
    - Create `internal/ioutil/write.go`: `WriteAtomic()` — write to temp file then rename
    - Handle write failures without leaving partial files; clean up temp files on error
    - Fixed: serialize.go now always double-quotes YAML string values for deterministic round-trips
    - Fixed: WriteAtomic detects read-only targets early (pre-flight check before rename)
    - _Requirements: 01-REQ-3.1, 01-REQ-3.4, 01-REQ-3.5, 01-REQ-3.6_

  - [x] 4.3 Create golden testdata fixtures
    - Populated `testdata/valid_spec/` with complete, internally consistent spec files
    - JSON is deterministically formatted (sorted keys, 2-space indent)
    - YAML frontmatter has correct field order with all strings double-quoted
    - `LoadSpec("testdata/valid_spec")` → `SaveSpec(tmpdir)` produces byte-identical JSON files; prd.md identical except updated_at
    - Added missing `requirements.json`, `test_spec.json`, `tasks.json` to `testdata/no_intent/`
    - _Test Spec: TS-01-7, TS-01-10, TS-01-13_

  - [x] 4.V Verify task group 4
    - [x] Spec tests TS-01-7, TS-01-10, TS-01-13, TS-01-46, TS-01-47 pass (load, save, round-trip, computed fields)
    - [x] Edge case tests TS-01-E3 through TS-01-E9 pass
    - [x] Property tests TS-01-P1 (round-trip idempotency), TS-01-P11 (computed coverage) pass
    - [x] Smoke tests TS-01-SMOKE-1, TS-01-SMOKE-2 pass
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-2.1 through 01-REQ-2.3, 01-REQ-3.1 through 01-REQ-3.6, all edge cases met

- [x] 5. Checkpoint — Data model + I/O complete
  - Ensure all model, serialization, and I/O tests pass.
  - Verify round-trip idempotency on golden fixtures.
  - Create or update documentation in README.md if needed.

- [x] 6. JSON Schema authoring and schema validation
  - [x] 6.1 Author JSON Schema files
    - Create `schemas/prd-frontmatter.v1.json`: validates 12 frontmatter fields, status enum, types
    - Create `schemas/requirements.v1.json`: validates requirements structure, discriminated `oneOf` for EARS patterns, ID format patterns
    - Create `schemas/test_spec.v1.json`: validates test spec structure, kind enum, ID formats
    - Create `schemas/tasks.v1.json`: validates tasks structure, kind enum, state enum, subtask ID format
    - Note: schema files placed in `internal/schema/` (required by go:embed); pure-Go validation used instead of external jsonschema library (not in go.mod)
    - _Requirements: 01-REQ-4.3_

  - [x] 6.2 Embed schemas and implement schema loading
    - Create `internal/schema/embed.go`: `//go:embed` for all four schema files
    - Expose via `Schemas()` map[string][]byte function
    - No external jsonschema library added (pure-Go validation in root validate.go instead)
    - _Requirements: 01-REQ-4.3_

  - [x] 6.3 Implement schema validation
    - Implemented `ValidateSchema(spec)`, `ValidateCrossFile(spec)`, `ValidateIDs(spec)`, `Validate(spec)`, `GetEmbeddedSchemas()` in root `validate.go`
    - All seven cross-file integrity rules implemented (integrity-1 through integrity-7)
    - All ID format patterns validated with regex; non-sequential IDs emit SeverityWarning
    - Return all errors (not just first) with file name, JSON path, description
    - _Requirements: 01-REQ-4.1, 01-REQ-4.2, 01-REQ-4.4, 01-REQ-5.1–5.7, 01-REQ-10.1–10.3_

  - [x] 6.V Verify task group 6
    - [x] Spec tests TS-01-14 through TS-01-17 pass
    - [x] Edge case tests TS-01-E10, TS-01-E11 pass
    - [x] Property test TS-01-P6 (schema soundness) passes
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-4.1 through 01-REQ-4.4, 01-REQ-4.E1, 01-REQ-4.E2 met

- [x] 7. Cross-file integrity and ID validation
  - [x] 7.1 Implement cross-file integrity checks
    - Create `internal/validate/crossfile.go`: `CrossFileIntegrity(spec)` — all 7 rules
    - Rule 1: requirement_id references resolve
    - Rule 2: requirement/edge case test coverage
    - Rule 3: property test coverage
    - Rule 4: execution path smoke test coverage
    - Rule 5: test_spec_id references in tasks resolve
    - Rule 7: spec_id/spec_name consistency across files
    - Note: implemented in root `validate.go` (crossFileRule1–7) to avoid import cycles; `internal/validate/helpers.go` provides pure utility functions (regex patterns, extractBacktickTerms, checkSequentiality)
    - _Requirements: 01-REQ-5.1 through 01-REQ-5.5, 01-REQ-5.7_

  - [x] 7.2 Implement glossary cross-check (rule 6)
    - In root `validate.go` (crossFileRule6): extract backtick-wrapped terms from checked fields, verify glossary entries
    - `internal/validate/helpers.go` provides `ExtractBacktickTerms()` helper
    - Checked fields: action, trigger, condition, error_condition, state, feature, for_any, invariant
    - _Requirements: 01-REQ-5.6_

  - [x] 7.3 Implement ID format validation
    - `internal/validate/helpers.go`: ID regex patterns for all Appendix A formats
    - Root `validate.go`: `ValidateIDs(spec)` validates all ID patterns, spec_id matching, positive integers
    - Non-sequential IDs produce SeverityWarning (not error)
    - _Requirements: 01-REQ-10.1, 01-REQ-10.2, 01-REQ-10.3_

  - [x] 7.4 Wire up public Validate API
    - Root `validate.go`: `Validate(spec)` calls ValidateSchema + ValidateCrossFile + ValidateIDs
    - Root `validate.go`: `ValidateCrossFile(spec)` public API delegates to crossFileRule1–7
    - _Requirements: 01-REQ-5.1_

  - [x] 7.V Verify task group 7
    - [x] Spec tests TS-01-18 through TS-01-24, TS-01-43 through TS-01-45 pass
    - [x] Edge case tests TS-01-E12, TS-01-E23, TS-01-E24 pass
    - [x] Property tests TS-01-P4, TS-01-P9 pass
    - [x] Smoke test TS-01-SMOKE-3 passes
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-5.1 through 01-REQ-5.7, 01-REQ-10.1 through 01-REQ-10.3, all edge cases met

- [x] 8. Markdown rendering
  - [x] 8.1 Implement EARS sentence rendering
    - Create `internal/render/ears.go`: `RenderEARS(criterion)` — six templates from §5.2.1
    - Handle null `return_contract` (omit clause) and empty fields (`<missing>` placeholder)
    - Handle non-null `return_contract`: append " AND return {return_contract}"
    - _Requirements: 01-REQ-6.2, 01-REQ-6.E1, 01-REQ-6.E2_

  - [x] 8.2 Implement per-file rendering
    - Create `internal/render/requirements.go`: `renderRequirements(req)` → markdown
    - Create `internal/render/testspec.go`: `renderTestSpec(ts)` → markdown
    - Create `internal/render/tasks.go`: `renderTasks(tasks)` → markdown
    - Create `render.go`: `RenderRequirements()`, `RenderTestSpec()`, `RenderTasks()` public API
    - _Requirements: 01-REQ-6.1, 01-REQ-6.3_

  - [x] 8.3 Implement combined rendering
    - In `render.go`: `RenderCombined(spec)` — PRD body verbatim + separator + rendered requirements + test_spec + tasks
    - Ensure correct section ordering
    - _Requirements: 01-REQ-6.4_

  - [x] 8.V Verify task group 8
    - [x] Spec tests TS-01-25 through TS-01-28 pass
    - [x] Edge case tests TS-01-E13, TS-01-E14 pass
    - [x] Property test TS-01-P2 (EARS determinism) passes
    - [x] Smoke tests TS-01-SMOKE-4, TS-01-SMOKE-5 pass
    - [x] All existing tests still pass: `go test -count=1 ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-6.1 through 01-REQ-6.4, 01-REQ-6.E1, 01-REQ-6.E2 met

- [ ] 9. Lifecycle management
  - [ ] 9.1 Implement lifecycle transition graph
    - Create `internal/lifecycle/transitions.go`: `ValidateTransition(current, target)` — legal edge checking
    - Define adjacency list for: draft→active, draft→archived, active→sealed, sealed→superseded, sealed→archived
    - _Requirements: 01-REQ-7.1_

  - [ ] 9.2 Implement lifecycle guards
    - Create `internal/lifecycle/guards.go`: `ApplyGuards(spec, current, target)` — mutation restrictions
    - Draft→active: compute and set intent hash
    - Active: reject Intent/immutable field changes
    - Sealed/superseded/archived: reject all changes
    - _Requirements: 01-REQ-7.2, 01-REQ-7.3, 01-REQ-7.4_

  - [ ] 9.3 Implement supersede workflow
    - Add deprecation banner insertion to all four files
    - Wire into sealed→superseded transition
    - _Requirements: 01-REQ-7.5_

  - [ ] 9.4 Wire up public Transition API
    - Create `lifecycle.go`: `Transition(spec, target)` — returns new Spec (immutable), validates transition, applies guards
    - Ensure original spec is not modified
    - _Requirements: 01-REQ-7.1_

  - [ ] 9.V Verify task group 9
    - [ ] Spec tests TS-01-29 through TS-01-33 pass
    - [ ] Edge case tests TS-01-E15, TS-01-E16 pass
    - [ ] Property tests TS-01-P3 (lifecycle monotonicity), TS-01-P5 (intent hash stability) pass
    - [ ] Smoke test TS-01-SMOKE-6 passes
    - [ ] All existing tests still pass: `go test -count=1 ./...`
    - [ ] No linter warnings introduced: `go vet ./...`
    - [ ] Requirements 01-REQ-7.1 through 01-REQ-7.5, 01-REQ-7.E1, 01-REQ-7.E2 met

- [ ] 10. Bootstrap mode
  - [ ] 10.1 Implement NewBootstrap and file writers
    - In `bootstrap.go`: `NewBootstrap(dir, specID, specName)` — create directory, initialize tracker
    - Implement `WritePRD()`, `WriteRequirements()`, `WriteTestSpec()`, `WriteTasks()` — per-file schema validation, write to disk
    - Use `sync.Mutex` for thread safety
    - _Requirements: 01-REQ-8.1, 01-REQ-8.4_

  - [ ] 10.2 Implement Finalize
    - In `bootstrap.go`: `Finalize()` — check completeness, run full validation, return `*Spec`
    - Handle: missing files → `IncompleteSpecError`, validation failures → `[]ValidationError`
    - _Requirements: 01-REQ-8.2, 01-REQ-8.3_

  - [ ] 10.3 Handle bootstrap edge cases
    - Overwrite on duplicate write (no error)
    - Error on existing folder
    - _Requirements: 01-REQ-8.E2, 01-REQ-8.E3_

  - [ ] 10.V Verify task group 10
    - [ ] Spec tests TS-01-34 through TS-01-37 pass
    - [ ] Edge case tests TS-01-E17 through TS-01-E19 pass
    - [ ] Property test TS-01-P8 (bootstrap deferred validation) passes
    - [ ] Smoke test TS-01-SMOKE-7 passes
    - [ ] All existing tests still pass: `go test -count=1 ./...`
    - [ ] No linter warnings introduced: `go vet ./...`
    - [ ] Requirements 01-REQ-8.1 through 01-REQ-8.4, 01-REQ-8.E1 through 01-REQ-8.E3 met

- [ ] 11. Spec discovery
  - [ ] 11.1 Implement spec root scanning
    - Create `internal/discovery/scan.go`: `ScanRoot(root)` — find dirs matching `{NN}_{snake_case}`, skip `archive/`
    - Handle empty root (default to cwd)
    - _Requirements: 01-REQ-9.1, 01-REQ-9.2, 01-REQ-9.5_

  - [ ] 11.2 Implement metadata loading
    - Create `internal/discovery/metadata.go`: `LoadMetadata(dir)` — read PRD frontmatter only (no full load)
    - Mark incomplete specs (missing files) with `Complete: false`
    - _Requirements: 01-REQ-9.3_

  - [ ] 11.3 Implement dependency graph construction
    - Create `internal/discovery/graph.go`: `BuildGraph(entries, root)` — read tasks.json dependencies, build adjacency list
    - Implement `TopologicalOrder()` with cycle detection (Kahn's algorithm)
    - _Requirements: 01-REQ-9.4_

  - [ ] 11.4 Wire up public DiscoverSpecs API
    - In `discover.go`: `DiscoverSpecs(root)` — scan, load metadata, build graph, return `*DiscoveryResult`
    - _Requirements: 01-REQ-9.1_

  - [ ] 11.V Verify task group 11
    - [ ] Spec tests TS-01-38 through TS-01-42 pass
    - [ ] Edge case tests TS-01-E20 through TS-01-E22 pass
    - [ ] Property test TS-01-P7 (discovery completeness) passes
    - [ ] Smoke test TS-01-SMOKE-8 passes
    - [ ] All existing tests still pass: `go test -count=1 ./...`
    - [ ] No linter warnings introduced: `go vet ./...`
    - [ ] Requirements 01-REQ-9.1 through 01-REQ-9.5, 01-REQ-9.E1 through 01-REQ-9.E3 met

- [ ] 12. Wiring verification

  - [ ] 12.1 Trace every execution path from design.md end-to-end
    - For each of the 8 paths, verify the entry point actually calls the next function in the chain (read the calling code, do not assume)
    - Confirm no function in the chain is a stub (`return nil`, `return []`, `panic("not implemented")`) that was never replaced
    - Every path must be live in production code — errata or deferrals do not satisfy this check
    - _Requirements: all_

  - [ ] 12.2 Verify return values propagate correctly
    - For every function in this spec that returns data consumed by a caller, confirm the caller receives and uses the return value
    - Key chains: LoadSpec → Spec, ValidateSchema → []ValidationError, RenderEARS → string used by renderRequirements
    - Grep for callers of each such function; confirm none discards the return
    - _Requirements: all_

  - [ ] 12.3 Run the integration smoke tests
    - All TS-01-SMOKE-1 through TS-01-SMOKE-8 tests pass using real components (no stub bypass)
    - _Test Spec: TS-01-SMOKE-1 through TS-01-SMOKE-8_

  - [ ] 12.4 Stub / dead-code audit
    - Search all files touched by this spec for: `return nil` on non-error returns, `return []` on non-empty returns, `panic(`, `// TODO`, `// stub`, `NotImplementedError`
    - Each hit must be either: (a) justified with a comment explaining why it is intentional, or (b) replaced with a real implementation
    - Document any intentional stubs here with rationale

  - [ ] 12.5 Cross-spec entry point verification
    - This is spec 01 — no upstream callers from other specs exist yet
    - Verify that the public API surface (LoadSpec, SaveSpec, Validate, Render*, Transition, NewBootstrap, DiscoverSpecs) is exported and callable
    - Verify Go module is importable as `github.com/agent-fox/afspec`
    - _Requirements: all_

  - [ ] 12.6 Thread safety audit
    - Run all tests with `-race` flag: `go test -race -count=1 ./...`
    - Verify `Bootstrap` methods use mutex correctly
    - Verify all exported types support concurrent reads (TS-01-6)
    - _Requirements: 01-REQ-1.6_

  - [ ] 12.V Verify wiring group
    - [ ] All smoke tests pass: `go test -count=1 -run 'SMOKE' ./...`
    - [ ] No unjustified stubs remain in touched files
    - [ ] All execution paths from design.md are live (traceable in code)
    - [ ] All cross-spec entry points are callable from production code
    - [ ] Race detector passes: `go test -race -count=1 ./...`
    - [ ] All existing tests still pass: `go test -count=1 ./...`

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
|---|---|---|---|
| 01-REQ-1.1 | TS-01-1 | 2.1 | spec_test.go::TestTS01_01 |
| 01-REQ-1.2 | TS-01-2 | 2.2 | spec_test.go::TestTS01_02 |
| 01-REQ-1.3 | TS-01-3 | 2.3 | spec_test.go::TestTS01_03 |
| 01-REQ-1.4 | TS-01-4 | 2.2 | spec_test.go::TestTS01_04 |
| 01-REQ-1.5 | TS-01-5 | 2.3 | spec_test.go::TestTS01_05 |
| 01-REQ-1.6 | TS-01-6 | 2.1, 12.6 | spec_test.go::TestTS01_06 |
| 01-REQ-1.E1 | TS-01-E1 | 3.1 | spec_test.go::TestTS01_E01 |
| 01-REQ-1.E2 | TS-01-E2 | 3.1 | spec_test.go::TestTS01_E02 |
| 01-REQ-2.1 | TS-01-7 | 4.1 | load_test.go::TestTS01_07 |
| 01-REQ-2.2 | TS-01-8 | 3.3 | load_test.go::TestTS01_08 |
| 01-REQ-2.3 | TS-01-9 | 3.1 | load_test.go::TestTS01_09 |
| 01-REQ-2.E1 | TS-01-E3 | 4.1 | load_test.go::TestTS01_E03 |
| 01-REQ-2.E2 | TS-01-E4 | 4.1 | load_test.go::TestTS01_E04 |
| 01-REQ-2.E3 | TS-01-E5 | 3.3 | load_test.go::TestTS01_E05 |
| 01-REQ-2.E4 | TS-01-E6 | 3.3 | load_test.go::TestTS01_E06 |
| 01-REQ-2.E5 | TS-01-E7 | 4.1 | load_test.go::TestTS01_E07 |
| 01-REQ-3.1 | TS-01-10 | 4.2 | save_test.go::TestTS01_10 |
| 01-REQ-3.2 | TS-01-11 | 3.1 | save_test.go::TestTS01_11 |
| 01-REQ-3.3 | TS-01-12 | 3.2 | save_test.go::TestTS01_12 |
| 01-REQ-3.4 | TS-01-13 | 4.2, 4.3 | save_test.go::TestTS01_13 |
| 01-REQ-3.5 | TS-01-46 | 4.2 | save_test.go::TestTS01_46 |
| 01-REQ-3.6 | TS-01-47 | 4.2 | save_test.go::TestTS01_47 |
| 01-REQ-3.E1 | TS-01-E8 | 4.2 | save_test.go::TestTS01_E08 |
| 01-REQ-3.E2 | TS-01-E9 | 4.2 | save_test.go::TestTS01_E09 |
| 01-REQ-4.1 | TS-01-14 | 6.3 | validate_test.go::TestTS01_14 |
| 01-REQ-4.2 | TS-01-15 | 6.3 | validate_test.go::TestTS01_15 |
| 01-REQ-4.3 | TS-01-16 | 6.1, 6.2 | validate_test.go::TestTS01_16 |
| 01-REQ-4.4 | TS-01-17 | 6.3 | validate_test.go::TestTS01_17 |
| 01-REQ-4.E1 | TS-01-E10 | 6.3 | validate_test.go::TestTS01_E10 |
| 01-REQ-4.E2 | TS-01-E11 | 6.1, 6.3 | validate_test.go::TestTS01_E11 |
| 01-REQ-5.1 | TS-01-18 | 7.1, 7.4 | validate_test.go::TestTS01_18 |
| 01-REQ-5.2 | TS-01-19 | 7.1 | validate_test.go::TestTS01_19 |
| 01-REQ-5.3 | TS-01-20 | 7.1 | validate_test.go::TestTS01_20 |
| 01-REQ-5.4 | TS-01-21 | 7.1 | validate_test.go::TestTS01_21 |
| 01-REQ-5.5 | TS-01-22 | 7.1 | validate_test.go::TestTS01_22 |
| 01-REQ-5.6 | TS-01-23 | 7.2 | validate_test.go::TestTS01_23 |
| 01-REQ-5.7 | TS-01-24 | 7.1 | validate_test.go::TestTS01_24 |
| 01-REQ-5.E1 | TS-01-E12 | 7.1 | validate_test.go::TestTS01_E12 |
| 01-REQ-6.1 | TS-01-25 | 8.2 | render_test.go::TestTS01_25 |
| 01-REQ-6.2 | TS-01-26 | 8.1 | render_test.go::TestTS01_26 |
| 01-REQ-6.3 | TS-01-27 | 8.2 | render_test.go::TestTS01_27 |
| 01-REQ-6.4 | TS-01-28 | 8.3 | render_test.go::TestTS01_28 |
| 01-REQ-6.E1 | TS-01-E13 | 8.1 | render_test.go::TestTS01_E13 |
| 01-REQ-6.E2 | TS-01-E14 | 8.1 | render_test.go::TestTS01_E14 |
| 01-REQ-7.1 | TS-01-29 | 9.1, 9.4 | lifecycle_test.go::TestTS01_29 |
| 01-REQ-7.2 | TS-01-30 | 9.2, 3.4 | lifecycle_test.go::TestTS01_30 |
| 01-REQ-7.3 | TS-01-31 | 9.2 | lifecycle_test.go::TestTS01_31 |
| 01-REQ-7.4 | TS-01-32 | 9.2 | lifecycle_test.go::TestTS01_32 |
| 01-REQ-7.5 | TS-01-33 | 9.3 | lifecycle_test.go::TestTS01_33 |
| 01-REQ-7.E1 | TS-01-E15 | 9.1 | lifecycle_test.go::TestTS01_E15 |
| 01-REQ-7.E2 | TS-01-E16 | 9.2 | lifecycle_test.go::TestTS01_E16 |
| 01-REQ-8.1 | TS-01-34 | 10.1 | bootstrap_test.go::TestTS01_34 |
| 01-REQ-8.2 | TS-01-35 | 10.1, 10.2 | bootstrap_test.go::TestTS01_35 |
| 01-REQ-8.3 | TS-01-36 | 10.2 | bootstrap_test.go::TestTS01_36 |
| 01-REQ-8.4 | TS-01-37 | 10.1 | bootstrap_test.go::TestTS01_37 |
| 01-REQ-8.E1 | TS-01-E17 | 10.2 | bootstrap_test.go::TestTS01_E17 |
| 01-REQ-8.E2 | TS-01-E18 | 10.3 | bootstrap_test.go::TestTS01_E18 |
| 01-REQ-8.E3 | TS-01-E19 | 10.3 | bootstrap_test.go::TestTS01_E19 |
| 01-REQ-9.1 | TS-01-38 | 11.1, 11.4 | discover_test.go::TestTS01_38 |
| 01-REQ-9.2 | TS-01-39 | 11.1 | discover_test.go::TestTS01_39 |
| 01-REQ-9.3 | TS-01-40 | 11.2 | discover_test.go::TestTS01_40 |
| 01-REQ-9.4 | TS-01-41 | 11.3 | discover_test.go::TestTS01_41 |
| 01-REQ-9.5 | TS-01-42 | 11.1 | discover_test.go::TestTS01_42 |
| 01-REQ-9.E1 | TS-01-E20 | 11.1 | discover_test.go::TestTS01_E20 |
| 01-REQ-9.E2 | TS-01-E21 | 11.2 | discover_test.go::TestTS01_E21 |
| 01-REQ-9.E3 | TS-01-E22 | 11.3 | discover_test.go::TestTS01_E22 |
| 01-REQ-10.1 | TS-01-43 | 7.3 | validate_test.go::TestTS01_43 |
| 01-REQ-10.2 | TS-01-44 | 7.3 | validate_test.go::TestTS01_44 |
| 01-REQ-10.3 | TS-01-45 | 7.3 | validate_test.go::TestTS01_45 |
| 01-REQ-10.E1 | TS-01-E23 | 7.3 | validate_test.go::TestTS01_E23 |
| 01-REQ-10.E2 | TS-01-E24 | 7.3 | validate_test.go::TestTS01_E24 |
| Property 1 | TS-01-P1 | 4.2 | save_test.go::TestPropertyP1 |
| Property 2 | TS-01-P2 | 8.1 | render_test.go::TestPropertyP2 |
| Property 3 | TS-01-P3 | 9.1 | lifecycle_test.go::TestPropertyP3 |
| Property 4 | TS-01-P4 | 7.1 | validate_test.go::TestPropertyP4 |
| Property 5 | TS-01-P5 | 9.2 | lifecycle_test.go::TestPropertyP5 |
| Property 6 | TS-01-P6 | 6.3 | validate_test.go::TestPropertyP6 |
| Property 7 | TS-01-P7 | 11.1 | discover_test.go::TestPropertyP7 |
| Property 8 | TS-01-P8 | 10.1 | bootstrap_test.go::TestPropertyP8 |
| Property 9 | TS-01-P9 | 7.3 | validate_test.go::TestPropertyP9 |
| Property 10 | TS-01-P10 | 3.1 | spec_test.go::TestPropertyP10 |
| Property 11 | TS-01-P11 | 4.2 | save_test.go::TestPropertyP11 |
| Path 1 | TS-01-SMOKE-1 | 4.1 | smoke_test.go::TestSmoke1 |
| Path 2 | TS-01-SMOKE-2 | 4.2 | smoke_test.go::TestSmoke2 |
| Path 3 | TS-01-SMOKE-3 | 7.4 | smoke_test.go::TestSmoke3 |
| Path 4 | TS-01-SMOKE-4 | 8.2 | smoke_test.go::TestSmoke4 |
| Path 5 | TS-01-SMOKE-5 | 8.3 | smoke_test.go::TestSmoke5 |
| Path 6 | TS-01-SMOKE-6 | 9.4 | smoke_test.go::TestSmoke6 |
| Path 7 | TS-01-SMOKE-7 | 10.2 | smoke_test.go::TestSmoke7 |
| Path 8 | TS-01-SMOKE-8 | 11.4 | smoke_test.go::TestSmoke8 |

## Notes

- Test fixtures in `testdata/` should cover all EARS patterns, null/empty edge cases, and cross-file reference scenarios.
- Property tests can use `testing/quick` from the standard library or a third-party library like `github.com/leanovate/gopter` for more control over generators.
- The `internal/` packages are implementation details. Only the root package `afspec` is exported.
- Each task group should be implementable in one coding session (~2-4 hours).
- The JSON Schema files (task group 6) are the most complex authoring task — budget extra time for the `requirements.v1.json` schema's discriminated union.
