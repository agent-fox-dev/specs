# Spec Format — Net-New Design (draft v0.1)

A clean-slate specification for how an agent-fox-style spec is represented on disk, mutated by agents and operators, validated, and rendered.

This document defines the **format**. A separate library and skill implement the **operations**.

---

## 1. Frame

A spec is a unit of design intent and execution planning for one cohesive feature or concern. It is the durable artifact that survives sessions, drives agent work, and gets reviewed when work is merged.

This format makes a deliberate split:

- **Narrative is markdown.** Slow-moving, human-authored, prose. The "why."
- **Evolving state is JSON.** Fast-moving, schema-validated, mutated by JSON Patch from both operators and agents. The "what / verify / do."

Four artifacts. No optional fifth. Anything outside this set belongs in project-level steering, not per-spec.

---

## 2. The artifacts

| File | Format | Role | Mutation owner | Mutation style |
|---|---|---|---|---|
| `prd.md` | markdown + YAML frontmatter | Why this exists; what it intends | operator | edit-in-place; frontmatter and `Intent` section frozen after creation |
| `requirements.json` | JSON | What the system must do, must guarantee, must wire | coordinator + operator | JSON Patch |
| `test_spec.json` | JSON | How each requirement is verified | coordinator only (derived) | JSON Patch (regenerated on requirements changes) |
| `tasks.json` | JSON | What work to do, in what order, with what dependencies | coordinator + operator | JSON Patch |

`design.md` is intentionally absent. Its valuable content has been redistributed:
- Correctness Properties → `requirements.json`
- Execution Paths → `requirements.json`
- Error Handling → `requirements.json`
- Module Responsibilities / Components / Tech Stack / Operational Readiness / Definition of Done / Testing Strategy → either dropped as required-per-spec, or moved to project-level steering.

---

## 3. `prd.md`

### 3.1 Frontmatter

YAML frontmatter at the top of the file. Schema-validated by the library. Operator-owned; frozen at spec sealing (no mutation after a Space is harvested).

```yaml
---
spec_id: "05"
spec_name: "spec_driven_spaces"
title: "Spec-driven Spaces for agent-fox"
status: "draft"           # draft | active | sealed | superseded | archived
created_at: "2026-05-18T12:00:00Z"
updated_at: "2026-05-18T12:00:00Z"
owner: "matthias"
source: "Space space_01HZ... initial prompt"
supersedes: []            # list of spec_ids, e.g. ["03"]
schema_version: 1
---
```

### 3.2 Body

Pure prose, free-form, with two required sections:

```markdown
# {title}

## Intent
{one paragraph — operator's original goal, preserved verbatim across all mutations}

...

## Source
{required: where the PRD input came from — file path, GitHub issue URL, or "Input provided by <user> via Space <id>"}
```

The `Intent` section is special: even the operator only edits it during spec creation. Once the spec moves to `status: active`, Intent is frozen.

All other body sections are operator-discretion: Goals, Non-goals, Background, Open Questions, etc. Free-form prose. No machine reads them. They exist for human reviewers.

### 3.3 Why not JSON-ify the PRD too

Because the PRD is narrative, and narrative resists schemas. The structured stuff that did try to live in the PRD (dependencies, design decisions, source) moves to: tasks.json (dependencies), requirements.json (everything design-decision-like), and frontmatter (source).

---

## 4. `requirements.json`

The biggest of the four files and the most heavily mutated by the Coordinator.

### 4.1 Top-level shape

```json
{
  "$schema": "https://agent-fox.dev/schemas/requirements.v1.json",
  "spec_id": "05",
  "spec_name": "spec_driven_spaces",
  "schema_version": 1,
  "introduction": "Brief description of the system being specified.",
  "glossary": {
    "Space": "An isolated, resumable container for one unit of agent work.",
    "LivingSpec": "The four-artifact spec package viewed through a mutation contract."
  },
  "requirements": [ ... ],
  "correctness_properties": [ ... ],
  "execution_paths": [ ... ],
  "error_handling": [ ... ]
}
```

### 4.2 Requirements (EARS, decomposed)

Each requirement carries a user story and a list of acceptance criteria. Each acceptance criterion is a **discriminated union** keyed on `ears_pattern`. The rendered EARS sentence is computed; the source of truth is the structured fields.

```json
{
  "id": "05-REQ-1",
  "title": "Space lifecycle",
  "user_story": {
    "role": "operator",
    "goal": "create isolated workspaces for each task",
    "benefit": "agents don't trample each other's work"
  },
  "acceptance_criteria": [
    {
      "id": "05-REQ-1.1",
      "ears_pattern": "event_driven",
      "trigger": "an operator invokes `space new`",
      "system": "the system",
      "action": "create a Space with a unique ID, a worktree, a SQLite store, and a LivingSpec",
      "return_contract": null
    },
    {
      "id": "05-REQ-1.2",
      "ears_pattern": "unwanted",
      "condition": "the target repo has uncommitted changes on the source branch",
      "system": "the system",
      "action": "reject Space creation and report the dirty files",
      "return_contract": "list of dirty file paths"
    }
  ],
  "edge_cases": [
    {
      "id": "05-REQ-1.E1",
      "ears_pattern": "unwanted",
      "condition": "the worktree creation fails partway",
      "system": "the system",
      "action": "roll back any partial state and report the failure",
      "return_contract": null
    }
  ]
}
```

#### EARS pattern → required fields

| `ears_pattern` | Required fields | Rendered template |
|---|---|---|
| `ubiquitous` | `system`, `action` | `THE {system} SHALL {action}` |
| `event_driven` | `trigger`, `system`, `action` | `WHEN {trigger}, THE {system} SHALL {action}` |
| `complex_event` | `trigger`, `condition`, `system`, `action` | `WHEN {trigger} AND {condition}, THE {system} SHALL {action}` |
| `state_driven` | `state`, `system`, `action` | `WHILE {state}, THE {system} SHALL {action}` |
| `unwanted` | `condition`, `system`, `action` | `IF {condition}, THEN THE {system} SHALL {action}` |
| `optional` | `feature`, `system`, `action` | `WHERE {feature}, THE {system} SHALL {action}` |

Schema validation enforces the field set per pattern via `oneOf` discriminated on `ears_pattern`.

`return_contract` is always optional. When non-null, it declares what the system gives back to the caller — the key signal that this requirement participates in a multi-step pipeline and must be wired correctly.

### 4.3 Correctness properties

Formal invariants. These were the most valuable part of design.md; they live here now.

```json
{
  "id": "05-PROP-1",
  "title": "Spec mutation is auditable",
  "for_any": "spec mutation event",
  "invariant": "the ledger contains a corresponding entry committed in the same transaction",
  "validates": ["05-REQ-1.1", "05-REQ-2.3"]
}
```

`validates` is a required, non-empty array of acceptance criterion IDs. The schema rejects properties that don't validate at least one requirement.

### 4.4 Execution paths

Integration-level requirements. Express the shape of how the system must be wired, abstracted from specific module/function names.

```json
{
  "id": "05-PATH-1",
  "title": "Operator creates a Space and dispatches the first task",
  "steps": [
    { "actor": "operator",       "action": "invoke `space new <prompt>`" },
    { "actor": "SpaceManager",   "action": "allocate worktree, store, and ledger" },
    { "actor": "Coordinator",    "action": "draft requirements.json from the prompt" },
    { "actor": "operator",       "action": "invoke `space run`" },
    { "actor": "Coordinator",    "action": "dispatch the first task to an archetype" },
    { "actor": "Implementor",    "action": "produce changes; commit; report completion" }
  ]
}
```

Actors are **logical components**, not module names. The mapping from actor to actual code is a wiring-verification concern at implementation time, not a spec-level commitment.

Every execution path **must** have a corresponding smoke test in `test_spec.json`.

### 4.5 Error handling

A table of error condition → behavior, cross-referencing requirement IDs. Eliminates duplication between requirements and design.

```json
{
  "condition": "Config file missing",
  "behavior": "Use defaults",
  "requirement_id": "05-REQ-2.E1"
}
```

Cross-file validation enforces that every `requirement_id` referenced here exists in `requirements`.

---

## 5. `test_spec.json`

Derived from `requirements.json`. The Coordinator generates and patches it; operators don't edit it directly. Schema validation enforces complete coverage.

### 5.1 Top-level shape

```json
{
  "$schema": "https://agent-fox.dev/schemas/test_spec.v1.json",
  "spec_id": "05",
  "schema_version": 1,
  "test_cases": [ ... ],
  "property_tests": [ ... ],
  "edge_case_tests": [ ... ],
  "smoke_tests": [ ... ],
  "coverage": { ... }
}
```

### 5.2 Test cases

One per acceptance criterion. The library enforces this via cross-file validation.

```json
{
  "id": "TS-05-1",
  "requirement_id": "05-REQ-1.1",
  "kind": "unit",
  "description": "Space creation produces all four artifacts",
  "preconditions": ["clean git working tree", "no existing Space with the same slug"],
  "input": { "prompt": "test" },
  "expected": {
    "space_id_format": "ULID",
    "worktree_exists": true,
    "store_exists": true,
    "ledger_exists": true
  },
  "assertion_pseudocode": "result = space_manager.create('test'); assert ULID.matches(result.id); assert exists(result.worktree)"
}
```

### 5.3 Property tests

One per correctness property. `for_any_strategy` describes how the property test generator should sample inputs.

```json
{
  "id": "TS-05-P1",
  "property_id": "05-PROP-1",
  "validates": ["05-REQ-1.1"],
  "for_any_strategy": "valid spec_mutation_event sampled from event_strategies.mutation",
  "invariant_check": "ledger.has_entry(mutation.tx_id) is true"
}
```

### 5.4 Edge case tests

Mirror structure of test_cases. One per `*.E*` ID.

### 5.5 Smoke tests

One per execution path. Names which components must NOT be mocked.

```json
{
  "id": "TS-05-SMOKE-1",
  "execution_path_id": "05-PATH-1",
  "description": "End-to-end Space creation through first task dispatch",
  "trigger": "agent-fox space new 'test' && agent-fox space run",
  "real_components": ["SpaceManager", "WorktreeManager", "Coordinator", "LedgerWriter"],
  "mockable": ["filesystem (transient)", "remote git (push only)"],
  "expected_effects": [
    "worktree directory exists with initialized git",
    "ledger contains a `space.created` event",
    "store.sqlite contains the Space row",
    "requirements.json exists with at least one requirement"
  ]
}
```

### 5.6 Coverage block

**Computed, not authored.** The library populates this on every save. Schema validation rejects a `test_spec.json` whose coverage doesn't include every ID from `requirements.json`.

```json
"coverage": {
  "requirements_covered": ["05-REQ-1.1", "05-REQ-1.2", "05-REQ-1.E1"],
  "properties_covered": ["05-PROP-1"],
  "paths_covered": ["05-PATH-1"],
  "gaps": []
}
```

`gaps` is non-empty only during in-flight Coordinator work; on save it must be empty or the file is rejected.

---

## 6. `tasks.json`

The most actively-mutated file. State changes happen constantly.

### 6.1 Top-level shape

```json
{
  "$schema": "https://agent-fox.dev/schemas/tasks.v1.json",
  "spec_id": "05",
  "schema_version": 1,
  "test_commands": {
    "spec_tests": "pytest -q tests/spec/test_05.py",
    "all_tests": "pytest -q",
    "linter": "ruff check"
  },
  "dependencies": [ ... ],
  "task_groups": [ ... ],
  "traceability": [ ... ]
}
```

### 6.2 Task groups

```json
{
  "id": 1,
  "title": "Write failing spec tests",
  "subtasks": [
    {
      "id": "1.1",
      "title": "Set up test file structure",
      "details": ["Create test files per module in test_spec.json", "Use project conventions"],
      "test_spec_refs": ["TS-05-1", "TS-05-2"],
      "requirement_refs": [],
      "state": "pending",
      "optional": false
    }
  ],
  "verification": {
    "id": "1.V",
    "checks": [
      "All spec tests exist and are syntactically valid",
      "All spec tests FAIL (red) — no implementation yet"
    ]
  }
}
```

#### Subtask state machine

| State | Meaning | Allowed transitions |
|---|---|---|
| `pending` | Not started | → `queued`, `dropped` |
| `queued` | Selected for dispatch | → `in_progress`, `pending`, `dropped` |
| `in_progress` | An archetype is executing it | → `done`, `pending_reevaluation` |
| `done` | Verification passed | → `pending_reevaluation` (only if upstream requirement changes) |
| `pending_reevaluation` | A referenced requirement was modified; needs Coordinator review | → `pending`, `dropped` |
| `dropped` | Removed from plan with explicit rationale | terminal |

The library enforces transitions on every patch. Illegal transitions are rejected.

Note: **runtime metadata (current run ID, started_at, agent assignment) does not live here.** That belongs in the Space's operational store. `tasks.json` is declarative planning state, not runtime state.

### 6.3 Dependencies

Cross-spec dependencies at task-group granularity. Maps to the af-spec convention (from_group / to_group) but in structured form.

```json
{
  "depends_on_spec": "01_agent_fox",
  "from_group": 3,
  "to_group": 1,
  "relationship": "Imports CLI registration from group 3 (earliest group where CLI entry point is defined)",
  "sentinel": false
}
```

`sentinel: true` with `from_group: 0` means the upstream spec doesn't have `tasks.json` yet (concurrent development). The library exposes this for downstream planner resolution.

### 6.4 Traceability

```json
{
  "requirement_id": "05-REQ-1.1",
  "test_spec_id": "TS-05-1",
  "task_id": "2.3",
  "test_path": "tests/spec/test_05.py::test_space_creation"
}
```

`test_path` is the only field allowed to refer to an actual file in the source tree. Populated when the test exists.

---

## 7. Mutation contract

### 7.1 JSON Patch as the primitive

Every mutation to a JSON artifact is expressed as an RFC 6902 JSON Patch. Operations are validated against the file's JSON Schema before being applied. The applied patch is recorded as a ledger event.

```json
{
  "ledger_event_id": "01HZ...",
  "kind": "spec.mutated",
  "file": "requirements.json",
  "actor": "coordinator",
  "ts": "2026-05-18T12:34:56Z",
  "patch": [
    { "op": "add", "path": "/requirements/-", "value": { "id": "05-REQ-3", "..." } },
    { "op": "replace", "path": "/requirements/0/acceptance_criteria/0/action", "value": "..." }
  ],
  "schema_version_before": 1,
  "schema_version_after": 1,
  "validation_result": "ok"
}
```

### 7.2 Per-actor permissions

| File | Operator may patch | Coordinator may patch | Archetype may patch |
|---|---|---|---|
| `prd.md` frontmatter (except `status`) | ✓ | ✗ | ✗ |
| `prd.md` body Intent section | ✓ (pre-active only) | ✗ | ✗ |
| `prd.md` body other sections | ✓ | ✗ | ✗ |
| `requirements.json` | ✓ | ✓ | ✗ |
| `test_spec.json` | ✗ | ✓ | ✗ |
| `tasks.json` planning fields | ✓ | ✓ | ✗ |
| `tasks.json` subtask `state` only | ✗ | ✓ | ✓ (only own assignment) |

Archetypes are deliberately narrow: they can flip their own task's state through the legal transitions, nothing else. Everything else routes through the Coordinator.

### 7.3 Cross-file integrity

After every patch, the library re-runs cross-file integrity checks:

1. Every `requirement_id` referenced in `test_spec.json`, `tasks.json` traceability, and `error_handling` exists in `requirements.json`.
2. Every requirement and edge case in `requirements.json` is covered by `test_spec.json` (coverage block matches).
3. Every property in `correctness_properties` is referenced by a `property_test` in `test_spec.json`.
4. Every execution path is referenced by a `smoke_test`.
5. Every `test_spec_id` referenced in `tasks.json` exists in `test_spec.json`.
6. Glossary cross-check: every non-common term in any requirement/property action field has a glossary entry.

A patch that breaks integrity is rejected. The Coordinator either fixes the dependent files in the same patch batch or doesn't make the change.

### 7.4 Multi-file patches

A single mutation event can patch multiple files atomically (e.g., add a requirement → add test cases → add tasks). The library exposes a transaction wrapper:

```python
with spec.mutation(actor="coordinator", reason="add token rotation requirement") as txn:
    txn.patch("requirements.json", [...])
    txn.patch("test_spec.json", [...])
    txn.patch("tasks.json", [...])
# commits all three or none; one ledger event with three patches
```

---

## 8. Rendering

The library provides a renderer that produces markdown from the JSON artifacts. Three rendering targets:

1. **Per-file view** (`spec view requirements`) — markdown rendering of one JSON file, suitable for terminal or PR comment.
2. **Combined view** (`spec view`) — all four artifacts rendered into a single markdown document, ordered prd → requirements → test_spec → tasks. This is the PR-review artifact.
3. **Diff view** (`spec diff <ledger_event_id>`) — markdown rendering of a single patch event, showing before/after.

EARS sentences are rendered from the decomposed fields using the templates in §4.2. Render output is **stable**: same JSON in, same markdown out, byte-for-byte. This makes rendered output diffable and reviewable in PRs even though it's a derived form.

The library exposes:

```python
spec = Spec.load("specs/05_spec_driven_spaces/")
spec.render(format="markdown", target="combined")       # full combined view
spec.render(format="markdown", target="requirements")   # one file
spec.diff(ledger_event_id="01HZ...", format="markdown") # patch view
```

---

## 9. Validation

Two layers of validation, both run on every mutation:

**Schema validation** (JSON Schema, per file): runs in sub-millisecond. Rejects malformed structure, unknown fields, missing required fields, EARS pattern field mismatches, illegal state transitions.

**Cross-file integrity** (custom, library-implemented): runs after schema validation succeeds. Enforces the rules in §7.3.

If either layer fails, the patch is rejected and no ledger event is recorded. The Coordinator receives a structured error response listing each violation by JSON path.

The library exposes `spec.validate()` as a standalone check (no mutation) for CI and pre-commit hooks.

---

## 10. Lifecycle and numbering

Numbering follows the af-spec convention unchanged: `NN_snake_case_name` folders under the project's spec root. The `NN` prefix is monotonic; collisions are flagged at creation.

### 10.1 Lifecycle states

Stored in `prd.md` frontmatter `status` field. Only the library/skill can transition the state (not free-form edits).

| State | Meaning | Mutations allowed |
|---|---|---|
| `draft` | Being authored, not yet executing | all (incl. Intent edits) |
| `active` | Work in progress | all except Intent + frontmatter (except `status`, `updated_at`) |
| `sealed` | Harvested; no further mutation | none |
| `superseded` | Replaced by another spec | none (banner added to all files) |
| `archived` | Moved to `archive/` | none |

### 10.2 Superseding

Preserved from af-spec. The new spec's `prd.md` frontmatter sets `supersedes: ["03"]`. The library auto-applies the deprecation banner and moves the superseded folder into `archive/`.

---

## 11. What this retires

This document replaces §5.2 of the Spec-Driven Spaces epic PRD (the "LivingSpec is one Markdown file" schema). The Space concept (§5.1) survives; it now contains a four-artifact spec package in its worktree instead of a single `spec.md`.

The af-spec skill is retired in favor of:
- A **library** (`agent-fox-spec` or similar) that owns the schemas, JSON Patch primitive, validation, rendering, and lifecycle.
- A **skill** (successor to af-spec) that uses the library to author new specs from PRDs and to mutate existing specs on behalf of the Coordinator.

---

## 12. Open items

1. **Schema versioning policy.** `schema_version: 1` is in every file. Need a migration story for schema_version bumps. Default proposal: library ships migrators per version; `spec migrate` is an explicit command, never automatic.
2. **Where do execution path actors come from?** Free-form strings (proposed) vs. a controlled vocabulary registered per-project (`actors.yaml` in steering). Free-form is permissive but invites drift.
3. **Renderer for `prd.md` body.** Markdown in, markdown out is trivial. But for the combined view we may want to normalize section ordering. Worth a small style guide.
4. **`gaps` field handling.** Proposed: must be empty on save. Alternative: allowed to be non-empty during in-flight Coordinator work, with a separate `spec status` command reporting them. The second is more honest about the iterative process.
5. **Linting test_paths.** When a `traceability` entry has a `test_path`, should the library verify the path resolves to an actual test on disk? Cheap to add; couples spec validation to the source tree (which is fine inside a Space worktree, less so during initial authoring).
6. **Per-file vs. combined schema.** Four schemas (one per file) vs. one root schema with `$defs`. Per-file is simpler; combined catches cross-file refs at JSON Schema level (with `$ref` across files). Decide before implementation.

---

## 13. What the library/skill needs to provide

Out of scope for this document, but worth listing so the next deliverable knows its surface:

- `Spec.create()` — bootstrap a new spec from a PRD prompt or file
- `Spec.load()` — load an existing spec from disk
- `Spec.mutation()` — transactional patch context
- `Spec.validate()` — full schema + integrity check
- `Spec.render()` — markdown output
- `Spec.diff()` — patch-event rendering
- `Spec.seal()` / `Spec.supersede()` / `Spec.archive()` — lifecycle transitions
- CLI surface that wraps the above for skill use
- Ledger writer interface (the spec library *emits* events; the Space's ledger *records* them — two separate concerns)
