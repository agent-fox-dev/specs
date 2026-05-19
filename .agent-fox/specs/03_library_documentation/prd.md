# afspec Library Documentation

## Intent

Create comprehensive API documentation and usage examples for both the Go and Python afspec libraries, enabling developers to integrate the spec-format library into their own tools and workflows.

## Goals

- API reference documentation for the Go library (`pkg/afspec/`).
- API reference documentation for the Python library (`afspec/`).
- Usage examples covering common operations: loading a spec, creating a spec from scratch, validating, rendering to markdown, lifecycle transitions, and bootstrap mode.
- A unified README.md for the monorepo that introduces both libraries and links to detailed docs.
- Cross-library comparison showing equivalent operations in Go and Python side by side.

## Non-Goals

- No tutorial or getting-started guide beyond the examples.
- No user guide for the spec format itself (that is `docs/spec-format.md`).
- No architecture or design documentation for the libraries (that belongs in code comments and the specs).
- No contributor guide (that belongs in CONTRIBUTING.md if needed).

## Background

The afspec libraries (Go at `pkg/afspec/`, Python at `afspec/`) implement the agent-fox spec format. They are building blocks consumed by other repositories. Good API documentation and examples are essential for adoption. Both libraries have identical functionality, so documentation should make this parallel structure clear.

## Design Decisions

1. **Documentation location**: API docs live in `docs/api/go/` and `docs/api/python/`. Examples live in `docs/examples/`.
2. **Format**: Markdown files. No generated API docs (godoc/Sphinx) — manual markdown for now, kept in sync with code.
3. **Example style**: Complete, runnable code snippets. Each example is a self-contained program (Go `main.go`, Python script) that can be copy-pasted.
4. **Cross-library comparison**: A single `docs/examples/comparison.md` showing equivalent operations in both languages side by side.
5. **README scope**: The monorepo README.md introduces both libraries, shows a quick-start for each, and links to detailed docs.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 01_golang_library | 0 | 1 | Needs Go library public API to document (From Group TBD — upstream spec not yet planned; using sentinel 0) |
| 02_python_library | 0 | 1 | Needs Python library public API to document (From Group TBD — upstream spec not yet planned; using sentinel 0) |

## Source

Source: Input provided by Michael Kuehl via interactive prompt
