# af-spec

Specifications and architecture documents for [agent-fox](https://github.com/agent-fox-dev) and its sub-projects. This is the canonical home for design-level artifacts: product requirements, format specifications, and architecture decisions that govern how agent-fox components are built.

## Documents

| Document | Description |
|---|---|
| [Spec Format Specification v1.1](docs/spec-format_v1.1.md) | The on-disk structure for spec packages: the artifacts that capture design intent, acceptance criteria, verification contracts, and implementation plans for a feature. |
| [Agentic Harness Core PRD](docs/agentic-harness-core-v1.0.md) | Product requirements for the agentic harness core: workspaces, the spec package lifecycle, the Context grounding model, multi-agent orchestration, and the pluggable provider/memory/issue-tracker contracts. |
| [Runtime Layer](docs/runtime-layer.md) | Specification for the container runtime, harness adapters, agent lifecycle, templates, and the Telos MCP bridge that sits underneath the coordination layer. |
| [Scion Runtime Mapping](docs/scion-runtime-mapping.md) | Analysis of Google's Scion platform as a potential runtime layer: concept mapping, gaps, conflicts, and the rationale for building our own thin runtime instead. |
| [Legacy af-spec reference](docs/af-spec-legacy.md) | Reference material from the original af-spec skill. Retained for historical context. |

## Spec format quick reference

A spec is a directory containing:

| File | Required | Purpose |
|---|---|---|
| `prd.md` | yes | Narrative intent: the "why" and "what" |
| `requirements.json` | yes | Acceptance criteria, correctness properties, execution paths |
| `test_spec.json` | yes | Verification contracts for each requirement |
| `tasks.json` | yes | Implementation plan with ordering and dependencies |
| `architecture.md` | no | Modules, interfaces, data models, technology choices |

The full specification lives in [`docs/spec-format_v1.1.md`](docs/spec-format_v1.1.md).

## Examples

- **`examples/migration/`** — reference programs (Go and Python) that programmatically build a complete spec using [speclib-go](https://github.com/agent-fox-dev/speclib-go) and [speclib-python](https://github.com/agent-fox-dev/speclib-python), then compare outputs for parity

## Libraries

| Language | Repository |
|---|---|
| Go | [speclib-go](https://github.com/agent-fox-dev/speclib-go) |
| Python | [speclib-python](https://github.com/agent-fox-dev/speclib-python) |
