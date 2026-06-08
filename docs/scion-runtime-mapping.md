# Scion as Runtime Layer for the Agentic Harness Core

**Status:** Draft for discussion

**Purpose:** This document maps the Agentic Harness Core PRD (v1.0) onto
Google's Scion platform, evaluating whether Scion can serve as the runtime
layer underneath our coordination and grounding model. The goal is to identify
what Scion already provides, what must be built on top, and where the two
designs conflict.

**Scion reference:** https://googlecloudplatform.github.io/scion — an
experimental, Apache 2.0-licensed multi-agent orchestration testbed from
Google Cloud Platform. Primarily Go (86%), early but actively developed. Local
mode is stable; Hub-based workflows are usable; Kubernetes runtime has rough
edges.

---

## 1. Architectural fit

Scion solves the runtime problem: how to run, isolate, and lifecycle-manage
LLM agents against a codebase. Our PRD solves the coordination problem: how
agents plan, execute, and verify work against a validated contract. These are
complementary layers with a clean boundary.

```
┌─────────────────────────────────────────────────────────┐
│                   Telos (our harness)                   │
│                                                         │
│  Spec store · Context store · Operational store         │
│  Spec lifecycle · Planner · Coordinator · Verifier      │
│  Prompt assembly · Grounding · Agent memory             │
│  Activity log · Runs · Orchestration API                │
├─────────────────────────────────────────────────────────┤
│                   Scion (runtime)                       │
│                                                         │
│  Container isolation · Git worktrees · Agent lifecycle  │
│  Provider abstraction (harnesses) · Templates           │
│  Hub / Broker · Secrets · Observability (OTEL)          │
│  CLI · Plugin system                                    │
└─────────────────────────────────────────────────────────┘
```

Telos becomes a layer that creates and drives Scion agents rather than
managing containers, worktrees, and provider processes itself. Scion handles
the infrastructure; Telos handles the intent.

---

## 2. Concept mapping

| Telos concept | Scion equivalent | Mapping quality | Notes |
| --- | --- | --- | --- |
| **Workspace** | **Project** | Strong | Both are the isolation boundary for one unit of work. A Telos workspace maps 1:1 to a Scion project. Scion's project provides the `.scion` directory, agent namespace, and workspace identity. |
| **Worktree / Branch** | **Git Worktree** (local) / **Git Init+Fetch** (Hub) | Direct | Scion creates per-agent worktrees at `../.scion_worktrees/<project>/<agent>` with dedicated branches. Our `telos/<name>` branch convention maps directly. Hub mode uses clone-based provisioning instead. |
| **Agent** | **Agent** | Strong | Both are isolated LLM instances with identity, workspace access, and tools. Scion adds container-level isolation (OCI) on top of what we specified as worktree-level isolation. |
| **Provider** | **Harness** | Direct | Both abstract the underlying LLM tool (Claude Code, Gemini CLI, Codex, OpenCode). Scion's `Harness` interface (`Name()`, `GetCommand()`, `Provision()`, `GetEnv()`) is a superset of our `Provider.run()` — it includes provisioning and environment setup that we left to bootstrap scripts. |
| **Specialist / Template** | **Template** | Partial | Scion templates define system prompt, tools (including MCP servers), env vars, home directory content, and harness selection. Our specialists define role, tool policy, model tier, and actor capability. Templates are a good vehicle for specialist configuration, but actor capabilities and the spec-read tool have no Scion equivalent. |
| **Setup scripts** | **Agent provisioning + ServiceSpec** | Strong | Scion runs provisioning during agent creation (the `Provision()` method) and supports sidecar services (`ServiceSpec` with readiness checks). This subsumes our bootstrap scripts (section 5.4) and managed scripts (section 11). |
| **Agent state** | **Phase × Activity × Detail** | Scion is richer | Scion's three-dimensional state model (Phase for container lifecycle, Activity for cognitive state, Detail for context) is more granular than our `running/stopped/completed/failed`. We could adopt Scion's model and map our subtask state machine on top. |
| **MCP servers** | **MCPServerConfig** | Direct | Scion has a universal, harness-agnostic MCP server description (`MCPServerConfig`) with transport types (stdio, SSE, streamable-http) and scoping (global/project). Templates translate these into each harness's native format. This directly maps to our MCP capability sources inside a Context. |
| **Activity log** | **Observability (OTEL)** | Partial | Scion normalizes agent telemetry to OpenTelemetry. Our activity log is a structured, append-only event stream with specific event types (spec_patch, context_pin, verification_outcome, etc.). Scion's OTEL covers agent-level events but not our coordination-level events. We would emit our own events and could feed them into the same OTEL pipeline. |
| **Managed scripts** | **ServiceSpec** | Direct | Scion's `ServiceSpec` defines sidecar processes with restart policies and readiness checks. This is more structured than our ManagedScript entity and subsumes it. |
| **Per-workspace config** | **Profile + settings.yaml** | Strong | Scion's profiles bind runtime + harness + behavior flags. Our per-workspace config (provider, model, Contexts, setup scripts) maps to profile selection plus Telos-specific overrides. |
| **File read/write, exec** | **Container filesystem + tmux** | Direct | Scion runs agents in containers with mounted workspaces. File operations and exec happen inside the container, mediated by the harness. Our file-claim mechanism would need to be layered on top. |
| **Hub** | *(no equivalent)* | n/a | Scion's Hub provides hosting, auth, multi-user collaboration, and remote execution. Our PRD explicitly lists these as non-goals (section 3). The Hub is available if we ever need it, but we don't depend on it. |
| **Runtime Broker** | *(no equivalent)* | n/a | Same — remote execution capacity is Scion's concern, not ours. |

---

## 3. What Scion provides (no build needed)

These capabilities exist in Scion today and can be consumed directly:

1. **Container isolation.** Per-agent OCI containers with dedicated filesystems,
   env vars, credentials, and shadow mounts. Stronger isolation than our
   worktree-only model — an upgrade, not a compromise.

2. **Git worktree management.** Automatic creation, branch naming, mounting
   into containers. Handles the `Created → Active` workspace transition
   we described in section 5.3.

3. **Provider abstraction (harnesses).** Claude Code, Gemini CLI, Codex,
   OpenCode all supported through one interface. Provisioning, auth resolution,
   and telemetry integration included.

4. **Agent lifecycle.** Start, stop, suspend, resume, attach, message, delete.
   Scion's `suspend` (intent to resume with session continuation) is richer
   than what we specified.

5. **Templates.** System prompt injection, MCP server configuration, env vars,
   home directory content, harness selection. Custom templates for specialized
   roles.

6. **Sidecar services.** `ServiceSpec` with restart policies and readiness
   gates replaces our managed scripts with a more robust model.

7. **Secret management.** Per-agent credential scoping and injection.

8. **Observability.** Normalized OpenTelemetry across harnesses.

9. **CLI.** A complete command-line interface for all agent operations.

10. **Hub (optional).** Multi-machine orchestration, collaboration, web
    dashboard — available if we ever need hosted deployments.

11. **Agent-to-agent messaging.** `scion message` and the messages inbox
    provide a communication channel between agents and humans that we didn't
    model.

---

## 4. What must be built on top of Scion (the Telos layer)

These are our core contributions. Scion has no equivalent and no opinion
on them. They compose cleanly on top of the runtime.

### 4.1 Spec store and spec lifecycle

Scion has no concept of a validated spec package, no schema-enforced
artifacts, no freeze, no spec lifecycle. The entire spec layer (sections 7.1
through 7.11 of the PRD) must be built as a Telos service:

- The spec store (section 11.1).
- Schema validation and cross-artifact integrity (section 7.8).
- The repair pass (section 7.8).
- The spec lifecycle state machine: `draft → active → sealed / superseded`
  (section 7.6).
- The freeze contract (section 7.7).
- Intent hashing and protection.
- The spec-read tool exposed to agents (section 7.11).
- The deterministic renderer (section 7.9).

### 4.2 Context store and grounding model

Scion has contextual instructions (markdown files appended by environment)
and MCP server configuration in templates, but no first-class Context entity.
The Telos Context layer must be built:

- The Context store (section 11.2).
- Typed sources with resolution strategy (pinned/retrieved) and freshness
  contract (snapshot/live).
- Context revisions and pinning at run start.
- The Context search/get tool.
- Instruction composition and precedence (section 8.4).
- Access policies and per-principal filtering.

Scion's MCP server configuration (defined in templates, translated per
harness) can serve as the mechanism for our MCP capability sources. When
Telos attaches a Context that includes an MCP source, it translates that
source into a Scion `MCPServerConfig` and injects it into the agent's
template.

### 4.3 Prompt assembly

Scion injects system prompts and agent instructions into the harness
(`InjectAgentInstructions`, `InjectSystemPrompt`), but has no concept of
composing prompts from a spec slice, Context sources, recalled memory, and
actor-capability constraints. The full prompt assembly logic (section 8.3)
is Telos-owned:

- Rendering the spec slice relevant to the agent's current work.
- Materializing pinned Context sources.
- Composing the precedence order (harness policy → actor constraints →
  Context instructions → task instruction).
- Recalling agent memory.

Telos assembles the prompt and hands it to Scion as the agent's system
prompt and instructions. Scion's `InjectAgentInstructions` and
`InjectSystemPrompt` methods are the delivery mechanism.

### 4.4 Coordination: Planner, Coordinator, Verifier

Scion's philosophy is "less is more" — agents "dynamically learn a CLI tool,
letting the models themselves decide how to coordinate." This is the opposite
of our blackboard model. All coordination logic must be built:

- The Planner agent that drafts the spec during `draft`.
- The Coordinator agent that delegates subtasks and monitors execution state.
- The Verifier agent that runs group checks and wiring verification.
- The subtask state machine (section 7.4) and its enforcement.
- The verification gate (section 9.5).
- Actor capabilities and write authority (section 8.4).

Telos starts Scion agents with the right template and instructions, then
orchestrates them through the coordination protocol. Each Scion agent is a
Telos specialist; the coordination logic lives in Telos, not in the agent's
prompt.

### 4.5 Runs and the operational store

Scion tracks agent lifecycle (phase, activity, detail) but has no concept
of a Run as a unit of execution spanning multiple agents against a spec.
The operational store (section 11.3) must be built:

- Run entity (spec-driven or Ralph).
- SubtaskExecution with the state machine.
- VerificationOutcome.
- File claims (the advisory lease mechanism).
- The activity log with Telos-specific event types.

Scion's agent state feeds into this: Telos maps Scion phase/activity
transitions to its own activity events.

### 4.6 Agent memory

Scion has no memory contract. The recall/consolidate lifecycle (section 8.6)
and the pluggable memory service must be built entirely in Telos.

### 4.7 Campaigns

Scion has no multi-project dependency graph. The Campaign layer (section 6)
is entirely Telos-owned: goal documents, dependency edges, workspace gating,
cross-spec orchestration.

### 4.8 Ralph loop

Scion has no autonomous goal+verifier loop mode. The Ralph flow (section 8.7
and 10.4) must be built in Telos, using Scion agents as the execution
mechanism.

---

## 5. Conflicts and design tensions

### 5.1 Project vs. workspace granularity

**Tension:** Scion's Project maps to a git repository (UUID v5 derived from
the git URL). Our workspace is finer-grained — one workspace per task, many
workspaces per repo. A repo with five concurrent features has five workspaces
but would naturally be one Scion project.

**Resolution:** Use Scion's project-per-workspace model, creating a Scion
project for each Telos workspace. This means many Scion projects per
repository, each with its own `.scion` directory and agent namespace. Scion's
deterministic project ID (UUID v5 from git URL) won't work here since all
workspaces share a repo; we would use Scion's Hub-style random UUID v4 IDs
instead, or derive IDs from (git URL + workspace ID). The alternative —
multiple workspaces inside one Scion project — would break Scion's
per-project agent isolation and complicate worktree management.

### 5.2 Coordination philosophy

**Conflict:** Scion's design philosophy is "let models decide how to
coordinate." Our design philosophy is "coordination through a validated,
frozen contract." These are fundamentally at odds.

**Resolution:** This is not a runtime conflict — it's a layer-above decision.
Scion doesn't enforce its philosophy in code; it simply doesn't provide
coordination infrastructure. Telos adds that infrastructure on top. Scion
agents remain free to call tools and write code; Telos constrains *what they
coordinate against* and *what they may write in the spec*. The runtime
doesn't resist this.

### 5.3 Agent-to-agent communication

**Tension:** Scion provides `scion message` for inter-agent communication and
agents can spawn child agents with ancestry tracking. Our design explicitly
forbids agent-to-agent messaging — coordination happens through the shared
store (section 9.2), not through direct communication.

**Resolution:** Telos does not expose Scion's messaging to agents as a
coordination mechanism. Scion's message system can still serve the
Operator-to-agent channel (the human sending instructions to a running agent
via `scion message`), but agent-to-agent messages are not part of the Telos
coordination model. The ancestry-based access control is useful for our
Coordinator → Implementor relationship but the communication it enables
must be replaced by the blackboard.

### 5.4 Who owns the tool loop

**Tension:** In our PRD (section 8.1), "the harness owns the tool loop and
the workspace state. The provider owns the model call and which tool to call
next." In Scion, the harness (Claude Code, Gemini CLI) owns both the tool
loop and the model call — Scion manages the container but does not intercept
tool calls.

**Resolution:** This is the deepest architectural tension. Our PRD assumes
the harness can intercept every tool call, enforce file claims at the
file-write tool, inject spec-read and Context-search as tools, and log every
action to the activity log. Scion's model is opaque: the harness runs inside
a container and Scion observes it through heartbeats and OTEL, but does not
sit in the tool loop.

Two approaches:

- **Sidecar approach.** Run a Telos sidecar service inside the Scion
  container (using `ServiceSpec`) that exposes the spec-read tool,
  Context-search tool, memory-recall tool, and file-claim enforcement as an
  MCP server. The harness (Claude Code, Gemini CLI) connects to this MCP
  server and gains access to Telos capabilities as tools. File claims are
  enforced by proxying file writes through the MCP server or by a filesystem
  overlay. Activity logging captures tool calls through the MCP server's own
  logging.

- **Custom harness.** Build a Telos-specific harness (via Scion's plugin
  system) that wraps an underlying provider and interposes on the tool loop.
  This gives Telos full control over tool execution, file-claim enforcement,
  and activity logging, at the cost of reimplementing what Claude Code and
  Gemini CLI already do.

The sidecar approach is simpler and preserves the "bring your own agent"
property. The custom harness gives stronger guarantees. The choice may differ
per deployment.

### 5.5 Spec artifacts outside the worktree

**Tension:** Scion mounts the worktree as `/workspace` inside the container
and the harness operates on it. Our spec store lives outside the worktree
(section 7.11) and agents access specs through an API, not as files.

**Resolution:** This aligns well with the sidecar approach in 5.4. The spec
store is a Telos service running outside the container (or as a sidecar
inside it). Agents access it through the spec-read MCP tool. The spec
artifacts never appear in `/workspace`, which is exactly our design intent.

### 5.6 Container overhead

**Tension:** Scion runs each agent in its own OCI container. Our PRD assumed
agents could share a process or run as lightweight threads. Container
creation has overhead (hundreds of milliseconds to seconds), which matters
for short-lived workers in a parallel execution phase.

**Resolution:** For the coordinated-feature flow where a Coordinator
delegates multiple subtasks to parallel Implementors, container startup
latency is real but acceptable — each Implementor runs for minutes to hours,
so seconds of setup cost is amortized. For fine-grained delegation (many
short subtasks), container pooling or Scion's suspend/resume could help. This
is an operational tuning concern, not an architectural conflict.

### 5.7 Agent identity and the Operator

**Tension:** Scion scopes agent identity as `project--agent` and tracks
ancestry chains. Our model has a distinct Operator principal (human) who is
never an agent. Scion does not model a non-agent principal who owns the
project.

**Resolution:** The Operator maps to the Scion user who runs the CLI. Scion's
auth system already distinguishes the human user from agents. Telos adds the
Operator concept on top: the user who creates the workspace, authors the PRD,
approves the spec, and reviews the result. This is a Telos-layer concern that
doesn't conflict with Scion's identity model.

---

## 6. Integration architecture

### 6.1 How Telos drives Scion

Telos uses Scion's CLI or API to manage the runtime:

| Telos operation | Scion command/API |
| --- | --- |
| Create workspace | `scion project init` + configure profile |
| Bootstrap workspace | Agent provisioning (automatic on first `scion start`) |
| Start a specialist agent | `scion start <name> --type <template> --config <telos-config>` |
| Stop an agent | `scion stop <name>` |
| Suspend/resume | `scion suspend <name>` / `scion resume <name>` |
| Send task to agent | `scion message <name> <task>` or task in start command |
| Observe agent state | `scion list`, OTEL events, `scion logs` |
| Cleanup | `scion delete <name>`, `scion clean` |

### 6.2 Telos services exposed to agents

Via an MCP server running as a Scion sidecar service inside the container:

- **Spec read.** Fetch artifacts, rendered views, traceability, coverage.
- **Context search/get.** Search retrieved sources, fetch pinned sources.
- **Memory recall.** Search agent memory for relevant learnings.
- **Subtask state.** Transition the agent's own subtask state.
- **File claim.** Claim, renew, release advisory leases.

These tools appear to the harness (Claude Code, Gemini CLI) as MCP tools,
indistinguishable from any other MCP server. The Telos MCP server
communicates with the Telos coordination service running on the host.

### 6.3 What stays on the host

The Telos coordination service runs on the host (not inside agent containers)
and owns:

- The spec store, Context store, and operational store.
- The spec lifecycle state machine and freeze enforcement.
- Run management and the Coordinator pattern.
- Prompt assembly (composing the system prompt before agent start).
- Agent memory recall and consolidation.
- The activity log (receiving events from the MCP sidecar and from Scion's
  OTEL pipeline).
- The Operator-facing API (section 12.1).
- Campaign management.

---

## 7. Summary

| Dimension | Assessment |
| --- | --- |
| **Runtime layer** | Scion covers ~80% of what we need: container isolation, worktree management, provider abstraction, agent lifecycle, templates, MCP, secrets, observability, CLI. |
| **Coordination layer** | Must be built entirely: spec store, spec lifecycle, Context store, prompt assembly, Planner/Coordinator/Verifier, runs, subtask state, verification gates, Campaigns, Ralph, agent memory. |
| **Conflicts** | The tool-loop ownership question (5.4) is the deepest tension. The sidecar MCP approach resolves it pragmatically. Project-vs-workspace granularity (5.1) requires a convention. Everything else composes. |
| **Risk** | Scion is "early and experimental" and "not an officially supported Google product." Depending on it as a load-bearing runtime carries the risk of the project being abandoned or changing direction. The Apache 2.0 license and the fact that it's a Go library/CLI (not a hosted service) mitigate this — we could fork and maintain if needed. |
| **Benefit** | Google's engineering behind container management, provider abstraction, agent lifecycle, Hub infrastructure, and observability. We focus entirely on the coordination and grounding layers that are our differentiators. |
