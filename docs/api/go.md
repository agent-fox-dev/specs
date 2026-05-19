# Go API Reference: afspec

The `afspec` Go library provides a complete API for the agent-fox specification format (v1). Import it as:

```go
import "github.com/agent-fox/afspec"
```

All public types and functions live in the root package. Implementation details are in `internal/` sub-packages and are not part of the public API.

---

## Loading

### LoadSpec

```go
func LoadSpec(dir string) (*Spec, error)
```

**Description:** Reads all four spec files (`prd.md`, `requirements.json`, `test_spec.json`, `tasks.json`) from the directory at `dir` and returns a fully populated `*Spec`. Files are parsed and validated for well-formedness (JSON schema and YAML) but cross-file integrity is not checked here — call `Validate` for full validation.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dir` | `string` | Absolute or relative path to the spec folder on disk. |

**Returns:** `(*Spec, error)` — a pointer to the populated spec, or `nil` and an error if any file is missing, malformed, or unreadable.

**Errors:**

| Condition | Error |
|-----------|-------|
| `dir` does not exist | error with path |
| A required file is missing | error listing missing files |
| Malformed JSON in a spec file | parse error with file name and details |
| Malformed YAML frontmatter in `prd.md` | parse error |
| Missing `## Intent` section in `prd.md` | validation error |

**Example:**

```go
package main

import (
    "fmt"
    "log"

    "github.com/agent-fox/afspec"
)

func main() {
    spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
    if err != nil {
        log.Fatalf("load: %v", err)
    }
    fmt.Printf("Loaded spec %s (status: %s)\n",
        spec.PRD.Frontmatter.SpecName,
        spec.PRD.Frontmatter.Status,
    )
}
```

---

## Saving

### SaveSpec

```go
func SaveSpec(dir string, spec *Spec) error
```

**Description:** Writes all four spec files to `dir` deterministically. Before writing, `SaveSpec` sets `updated_at` to the current UTC timestamp and recomputes the `coverage` field in `test_spec.json` from cross-references. Files are written atomically (write-to-temp-then-rename). If any write fails, already-written files are removed to prevent partial results.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dir` | `string` | Absolute or relative path to the spec folder on disk. Must already exist. |
| `spec` | `*Spec` | Pointer to the spec to save. Must not be `nil`. |

**Returns:** `error` — `nil` on success, or an error if the directory does not exist, a file write fails, or a mutation guard rejects the save.

**Errors:**

| Condition | Error |
|-----------|-------|
| `dir` does not exist | error; no files written |
| File write failure mid-operation | error; previously-written files removed (atomic all-or-nothing) |
| Spec status is `sealed` | error; mutation rejected |
| Spec status is `superseded` | error; mutation rejected |
| Spec status is `archived` | error; mutation rejected |

**Example:**

```go
package main

import (
    "log"

    "github.com/agent-fox/afspec"
)

func main() {
    spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
    if err != nil {
        log.Fatalf("load: %v", err)
    }

    spec.PRD.Frontmatter.Owner = "new-owner"

    if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", spec); err != nil {
        log.Fatalf("save: %v", err)
    }
}
```

---

## Validation

### Validate

```go
func Validate(spec *Spec) ([]ValidationError, error)
```

**Description:** Runs the full validation suite: JSON Schema validation for all four files, cross-file integrity checks (7 rules), and ID format validation. Returns all errors found. An empty slice means the spec is valid.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `*Spec` | Pointer to the spec to validate. Must not be `nil`. |

**Returns:** `([]ValidationError, error)` — the slice of validation errors found (may be empty), and a non-nil error only if validation itself fails due to an internal error (e.g., cannot serialize to JSON for schema checking).

**Errors:**

| Condition | Error |
|-----------|-------|
| Internal serialization failure | non-nil second return value |

**Example:**

```go
package main

import (
    "fmt"
    "log"

    "github.com/agent-fox/afspec"
)

func main() {
    spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
    if err != nil {
        log.Fatalf("load: %v", err)
    }

    errs, err := afspec.Validate(spec)
    if err != nil {
        log.Fatalf("validate internal error: %v", err)
    }
    for _, e := range errs {
        fmt.Printf("[%s] %s at %s: %s\n", e.Severity, e.File, e.Path, e.Message)
    }
    if len(errs) == 0 {
        fmt.Println("Spec is valid.")
    }
}
```

---

### ValidateSchema

```go
func ValidateSchema(spec *Spec) ([]ValidationError, error)
```

**Description:** Runs only JSON Schema validation against the embedded schemas for each of the four spec files. Does not perform cross-file integrity or ID format checks.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `*Spec` | Pointer to the spec to validate. Must not be `nil`. |

**Returns:** `([]ValidationError, error)` — schema validation errors, and a non-nil error only for internal failures.

**Errors:**

| Condition | Error |
|-----------|-------|
| Internal serialization failure | non-nil second return value |

---

### ValidateCrossFile

```go
func ValidateCrossFile(spec *Spec) ([]ValidationError, error)
```

**Description:** Runs only the 7 cross-file integrity rules. Checks that IDs referenced in `test_spec.json` and `tasks.json` resolve to existing entities in `requirements.json`, and that every requirement/property/path has corresponding test coverage.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `*Spec` | Pointer to the spec to validate. Must not be `nil`. |

**Returns:** `([]ValidationError, error)` — cross-file integrity errors, and a non-nil error only for internal failures.

**Errors:**

| Condition | Error |
|-----------|-------|
| Internal failure | non-nil second return value |

---

## Rendering

### RenderRequirements

```go
func RenderRequirements(req *Requirements) ([]byte, error)
```

**Description:** Renders a `Requirements` struct to markdown. The output includes a header, glossary section, and each requirement with its EARS acceptance criteria and edge cases rendered as human-readable sentences.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `req` | `*Requirements` | Pointer to the requirements to render. Must not be `nil`. |

**Returns:** `([]byte, error)` — rendered markdown bytes, or an error if rendering fails.

**Errors:**

| Condition | Error |
|-----------|-------|
| `req` is `nil` | error |
| Template execution failure | error |

---

### RenderTestSpec

```go
func RenderTestSpec(ts *TestSpecDoc) ([]byte, error)
```

**Description:** Renders a `TestSpecDoc` struct to markdown, including all test cases, property tests, edge case tests, smoke tests, and a coverage matrix.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ts` | `*TestSpecDoc` | Pointer to the test spec to render. Must not be `nil`. |

**Returns:** `([]byte, error)` — rendered markdown bytes, or an error if rendering fails.

**Errors:**

| Condition | Error |
|-----------|-------|
| `ts` is `nil` | error |
| Template execution failure | error |

---

### RenderTasks

```go
func RenderTasks(tasks *Tasks) ([]byte, error)
```

**Description:** Renders a `Tasks` struct to markdown, including all task groups with their subtasks, verification steps, and the traceability matrix.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tasks` | `*Tasks` | Pointer to the tasks to render. Must not be `nil`. |

**Returns:** `([]byte, error)` — rendered markdown bytes, or an error if rendering fails.

**Errors:**

| Condition | Error |
|-----------|-------|
| `tasks` is `nil` | error |
| Template execution failure | error |

---

### RenderCombined

```go
func RenderCombined(spec *Spec) ([]byte, error)
```

**Description:** Produces a single combined markdown document: the PRD body verbatim, followed by separator lines and the rendered output of requirements, test_spec, and tasks. Useful for generating a complete spec document for review.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `*Spec` | Pointer to the spec to render. Must not be `nil`. |

**Returns:** `([]byte, error)` — combined rendered markdown bytes, or an error if any part of rendering fails.

**Errors:**

| Condition | Error |
|-----------|-------|
| `spec` is `nil` | error |
| Any rendering sub-step fails | error |

---

## Lifecycle

### Transition

```go
func Transition(spec *Spec, target Status) (*Spec, error)
```

**Description:** Applies a lifecycle state transition, returning a new `*Spec` with the updated status. The original spec is not modified. Valid transitions follow the lifecycle graph: `draft → active`, `draft → archived`, `active → sealed`, `sealed → superseded`, `sealed → archived`. On `draft → active`, the intent hash is computed and stored in `Frontmatter.IntentHash`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `*Spec` | Pointer to the current spec. Must not be `nil`. |
| `target` | `Status` | Target lifecycle status (e.g., `afspec.StatusActive`). |

**Returns:** `(*Spec, error)` — a new spec with the updated status, or `nil` and a `*LifecycleError` if the transition is rejected.

**Errors:**

| Condition | Error |
|-----------|-------|
| Illegal transition (not in allowed edges) | `*LifecycleError` with current and target status |
| Guard rejection (e.g., intent hash mismatch) | `*LifecycleError` with reason |

**Example:**

```go
package main

import (
    "fmt"
    "log"

    "github.com/agent-fox/afspec"
)

func main() {
    spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
    if err != nil {
        log.Fatalf("load: %v", err)
    }

    activated, err := afspec.Transition(spec, afspec.StatusActive)
    if err != nil {
        log.Fatalf("transition: %v", err)
    }
    fmt.Printf("New status: %s\n", activated.PRD.Frontmatter.Status)

    if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", activated); err != nil {
        log.Fatalf("save: %v", err)
    }
}
```

---

## Bootstrap

### NewBootstrap

```go
func NewBootstrap(dir string, specID string, specName string) (*Bootstrap, error)
```

**Description:** Creates a new spec folder at `dir/specID_specName/` and returns a `*Bootstrap` handle for writing spec files one at a time. The directory must not already exist. Call `Write*` methods to add each file, then call `Finalize()` to run full validation and return the complete `*Spec`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dir` | `string` | Parent directory in which to create the spec folder. |
| `specID` | `string` | Spec ID (e.g., `"05"`). |
| `specName` | `string` | Snake-case spec name (e.g., `"my_feature"`). |

**Returns:** `(*Bootstrap, error)` — a bootstrap handle, or `nil` and an error if the folder already exists or cannot be created.

**Errors:**

| Condition | Error |
|-----------|-------|
| Spec folder already exists | error; prevents overwrite |
| Parent directory not writable | error |

---

### Bootstrap.WritePRD

```go
func (b *Bootstrap) WritePRD(prd *PRD) error
```

**Description:** Validates `prd` against the PRD frontmatter JSON Schema and writes `prd.md` to the spec folder. Must be called before `Finalize`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `prd` | `*PRD` | PRD struct to serialize and write. Must not be `nil`. |

**Returns:** `error` — `nil` on success, or an error if schema validation fails or the file cannot be written.

**Errors:**

| Condition | Error |
|-----------|-------|
| Schema validation failure | error with details |
| File write failure | error |

---

### Bootstrap.WriteRequirements

```go
func (b *Bootstrap) WriteRequirements(req *Requirements) error
```

**Description:** Validates `req` against the requirements JSON Schema and writes `requirements.json` to the spec folder.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `req` | `*Requirements` | Requirements struct to serialize and write. Must not be `nil`. |

**Returns:** `error` — `nil` on success, or an error if schema validation fails or the file cannot be written.

**Errors:**

| Condition | Error |
|-----------|-------|
| Schema validation failure | error with details |
| File write failure | error |

---

### Bootstrap.WriteTestSpec

```go
func (b *Bootstrap) WriteTestSpec(ts *TestSpecDoc) error
```

**Description:** Validates `ts` against the test_spec JSON Schema and writes `test_spec.json` to the spec folder.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ts` | `*TestSpecDoc` | Test spec struct to serialize and write. Must not be `nil`. |

**Returns:** `error` — `nil` on success, or an error if schema validation fails or the file cannot be written.

**Errors:**

| Condition | Error |
|-----------|-------|
| Schema validation failure | error with details |
| File write failure | error |

---

### Bootstrap.WriteTasks

```go
func (b *Bootstrap) WriteTasks(tasks *Tasks) error
```

**Description:** Validates `tasks` against the tasks JSON Schema and writes `tasks.json` to the spec folder.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tasks` | `*Tasks` | Tasks struct to serialize and write. Must not be `nil`. |

**Returns:** `error` — `nil` on success, or an error if schema validation fails or the file cannot be written.

**Errors:**

| Condition | Error |
|-----------|-------|
| Schema validation failure | error with details |
| File write failure | error |

---

### Bootstrap.Finalize

```go
func (b *Bootstrap) Finalize() (*Spec, error)
```

**Description:** Runs full validation on the written spec files and returns a complete `*Spec`. All four files (`prd.md`, `requirements.json`, `test_spec.json`, `tasks.json`) must have been written before calling `Finalize`. Cross-file integrity validation is performed here.

**Parameters:** None.

**Returns:** `(*Spec, error)` — the fully validated spec, or `nil` and an error if any file is missing or validation fails.

**Errors:**

| Condition | Error |
|-----------|-------|
| Not all four files written | `*IncompleteSpecError` listing missing files |
| Validation failures | `[]ValidationError` wrapped in error |

**Example:**

```go
package main

import (
    "fmt"
    "log"
    "time"

    "github.com/agent-fox/afspec"
)

func main() {
    b, err := afspec.NewBootstrap(".agent-fox/specs", "05", "my_feature")
    if err != nil {
        log.Fatalf("bootstrap: %v", err)
    }

    now := time.Now().UTC().Format(time.RFC3339)
    prd := &afspec.PRD{
        Frontmatter: afspec.Frontmatter{
            SpecID:        "05",
            SpecName:      "my_feature",
            Title:         "My Feature",
            Status:        afspec.StatusDraft,
            CreatedAt:     now,
            UpdatedAt:     now,
            Owner:         "team",
            SchemaVersion: 1,
        },
        Body: "## Intent\n\nThis feature does something important.\n",
    }
    if err := b.WritePRD(prd); err != nil {
        log.Fatalf("WritePRD: %v", err)
    }

    // ... write Requirements, TestSpec, Tasks similarly ...

    spec, err := b.Finalize()
    if err != nil {
        log.Fatalf("Finalize: %v", err)
    }
    fmt.Printf("Created spec: %s\n", spec.PRD.Frontmatter.SpecName)
}
```

---

## Discovery

### DiscoverSpecs

```go
func DiscoverSpecs(root string) (*DiscoveryResult, error)
```

**Description:** Scans `root` for spec folders matching the `{NN}_{snake_case_name}` naming pattern, loads metadata from each folder's `prd.md`, and builds a dependency graph from `tasks.json` files. Folders inside `archive/` are excluded. If `root` is an empty string, the current working directory is used.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `root` | `string` | Path to the spec root directory. Empty string uses the current working directory. |

**Returns:** `(*DiscoveryResult, error)` — discovery result with entries and dependency graph, or `nil` and an error if the root directory does not exist or a cycle is detected.

**Errors:**

| Condition | Error |
|-----------|-------|
| `root` directory does not exist | error |
| Dependency cycle detected | error identifying cycle participants |

**Example:**

```go
package main

import (
    "fmt"
    "log"

    "github.com/agent-fox/afspec"
)

func main() {
    result, err := afspec.DiscoverSpecs(".agent-fox/specs")
    if err != nil {
        log.Fatalf("discover: %v", err)
    }

    fmt.Printf("Found %d specs:\n", len(result.Entries))
    for _, entry := range result.Entries {
        fmt.Printf("  %s (%s) — status: %s, complete: %v\n",
            entry.SpecID, entry.SpecName, entry.Status, entry.Complete)
    }

    order, err := result.Graph.TopologicalOrder()
    if err != nil {
        log.Fatalf("topological order: %v", err)
    }
    fmt.Printf("Build order: %v\n", order)
}
```

---

## Types

### Spec

The complete in-memory representation of a four-artifact spec package.

| Field | Type | Description |
|-------|------|-------------|
| `PRD` | `*PRD` | Parsed `prd.md` (frontmatter + body). |
| `Requirements` | `*Requirements` | Parsed `requirements.json`. |
| `TestSpec` | `*TestSpecDoc` | Parsed `test_spec.json`. |
| `Tasks` | `*Tasks` | Parsed `tasks.json`. |
| `Dir` | `string` | Absolute path to the spec folder on disk. |

---

### PRD

Represents `prd.md`: YAML frontmatter and markdown body.

| Field | Type | Description |
|-------|------|-------------|
| `Frontmatter` | `Frontmatter` | Parsed YAML frontmatter fields. |
| `Body` | `string` | Full markdown body (everything after the frontmatter block). |

---

### Frontmatter

The 12 YAML frontmatter fields with fixed serialization order.

| Field | Type | YAML key | Description |
|-------|------|----------|-------------|
| `SpecID` | `string` | `spec_id` | Numeric spec identifier (e.g., `"05"`). |
| `SpecName` | `string` | `spec_name` | Snake-case spec name (e.g., `"my_feature"`). |
| `Title` | `string` | `title` | Human-readable title. |
| `Status` | `Status` | `status` | Lifecycle status (see `Status` type). |
| `CreatedAt` | `string` | `created_at` | ISO 8601 creation timestamp. |
| `UpdatedAt` | `string` | `updated_at` | ISO 8601 last-updated timestamp. |
| `Owner` | `string` | `owner` | Team or individual responsible for the spec. |
| `Source` | `string` | `source` | URL or reference to the originating issue/request. |
| `Supersedes` | `[]string` | `supersedes` | List of spec IDs this spec supersedes. |
| `Tags` | `[]string` | `tags` | Classification tags. |
| `IntentHash` | `*string` | `intent_hash` | SHA-256 hash of the `## Intent` section body (null until `draft → active`). |
| `SchemaVersion` | `int` | `schema_version` | Schema version (currently `1`). |

---

### Status

Lifecycle status string type.

```go
type Status string

const (
    StatusDraft      Status = "draft"
    StatusActive     Status = "active"
    StatusSealed     Status = "sealed"
    StatusSuperseded Status = "superseded"
    StatusArchived   Status = "archived"
)
```

| Value | Description |
|-------|-------------|
| `draft` | Initial state; spec is under active authorship. |
| `active` | Spec is approved and implementation is in progress. |
| `sealed` | Implementation is complete; spec may only be superseded or archived. |
| `superseded` | Replaced by another spec (terminal). |
| `archived` | No longer active (terminal). |

---

### Requirements

Parsed `requirements.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `Schema` | `string` | `$schema` | JSON Schema URI. |
| `SpecID` | `string` | `spec_id` | Spec identifier. |
| `SpecName` | `string` | `spec_name` | Spec name. |
| `SchemaVersion` | `int` | `schema_version` | Schema version. |
| `Introduction` | `string` | `introduction` | Introductory text. |
| `Glossary` | `map[string]string` | `glossary` | Term-to-definition map. |
| `Requirements` | `[]Requirement` | `requirements` | List of requirements. |
| `CorrectnessProperties` | `[]CorrectnessProperty` | `correctness_properties` | Formal correctness properties. |
| `ExecutionPaths` | `[]ExecutionPath` | `execution_paths` | Traced execution paths. |
| `ErrorHandling` | `[]ErrorHandlingEntry` | `error_handling` | Error handling entries. |

---

### Criterion

An EARS discriminated union representing a single acceptance criterion or edge case. `EarsPattern` determines which pattern-specific fields are populated.

| Field | Type | Description |
|-------|------|-------------|
| `ID` | `string` | Criterion ID (e.g., `"01-REQ-1.1"`). |
| `EarsPattern` | `string` | EARS pattern: `ubiquitous`, `event_driven`, `complex_event`, `state_driven`, `unwanted`, `optional`. |
| `System` | `string` | The system performing the action. |
| `Action` | `string` | The required action. |
| `ReturnContract` | `*string` | Optional return contract appended to the EARS sentence (null if not applicable). |
| `Trigger` | `string` | Event trigger (populated for `event_driven` and `complex_event`). |
| `Condition` | `string` | Additional condition (populated for `complex_event`). |
| `ErrorCondition` | `string` | Error/unwanted condition (populated for `unwanted`). |
| `State` | `string` | System state (populated for `state_driven`). |
| `Feature` | `string` | Optional feature gate (populated for `optional`). |

---

### TestSpecDoc

Parsed `test_spec.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `Schema` | `string` | `$schema` | JSON Schema URI. |
| `SpecID` | `string` | `spec_id` | Spec identifier. |
| `SpecName` | `string` | `spec_name` | Spec name. |
| `SchemaVersion` | `int` | `schema_version` | Schema version. |
| `TestCases` | `[]TestCase` | `test_cases` | Unit and integration test cases. |
| `PropertyTests` | `[]PropertyTest` | `property_tests` | Property-based tests. |
| `EdgeCaseTests` | `[]EdgeCaseTest` | `edge_case_tests` | Edge case tests. |
| `SmokeTests` | `[]SmokeTest` | `smoke_tests` | Smoke/integration tests. |
| `Coverage` | `Coverage` | `coverage` | Coverage tracking matrix. |

---

### Tasks

Parsed `tasks.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `Schema` | `string` | `$schema` | JSON Schema URI. |
| `SpecID` | `string` | `spec_id` | Spec identifier. |
| `SpecName` | `string` | `spec_name` | Spec name. |
| `SchemaVersion` | `int` | `schema_version` | Schema version. |
| `TestCommands` | `TestCommands` | `test_commands` | Test and lint commands for this spec. |
| `Dependencies` | `[]TaskDependency` | `dependencies` | Cross-spec dependencies. |
| `TaskGroups` | `[]TaskGroup` | `task_groups` | Ordered task groups. |
| `Traceability` | `[]TraceabilityEntry` | `traceability` | Requirement-to-test traceability entries. |

---

### ValidationError

A single validation finding.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `File` | `string` | `file` | File containing the error (e.g., `"requirements.json"`). |
| `Path` | `string` | `path` | JSON path to the offending element (e.g., `"/requirements/0/acceptance_criteria/1"`). |
| `Rule` | `string` | `rule` | Rule identifier (e.g., `"schema"`, `"integrity-1"`, `"id-format"`). |
| `Message` | `string` | `message` | Human-readable description of the error. |
| `Severity` | `Severity` | `severity` | `"error"` or `"warning"`. |

---

### LifecycleError

Returned when a lifecycle transition is rejected.

| Field | Type | Description |
|-------|------|-------------|
| `Current` | `Status` | The spec's current lifecycle status. |
| `Target` | `Status` | The requested target status. |
| `Reason` | `string` | Human-readable explanation of why the transition was rejected. |

```go
func (e *LifecycleError) Error() string
```

---

### IncompleteSpecError

Returned when `Bootstrap.Finalize()` is called before all four files have been written.

| Field | Type | Description |
|-------|------|-------------|
| `MissingFiles` | `[]string` | Names of the files that have not been written yet. |

```go
func (e *IncompleteSpecError) Error() string
```

---

### DiscoveryResult

The result of a `DiscoverSpecs` call.

| Field | Type | Description |
|-------|------|-------------|
| `Entries` | `[]SpecEntry` | All spec entries found in the root directory. |
| `Graph` | `*DependencyGraph` | Dependency graph built from cross-spec task dependencies. |

---

### SpecEntry

Metadata about a single discovered spec.

| Field | Type | Description |
|-------|------|-------------|
| `Dir` | `string` | Absolute path to the spec folder. |
| `SpecID` | `string` | Spec identifier extracted from the folder name. |
| `SpecName` | `string` | Snake-case spec name extracted from the folder name. |
| `Status` | `Status` | Lifecycle status from `prd.md` frontmatter. |
| `Complete` | `bool` | `true` if all four spec files are present. |

---

### DependencyGraph

Adjacency list of cross-spec dependencies.

| Field | Type | Description |
|-------|------|-------------|
| `Edges` | `map[string][]string` | Maps each `spec_id` to the list of `spec_id` values it depends on. |

### TopologicalOrder

```go
func (g *DependencyGraph) TopologicalOrder() ([]string, error)
```

**Description:** Returns spec IDs in dependency order (dependencies before dependents). This method is defined on `DependencyGraph`.

**Parameters:** None.

**Returns:** `([]string, error)` — ordered list of spec IDs, or an error if a cycle is detected.

**Errors:**

| Condition | Error |
|-----------|-------|
| Dependency cycle detected | error identifying cycle participants |

Note: A `nil` error means a valid ordering was produced.

---

### Bootstrap

Handle for incrementally writing spec files to a new spec folder. Returned by `NewBootstrap`. Safe for concurrent use within a single goroutine; mutex-guarded for safety.

| Field | Type | Description |
|-------|------|-------------|
| `dir` | `string` | Path to the spec folder (unexported). |
| `specID` | `string` | Spec ID (unexported). |
| `specName` | `string` | Spec name (unexported). |
| `written` | `map[string]bool` | Tracks which files have been written (unexported). |
| `mu` | `sync.Mutex` | Guards concurrent access (unexported). |

Methods: `WritePRD`, `WriteRequirements`, `WriteTestSpec`, `WriteTasks`, `Finalize` — see [Bootstrap](#bootstrap) section above.

---

### SubtaskState

Lifecycle state for individual task subtasks.

```go
type SubtaskState string

const (
    StatePending             SubtaskState = "pending"
    StateQueued              SubtaskState = "queued"
    StateInProgress          SubtaskState = "in_progress"
    StateDone                SubtaskState = "done"
    StatePendingReevaluation SubtaskState = "pending_reevaluation"
    StateDropped             SubtaskState = "dropped"
)
```

### LegalTransitions

```go
func (s SubtaskState) LegalTransitions() []SubtaskState
```

**Description:** Returns the allowed next states for a given subtask state. This method is defined on `SubtaskState`.

**Parameters:** None.

**Returns:** `[]SubtaskState` — slice of allowed next states. Returns an empty slice for the terminal state (`dropped`).

**Errors:** None. This method does not return an error.

| Current State | Allowed Next States |
|---------------|---------------------|
| `pending` | `queued`, `dropped` |
| `queued` | `in_progress`, `pending`, `dropped` |
| `in_progress` | `done`, `pending_reevaluation` |
| `done` | `pending_reevaluation` |
| `pending_reevaluation` | `pending`, `dropped` |
| `dropped` | _(terminal — empty slice)_ |

---

### Additional Types

The following types are used within the above primary types. Refer to the design document (`.agent-fox/specs/01_golang_library/design.md`) for full field definitions.

| Type | Used In | Description |
|------|---------|-------------|
| `Requirement` | `Requirements.Requirements` | A single requirement with user story, acceptance criteria, and edge cases. |
| `UserStory` | `Requirement.UserStory` | Role/goal/benefit structure. |
| `CorrectnessProperty` | `Requirements.CorrectnessProperties` | Formal correctness property with `for_any` / `invariant` clauses. |
| `ExecutionPath` | `Requirements.ExecutionPaths` | Traced execution path with ordered steps. |
| `ExecutionPathStep` | `ExecutionPath.Steps` | Actor + action pair. |
| `ErrorHandlingEntry` | `Requirements.ErrorHandling` | Error condition, behavior, and requirement reference. |
| `TestCase` | `TestSpecDoc.TestCases` | Unit or integration test case. |
| `PropertyTest` | `TestSpecDoc.PropertyTests` | Property-based test with strategy and invariant. |
| `EdgeCaseTest` | `TestSpecDoc.EdgeCaseTests` | Edge case test case. |
| `SmokeTest` | `TestSpecDoc.SmokeTests` | Smoke/integration test with real components list. |
| `Coverage` | `TestSpecDoc.Coverage` | Coverage tracking: covered requirements, gaps, properties, paths. |
| `TestCommands` | `Tasks.TestCommands` | Spec test, all-tests, and linter command strings. |
| `TaskDependency` | `Tasks.Dependencies` | Cross-spec dependency with group and relationship metadata. |
| `TaskGroup` | `Tasks.TaskGroups` | A group of subtasks with a kind and verification step. |
| `Subtask` | `TaskGroup.Subtasks` | Individual task item with state, details, and traceability refs. |
| `VerificationSubtask` | `TaskGroup.Verification` | Verification checklist for a task group. |
| `TraceabilityEntry` | `Tasks.Traceability` | Links a requirement ID to a test spec ID, task ID, and test file path. |
| `Severity` | `ValidationError.Severity` | `"error"` or `"warning"`. |
