# afspec Library Documentation

## Intent

Create comprehensive API documentation and usage examples for both the Go and Python afspec libraries, enabling developers to integrate the spec-format library into their own tools and workflows.

## Goals

- API reference documentation for the Go library (root package `github.com/agent-fox/afspec`).
- API reference documentation for the Python library (`afspec/`).
- Usage examples covering common operations: loading a spec, creating a spec from scratch, validating, rendering to markdown, lifecycle transitions, and bootstrap mode.
- A unified README.md for the monorepo that introduces both libraries and links to detailed docs.
- Cross-library comparison showing equivalent operations in Go and Python side by side.

## Non-Goals

- No tutorial or getting-started guide beyond the examples.
- No user guide for the spec format itself (that is `docs/spec-format.md`).
- No architecture or design documentation for the libraries (that belongs in code comments and the specs).
- No contributor guide (that belongs in CONTRIBUTING.md if needed).
- No auto-generated API docs (godoc/Sphinx) — manual markdown kept in sync with code.
- No CI verification of example code snippets — they are best-effort and reviewed manually.

## Background

The afspec libraries (Go at root level, Python at `afspec/`) implement the agent-fox spec format. They are building blocks consumed by other repositories. Good API documentation and examples are essential for adoption. Both libraries have identical functionality, so documentation should make this parallel structure clear.

The Go library is imported as `github.com/agent-fox/afspec` and the code lives at the monorepo root (not `pkg/afspec/`). The Python library is the `afspec` package at `afspec/`.

## Design Decisions

1. **Documentation location**: API docs live in `docs/api/go.md` and `docs/api/python.md` (one file per library). Examples live in `docs/examples/`. This keeps the structure flat — each library's API fits in a single well-organized file.

2. **API reference detail level**: Each public function is documented with: function signature, one-paragraph description, parameters table (name, type, description), return type, possible errors/exceptions, and a brief inline usage example for non-trivial functions.

3. **API reference organization**: Within each API doc, functions are grouped by category: Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery. Types are in a separate section at the bottom.

4. **Example format**: All examples are markdown files containing fenced code blocks. Go examples are complete `package main` programs with imports. Python examples are standalone scripts. They are not separate `.go`/`.py` files — keeping them in markdown avoids module graph issues and makes the docs self-contained.

5. **Example files**: Six focused example files in `docs/examples/`:
   - `loading_and_saving.md` — load a spec, save a spec, round-trip
   - `validation.md` — schema validation, cross-file validation, handling errors
   - `rendering.md` — per-file rendering, combined rendering, EARS sentences
   - `lifecycle.md` — lifecycle transitions, intent hash, mutation guards
   - `bootstrap_and_discovery.md` — bootstrap new spec, discover specs, dependency graph
   - `comparison.md` — cross-library comparison of equivalent operations

6. **Cross-library comparison structure**: Organized by operation. Each section has a brief description, then alternating Go and Python code blocks under the same heading.

7. **README scope**: The monorepo README.md introduces both libraries with a one-paragraph overview, shows a minimal quick-start for each (load → validate → render), and links to the API docs and examples. It does not duplicate the API reference.

8. **Authoring from design docs**: The documentation can be authored entirely from the public API surfaces defined in specs 01 and 02 design documents. When the libraries are implemented, the docs should be reviewed for accuracy against actual code.

9. **Go library path correction**: The original PRD referenced `pkg/afspec/` but the Go library lives at the monorepo root. All documentation references the root package path `github.com/agent-fox/afspec`.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 01_golang_library | 0 | 1 | Needs Go library public API to document (From Group TBD — upstream spec not yet planned; using sentinel 0) |
| 02_python_library | 0 | 1 | Needs Python library public API to document (From Group TBD — upstream spec not yet planned; using sentinel 0) |

## Source

Source: .agent-fox/specs/03_library_documentation/prd.md
