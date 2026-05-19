# Requirements Document

## Introduction

This document specifies the requirements for the afspec library documentation suite. The documentation covers both the Go library (root package `github.com/agent-fox/afspec`) and the Python library (`afspec/`), providing API reference documentation, usage examples, a cross-library comparison, and a unified monorepo README.

## Glossary

| Term | Definition |
|------|-----------|
| API reference | A documentation file listing every public function and type with signatures, descriptions, parameters, return types, and error conditions |
| Usage example | A self-contained code snippet demonstrating how to call one or more library functions to accomplish a task |
| Cross-library comparison | A document showing equivalent operations in Go and Python side by side |
| Public API | The set of exported functions and types that library consumers import and call |
| Quick-start | A minimal code snippet showing the most common workflow (load → validate → render) |
| EARS | Easy Approach to Requirements Syntax — the pattern language used in spec-format requirements |
| Spec | A four-artifact package (prd.md, requirements.json, test_spec.json, tasks.json) representing one feature |
| Spec root | The directory containing spec folders |

## Requirements

### Requirement 1: Go API Reference

**User Story:** As a Go developer, I want a complete API reference for the afspec library, so that I can discover and correctly use all public functions and types.

#### Acceptance Criteria

1. [03-REQ-1.1] WHEN a developer reads the Go API reference, THE documentation SHALL contain a section for every public function defined in the Go library design (LoadSpec, SaveSpec, Validate, ValidateSchema, ValidateCrossFile, RenderRequirements, RenderTestSpec, RenderTasks, RenderCombined, Transition, NewBootstrap, DiscoverSpecs).
2. [03-REQ-1.2] THE documentation SHALL include for each function: the full Go function signature, a description of what the function does, a parameters table listing each parameter with its type and description, the return type, and the errors the function may return.
3. [03-REQ-1.3] THE documentation SHALL include a types section listing every public type (Spec, PRD, Frontmatter, Requirements, Criterion, TestSpecDoc, Tasks, ValidationError, LifecycleError, IncompleteSpecError, DiscoveryResult, SpecEntry, DependencyGraph, Bootstrap, Status, SubtaskState, Severity) with their field definitions.
4. [03-REQ-1.4] THE documentation SHALL be organized into sections by functional category: Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery, Types.
5. [03-REQ-1.5] THE documentation SHALL exist as a single markdown file at `docs/api/go.md`.

#### Edge Cases

1. [03-REQ-1.E1] IF a public function has no error return, THEN THE documentation SHALL still include an Errors section stating "None" or equivalent.

### Requirement 2: Python API Reference

**User Story:** As a Python developer, I want a complete API reference for the afspec library, so that I can discover and correctly use all public functions and types.

#### Acceptance Criteria

1. [03-REQ-2.1] WHEN a developer reads the Python API reference, THE documentation SHALL contain a section for every public function defined in the Python library design (load_spec, save_spec, validate, render_requirements, render_test_spec, render_tasks, render_combined, transition, discover, schema_version).
2. [03-REQ-2.2] THE documentation SHALL include for each function: the Python function signature with type annotations, a description of what the function does, a parameters table listing each parameter with its type and description, the return type, and the exceptions the function may raise.
3. [03-REQ-2.3] THE documentation SHALL include a types section listing every public type (Spec, PRD, PRDFrontmatter, Requirements, EARSCriterion and subclasses, TestSpec, Tasks, ValidationError, SpecValidationError, LifecycleError, IncompleteSpecError, DiscoveryResult, SpecEntry, DependencyGraph, BootstrapSpec, SubtaskState) with their field definitions.
4. [03-REQ-2.4] THE documentation SHALL be organized into sections by functional category: Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery, Types.
5. [03-REQ-2.5] THE documentation SHALL exist as a single markdown file at `docs/api/python.md`.

#### Edge Cases

1. [03-REQ-2.E1] IF a public function raises no exceptions, THEN THE documentation SHALL still include an Exceptions section stating "None" or equivalent.

### Requirement 3: Usage Examples

**User Story:** As a developer new to the afspec library, I want runnable code examples covering common operations, so that I can quickly learn how to use the library.

#### Acceptance Criteria

1. [03-REQ-3.1] THE documentation SHALL provide example files covering six operation categories: loading and saving, validation, rendering, lifecycle management, bootstrap and discovery, and cross-library comparison.
2. [03-REQ-3.2] WHEN a developer reads an example file, THE documentation SHALL present each example as a complete, self-contained code snippet that can be copy-pasted — Go examples as `package main` programs with imports, Python examples as standalone scripts with imports.
3. [03-REQ-3.3] THE documentation SHALL provide examples in both Go and Python for each operation (except in comparison.md which shows both side by side) AND return the example file paths to the caller via the README links section.
4. [03-REQ-3.4] THE documentation SHALL place example files at the following paths: `docs/examples/loading_and_saving.md`, `docs/examples/validation.md`, `docs/examples/rendering.md`, `docs/examples/lifecycle.md`, `docs/examples/bootstrap_and_discovery.md`, `docs/examples/comparison.md`.
5. [03-REQ-3.5] WHEN a developer reads an example, THE documentation SHALL include a brief prose description before each code block explaining what the example demonstrates and what output to expect.

#### Edge Cases

1. [03-REQ-3.E1] IF a library operation has different behavior in Go vs Python (e.g., error handling via return values vs exceptions), THEN THE documentation SHALL note the difference in the prose description accompanying the example.

### Requirement 4: Cross-Library Comparison

**User Story:** As a developer who works in both Go and Python, I want a side-by-side comparison of equivalent operations, so that I can translate between the two libraries.

#### Acceptance Criteria

1. [03-REQ-4.1] THE documentation SHALL provide a comparison file at `docs/examples/comparison.md` showing equivalent operations in Go and Python side by side.
2. [03-REQ-4.2] THE comparison document SHALL cover at minimum: loading a spec, saving a spec, validating, rendering to markdown, lifecycle transitions, bootstrap creation, and spec discovery.
3. [03-REQ-4.3] WHEN presenting a comparison, THE documentation SHALL show each operation as a heading followed by alternating Go and Python code blocks with brief prose noting any behavioral differences.

#### Edge Cases

1. [03-REQ-4.E1] IF an operation exists in one library but not the other (e.g., Go's ValidateSchema has no direct Python equivalent as a standalone function), THEN THE documentation SHALL note the absence and describe the closest alternative.

### Requirement 5: Monorepo README

**User Story:** As a developer visiting the repository for the first time, I want a README that orients me to both libraries and links to detailed documentation, so that I can quickly find what I need.

#### Acceptance Criteria

1. [03-REQ-5.1] THE README.md at the repository root SHALL introduce both the Go and Python libraries with a one-paragraph overview of the afspec project.
2. [03-REQ-5.2] THE README.md SHALL contain a quick-start section for each library showing a minimal code example (load → validate → render workflow) AND return the example inline so developers can get started without navigating elsewhere.
3. [03-REQ-5.3] THE README.md SHALL contain a documentation links section with relative links to: `docs/api/go.md`, `docs/api/python.md`, `docs/examples/`, and `docs/spec-format.md`.
4. [03-REQ-5.4] THE README.md SHALL exist at the repository root as `README.md`.

#### Edge Cases

1. [03-REQ-5.E1] IF a linked documentation file does not yet exist at authoring time, THEN THE README SHALL still include the link with a note that the target is a planned location.

### Requirement 6: Documentation Accuracy

**User Story:** As a developer relying on the documentation, I want the documented function signatures and types to match the library's actual public API, so that the docs do not mislead me.

#### Acceptance Criteria

1. [03-REQ-6.1] THE Go API reference SHALL document function signatures that match the Go library design document (spec 01 design.md, Components and Interfaces section).
2. [03-REQ-6.2] THE Python API reference SHALL document function signatures that match the Python library design document (spec 02 design.md, Components and Interfaces section).
3. [03-REQ-6.3] WHEN a type is documented, THE documentation SHALL list the same fields with the same types as defined in the corresponding design document.
4. [03-REQ-6.4] THE documentation SHALL use consistent terminology — every domain term used in the docs SHALL match the glossary defined in the spec-format specification (`docs/spec-format.md` §2).

#### Edge Cases

1. [03-REQ-6.E1] IF the design document is ambiguous about a function's behavior, THEN THE documentation SHALL describe the behavior as specified in the design document and add a note referencing the design document section.
