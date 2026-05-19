# Requirements Document

## Introduction

This document specifies the requirements for the Go spec-format library (`afspec`). The library provides data structures, file I/O, validation, rendering, lifecycle management, and discovery for the agent-fox specification format defined in `docs/spec-format.md` v1. It is a building block consumed by other tools (CLI, MCP servers, database bindings).

## Glossary

| Term | Definition |
|------|-----------|
| spec | A four-artifact package (prd.md, requirements.json, test_spec.json, tasks.json) representing one feature or concern. |
| spec root | The directory containing spec folders (e.g., `.agent-fox/specs/`). Defaults to the current working directory if not provided. |
| spec folder | A directory within the spec root containing a spec's four artifacts, named `{NN}_{snake_case_name}`. |
| PRD | Product Requirements Document — the narrative markdown artifact with YAML frontmatter (`prd.md`). |
| frontmatter | YAML metadata block at the top of `prd.md`, delimited by `---` lines. Contains 12 structured fields. |
| EARS | Easy Approach to Requirements Syntax — a pattern language for writing testable requirements with six variants. |
| `ears_pattern` | The discriminator field in an EARS criterion that selects one of six variants: ubiquitous, event_driven, complex_event, state_driven, unwanted, optional. |
| discriminated union | A data type that holds one of several variants, identified by a tag field (`ears_pattern`). |
| bootstrap mode | A library mode where cross-file validation is deferred, allowing spec files to be created one at a time. |
| `intent_hash` | SHA-256 hex digest of the normalized `## Intent` section body. Computed at the draft→active transition and verified on subsequent mutations. |
| cross-file integrity | Validation rules (§9.2 of spec-format.md) that check consistency across all four spec artifacts. |
| lifecycle state machine | The five-state machine (draft, active, sealed, superseded, archived) governing spec mutation permissions. |
| idempotent round-trip | The guarantee that loading a spec from disk and saving it back without modification produces byte-identical files. |
| schema validation | Per-file validation of JSON/YAML structure against bundled JSON Schema files. |
| per-file rendering | Converting a single JSON artifact to its markdown representation. |
| combined rendering | Producing a single document with the PRD markdown (verbatim) followed by rendered JSON artifacts in order. |
| `spec_id` | The numeric prefix of a spec folder, stored as a string (e.g., `"05"`). |
| `spec_name` | The snake_case slug suffix of a spec folder name (e.g., `"my_feature"`). |
| `return_contract` | An optional field on EARS criteria describing what the function returns to callers. Null when no return value is relevant. |
| subtask state machine | The six-state machine (pending, queued, in_progress, done, pending_reevaluation, dropped) for task execution tracking. |
| intent normalization | The process of normalizing the Intent section body before hashing: LF line endings, collapse multiple blank lines, lower-case, trim whitespace. |
| atomic write | A file write strategy using write-to-temporary-file-then-rename to prevent partial writes on failure. |
| computed coverage | The `coverage` field in test_spec.json, which is populated automatically by the library on every save rather than authored manually. |
| golden fixture | A complete spec folder with all four artifacts used as a shared test reference for verifying cross-library consistency between Go and Python implementations. |

## Requirements

### Requirement 1: Data Model Fidelity

**User Story:** As a library consumer, I want Go types that faithfully represent all spec-format entities, so that I can work with specs programmatically without data loss.

#### Acceptance Criteria

[01-REQ-1.1] THE library SHALL provide exported Go types for PRD frontmatter containing all 12 fields (`spec_id`, `spec_name`, `title`, `status`, `created_at`, `updated_at`, `owner`, `source`, `supersedes`, `tags`, `intent_hash`, `schema_version`) and a separate markdown body string.

[01-REQ-1.2] THE library SHALL provide exported Go types for the requirements top-level container (`spec_id`, `spec_name`, `schema_version`, `introduction`, `glossary`, `requirements`, `correctness_properties`, `execution_paths`, `error_handling`) and all nested types: Requirement, UserStory, CorrectnessProperty, ExecutionPath, ExecutionPathStep, ErrorHandlingEntry.

[01-REQ-1.3] THE library SHALL provide exported Go types for the test spec top-level container (`test_cases`, `property_tests`, `edge_case_tests`, `smoke_tests`, `coverage`) and the tasks top-level container (`test_commands`, `dependencies`, `task_groups`, `traceability`) with all nested types: TestCase, PropertyTest, EdgeCaseTest, SmokeTest, Coverage, TaskGroup, Subtask, VerificationSubtask, Dependency, TraceabilityEntry.

[01-REQ-1.4] THE library SHALL represent EARS criteria as a discriminated union on `ears_pattern` with six variants (ubiquitous, event_driven, complex_event, state_driven, unwanted, optional), each variant exposing only the fields valid for its pattern plus the common fields (`id`, `system`, `action`, `return_contract`).

[01-REQ-1.5] THE library SHALL represent the subtask state as an enumerated type with six values (pending, queued, in_progress, done, pending_reevaluation, dropped) AND enforce legal transitions as defined in spec-format.md §7.3.1.

[01-REQ-1.6] THE library SHALL make all exported types safe for concurrent read access from multiple goroutines.

#### Edge Cases

[01-REQ-1.E1] IF a JSON field is null (e.g., `return_contract`, `intent_hash`), THEN THE library SHALL represent it using a Go pointer type or equivalent that preserves null semantics during round-trip serialization (null in → null out, not omitted or zero-valued).

[01-REQ-1.E2] IF a required array field is present but empty (e.g., `edge_cases: []`), THEN THE library SHALL represent it as an empty slice (not nil) to ensure JSON serialization produces `[]` rather than `null`.

---

### Requirement 2: Spec Loading

**User Story:** As a library consumer, I want to load a spec folder from disk into in-memory structures, so that I can inspect and operate on spec data programmatically.

#### Acceptance Criteria

[01-REQ-2.1] WHEN a valid spec folder path is provided, THE library SHALL read all four files (`prd.md`, `requirements.json`, `test_spec.json`, `tasks.json`) AND return populated in-memory structures.

[01-REQ-2.2] WHEN loading `prd.md`, THE library SHALL parse the YAML frontmatter (delimited by `---` lines) and the markdown body separately, AND extract the `## Intent` section body for hash computation.

[01-REQ-2.3] WHEN loading JSON files, THE library SHALL unmarshal into the corresponding typed Go structs, preserving all field values including nulls AND return the populated struct to the caller.

#### Edge Cases

[01-REQ-2.E1] IF a spec folder is missing one or more of the four required files, THEN THE library SHALL return an error listing which files are absent.

[01-REQ-2.E2] IF a JSON file contains malformed JSON, THEN THE library SHALL return a parse error identifying the file name and the parse failure details.

[01-REQ-2.E3] IF `prd.md` has malformed YAML frontmatter (unparseable YAML between `---` delimiters), THEN THE library SHALL return a parse error.

[01-REQ-2.E4] IF `prd.md` does not contain a `## Intent` section, THEN THE library SHALL return a validation error.

[01-REQ-2.E5] IF the spec folder path does not exist or is not a directory, THEN THE library SHALL return an error.

---

### Requirement 3: Spec Saving

**User Story:** As a library consumer, I want to write in-memory spec structures back to disk, so that modifications are persisted deterministically and automatic fields are computed correctly.

#### Acceptance Criteria

[01-REQ-3.1] WHEN in-memory structures are saved, THE library SHALL write all four files (`prd.md`, `requirements.json`, `test_spec.json`, `tasks.json`) to the specified directory.

[01-REQ-3.2] THE library SHALL produce deterministic JSON output: keys sorted alphabetically, 2-space indentation, and a trailing newline.

[01-REQ-3.3] THE library SHALL produce deterministic YAML frontmatter with a fixed field order: `spec_id`, `spec_name`, `title`, `status`, `created_at`, `updated_at`, `owner`, `source`, `supersedes`, `tags`, `intent_hash`, `schema_version`.

[01-REQ-3.4] WHEN a spec is loaded from disk and saved without modification, THE library SHALL produce byte-identical files (except for the `updated_at` field, which is always set to the current timestamp) AND return identical in-memory structures on subsequent reload (idempotent round-trip).

[01-REQ-3.5] WHEN saving `prd.md`, THE library SHALL set the `updated_at` frontmatter field to the current UTC timestamp in ISO 8601 format before writing.

[01-REQ-3.6] WHEN saving `test_spec.json`, THE library SHALL compute the `coverage` field by scanning test cases, property tests, edge case tests, and smoke tests against the spec's requirements AND populate `requirements_covered`, `properties_covered`, `paths_covered`, and `gaps` AND return the updated test spec structure with computed coverage to the caller.

#### Edge Cases

[01-REQ-3.E1] IF the target directory does not exist, THEN THE library SHALL return an error without creating the directory.

[01-REQ-3.E2] IF writing any file fails mid-operation (e.g., permission denied, disk full), THEN THE library SHALL return an error and not leave partially-written files in the target directory.

---

### Requirement 4: Schema Validation

**User Story:** As a library consumer, I want to validate spec files against JSON Schema, so that structural errors are caught before they propagate.

#### Acceptance Criteria

[01-REQ-4.1] WHEN validating a spec, THE library SHALL validate each JSON file against its corresponding bundled JSON Schema (`requirements.v1.json`, `test_spec.v1.json`, `tasks.v1.json`).

[01-REQ-4.2] WHEN validating `prd.md`, THE library SHALL parse the YAML frontmatter, convert it to a JSON-compatible representation, and validate against `prd-frontmatter.v1.json`.

[01-REQ-4.3] THE library SHALL embed four JSON Schema files using Go's `//go:embed` directive AND expose the schema version information to callers.

[01-REQ-4.4] IF schema validation finds errors, THEN THE library SHALL return all errors (not just the first) with file name, JSON path, and human-readable description for each violation.

#### Edge Cases

[01-REQ-4.E1] IF a JSON file contains fields not defined in the schema, THEN THE library SHALL reject it with an error identifying the unknown field path.

[01-REQ-4.E2] IF an EARS criterion has fields that are invalid for its declared `ears_pattern` (e.g., a `trigger` field on a `ubiquitous` pattern), THEN THE library SHALL reject it with an error identifying the criterion ID and the invalid field.

---

### Requirement 5: Cross-File Integrity Validation

**User Story:** As a library consumer, I want to check cross-file consistency, so that all spec artifacts are verified to be internally coherent.

#### Acceptance Criteria

[01-REQ-5.1] WHEN cross-file validation is run on a complete spec, THE library SHALL check all seven integrity rules from spec-format.md §9.2 AND return a list of all violations found.

[01-REQ-5.2] THE library SHALL verify every `requirement_id` referenced in `test_spec.json` test cases, `tasks.json` traceability entries, and `requirements.json` error_handling entries exists as an acceptance criterion or edge case ID in `requirements.json` (rule 1).

[01-REQ-5.3] THE library SHALL verify every acceptance criterion and edge case in `requirements.json` has a corresponding test case (by `requirement_id`) in `test_spec.json` (rule 2).

[01-REQ-5.4] THE library SHALL verify every correctness property in `requirements.json` has a corresponding property test (by `property_id`) in `test_spec.json` (rule 3) AND every execution path has a corresponding smoke test (by `execution_path_id`) (rule 4).

[01-REQ-5.5] THE library SHALL verify every `test_spec_id` referenced in `tasks.json` traceability entries and subtask `test_spec_refs` exists in `test_spec.json` (rule 5).

[01-REQ-5.6] THE library SHALL verify that every backtick-wrapped term in checked fields (`action`, `trigger`, `condition`, `error_condition`, `state`, `feature`, `for_any`, `invariant`) of `requirements.json` has a corresponding entry in the glossary (rule 6).

[01-REQ-5.7] THE library SHALL verify that `spec_id` and `spec_name` are identical across all four files: PRD frontmatter, requirements.json, test_spec.json, and tasks.json (rule 7).

#### Edge Cases

[01-REQ-5.E1] WHILE a spec is in bootstrap mode with fewer than four files written, THE library SHALL skip cross-file rules that reference missing files and validate only the files present.

---

### Requirement 6: Markdown Rendering

**User Story:** As a library consumer, I want to render JSON spec artifacts to markdown, so that I can produce human-readable documentation from structured data.

#### Acceptance Criteria

[01-REQ-6.1] WHEN rendering a JSON artifact to markdown, THE library SHALL produce deterministic output: the same in-memory state SHALL always produce byte-identical markdown AND return the rendered bytes to the caller.

[01-REQ-6.2] WHEN rendering EARS criteria from `requirements.json`, THE library SHALL use the six sentence templates from spec-format.md §5.2.1 (ubiquitous: "THE {system} SHALL {action}", event_driven: "WHEN {trigger}, THE {system} SHALL {action}", etc.).

[01-REQ-6.3] THE library SHALL support per-file rendering: accept one loaded JSON artifact (requirements, test_spec, or tasks) and return its markdown representation.

[01-REQ-6.4] THE library SHALL support combined rendering: produce a single document containing the PRD markdown verbatim, followed by the rendered requirements, test_spec, and tasks markdown in that order, AND return the complete document to the caller.

#### Edge Cases

[01-REQ-6.E1] IF a required field for EARS rendering is an empty string, THEN THE library SHALL render a placeholder string (`<missing>`) in that field's position.

[01-REQ-6.E2] IF the `return_contract` field on a criterion is null or an empty string, THEN THE library SHALL omit the return contract clause from the rendered EARS sentence.

---

### Requirement 7: Lifecycle Management

**User Story:** As a library consumer, I want to manage spec lifecycle transitions programmatically, so that workflow rules are enforced consistently.

#### Acceptance Criteria

[01-REQ-7.1] THE library SHALL enforce the lifecycle transition graph: draft→active, active→sealed, sealed→superseded, sealed→archived, draft→archived AND reject all other transitions.

[01-REQ-7.2] WHEN transitioning from draft to active, THE library SHALL compute the `intent_hash` (SHA-256 of the normalized `## Intent` section body) AND store it in the PRD frontmatter AND return the updated spec to the caller.

[01-REQ-7.3] WHILE a spec is in active state, THE library SHALL reject any mutation to the `## Intent` section body or to immutable frontmatter fields (`created_at`, `spec_id`, `spec_name`) AND return an error identifying the rejected field.

[01-REQ-7.4] WHILE a spec is in sealed, superseded, or archived state, THE library SHALL reject all mutations AND return an error identifying the current state.

[01-REQ-7.5] WHEN transitioning to superseded state, THE library SHALL add a deprecation banner to all four files in the spec folder AND set the `supersedes` field on the superseding spec's frontmatter.

#### Edge Cases

[01-REQ-7.E1] IF an illegal state transition is attempted (e.g., draft→sealed, active→draft), THEN THE library SHALL return an error naming the current state and the requested target state.

[01-REQ-7.E2] IF the `## Intent` section body has been altered since the draft→active transition (recomputed hash differs from stored `intent_hash`), THEN THE library SHALL reject the save with an intent-tamper error.

---

### Requirement 8: Bootstrap Mode

**User Story:** As a library consumer, I want to create specs incrementally, so that I can author artifacts one at a time during the creation workflow.

#### Acceptance Criteria

[01-REQ-8.1] THE library SHALL provide a `BootstrapSpec` API that creates a new spec folder and allows files to be written one at a time AND return a handle for subsequent file additions.

[01-REQ-8.2] WHILE in bootstrap mode, THE library SHALL defer all cross-file validation until `Finalize()` is called, performing only per-file schema validation on each written file.

[01-REQ-8.3] WHEN `Finalize()` is called, THE library SHALL run full validation (schema + cross-file integrity) AND return the completed Spec on success or all validation errors on failure.

[01-REQ-8.4] WHILE in bootstrap mode, THE library SHALL allow writing any individual file (prd.md, requirements.json, test_spec.json, tasks.json) without requiring the others to exist.

#### Edge Cases

[01-REQ-8.E1] IF `Finalize()` is called before all four files have been written, THEN THE library SHALL return an incompleteness error listing the missing files.

[01-REQ-8.E2] IF the same file is written more than once during bootstrap, THEN THE library SHALL overwrite the previous version without error.

[01-REQ-8.E3] IF a `BootstrapSpec` is started for a spec folder that already exists, THEN THE library SHALL return an error to prevent accidental overwrite.

---

### Requirement 9: Spec Discovery

**User Story:** As a library consumer, I want to discover and enumerate specs in a root directory, so that I can build tools that operate across the full spec tree and resolve cross-spec dependencies.

#### Acceptance Criteria

[01-REQ-9.1] WHEN a spec root directory is provided, THE library SHALL scan for directories matching the `{NN}_{snake_case_name}` naming pattern AND return a list of discovered spec entries to the caller.

[01-REQ-9.2] THE library SHALL skip the `archive/` subdirectory during spec discovery.

[01-REQ-9.3] THE library SHALL load spec metadata (`spec_id`, `spec_name`, `status`) for each discovered spec by reading only the PRD frontmatter, without loading all four artifacts.

[01-REQ-9.4] WHEN tasks.json files are present, THE library SHALL build a dependency graph from cross-spec dependency declarations AND return the graph to the caller for use in topological ordering and cycle detection.

[01-REQ-9.5] IF no spec root directory is provided, THEN THE library SHALL default to the current working directory.

#### Edge Cases

[01-REQ-9.E1] IF the spec root directory does not exist or is not a directory, THEN THE library SHALL return an error.

[01-REQ-9.E2] IF a discovered directory matches the naming pattern but is missing one or more required files, THEN THE library SHALL include it in results marked as incomplete rather than skipping it.

[01-REQ-9.E3] IF the dependency graph constructed from tasks.json declarations contains a cycle, THEN THE library SHALL return an error identifying the spec IDs involved in the cycle.

---

### Requirement 10: ID Format Validation

**User Story:** As a library consumer, I want all IDs to be validated against the spec-format conventions, so that malformed or inconsistent IDs are caught during validation.

#### Acceptance Criteria

[01-REQ-10.1] THE library SHALL validate all ID fields against the format patterns defined in spec-format.md Appendix A: requirement IDs (`{spec_id}-REQ-{N}`), criterion IDs (`{spec_id}-REQ-{N}.{C}`), edge case IDs (`{spec_id}-REQ-{N}.E{C}`), property IDs (`{spec_id}-PROP-{N}`), path IDs (`{spec_id}-PATH-{N}`), error IDs (`{spec_id}-ERR-{N}`), test case IDs (`TS-{spec_id}-{N}`), property test IDs (`TS-{spec_id}-P{N}`), edge case test IDs (`TS-{spec_id}-E{N}`), smoke test IDs (`TS-{spec_id}-SMOKE-{N}`), subtask IDs (`{group}.{N}`), verification IDs (`{group}.V`).

[01-REQ-10.2] WHEN validating IDs, THE library SHALL verify that the `spec_id` component embedded in each ID matches the file's declared `spec_id` field.

[01-REQ-10.3] WHEN validating IDs, THE library SHALL verify that numeric components (N, C) are positive integers AND return validation errors for zero or negative values.

#### Edge Cases

[01-REQ-10.E1] IF an ID contains a `spec_id` that does not match the file's `spec_id`, THEN THE library SHALL return a validation error identifying the mismatched ID and the expected `spec_id`.

[01-REQ-10.E2] IF IDs within a scope are not sequential (e.g., requirements numbered 1, 2, 5), THEN THE library SHALL return a validation warning (not a blocking error), since gaps may result from deliberate deletions.
