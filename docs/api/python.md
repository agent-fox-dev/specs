# Python API Reference: afspec

The `afspec` Python library provides a complete implementation of the agent-fox
specification format (v1). Import it as:

```python
import afspec
```

The library targets Python 3.10+. All public functions and types are exported
from the top-level `afspec` package. Internal modules (`afspec/loader.py`,
`afspec/saver.py`, etc.) are implementation details and are not part of the
public API.

---

## Loading

### load_spec

```python
def load_spec(path: Path) -> Spec:
```

**Description:** Reads all four spec files (`prd.md`, `requirements.json`,
`test_spec.json`, `tasks.json`) from the directory at `path` and returns a
fully populated `Spec`. Files are parsed and validated for structural
well-formedness (JSON schema and YAML frontmatter) but cross-file integrity
is not checked here — call `validate` for full validation.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Path to the spec folder on disk. |

**Returns:** `Spec` — a frozen dataclass instance populated from all four spec
files.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | `path` does not exist. |
| `IncompleteSpecError` | A required file (`prd.md`, `requirements.json`, `test_spec.json`, or `tasks.json`) is missing. |
| `SpecValidationError` | Malformed JSON in a spec file, malformed YAML frontmatter, or missing `## Intent` section in `prd.md`. |

**Example:**

```python
import afspec
from pathlib import Path

spec = afspec.load_spec(Path(".agent-fox/specs/01_my_feature"))
print(f"Loaded spec {spec.prd.frontmatter.spec_name!r}")
print(f"Status: {spec.prd.frontmatter.status}")
```

---

## Saving

### save_spec

```python
def save_spec(spec: Spec, path: Path) -> None:
```

**Description:** Writes all four spec files to `path` deterministically.
Before writing, `save_spec` sets `updated_at` to the current UTC timestamp
and recomputes the `coverage` field in `test_spec.json` from cross-references.
Files are written atomically (write-to-temp-then-rename). If any write fails,
already-written temp files are cleaned up to prevent partial results.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `Spec` | The spec instance to write. |
| `path` | `Path` | Path to the spec folder on disk. Must already exist. |

**Returns:** `None`.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | `path` does not exist; no files written. |
| `LifecycleError` | Spec status is `sealed`, `superseded`, or `archived`; mutation rejected. |
| `OSError` | File write failure mid-operation; temp files cleaned up, pre-save state preserved. |

**Example:**

```python
import afspec
from pathlib import Path

spec = afspec.load_spec(Path(".agent-fox/specs/01_my_feature"))
# Spec is a frozen dataclass; use dataclasses.replace for mutations.
import dataclasses
updated_frontmatter = dataclasses.replace(spec.prd.frontmatter, owner="new-owner")
updated_prd = dataclasses.replace(spec.prd, frontmatter=updated_frontmatter)
updated_spec = dataclasses.replace(spec, prd=updated_prd)

afspec.save_spec(updated_spec, Path(".agent-fox/specs/01_my_feature"))
print("Spec saved.")
```

---

## Validation

### validate

```python
def validate(spec: Spec) -> list[ValidationError]:
```

**Description:** Runs the full validation suite: JSON Schema validation for
all four spec files, ID format validation, and seven cross-file integrity
checks. Returns all errors found. An empty list means the spec is valid.

Note: Unlike the Go library which uses two return values to signal internal
errors, the Python library raises exceptions for internal failures and returns
only the list of `ValidationError` instances.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `Spec` | The spec instance to validate. |

**Returns:** `list[ValidationError]` — all validation errors found (may be
empty for a valid spec).

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `SpecValidationError` | Internal validation failure (e.g., schema loading error). |

**Example:**

```python
import afspec
from pathlib import Path

spec = afspec.load_spec(Path(".agent-fox/specs/01_my_feature"))
errors = afspec.validate(spec)
for err in errors:
    print(f"[{err.severity}] {err.file} at {err.path}: {err.message}")
if not errors:
    print("Spec is valid.")
```

---

## Rendering

### render_requirements

```python
def render_requirements(requirements: Requirements) -> str:
```

**Description:** Renders a `Requirements` instance to markdown. The output
includes a header, glossary section, and each requirement with its EARS
acceptance criteria and edge cases rendered as human-readable sentences using
EARS pattern templates.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `requirements` | `Requirements` | The requirements instance to render. |

**Returns:** `str` — deterministic markdown string.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | `requirements` is in an invalid state (e.g., unknown EARS pattern). |

---

### render_test_spec

```python
def render_test_spec(test_spec: TestSpec) -> str:
```

**Description:** Renders a `TestSpec` instance to markdown, including all
test cases, property tests, edge case tests, smoke tests, and a coverage
matrix.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `test_spec` | `TestSpec` | The test spec instance to render. |

**Returns:** `str` — deterministic markdown string.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | `test_spec` is in an invalid state. |

---

### render_tasks

```python
def render_tasks(tasks: Tasks) -> str:
```

**Description:** Renders a `Tasks` instance to markdown, including all task
groups with their subtasks, verification steps, and the traceability matrix.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tasks` | `Tasks` | The tasks instance to render. |

**Returns:** `str` — deterministic markdown string.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | `tasks` is in an invalid state. |

---

### render_combined

```python
def render_combined(spec: Spec) -> str:
```

**Description:** Produces a single combined markdown document: the PRD body
verbatim, followed by separator lines and the rendered output of requirements,
test_spec, and tasks. Useful for generating a complete spec document for
review.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `Spec` | The spec instance to render. |

**Returns:** `str` — combined markdown string joining PRD body and all
rendered artifacts.

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | Any rendering sub-step encounters an invalid state. |

**Example:**

```python
import afspec
from pathlib import Path

spec = afspec.load_spec(Path(".agent-fox/specs/01_my_feature"))
combined_md = afspec.render_combined(spec)
Path("output.md").write_text(combined_md, encoding="utf-8")
print(f"Wrote {len(combined_md)} characters.")
```

---

## Lifecycle

### transition

```python
def transition(spec: Spec, target_status: str) -> Spec:
```

**Description:** Applies a lifecycle state transition and returns a new
`Spec` with the updated status. The original spec is not modified (frozen
dataclass). Valid transitions follow the lifecycle graph: `draft → active`,
`draft → archived`, `active → sealed`, `sealed → superseded`,
`sealed → archived`. On `draft → active`, the intent hash is computed from
the `## Intent` section body and stored in `PRDFrontmatter.intent_hash`.

Note: Unlike Go (which uses return values), the Python library raises a
`LifecycleError` exception for illegal transitions.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `Spec` | The current spec instance. |
| `target_status` | `str` | Target lifecycle status string (e.g., `"active"`, `"sealed"`). |

**Returns:** `Spec` — a new spec instance with `prd.frontmatter.status` set
to `target_status` (and `intent_hash` set if transitioning to `active`).

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `LifecycleError` | Illegal transition (not in the allowed transition graph). |
| `LifecycleError` | Guard rejection (e.g., intent hash mismatch for active spec). |

**Example:**

```python
import afspec
from pathlib import Path

spec = afspec.load_spec(Path(".agent-fox/specs/01_my_feature"))
activated = afspec.transition(spec, "active")
print(f"New status: {activated.prd.frontmatter.status}")
print(f"Intent hash: {activated.prd.frontmatter.intent_hash}")

afspec.save_spec(activated, Path(".agent-fox/specs/01_my_feature"))
```

---

## Bootstrap

### BootstrapSpec

`BootstrapSpec` is a context manager for incrementally writing spec files to
a new spec folder. It defers cross-file validation until `__exit__` so that
each file can be written and validated individually before the complete spec
is assembled.

```python
class BootstrapSpec:
    def __init__(self, spec_root: Path, spec_id: str, spec_name: str) -> None: ...
    def __enter__(self) -> BootstrapSpec: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool: ...
    def write_prd(self, prd: PRD) -> None: ...
    def write_requirements(self, requirements: Requirements) -> None: ...
    def write_test_spec(self, test_spec: TestSpec) -> None: ...
    def write_tasks(self, tasks: Tasks) -> None: ...
```

**Description:** Creates a new spec folder at `spec_root / "{spec_id}_{spec_name}/"`.
The folder must not already exist. Each `write_*` method validates the
artifact against its per-file JSON Schema before writing. On `__exit__`, full
validation (schema + cross-file) is run and the completed `Spec` is returned
via `__exit__`; if validation fails, `SpecValidationError` is raised.

> **Note:** `BootstrapSpec` has no direct Go equivalent as a standalone
> function — Go uses `NewBootstrap` + `Bootstrap.Write*` + `Bootstrap.Finalize`.
> The Python version encapsulates all of this into a single context manager,
> making the lifecycle explicit and exception-safe.

**Parameters (constructor):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec_root` | `Path` | Parent directory in which to create the spec folder. |
| `spec_id` | `str` | Spec ID (e.g., `"05"`). |
| `spec_name` | `str` | Snake-case spec name (e.g., `"my_feature"`). |

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `FileExistsError` | Spec folder already exists; prevents overwrite. |
| `SpecValidationError` | Per-file schema validation fails during a `write_*` call. |
| `IncompleteSpecError` | `__exit__` called before all four files have been written. |
| `SpecValidationError` | Full validation (schema + cross-file) fails on `__exit__`. |

**Example:**

```python
import afspec
from afspec import BootstrapSpec, PRD, PRDFrontmatter, Requirements, TestSpec, Tasks
from pathlib import Path
from datetime import datetime, timezone

spec_root = Path(".agent-fox/specs")
now = datetime.now(timezone.utc).isoformat()

with BootstrapSpec(spec_root, "05", "my_feature") as bs:
    frontmatter = PRDFrontmatter(
        spec_id="05",
        spec_name="my_feature",
        title="My Feature",
        status="draft",
        created_at=now,
        updated_at=now,
        owner="team",
        source="https://github.com/org/repo/issues/42",
        supersedes=[],
        tags=[],
        intent_hash=None,
        schema_version=1,
    )
    prd = PRD(frontmatter=frontmatter, body="## Intent\n\nThis feature does something.\n")
    bs.write_prd(prd)
    # ... write requirements, test_spec, tasks similarly ...

print("Spec created and validated.")
```

---

## Discovery

### discover

```python
def discover(spec_root: Path | None = None) -> DiscoveryResult:
```

**Description:** Scans `spec_root` for spec folders matching the
`{NN}_{snake_case_name}` naming pattern, loads metadata from each folder's
`prd.md` frontmatter, and builds a dependency graph from `tasks.json`
dependency declarations. Folders inside `archive/` are excluded. If
`spec_root` is `None`, the current working directory is used.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec_root` | `Path \| None` | Path to the spec root directory. `None` uses the current working directory. |

**Returns:** `DiscoveryResult` — frozen dataclass containing `entries` (list
of `SpecEntry`) and `dependency_graph` (`DependencyGraph`).

**Exceptions:**

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | `spec_root` directory does not exist. |
| `SpecValidationError` | Dependency cycle detected among spec IDs. |

**Example:**

```python
import afspec
from pathlib import Path

result = afspec.discover(Path(".agent-fox/specs"))
print(f"Found {len(result.entries)} specs:")
for entry in result.entries:
    print(f"  {entry.spec_id} ({entry.spec_name}) — status: {entry.status}, complete: {entry.complete}")

order = result.dependency_graph.topological_sort()
print(f"Build order: {order}")
```

---

### schema_version

```python
def schema_version() -> int:
```

**Description:** Returns the schema version number supported by this
installation of the `afspec` library. Currently returns `1`. Use this to
guard version-sensitive operations when loading specs across library
upgrades.

**Parameters:** None.

**Returns:** `int` — the schema version integer (currently `1`).

**Exceptions:** None. This function always succeeds and does not raise any
exceptions.

**Example:**

```python
import afspec

version = afspec.schema_version()
print(f"afspec schema version: {version}")
assert version == 1, f"Unsupported schema version: {version}"
```

---

## Types

### Spec

The complete in-memory representation of a four-artifact spec package.
All fields are frozen (immutable).

| Field | Type | Description |
|-------|------|-------------|
| `prd` | `PRD` | Parsed `prd.md` (frontmatter + body). |
| `requirements` | `Requirements` | Parsed `requirements.json`. |
| `test_spec` | `TestSpec` | Parsed `test_spec.json`. |
| `tasks` | `Tasks` | Parsed `tasks.json`. |

---

### PRD

Represents `prd.md`: YAML frontmatter and markdown body.

| Field | Type | Description |
|-------|------|-------------|
| `frontmatter` | `PRDFrontmatter` | Parsed YAML frontmatter fields. |
| `body` | `str` | Full markdown body (everything after the frontmatter block). |

---

### PRDFrontmatter

The 12 YAML frontmatter fields with fixed serialization order.

| Field | Type | YAML key | Description |
|-------|------|----------|-------------|
| `spec_id` | `str` | `spec_id` | Numeric spec identifier (e.g., `"05"`). |
| `spec_name` | `str` | `spec_name` | Snake-case spec name (e.g., `"my_feature"`). |
| `title` | `str` | `title` | Human-readable title. |
| `status` | `str` | `status` | Lifecycle status (e.g., `"draft"`, `"active"`, `"sealed"`). |
| `created_at` | `str` | `created_at` | ISO 8601 creation timestamp. |
| `updated_at` | `str` | `updated_at` | ISO 8601 last-updated timestamp (set by `save_spec`). |
| `owner` | `str` | `owner` | Team or individual responsible for the spec. |
| `source` | `str` | `source` | URL or reference to the originating issue/request. |
| `supersedes` | `list[str]` | `supersedes` | List of spec IDs this spec supersedes. |
| `tags` | `list[str]` | `tags` | Classification tags. |
| `intent_hash` | `str \| None` | `intent_hash` | SHA-256 hash of the `## Intent` section body (None until `draft → active`). |
| `schema_version` | `int` | `schema_version` | Schema version (currently `1`). |

---

### Requirements

Parsed `requirements.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `schema` | `str` | `$schema` | JSON Schema URI. |
| `spec_id` | `str` | `spec_id` | Spec identifier. |
| `spec_name` | `str` | `spec_name` | Spec name. |
| `schema_version` | `int` | `schema_version` | Schema version. |
| `introduction` | `str` | `introduction` | Introductory text. |
| `glossary` | `dict[str, str]` | `glossary` | Term-to-definition map. |
| `requirements` | `list[Requirement]` | `requirements` | List of requirements. |
| `correctness_properties` | `list[CorrectnessProperty]` | `correctness_properties` | Formal correctness properties. |
| `execution_paths` | `list[ExecutionPath]` | `execution_paths` | Traced execution paths. |
| `error_handling` | `list[ErrorHandlingEntry]` | `error_handling` | Error handling entries. |

---

### EARSCriterion

Base class for EARS-pattern acceptance criteria. The `ears_pattern` field
determines which subclass and which pattern-specific fields are populated.
Use the `EARSCriterion.from_dict` factory to construct the correct subclass.

```python
@dataclass(frozen=True)
class EARSCriterion:
    id: str
    ears_pattern: str
    system: str
    action: str
    return_contract: str | None

    @classmethod
    def from_dict(cls, data: dict) -> EARSCriterion: ...
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Criterion ID (e.g., `"01-REQ-1.1"`). |
| `ears_pattern` | `str` | EARS pattern: `ubiquitous`, `event_driven`, `complex_event`, `state_driven`, `unwanted`, `optional`. |
| `system` | `str` | The system performing the action. |
| `action` | `str` | The required action. |
| `return_contract` | `str \| None` | Optional return contract appended to the EARS sentence. |

**Subclasses:**

| Subclass | Additional Fields | Pattern |
|----------|-----------------|---------|
| `UbiquitousCriterion` | _(none)_ | `ubiquitous` |
| `EventDrivenCriterion` | `trigger: str` | `event_driven` |
| `ComplexEventCriterion` | `trigger: str`, `condition: str` | `complex_event` |
| `StateDrivenCriterion` | `state: str` | `state_driven` |
| `UnwantedCriterion` | `error_condition: str` | `unwanted` |
| `OptionalCriterion` | `feature: str` | `optional` |

---

### TestSpec

Parsed `test_spec.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `schema` | `str` | `$schema` | JSON Schema URI. |
| `spec_id` | `str` | `spec_id` | Spec identifier. |
| `spec_name` | `str` | `spec_name` | Spec name. |
| `schema_version` | `int` | `schema_version` | Schema version. |
| `test_cases` | `list[TestCase]` | `test_cases` | Unit and integration test cases. |
| `property_tests` | `list[PropertyTest]` | `property_tests` | Property-based tests. |
| `edge_case_tests` | `list[EdgeCaseTest]` | `edge_case_tests` | Edge case tests. |
| `smoke_tests` | `list[SmokeTest]` | `smoke_tests` | Smoke/integration tests. |
| `coverage` | `Coverage` | `coverage` | Coverage tracking matrix. |

---

### Tasks

Parsed `tasks.json`.

| Field | Type | JSON key | Description |
|-------|------|----------|-------------|
| `schema` | `str` | `$schema` | JSON Schema URI. |
| `spec_id` | `str` | `spec_id` | Spec identifier. |
| `spec_name` | `str` | `spec_name` | Spec name. |
| `schema_version` | `int` | `schema_version` | Schema version. |
| `test_commands` | `TestCommands` | `test_commands` | Test and lint commands for this spec. |
| `dependencies` | `list[TaskDependency]` | `dependencies` | Cross-spec dependencies. |
| `task_groups` | `list[TaskGroup]` | `task_groups` | Ordered task groups. |
| `traceability` | `list[TraceabilityEntry]` | `traceability` | Requirement-to-test traceability entries. |

---

### ValidationError

A single validation finding returned by `validate`.

| Field | Type | Description |
|-------|------|-------------|
| `file` | `str` | File containing the error (e.g., `"requirements.json"`). |
| `path` | `str` | JSON path to the offending element (e.g., `"/requirements/0/acceptance_criteria/1"`). |
| `rule` | `str` | Rule identifier (e.g., `"schema"`, `"integrity-1"`, `"id-format"`). |
| `message` | `str` | Human-readable description of the error. |
| `severity` | `str` | `"error"` or `"warning"`. |

---

### SubtaskState

Lifecycle state enum for individual task subtasks.

```python
class SubtaskState(enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    PENDING_REEVALUATION = "pending_reevaluation"
    DROPPED = "dropped"

    def can_transition_to(self, target: SubtaskState) -> bool: ...
```

| Value | Description |
|-------|-------------|
| `PENDING` | Not yet started. |
| `QUEUED` | Scheduled for work. |
| `IN_PROGRESS` | Currently being worked on. |
| `DONE` | Completed. |
| `PENDING_REEVALUATION` | Completed but under review. |
| `DROPPED` | Cancelled (terminal state). |

**Transition table:**

| From State | Allowed Next States |
|------------|-------------------|
| `PENDING` | `QUEUED`, `DROPPED` |
| `QUEUED` | `IN_PROGRESS`, `PENDING`, `DROPPED` |
| `IN_PROGRESS` | `DONE`, `PENDING_REEVALUATION` |
| `DONE` | `PENDING_REEVALUATION` |
| `PENDING_REEVALUATION` | `PENDING`, `DROPPED` |
| `DROPPED` | _(terminal — no transitions)_ |

---

### DiscoveryResult

The result of a `discover` call.

| Field | Type | Description |
|-------|------|-------------|
| `entries` | `list[SpecEntry]` | All spec entries found in the spec root. |
| `dependency_graph` | `DependencyGraph` | Dependency graph built from cross-spec task dependencies. |

---

### SpecEntry

Metadata about a single discovered spec.

| Field | Type | Description |
|-------|------|-------------|
| `spec_id` | `str` | Spec identifier extracted from the folder name. |
| `spec_name` | `str` | Snake-case spec name extracted from the folder name. |
| `status` | `str` | Lifecycle status from `prd.md` frontmatter. |
| `path` | `Path` | Path to the spec folder on disk. |
| `complete` | `bool` | `True` if all four spec files are present. |

---

### DependencyGraph

Adjacency list of cross-spec dependencies.

| Field | Type | Description |
|-------|------|-------------|
| `edges` | `list[DependencyEdge]` | List of directed dependency edges between spec IDs. |

**Methods:**

```python
def topological_sort(self) -> list[str]: ...
def has_cycle(self) -> bool: ...
```

- `topological_sort()` — Returns spec IDs in dependency order (dependencies
  before dependents). Raises `SpecValidationError` if a cycle is detected.
- `has_cycle()` — Returns `True` if the graph contains a dependency cycle.

---

### BootstrapSpec

Context manager for incrementally creating a new spec folder. See the
[Bootstrap](#bootstrap) section for full documentation and examples.

| Field | Type | Description |
|-------|------|-------------|
| `spec_root` | `Path` | Parent directory for the new spec folder. |
| `spec_id` | `str` | Spec ID. |
| `spec_name` | `str` | Spec name (snake_case). |

**Methods:** `write_prd`, `write_requirements`, `write_test_spec`,
`write_tasks`.

---

### Exception Hierarchy

The `afspec` library uses a typed exception hierarchy rooted at `AfspecError`.

```
AfspecError (base)
├── SpecValidationError   — validation failures (schema, cross-file)
├── LifecycleError        — illegal state transitions or mutation guards
└── IncompleteSpecError   — spec folder missing required files
```

---

### AfspecError

Base class for all `afspec`-specific exceptions.

```python
class AfspecError(Exception): ...
```

All `afspec` exceptions inherit from `AfspecError`. Use this as a catch-all
for library-specific errors.

---

### SpecValidationError

Raised when schema validation or cross-file integrity checks fail.

```python
class SpecValidationError(AfspecError):
    errors: list[ValidationError]
```

| Field | Type | Description |
|-------|------|-------------|
| `errors` | `list[ValidationError]` | All validation errors that caused the failure. |

---

### LifecycleError

Raised when a lifecycle transition is rejected or a mutation guard is
triggered.

```python
class LifecycleError(AfspecError):
    current_state: str
    target_state: str | None
    field: str | None
```

| Field | Type | Description |
|-------|------|-------------|
| `current_state` | `str` | The spec's current lifecycle status. |
| `target_state` | `str \| None` | The requested target status, or `None` for mutation guard rejections. |
| `field` | `str \| None` | The field that triggered the guard (e.g., `"intent_hash"`), or `None`. |

---

### IncompleteSpecError

Raised when a spec folder is missing required files (e.g., at load time or
when `BootstrapSpec.__exit__` is called before all files are written).

```python
class IncompleteSpecError(AfspecError):
    missing_files: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `missing_files` | `list[str]` | Names of the required files that are absent. |

---

### Additional Types

The following types are used within the above primary types. Refer to the
design document (`.agent-fox/specs/02_python_library/design.md`) for full
field definitions.

| Type | Used In | Description |
|------|---------|-------------|
| `Requirement` | `Requirements.requirements` | A single requirement with user story, criteria, and edge cases. |
| `UserStory` | `Requirement.user_story` | Role/goal/benefit structure. |
| `CorrectnessProperty` | `Requirements.correctness_properties` | Formal correctness property with `for_any` / `invariant` clauses. |
| `ExecutionPath` | `Requirements.execution_paths` | Traced execution path with ordered steps. |
| `ExecutionPathStep` | `ExecutionPath.steps` | Actor + action pair. |
| `ErrorHandlingEntry` | `Requirements.error_handling` | Error condition, behavior, and requirement reference. |
| `TestCase` | `TestSpec.test_cases` | Unit or integration test case. |
| `PropertyTest` | `TestSpec.property_tests` | Property-based test with strategy and invariant. |
| `EdgeCaseTest` | `TestSpec.edge_case_tests` | Edge case test case. |
| `SmokeTest` | `TestSpec.smoke_tests` | Smoke/integration test with real components list. |
| `Coverage` | `TestSpec.coverage` | Coverage tracking: covered requirements, gaps, properties, paths. |
| `TestCommands` | `Tasks.test_commands` | Spec test, all-tests, and linter command strings. |
| `TaskDependency` | `Tasks.dependencies` | Cross-spec dependency with group and relationship metadata. |
| `TaskGroup` | `Tasks.task_groups` | A group of subtasks with a kind and verification step. |
| `Subtask` | `TaskGroup.subtasks` | Individual task item with state, details, and traceability refs. |
| `VerificationSubtask` | `TaskGroup.verification` | Verification checklist for a task group. |
| `TraceabilityEntry` | `Tasks.traceability` | Links a requirement ID to a test spec ID, task ID, and test file path. |
| `DependencyEdge` | `DependencyGraph.edges` | Directed edge from one spec ID to another. |
