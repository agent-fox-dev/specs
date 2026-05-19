# Implementation Plan: afspec Library Documentation

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

The implementation produces markdown documentation files and tests that verify their completeness and accuracy. Task group 1 writes failing tests that check for documentation files and content. Subsequent groups author the actual documentation to make those tests pass. The Go API reference, Python API reference, and examples are authored in separate groups to keep sessions focused.

## Test Commands

- Spec tests: `uv run pytest -q tests/test_docs.py`
- All tests: `uv run pytest -q`
- Linter: `uv run ruff check`

## Tasks

- [x] 1. Write failing spec tests
  - [x] 1.1 Set up test file structure
    - Create `tests/test_docs.py` with pytest test functions
    - Implement markdown parsing helpers: `extract_h2_headings()`, `extract_h3_headings()`, `extract_code_blocks()`, `extract_relative_links()`, `extract_section()`
    - _Test Spec: TS-03-1 through TS-03-25_

  - [x] 1.2 Translate file existence and structure tests
    - TS-03-5: Go API reference file exists
    - TS-03-10: Python API reference file exists
    - TS-03-11: All six example files exist
    - TS-03-16: Comparison file exists
    - TS-03-22: README.md exists
    - _Test Spec: TS-03-5, TS-03-10, TS-03-11, TS-03-16, TS-03-22_

  - [x] 1.3 Translate Go API reference content tests
    - TS-03-1: All public functions present
    - TS-03-2: Function entries have required sections
    - TS-03-3: Types section present
    - TS-03-4: Category organization
    - TS-03-23: Signatures match design doc
    - _Test Spec: TS-03-1, TS-03-2, TS-03-3, TS-03-4, TS-03-23_

  - [x] 1.4 Translate Python API reference, example, README, and accuracy tests
    - TS-03-6 through TS-03-9: Python API content
    - TS-03-12 through TS-03-15: Example content
    - TS-03-17 through TS-03-21: Comparison and README content
    - TS-03-24, TS-03-25: Accuracy tests
    - _Test Spec: TS-03-6, TS-03-7, TS-03-8, TS-03-9, TS-03-12, TS-03-13, TS-03-14, TS-03-15, TS-03-17, TS-03-18, TS-03-19, TS-03-20, TS-03-21, TS-03-24, TS-03-25_

  - [x] 1.5 Translate edge case, property, and smoke tests
    - Edge cases: TS-03-E1 through TS-03-E6
    - Property tests: TS-03-P1 through TS-03-P5
    - Smoke tests: TS-03-SMOKE-1 through TS-03-SMOKE-5
    - _Test Spec: TS-03-E1 through TS-03-E6, TS-03-P1 through TS-03-P5, TS-03-SMOKE-1 through TS-03-SMOKE-5_

  - [x] 1.V Verify task group 1
    - [x] All spec tests exist and are syntactically valid
    - [x] All spec tests FAIL (red) — no documentation files yet
    - [x] No linter warnings introduced: `uv run ruff check`

- [x] 2. Write Go API reference
  - [x] 2.1 Create docs/api/ directory and Go API reference skeleton
    - Create `docs/api/go.md` with title and category headings (Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery, Types)
    - _Requirements: 03-REQ-1.4, 03-REQ-1.5_

  - [x] 2.2 Document Go functions: Loading, Saving, Validation
    - LoadSpec: signature, description, parameters, returns, errors, example
    - SaveSpec: signature, description, parameters, returns, errors, example
    - Validate, ValidateSchema, ValidateCrossFile: each with full documentation
    - All signatures taken from spec 01 design.md Components and Interfaces
    - _Requirements: 03-REQ-1.1, 03-REQ-1.2, 03-REQ-6.1_

  - [x] 2.3 Document Go functions: Rendering, Lifecycle, Bootstrap, Discovery
    - RenderRequirements, RenderTestSpec, RenderTasks, RenderCombined
    - Transition
    - NewBootstrap, Bootstrap.WritePRD/WriteRequirements/WriteTestSpec/WriteTasks, Bootstrap.Finalize
    - DiscoverSpecs
    - _Requirements: 03-REQ-1.1, 03-REQ-1.2, 03-REQ-6.1_

  - [x] 2.4 Document Go types
    - All public types from spec 01 design.md with field tables
    - Spec, PRD, Frontmatter, Status, Requirements, Criterion, TestSpecDoc, Tasks
    - ValidationError, LifecycleError, IncompleteSpecError, DiscoveryResult, SpecEntry, DependencyGraph, Bootstrap, SubtaskState
    - _Requirements: 03-REQ-1.3, 03-REQ-6.3_

  - [x] 2.V Verify task group 2
    - [x] Spec tests TS-03-1 through TS-03-5, TS-03-23 pass
    - [x] Edge case test TS-03-E1 passes
    - [x] Property test TS-03-P1 passes
    - [x] Smoke test TS-03-SMOKE-2 passes
    - [x] All existing tests still pass: `uv run pytest -q`
    - [x] No linter warnings introduced: `uv run ruff check`
    - [x] Requirements 03-REQ-1.1 through 03-REQ-1.5, 03-REQ-1.E1, 03-REQ-6.1, 03-REQ-6.3 met

- [x] 3. Write Python API reference
  - [x] 3.1 Create Python API reference skeleton
    - Create `docs/api/python.md` with title and category headings
    - _Requirements: 03-REQ-2.4, 03-REQ-2.5_

  - [x] 3.2 Document Python functions: Loading, Saving, Validation, Rendering
    - load_spec, save_spec, validate
    - render_requirements, render_test_spec, render_tasks, render_combined
    - All signatures taken from spec 02 design.md
    - _Requirements: 03-REQ-2.1, 03-REQ-2.2, 03-REQ-6.2_

  - [x] 3.3 Document Python functions: Lifecycle, Bootstrap, Discovery
    - transition, BootstrapSpec (context manager), discover, schema_version
    - _Requirements: 03-REQ-2.1, 03-REQ-2.2, 03-REQ-6.2_

  - [x] 3.4 Document Python types
    - All public types from spec 02 design.md with field tables
    - Exception hierarchy: AfspecError, SpecValidationError, LifecycleError, IncompleteSpecError
    - _Requirements: 03-REQ-2.3, 03-REQ-6.3_

  - [x] 3.V Verify task group 3
    - [x] Spec tests TS-03-6 through TS-03-10, TS-03-24 pass
    - [x] Edge case test TS-03-E2 passes
    - [x] Property test TS-03-P2 passes
    - [x] Smoke test TS-03-SMOKE-3 passes
    - [x] All existing tests still pass: `uv run pytest -q`
    - [x] No linter warnings introduced: `uv run ruff check`
    - [x] Requirements 03-REQ-2.1 through 03-REQ-2.5, 03-REQ-2.E1, 03-REQ-6.2, 03-REQ-6.3 met

- [ ] 4. Checkpoint — API references complete
  - Ensure Go and Python API references both pass all content tests.
  - Verify function signatures match design docs (TS-03-23, TS-03-24).
  - Ask the user if questions arise.

- [ ] 5. Write usage examples and comparison
  - [ ] 5.1 Create docs/examples/ directory and write loading_and_saving.md
    - Go and Python examples for LoadSpec/load_spec, SaveSpec/save_spec, round-trip
    - Each example is complete (package main / import afspec)
    - Prose descriptions before each code block
    - _Requirements: 03-REQ-3.1, 03-REQ-3.2, 03-REQ-3.3, 03-REQ-3.4, 03-REQ-3.5_

  - [ ] 5.2 Write validation.md and rendering.md
    - validation.md: schema validation, cross-file validation, error handling examples
    - rendering.md: per-file rendering, combined rendering, EARS sentence examples
    - Both Go and Python in each file
    - _Requirements: 03-REQ-3.1, 03-REQ-3.2, 03-REQ-3.3, 03-REQ-3.4, 03-REQ-3.5_

  - [ ] 5.3 Write lifecycle.md and bootstrap_and_discovery.md
    - lifecycle.md: draft→active→sealed transitions, intent hash, mutation guards
    - bootstrap_and_discovery.md: BootstrapSpec/NewBootstrap, DiscoverSpecs/discover, dependency graph
    - Note Go/Python behavioral differences (error returns vs exceptions)
    - _Requirements: 03-REQ-3.1, 03-REQ-3.2, 03-REQ-3.3, 03-REQ-3.4, 03-REQ-3.5, 03-REQ-3.E1_

  - [ ] 5.4 Write comparison.md
    - Cover all 7 operations: loading, saving, validating, rendering, lifecycle, bootstrap, discovery
    - Alternating Go and Python code blocks per operation
    - Note any operations without direct equivalents (e.g., ValidateSchema as standalone)
    - _Requirements: 03-REQ-4.1, 03-REQ-4.2, 03-REQ-4.3, 03-REQ-4.E1_

  - [ ] 5.V Verify task group 5
    - [ ] Spec tests TS-03-11 through TS-03-18 pass
    - [ ] Edge case tests TS-03-E3, TS-03-E4 pass
    - [ ] Property test TS-03-P3 passes
    - [ ] Smoke tests TS-03-SMOKE-4, TS-03-SMOKE-5 pass
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check`
    - [ ] Requirements 03-REQ-3.1 through 03-REQ-3.5, 03-REQ-3.E1, 03-REQ-4.1 through 03-REQ-4.3, 03-REQ-4.E1 met

- [ ] 6. Update README and verify documentation accuracy
  - [ ] 6.1 Rewrite README.md
    - One-paragraph afspec overview introducing both libraries
    - Quick-start section with Go example (load → validate → render)
    - Quick-start section with Python example (load → validate → render)
    - Documentation links section with relative links to api docs, examples, spec-format
    - Libraries section with import paths, version requirements, key features
    - _Requirements: 03-REQ-5.1, 03-REQ-5.2, 03-REQ-5.3, 03-REQ-5.4_

  - [ ] 6.2 Verify terminology consistency
    - Review all documentation files for consistent use of domain terms from docs/spec-format.md §2
    - Fix any inconsistencies found
    - _Requirements: 03-REQ-6.4_

  - [ ] 6.3 Verify all cross-references and links
    - Check all relative links in README.md point to existing files
    - Check all internal cross-references between docs are valid
    - _Requirements: 03-REQ-5.3, 03-REQ-5.E1_

  - [ ] 6.V Verify task group 6
    - [ ] Spec tests TS-03-19 through TS-03-22, TS-03-25 pass
    - [ ] Edge case tests TS-03-E5, TS-03-E6 pass
    - [ ] Property test TS-03-P4 passes
    - [ ] Smoke test TS-03-SMOKE-1 passes
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check`
    - [ ] Requirements 03-REQ-5.1 through 03-REQ-5.4, 03-REQ-5.E1, 03-REQ-6.4 met

- [ ] 7. Wiring verification

  - [ ] 7.1 Trace every execution path from design.md end-to-end
    - Path 1 (README discovery): Verify README → API docs links are live and target files have function entries
    - Path 2 (Go function lookup): Verify docs/api/go.md has navigable category → function structure
    - Path 3 (Python function lookup): Verify docs/api/python.md has navigable category → function structure
    - Path 4 (Example learning): Verify example files have prose + code block structure
    - Path 5 (Cross-library translation): Verify comparison.md has paired Go/Python blocks per operation
    - _Requirements: all_

  - [ ] 7.2 Verify return values propagate correctly
    - README links resolve to actual files (not 404s)
    - API doc function entries reference the correct types (types section exists with matching entries)
    - Example code blocks reference functions that exist in the API docs
    - _Requirements: all_

  - [ ] 7.3 Run the integration smoke tests
    - All TS-03-SMOKE-1 through TS-03-SMOKE-5 pass
    - _Test Spec: TS-03-SMOKE-1 through TS-03-SMOKE-5_

  - [ ] 7.4 Stub / dead-code audit
    - Search all documentation files for TODO markers, placeholder text (e.g., "TBD", "TODO", "FIXME"), or empty sections
    - Each hit must be resolved or justified
    - _Requirements: all_

  - [ ] 7.5 Cross-spec entry point verification
    - Verify all documented function signatures match the design docs (specs 01 and 02)
    - Verify the documentation is self-consistent (no internal contradictions between API docs, examples, and comparison)
    - Property test TS-03-P5 (type completeness) passes
    - _Requirements: all_

  - [ ] 7.V Verify wiring group
    - [ ] All smoke tests pass: `uv run pytest -q tests/test_docs.py -k smoke`
    - [ ] No placeholder content remains in documentation files
    - [ ] All execution paths from design.md are traceable in the documentation
    - [ ] All documented signatures match design docs
    - [ ] All existing tests still pass: `uv run pytest -q`

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
| 03-REQ-1.1 | TS-03-1 | 2.2, 2.3 | tests/test_docs.py::test_go_api_public_functions |
| 03-REQ-1.2 | TS-03-2 | 2.2, 2.3 | tests/test_docs.py::test_go_api_function_sections |
| 03-REQ-1.3 | TS-03-3 | 2.4 | tests/test_docs.py::test_go_api_types |
| 03-REQ-1.4 | TS-03-4 | 2.1 | tests/test_docs.py::test_go_api_categories |
| 03-REQ-1.5 | TS-03-5 | 2.1 | tests/test_docs.py::test_go_api_file_exists |
| 03-REQ-1.E1 | TS-03-E1 | 2.4 | tests/test_docs.py::test_go_no_error_documented |
| 03-REQ-2.1 | TS-03-6 | 3.2, 3.3 | tests/test_docs.py::test_python_api_public_functions |
| 03-REQ-2.2 | TS-03-7 | 3.2, 3.3 | tests/test_docs.py::test_python_api_function_sections |
| 03-REQ-2.3 | TS-03-8 | 3.4 | tests/test_docs.py::test_python_api_types |
| 03-REQ-2.4 | TS-03-9 | 3.1 | tests/test_docs.py::test_python_api_categories |
| 03-REQ-2.5 | TS-03-10 | 3.1 | tests/test_docs.py::test_python_api_file_exists |
| 03-REQ-2.E1 | TS-03-E2 | 3.3 | tests/test_docs.py::test_python_no_exception_documented |
| 03-REQ-3.1 | TS-03-12 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_example_categories |
| 03-REQ-3.2 | TS-03-13 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_examples_self_contained |
| 03-REQ-3.3 | TS-03-14 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_examples_both_languages |
| 03-REQ-3.4 | TS-03-11 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_example_files_exist |
| 03-REQ-3.5 | TS-03-15 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_examples_prose_descriptions |
| 03-REQ-3.E1 | TS-03-E3 | 5.3 | tests/test_docs.py::test_behavioral_differences_noted |
| 03-REQ-4.1 | TS-03-16 | 5.4 | tests/test_docs.py::test_comparison_file_exists |
| 03-REQ-4.2 | TS-03-17 | 5.4 | tests/test_docs.py::test_comparison_operations |
| 03-REQ-4.3 | TS-03-18 | 5.4 | tests/test_docs.py::test_comparison_go_python_blocks |
| 03-REQ-4.E1 | TS-03-E4 | 5.4 | tests/test_docs.py::test_comparison_missing_equivalent |
| 03-REQ-5.1 | TS-03-19 | 6.1 | tests/test_docs.py::test_readme_overview |
| 03-REQ-5.2 | TS-03-20 | 6.1 | tests/test_docs.py::test_readme_quickstart |
| 03-REQ-5.3 | TS-03-21 | 6.1 | tests/test_docs.py::test_readme_links |
| 03-REQ-5.4 | TS-03-22 | 6.1 | tests/test_docs.py::test_readme_exists |
| 03-REQ-5.E1 | TS-03-E5 | 6.3 | tests/test_docs.py::test_readme_broken_links |
| 03-REQ-6.1 | TS-03-23 | 2.2, 2.3 | tests/test_docs.py::test_go_signatures_match_design |
| 03-REQ-6.2 | TS-03-24 | 3.2, 3.3 | tests/test_docs.py::test_python_signatures_match_design |
| 03-REQ-6.3 | TS-03-25 | 2.4, 3.4 | tests/test_docs.py::test_type_fields_match_design |
| 03-REQ-6.4 | TS-03-25 | 6.2 | tests/test_docs.py::test_terminology_consistency |
| 03-REQ-6.E1 | TS-03-E6 | 2.2, 3.2 | tests/test_docs.py::test_ambiguity_notes |
| Property 1 | TS-03-P1 | 2.2, 2.3 | tests/test_docs.py::test_property_go_coverage |
| Property 2 | TS-03-P2 | 3.2, 3.3 | tests/test_docs.py::test_property_python_coverage |
| Property 3 | TS-03-P3 | 5.1, 5.2, 5.3 | tests/test_docs.py::test_property_example_coverage |
| Property 4 | TS-03-P4 | 6.1, 6.3 | tests/test_docs.py::test_property_link_integrity |
| Property 5 | TS-03-P5 | 2.4, 3.4 | tests/test_docs.py::test_property_type_completeness |
| Path 1 | TS-03-SMOKE-1 | 6.1 | tests/test_docs.py::test_smoke_readme_discovery |
| Path 2 | TS-03-SMOKE-2 | 2.2 | tests/test_docs.py::test_smoke_go_function_lookup |
| Path 3 | TS-03-SMOKE-3 | 3.2 | tests/test_docs.py::test_smoke_python_function_lookup |
| Path 4 | TS-03-SMOKE-4 | 5.1 | tests/test_docs.py::test_smoke_example_learning |
| Path 5 | TS-03-SMOKE-5 | 5.4 | tests/test_docs.py::test_smoke_cross_library_comparison |

## Notes

- This is a documentation-only spec. The "implementation" is authoring markdown files.
- Tests parse markdown files to verify structure and content. They do not compile Go examples or execute Python examples.
- All function signatures and type definitions are sourced from the design documents (specs 01 and 02). When the actual libraries are implemented, documentation should be reviewed for accuracy against real code.
- The test file `tests/test_docs.py` needs markdown parsing helpers. Use Python's `re` module for heading extraction and code block detection — no external markdown parser needed.
