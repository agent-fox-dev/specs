# af-spec

The specification format used by [agent-fox](https://github.com/agent-fox-dev). Defines the on-disk structure for spec packages — the artifacts that capture design intent, acceptance criteria, verification contracts, and implementation plans for a feature.

## Spec format

A spec is a directory containing:

| File | Required | Purpose |
|---|---|---|
| `prd.md` | yes | Narrative intent — the "why" and "what" |
| `requirements.json` | yes | Acceptance criteria, correctness properties, execution paths |
| `test_spec.json` | yes | Verification contracts for each requirement |
| `tasks.json` | yes | Implementation plan with ordering and dependencies |
| `architecture.md` | no | Modules, interfaces, data models, technology choices |

The full specification lives in [`docs/spec-format.md`](docs/spec-format.md) (v1.1).

## What's in this repo

- **`docs/spec-format.md`** — the normative spec format specification
- **`examples/migration/`** — reference programs (Go and Python) that programmatically build a complete spec using [speclib-go](https://github.com/agent-fox-dev/speclib-go) and [speclib-python](https://github.com/agent-fox-dev/speclib-python), then compare outputs for parity

## Libraries

| Language | Repository |
|---|---|
| Go | [speclib-go](https://github.com/agent-fox-dev/speclib-go) |
| Python | [speclib-python](https://github.com/agent-fox-dev/speclib-python) |
