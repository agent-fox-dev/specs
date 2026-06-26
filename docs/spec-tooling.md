# Spec Tooling Reference

This document describes the Python packages that implement the
[Spec Format Specification](spec-format_v1.2.md). Two packages provide the
core functionality: **afspec** (standalone format library) and **agentspec**
(AI-powered spec creation). A third package, **spec**, wraps agentspec as a
CLI. All three live in the `agent-fox` monorepo under `packages/`.

```
afspec              standalone format library (no internal deps)
  ↑
agentspec           AI-powered spec creation (depends on afspec, agentfox)
  ↑
spec CLI            command-line wrapper (depends on agentspec)
```

The harness packages (`agentfox`, `af`) also depend on `afspec` for
validation, rendering, and prompt assembly at execution time.

---

## 1. afspec

Standalone Python library for loading, validating, rendering, and mutating
spec packages. No AI, no network calls, no internal dependencies beyond
pydantic, PyYAML, and jsonschema. Use this package when you need to work
with spec artifacts programmatically.

**Version:** 4.0.0-rc5  
**Python:** ≥ 3.12  
**Dependencies:** pydantic ≥ 2.13, PyYAML ≥ 6.0, jsonschema ≥ 4.0

### 1.1 Core types

All models are Pydantic `BaseModel` subclasses. Mutation methods return new
instances (immutable pattern).

**Top-level container:**

| Type | Description |
| --- | --- |
| `Spec` | Top-level container: `prd`, `requirements`, `test_spec`, `tasks`, `architecture` (optional string). |
| `PRDDocument` | `frontmatter: PRDFrontmatter`, `body: str`. |
| `PRDFrontmatter` | All YAML frontmatter fields: `spec_id`, `spec_name`, `title`, `status`, `created_at`, `updated_at`, `owner`, `source`, `supersedes`, `tags`, `intent_hash`, `schema_version`. |

**Requirements:**

| Type | Description |
| --- | --- |
| `Requirements` | Top-level: `introduction`, `glossary`, `requirements`, `correctness_properties`, `execution_paths`, `error_handling`. |
| `Requirement` | `id`, `title`, `user_story`, `acceptance_criteria: list[Criterion]`, `edge_cases: list[Criterion]`. |
| `UserStory` | `role`, `goal`, `benefit`. |
| `Criterion` | EARS criterion: `id`, `ears_pattern`, `system`, `action`, `return_contract`, plus pattern-specific fields (`trigger`, `condition`, `error_condition`, `state`, `feature`). Has `with_return_contract()`. |
| `CorrectnessProperty` | `id`, `title`, `for_any`, `invariant`, `validates: list[str]`. |
| `ExecutionPath` | `id`, `title`, `steps: list[PathStep]`. |
| `PathStep` | `actor`, `action`. |
| `ErrorHandlingEntry` | `id`, `condition`, `behavior`, `requirement_id`. |

**Test spec:**

| Type | Description |
| --- | --- |
| `TestSpec` | Top-level: `test_cases`, `property_tests`, `edge_case_tests`, `smoke_tests`, `coverage`. |
| `TestCase` | `id`, `requirement_id`, `kind`, `description`, `preconditions`, `input`, `expected`, `assertion_pseudocode`. |
| `PropertyTest` | `id`, `property_id`, `validates`, `description`, `for_any_strategy`, `invariant_check`. |
| `EdgeCaseTest` | Same structure as `TestCase`, edge-case ID format. |
| `SmokeTest` | `id`, `execution_path_id`, `description`, `trigger`, `real_components`, `mockable`, `expected_effects`. |
| `Coverage` | `requirements_covered`, `properties_covered`, `paths_covered`, `gaps`. |

**Tasks:**

| Type | Description |
| --- | --- |
| `Tasks` | Top-level: `test_commands`, `dependencies`, `task_groups`, `traceability`. |
| `TestCommands` | `spec_tests`, `all_tests`, `linter`. |
| `TaskDependency` | `depends_on_spec`, `from_group`, `to_group`, `relationship`, `sentinel: bool`. |
| `TaskGroup` | `id: int`, `kind: TaskGroupKind`, `title`, `subtasks`, `verification`. |
| `Subtask` | `id`, `title`, `details`, `test_spec_refs`, `requirement_refs`, `state: SubtaskState`, `optional: bool`. Has `transition_to()`. |
| `VerificationSubtask` | `id`, `checks: list[str]`. |
| `TraceabilityEntry` | `requirement_id`, `test_spec_id`, `task_id`, `test_path: str | None`. |

**Enums:**

| Enum | Values |
| --- | --- |
| `Status` | `DRAFT`, `ACTIVE`, `SEALED`, `SUPERSEDED`, `ARCHIVED` |
| `EARSPattern` | `UBIQUITOUS`, `EVENT_DRIVEN`, `COMPLEX_EVENT`, `STATE_DRIVEN`, `UNWANTED`, `OPTIONAL` |
| `SubtaskState` | `PENDING`, `QUEUED`, `IN_PROGRESS`, `DONE`, `PENDING_REEVALUATION`, `DROPPED` |
| `TaskGroupKind` | `TESTS`, `STANDARD`, `CHECKPOINT`, `WIRING_VERIFICATION` |

**Utility types:**

| Type | Description |
| --- | --- |
| `SpecMeta` | Lightweight spec metadata (id, name, status) without full artifact content. |
| `DependencyEdge` | Edge in the cross-spec dependency graph. |
| `DependencyGraph` | Directed graph with topological sort over specs. |
| `ValidationResult` | `valid: bool`, lists of `ValidationError` and `ValidationWarning`. |

### 1.2 Functions

**I/O:**

| Function | Description |
| --- | --- |
| `load_spec(path)` | Load a spec from a directory. Returns a `Spec`. |
| `save(spec, path)` | Write a spec to a directory. |
| `marshal_json(model)` | Serialize a Pydantic model to JSON-compatible dict. |

**Validation:**

| Function | Description |
| --- | --- |
| `validate(spec)` | Run both schema validation and cross-file integrity checks. Returns `ValidationResult`. |
| `validate_schema(data)` | Schema-only validation against bundled JSON Schemas. |
| `validate_cross_file(spec)` | Cross-file integrity checks (referential integrity, coverage, glossary). |

**Lifecycle:**

| Function | Description |
| --- | --- |
| `transition(spec, target_status, dir)` | Transition a spec to a new lifecycle status. Enforces the state machine. |
| `supersede(spec, supersedes_id, dir)` | Supersede a spec: apply deprecation banner, transition to `SUPERSEDED`. |
| `move_to_archive(spec, archive_dir)` | Move a spec directory to the archive. |
| `valid_transition(current, target)` | Check whether a subtask state transition is legal. |

**Rendering:**

| Function | Description |
| --- | --- |
| `render_combined(spec)` | Render the full spec as a single markdown document. |
| `render_individual(spec)` | Render each artifact separately. Returns a dict of artifact name to markdown. |
| `render_requirements(req)` | Render `requirements.json` as markdown. |
| `render_test_spec(ts)` | Render `test_spec.json` as markdown. |
| `render_tasks(tasks)` | Render `tasks.json` as markdown. |
| `render_ears_sentence(criterion)` | Render a single EARS criterion as a natural-language sentence. |

**Discovery:**

| Function | Description |
| --- | --- |
| `discover_specs(root)` | Find all valid spec directories under a root path. |
| `build_dependency_graph(root)` | Build a `DependencyGraph` from all specs under a root. |

**Construction:**

| Function | Description |
| --- | --- |
| `create_spec(spec_id, spec_name)` | Create an empty `Spec` with initialized metadata. |
| `ubiquitous_criterion(...)` | Build an EARS criterion with the `ubiquitous` pattern. |
| `event_driven_criterion(...)` | Build an EARS criterion with the `event_driven` pattern. |
| `complex_event_criterion(...)` | Build an EARS criterion with the `complex_event` pattern. |
| `state_driven_criterion(...)` | Build an EARS criterion with the `state_driven` pattern. |
| `unwanted_criterion(...)` | Build an EARS criterion with the `unwanted` pattern. |
| `optional_criterion(...)` | Build an EARS criterion with the `optional` pattern. |

**Other:**

| Function | Description |
| --- | --- |
| `compute_intent_hash(body)` | SHA-256 hex digest of the Intent section body (trimmed). |
| `compute_coverage(test_spec, requirements)` | Compute test coverage from a test spec against requirements. |

### 1.3 BootstrapSpec

Incremental spec creation with deferred validation. Use when building a spec
artifact-by-artifact (the normal creation flow) rather than loading a
complete spec from disk.

```python
bs = BootstrapSpec(spec_id="05", spec_name="my_feature")
bs.set_prd(prd_document)
bs.set_requirements(requirements)
bs.set_test_spec(test_spec)
bs.set_tasks(tasks)
bs.set_architecture(content)           # optional

spec, errors = bs.finalize()           # runs full validation
```

Cross-file validation is deferred until `finalize()`. A partially-built
`BootstrapSpec` is not validated — this mirrors the bootstrap mode described
in the format spec (§3.3).

### 1.4 Exceptions

| Exception | When raised |
| --- | --- |
| `SpecError` | Base class for all afspec errors. |
| `LoadError` | Failed to load a spec from disk. |
| `SaveError` | Failed to write a spec to disk. |
| `LifecycleError` | Illegal lifecycle transition. |
| `IntentError` | Intent hash mismatch or missing. |
| `BootstrapError` | Bootstrap invariant violated. |

---

## 2. agentspec

AI-powered spec creation library. Drives PRD assessment, refinement, and
artifact generation using the Anthropic API with Claude models. Depends on
`afspec` for models and validation, and on `agentfox` for shared
infrastructure.

**Version:** 4.0.0-rc5  
**Python:** ≥ 3.12  
**Dependencies:** afspec ≥ 4.0.0rc5, agentfox ≥ 4.0.0rc5, pyyaml ≥ 6.0

### 2.1 Campaign

Manages a campaign working directory containing one or more specs.

```python
# Create a new campaign
campaign = Campaign.create(path, name="auth-system", description="...")

# Open an existing campaign
campaign = Campaign.open(path)

# List specs in the campaign
specs: list[Path] = campaign.specs()

# Create a new spec from a PRD
session: SpecSession = campaign.new_spec(
    spec_name="data_models",
    prd="path/to/prd.md",            # or PRD content as string
    mode="interactive",               # or "one-shot"
)

# Access metadata
campaign.path          # Path
campaign.metadata      # CampaignMetadata (name, description, timestamps)
```

### 2.2 SpecSession

Stateful authoring session for one spec. Tracks the lifecycle from PRD input
to completed package. Sessions persist to `_session.json` in the spec
directory and can be resumed.

**State machine:**

```
init → assessing → refining ⟲ → prd_accepted → generating → generated
```

**API:**

```python
# Resume an existing session
session = SpecSession.resume(spec_dir)

# Assess the PRD (async)
assessment: Assessment = await session.assess()

# Refine with answers to agent questions (async, repeatable)
assessment: Assessment = await session.refine({"q1": "answer", "q2": "answer"})

# Accept the PRD, ending the refinement loop
session.accept_prd()

# Generate JSON artifacts (async)
result: GenerateResult = await session.generate()

# Validate the spec
validation: ValidationResult = session.validate()

# Render the spec
markdown: str = session.render(combined=True)

# Query state
session.state            # SessionState enum
session.spec_dir         # Path
session.assessment       # Assessment | None
```

### 2.3 Assessment model

The agent's evaluation of a PRD, with structured questions for refinement.

```python
@dataclass
class Assessment:
    quality: str                    # "ready" | "needs_refinement" | "incomplete"
    summary: str                    # agent's assessment
    gaps: list[str]                 # identified gaps or weaknesses
    questions: list[Question]       # structured questions for the user

@dataclass
class Question:
    id: str
    text: str                       # the question
    context: str                    # why the agent is asking
    options: list[str] | None       # suggested answers, if applicable
    required: bool
```

### 2.4 Generation result

```python
@dataclass
class GenerateResult:
    artifacts: list[str]            # names of generated artifacts
    validation: ValidationResult    # post-generation validation
    warnings: list[str]             # non-fatal warnings

@dataclass
class ValidationResult:
    valid: bool
    schema_errors: list[str]
    integrity_errors: list[str]
    repair_suggestions: list[RepairSuggestion]

@dataclass
class RepairSuggestion:
    artifact: str                   # which file
    description: str                # what's wrong
    patch: str                      # RFC 6902 JSON Patch
    auto_fixable: bool
```

### 2.5 Configuration

```python
config: AgentSpecConfig = load_config(agent_fox_config)
```

Configuration is resolved with 4-step precedence:

1. Environment variables (`AF_SPEC_MODEL`, `ANTHROPIC_API_KEY`)
2. `~/.af/settings.yaml` under `spec_tool`
3. Project-level `.af/settings.yaml`
4. Defaults (latest Claude Sonnet)

### 2.6 Exceptions

| Exception | When raised |
| --- | --- |
| `AgentSpecError` | Base class. |
| `AgentError` | API communication or parsing failures. |
| `SessionError` | Session state machine violations. |
| `ConfigError` | Missing or invalid configuration. |
| `CampaignError` | Campaign directory operation failures. |

---

## 3. spec CLI

Command-line wrapper around agentspec. Does not require the hub — works
against a local campaign directory. Entry point: `spec`.

| Command | Description |
| --- | --- |
| `spec new <prd-file> [--name <name>]` | Create a new spec from a PRD file. Runs initial assessment. |
| `spec refine <spec> --answers <file>` | Submit answers to agent questions as JSON. Agent re-assesses. |
| `spec generate <spec>` | Generate JSON artifacts from the accepted PRD. |
| `spec render <spec> [--combined] [--json]` | Render the spec as markdown (or JSON). |
| `spec validate <spec>` | Run schema and cross-file validation checks. |
| `spec status [<spec>]` | Print session state. Without `<spec>`, shows all specs. |

The `<spec>` argument is a spec directory name (e.g. `01_data_models`) or
number (e.g. `01`). Commands run relative to the current directory, which
must be a campaign directory containing `campaign.yaml`.

---

## 4. Relationship to the harness

The harness packages (`agentfox`, `af`) depend on `afspec` but not on
`agentspec`. The split is intentional:

- **afspec** is the shared foundation. The harness uses it at execution time
  for validation, rendering, and prompt assembly. No AI dependency.
- **agentspec** is the authoring tool. It uses afspec for models and
  validation, and the Anthropic API for PRD assessment and artifact
  generation. It runs standalone or through the Planner specialist inside
  the harness.

```
af CLI ──► agentfox ──► afspec          (execution-time: validate, render)
spec CLI ──► agentspec ──► afspec       (authoring-time: assess, generate)
                       ──► agentfox     (shared infrastructure)
```

The `spec submit` command (not yet implemented) will push a completed spec
to the hub's spec store. The `af spec approve` command transitions it from
`draft` to `active`. See
[services-architecture.md §7.4](services-architecture.md#74-relationship-to-the-harness)
for the full authoring-to-execution handoff.
