# Migration Report: Audit Hub Spec → speclib

This report documents the results of programmatically importing the
`01_audit_hub` reference specification into the Go and Python speclib
libraries, and the gaps discovered during the process.

## Artifacts Produced

Both `main.go` and `main.py` produce four output files:

| File | Format | Source Artifact |
|------|--------|----------------|
| `prd.md` | Markdown with YAML frontmatter | `01_audit_hub/prd.md` |
| `requirements.json` | JSON | `01_audit_hub/requirements.md` |
| `test_spec.json` | JSON | `01_audit_hub/test_spec.md` |
| `tasks.json` | JSON | `01_audit_hub/tasks.md` |

## Expected Serialization Differences

The Go and Python outputs are semantically identical. The following
serialization-level differences are expected and harmless:

1. **`$schema: null`** — Python emits `"$schema": null` at the top level of
   JSON files. Go omits the field (`omitempty`). Both are valid.

2. **HTML entity escaping** — Go's `encoding/json` escapes `<`, `>`, and `&`
   as `<`, `>`, `&`. Python outputs them literally. Both are
   valid JSON.

3. **`input: null`** — Python emits `"input": null` for test cases and edge
   case tests. Go omits the field (`omitempty`). Both are valid.

4. **Timestamp precision** — Go includes sub-second precision in
   `updated_at` (e.g. `2026-05-21T10:19:40.64245Z`). Python truncates to
   seconds (e.g. `2026-05-21T10:19:46Z`). Both are valid ISO 8601.

## Content Not Representable in speclib

The speclib `Spec` type has no `Design` artifact. The reference specification
includes `design.md` with substantial content that is partially captured
through other speclib fields and partially lost.

### Captured via other fields

The following design.md sections map to speclib fields on the Requirements
object:

| design.md Section | speclib Field |
|-------------------|---------------|
| Correctness Properties (P1–P9) | `Requirements.CorrectnessProperties` |
| Execution Paths (PATH-1–PATH-5) | `Requirements.ExecutionPaths` |
| Error Handling Matrix | `Requirements.ErrorHandling` |

### Not representable

The following design.md sections have no corresponding speclib field:

- **Architecture overview** — high-level description of the system's
  layered architecture and request flow
- **Module responsibilities** — per-module purpose and public interface
  descriptions (`config`, `model`, `store`, `validator`, `middleware`,
  `handler`, `health`, `retention`, `server`)
- **Component interfaces** — function signatures, parameter types, return
  types, and behavioral contracts for each module
- **Data models** — SQLite schema (CREATE TABLE statement), TOML
  configuration structure, AuditEvent struct definition
- **Technology stack** — language, framework, database, and library choices
  with rationale
- **Operational readiness** — deployment model, Docker configuration,
  resource estimates, monitoring approach
- **Testing strategy** — test pyramid structure, tooling choices, coverage
  approach
- **Definition of done** — checklist for implementation completeness

### Traceability granularity

The original `tasks.md` traceability table has multi-value cells where one
requirement maps to multiple task_ids (e.g. `01-REQ-1.3` → tasks `5.3, 2.2`).
The speclib `TraceabilityEntry` type stores single values per field, and
enforces uniqueness on the `(requirement_id, test_spec_id)` pair.

This means that when the original maps one requirement to multiple task_ids
under the same test_spec_id, only one task_id can be stored. The first
task_id from the original table was chosen in these cases:

| Requirement | Original task_ids | Stored task_id |
|-------------|-------------------|----------------|
| 01-REQ-1.3 | 5.3, 2.2 | 5.3 |
| 01-REQ-1.4 | 5.3, 2.2 | 5.3 |
| 01-REQ-2.3 | 4.1, 5.1 | 4.1 |
| 01-REQ-7.1 | 6.1, 3.3 | 6.1 |
| 01-REQ-10.1 | 3.1, 3.2 | 3.1 |

When a requirement maps to multiple *test_spec_ids* (e.g. `01-REQ-3.3` →
`TS-01-6, TS-01-7` or `01-REQ-6.2` → `TS-01-13, TS-01-14`), separate
entries are created — this is fully supported.

### Task subtask details

The original `tasks.md` contains verbose detail text for each subtask
(multi-line descriptions with inline code references). Both scripts use
abbreviated details that capture the key points. The abbreviation is
consistent between Go and Python but does not reproduce the original
verbatim.
