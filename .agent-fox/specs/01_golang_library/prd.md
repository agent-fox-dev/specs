# Go Spec-Format Library (afspec)

## Intent

Build an idiomatic Go library that provides data structures, validation, file I/O, lifecycle management, and markdown rendering for the agent-fox specification format as defined in `docs/spec-format.md` v1.

## Goals

- Provide Go structs for all four spec artifacts: PRD (markdown with YAML frontmatter), requirements.json, test_spec.json, tasks.json.
- Read a spec folder from disk into in-memory structures.
- Write in-memory structures back to disk.
- Validate specs: JSON Schema validation per file, plus cross-file integrity checks.
- Render JSON artifacts to deterministic markdown (per-file and combined).
- Implement and enforce the spec lifecycle state machine (draft, active, sealed, superseded, archived) with all guards.
- Support an explicit bootstrap mode for sequential file creation with deferred cross-file validation.
- Bundle JSON Schema files as embedded resources via Go `embed`.
- Create the four JSON Schema files (requirements.v1.json, test_spec.v1.json, tasks.v1.json, prd-frontmatter.v1.json) as part of this spec's implementation.
- Guarantee idempotent round-trip: load followed by save followed by load produces identical in-memory state (excluding auto-computed fields).
- Automatically compute and populate the `coverage` field in `test_spec.json` on every save.
- Automatically update the `updated_at` timestamp in PRD frontmatter on every save.
- Provide spec root discovery: scan a root directory to enumerate available specs and resolve cross-spec dependencies.
- All exported types and functions must be safe for concurrent use from multiple goroutines.

## Non-Goals

- No JSON Patch (RFC 6902) mutation API. Consumers handle mutations.
- No per-actor permission enforcement. Consumers handle access control.
- No diff rendering. Only per-file and combined rendering.
- No LLM integration at this level.
- No CLI. This is a library-only package.
- No network access. Schemas are bundled, not fetched from URLs.

## Background

The spec format (`docs/spec-format.md` v1) defines a four-artifact package for spec-driven development. Each package consists of `prd.md` (markdown with YAML frontmatter), `requirements.json`, `test_spec.json`, and `tasks.json`. This library is a building block: other repositories will build on top of it (MCP servers, database bindings, CLI tools, etc.).

### Spec-Format Reference

The full specification is in `docs/spec-format.md`. Key sections for implementors:

- Section 3: Folder layout, naming convention (`{NN}_{snake_case_name}`), completeness rules.
- Section 4: PRD structure — YAML frontmatter (required fields, protected fields, mutable fields), body with mandatory `## Intent` section, intent hash computation.
- Section 5: Requirements — requirements array, EARS criteria as discriminated union on `ears_pattern`, correctness properties, execution paths, error handling entries.
- Section 6: Test specification — test cases (1:1 with acceptance criteria), property tests (1:1 with correctness properties), edge case tests, smoke tests (1:1 with execution paths), computed coverage.
- Section 7: Tasks — task groups with subtask state machine (pending, queued, in_progress, done, pending_reevaluation, dropped), verification subtasks, cross-spec dependencies, traceability entries.
- Section 8: Lifecycle — five states with transition rules and mutation guards.
- Section 9: Validation — schema validation + seven cross-file integrity rules.
- Section 11: Rendering — deterministic markdown output from JSON, EARS sentence templates.

### Data Model Summary

The library must model these entities:

**PRD** — YAML frontmatter struct with 12 fields (spec_id, spec_name, title, status, created_at, updated_at, owner, source, supersedes, tags, intent_hash, schema_version) plus a free-form markdown body. The `## Intent` section body is machine-read for hash computation.

**Requirements** — Top-level container with introduction, glossary (term-to-definition map), array of Requirement objects (each with user_story, acceptance_criteria as EARS criteria, edge_cases), correctness properties, execution paths, error handling entries.

**EARS Criteria** — Discriminated union on `ears_pattern` with six variants (ubiquitous, event_driven, complex_event, state_driven, unwanted, optional). Each variant has pattern-specific fields plus common fields (id, system, action, return_contract).

**TestSpec** — Test cases, property tests, edge case tests, smoke tests, and a computed coverage object.

**Tasks** — Test commands, cross-spec dependencies, task groups (each with subtasks and a verification subtask), and traceability entries.

**Subtask State Machine** — Six states (pending, queued, in_progress, done, pending_reevaluation, dropped) with defined legal transitions per `docs/spec-format.md` §7.3.1.

### Validation Rules

**Schema validation (§9.1):** Per-file JSON Schema validation. Rejects malformed structure, missing fields, EARS pattern mismatches, illegal state transitions, invalid ID formats.

**Cross-file integrity (§9.2):** Seven rules:
1. Every `requirement_id` referenced in test_spec.json, tasks.json traceability, and error_handling must exist in requirements.json.
2. Every requirement and edge case must have a test case in test_spec.json.
3. Every correctness property must have a property test.
4. Every execution path must have a smoke test.
5. Every `test_spec_id` in tasks.json must exist in test_spec.json.
6. Glossary cross-check: backtick-wrapped terms in checked fields must have glossary entries.
7. `spec_id` and `spec_name` must be consistent across all four files.

### Rendering Rules

Rendering applies only to JSON artifacts (requirements.json, test_spec.json, tasks.json). The PRD is already markdown and is not rendered — it is included as-is.

EARS sentences are rendered from decomposed fields using templates (§5.2.1). Rendering is deterministic: same in-memory state produces byte-identical markdown output.

Render targets:
- **Per-file**: One JSON artifact rendered to markdown.
- **Combined**: The PRD markdown (as-is) with the rendered JSON artifacts appended, in order: prd, requirements, test_spec, tasks.

### Lifecycle Rules

Five states: draft, active, sealed, superseded, archived.

- draft: All mutations allowed including Intent edits.
- active: All mutations except Intent section and immutable frontmatter (created_at, spec_id, spec_name). Intent hash is computed and locked at draft-to-active transition.
- sealed: No mutations allowed.
- superseded: No mutations allowed. Deprecation banner added automatically.
- archived: No mutations allowed.

Transition graph: draft→active, active→sealed, sealed→superseded, sealed→archived, draft→archived.

### Bootstrap Mode

During creation, files come into existence sequentially. The library operates in bootstrap mode: cross-file validation is deferred until all four files are written. A partially-created spec is in an "incomplete" state, not invalid but not yet valid.

### Automatic Behaviors on Save

Two fields are automatically managed by the library on every save operation:

- **`updated_at`**: Set to the current UTC timestamp (ISO 8601) on every save of `prd.md` frontmatter. The caller does not set this field.
- **`coverage`**: The `coverage` field in `test_spec.json` is computed (not authored). On every save, the library scans test cases, property tests, edge case tests, and smoke tests against the requirements in the same spec to populate `requirements_covered`, `properties_covered`, `paths_covered`, and `gaps`. A non-empty `gaps` array is a validation warning, not a blocking error.

### Intent Hash Computation

The intent hash is a SHA-256 hex digest of the `## Intent` section body after normalization:

1. Extract the text between `## Intent` and the next `##` heading (or end of file).
2. Normalize line endings to LF (`\n`).
3. Collapse multiple consecutive blank lines into a single blank line.
4. Lower-case the entire text.
5. Trim leading and trailing whitespace.
6. Compute SHA-256 of the resulting bytes and store as lowercase hex.

### Spec Root and Discovery

The library must have the concept of a "spec root" — the directory containing spec folders (e.g., `.agent-fox/specs/`). If not provided, it defaults to the current working directory.

The library must provide a discovery function that scans the spec root to:
- Enumerate all valid spec folders (matching the `{NN}_{snake_case_name}` pattern).
- Skip the `archive/` subdirectory.
- Load spec metadata (at minimum: spec_id, spec_name, status) without fully loading all artifacts.
- Build a dependency graph from cross-spec dependency declarations in tasks.json.

This is required because specs can have cross-spec dependencies that must be resolvable.

### ID Format Reference

- Requirement: `{spec_id}-REQ-{N}`
- Acceptance criterion: `{spec_id}-REQ-{N}.{C}`
- Edge case: `{spec_id}-REQ-{N}.E{C}`
- Correctness property: `{spec_id}-PROP-{N}`
- Execution path: `{spec_id}-PATH-{N}`
- Error handling: `{spec_id}-ERR-{N}`
- Test case: `TS-{spec_id}-{N}`
- Property test: `TS-{spec_id}-P{N}`
- Edge case test: `TS-{spec_id}-E{N}`
- Smoke test: `TS-{spec_id}-SMOKE-{N}`

## Design Decisions

1. **Module path**: The Go module is `github.com/agent-fox/afspec`. The library code lives at the package root (not in a subdirectory). The existing repo-level `go.mod` is the library's module file. The `cmd/`, `internal/`, and other directories coexist in the same module. Consumers import the library as `github.com/agent-fox/afspec`. Sub-packages (e.g., for validation, rendering) are imported as `github.com/agent-fox/afspec/validation`, etc.
2. **No mutation API**: Read, write, validate, render only. Consumers build mutation logic on top.
3. **No permission enforcement**: Roles are documented but not enforced by the library.
4. **Render scope**: Per-file and combined only. No diff rendering. The combined render includes the PRD as-is (not re-rendered) followed by rendered JSON artifacts.
5. **Lifecycle enforcement**: Full state machine with all guards (intent hash, mutation restrictions per state).
6. **Bootstrap mode**: Explicit `BootstrapSpec` API that defers cross-file validation until `Finalize()` is called.
7. **Bundled schemas**: JSON schemas embedded via `//go:embed` directive. The four schema files are authored as part of this spec's implementation scope.
8. **Idempotency guarantee**: Byte-identical output for same in-memory state. JSON files sorted by key, consistent indentation (2 spaces). YAML frontmatter field order fixed.
9. **Error handling style**: Return `error` values (no panics). Validation returns a structured error list, not just the first error.
10. **Go version**: Go 1.26+ as specified in the repo's `go.mod`.
11. **External dependencies**: Minimize. Use `gopkg.in/yaml.v3` for YAML, `github.com/santhosh-tekuri/jsonschema` or similar for JSON Schema validation. Standard library for JSON and file I/O.
12. **Thread safety**: All exported types and functions must be safe for concurrent use. Use value types (structs) where possible; where shared mutable state is needed, protect with appropriate synchronization.
13. **Spec root**: The library operates relative to a configurable spec root directory. If not provided, defaults to the current working directory. Discovery scans the spec root for valid spec folders, skipping `archive/`.
14. **Intent hash normalization**: LF line endings, collapse multiple blank lines, lower-case, trim whitespace — then SHA-256.
15. **Cross-library consistency**: The Go and Python libraries must produce byte-identical output for the same input. Verified via shared golden fixture files in `testdata/golden/` at the monorepo root. Each fixture is a complete spec folder with all four artifacts. Both libraries' test suites load the same fixtures, process them (round-trip, render), and compare output byte-for-byte. The golden fixtures are authored once and shared.
16. **Computed fields on save**: The library automatically computes `coverage` in test_spec.json and sets `updated_at` in PRD frontmatter on every save. Callers do not set these fields manually.
17. **Atomic saves**: Save operations use write-to-temporary-file-then-rename to prevent partial writes on failure. If any file in a multi-file save fails, previously written files in the same save are cleaned up.

## Source

Source: docs/spec-format.md + input provided by Michael Kuehl via interactive prompt
