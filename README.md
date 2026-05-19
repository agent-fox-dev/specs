# afspec — Go Spec-Format Library

`afspec` is a Go library for reading, writing, validating, rendering, and managing
[agent-fox](https://github.com/agent-fox) specification packages. It is the
canonical Go implementation of the agent-fox spec format v1.

## Module

```
github.com/agent-fox/afspec
```

## Installation

```sh
go get github.com/agent-fox/afspec
```

## Overview

A spec package is a directory containing four artifacts:

| File | Description |
|------|-------------|
| `prd.md` | Product Requirements Document — narrative markdown with YAML frontmatter |
| `requirements.json` | Structured EARS-syntax requirements with glossary, correctness properties, and execution paths |
| `test_spec.json` | Test contracts: unit tests, property tests, edge-case tests, smoke tests |
| `tasks.json` | Implementation plan: task groups, subtasks, dependencies, and traceability |

## Public API

### Loading and Saving

```go
// Load all four spec files from a directory into memory.
spec, err := afspec.LoadSpec("/path/to/spec/folder")

// Save all four spec files deterministically to a directory.
// Automatically updates updated_at and computes test coverage.
err = afspec.SaveSpec("/path/to/spec/folder", spec)
```

### Validation

```go
// Full validation: schema + cross-file integrity + ID format checks.
errs, err := afspec.Validate(spec)

// Schema-only validation.
errs, err := afspec.ValidateSchema(spec)

// Cross-file integrity checks only (7 rules).
errs, err := afspec.ValidateCrossFile(spec)
```

### Rendering

```go
// Render individual JSON artifacts to markdown.
md, err := afspec.RenderRequirements(spec.Requirements)
md, err = afspec.RenderTestSpec(spec.TestSpec)
md, err = afspec.RenderTasks(spec.Tasks)

// Render a combined document: PRD verbatim + requirements + test_spec + tasks.
md, err = afspec.RenderCombined(spec)
```

### Lifecycle Management

```go
// Transition a spec through its lifecycle states.
// Valid transitions: draft→active, draft→archived,
//   active→sealed, sealed→superseded, sealed→archived.
newSpec, err := afspec.Transition(spec, afspec.StatusActive)
```

### Bootstrap (Incremental Creation)

```go
// Create a new spec folder and write files one at a time.
bs, err := afspec.NewBootstrap("/path/to/specs/05_my_feature", "05", "my_feature")

bs.WritePRD(prd)
bs.WriteRequirements(req)
bs.WriteTestSpec(ts)
bs.WriteTasks(tasks)

// Finalize runs full validation and returns the complete spec.
spec, err = bs.Finalize()
```

### Discovery

```go
// Scan a spec root directory for all spec packages.
result, err := afspec.DiscoverSpecs("/path/to/specs")

for _, entry := range result.Entries {
    fmt.Println(entry.SpecID, entry.SpecName, entry.Status)
}

// Topological order (respects cross-spec dependencies).
order, err := result.Graph.TopologicalOrder()
```

## Core Types

```go
type Spec struct {
    PRD          *PRD
    Requirements *Requirements
    TestSpec     *TestSpecDoc
    Tasks        *Tasks
    Dir          string
}

type Frontmatter struct {
    SpecID        string   // "05"
    SpecName      string   // "my_feature"
    Title         string
    Status        Status   // "draft" | "active" | "sealed" | "superseded" | "archived"
    CreatedAt     string   // ISO 8601
    UpdatedAt     string   // ISO 8601 (auto-set on save)
    Owner         string
    Source        string
    Supersedes    []string
    Tags          []string
    IntentHash    *string  // SHA-256 of normalized Intent section; nil until draft→active
    SchemaVersion int
}
```

## Serialization Guarantees

- **Deterministic JSON**: keys sorted alphabetically, 2-space indentation, trailing newline.
- **Fixed YAML field order** in `prd.md` frontmatter: `spec_id`, `spec_name`, `title`, `status`, `created_at`, `updated_at`, `owner`, `source`, `supersedes`, `tags`, `intent_hash`, `schema_version`.
- **Null preservation**: `null` JSON fields round-trip as nil pointers, not as zero values or omitted fields.
- **Idempotent round-trips**: `LoadSpec` → `SaveSpec` → `LoadSpec` produces byte-identical JSON files and deeply-equal in-memory structures (only `updated_at` changes on each save).

## Development

```sh
# Run all tests
go test -count=1 ./...

# Run linter
go vet ./...

# Run quality gate
make check
```

---

## Python Library (`afspec`)

The `afspec` Python package provides identical functionality to the Go library
and targets Python 3.10+.  It uses standard-library types throughout
(`dataclasses`, `enum`, `hashlib`, `importlib.resources`, `pathlib`,
`tempfile`) with two external dependencies: **PyYAML** and **jsonschema**.

### Installation

```sh
# from the repository root (uses uv)
uv pip install -e .
```

### Quick Start

```python
import pathlib
import afspec

# Load a spec from disk
spec = afspec.load_spec(pathlib.Path("specs/01_my_feature"))

# Validate (schema + ID format + cross-file integrity)
errors = afspec.validate(spec)
if errors:
    for e in errors:
        print(f"[{e.severity}] {e.file}#{e.path}: {e.message}")

# Render to markdown
doc = afspec.render_combined(spec)

# Lifecycle transition: draft → active (computes intent hash)
active = afspec.transition(spec, "active")
afspec.save_spec(active, pathlib.Path("specs/01_my_feature"))

# Discover all specs in a root directory
result = afspec.discover(pathlib.Path("specs"))
for entry in result.entries:
    print(entry.spec_id, entry.spec_name, entry.status, entry.complete)

# Topological order (respects cross-spec dependencies)
order = result.dependency_graph.topological_sort()
```

### Bootstrap (Incremental Creation)

```python
from afspec import BootstrapSpec

with BootstrapSpec(pathlib.Path("specs"), "05", "my_feature") as bs:
    bs.write_prd(prd)           # per-file schema validation on each write
    bs.write_requirements(req)
    bs.write_test_spec(ts)
    bs.write_tasks(tasks)
# Full validation (schema + cross-file) runs on context exit.
# bs.result holds the completed Spec.
spec = bs.result
```

### Public API

| Function | Description |
|----------|-------------|
| `load_spec(path)` | Load all four artifacts from a spec folder |
| `save_spec(spec, path)` | Write artifacts atomically; auto-computes `updated_at` and `coverage` |
| `validate(spec)` | Schema + ID format + cross-file integrity checks; returns all errors |
| `render_requirements(req)` | Render requirements artifact to markdown |
| `render_test_spec(ts)` | Render test-spec artifact to markdown |
| `render_tasks(tasks)` | Render tasks artifact to markdown |
| `render_combined(spec)` | PRD verbatim + all three rendered artifacts |
| `transition(spec, status)` | Apply a lifecycle transition; returns updated `Spec` |
| `discover(spec_root)` | Scan root for specs; returns entries + dependency graph |
| `schema_version()` | Return the bundled schema version integer |

### EARS Criterion Types

```python
from afspec import EARSCriterion

criterion = EARSCriterion.from_dict({
    "id": "05-REQ-1.1",
    "ears_pattern": "event_driven",
    "trigger": "a request arrives",
    "system": "MySystem",
    "action": "process the request",
    "return_contract": "the processed result",
})
# Returns an EventDrivenCriterion instance
```

Six subclasses are available: `UbiquitousCriterion`, `EventDrivenCriterion`,
`ComplexEventCriterion`, `StateDrivenCriterion`, `UnwantedCriterion`,
`OptionalCriterion`.

### Subtask State Machine

```python
from afspec import SubtaskState

state = SubtaskState.PENDING
assert state.can_transition_to(SubtaskState.QUEUED)   # True
assert not state.can_transition_to(SubtaskState.DONE)  # False
```

### Python Development

```sh
# Run all Python tests
uv run pytest -q afspec/tests/

# Run linter
uv run ruff check

# Type check
uv run mypy afspec/

# Run quality gate (lint + tests for both Go and Python)
make check
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
