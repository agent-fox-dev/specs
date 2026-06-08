# Runtime Layer Specification

**Status:** Draft
**Parent:** Agentic Harness Core PRD v1.0, section 14

This document specifies the runtime layer that sits underneath the Telos
coordination layer. It covers container isolation, git worktree management,
harness adapters, agent lifecycle, templates, sidecar services, and the Telos
MCP bridge. The design follows patterns established by Google's Scion project,
adapted to our requirements.

---

## 1. Design principles

1. **Thin and focused.** The runtime handles infrastructure; it has no opinion
   on specs, Contexts, coordination, or verification. It starts containers,
   manages worktrees, and exposes agent lifecycle operations.

2. **Provider-agnostic.** Claude Code, Gemini CLI, Codex, and OpenCode are
   interchangeable through one harness adapter interface. Adding a new
   provider means implementing one adapter.

3. **Container-first isolation.** Each agent runs in its own OCI container.
   The worktree is mounted in; everything else (spec store, Telos
   configuration, sibling agents) is invisible. This is stronger than
   process-level or worktree-level isolation alone.

4. **The coordination layer drives.** The runtime exposes a narrow API. The
   coordination layer calls it to start/stop agents, provision worktrees, and
   inject configuration. The runtime never calls back into the coordination
   layer — the Telos MCP bridge handles that direction (section 8).

5. **Portable across container runtimes.** Podman (rootless) is the default.
   Kubernetes is supported through the same container runtime interface.
   Other OCI-compatible runtimes can be added by implementing the interface.

---

## 2. Container runtime interface

The runtime abstracts the container backend behind one interface. Every
operation the coordination layer needs goes through it.

```
interface ContainerRuntime {
  create(spec: ContainerSpec): Promise<ContainerId>
  start(id: ContainerId): Promise<void>
  stop(id: ContainerId, timeout: Duration): Promise<void>
  remove(id: ContainerId): Promise<void>
  exec(id: ContainerId, command: string[]): Promise<ExecResult>
  logs(id: ContainerId, follow: boolean): AsyncStream<string>
  inspect(id: ContainerId): Promise<ContainerState>
}

type ContainerSpec = {
  image: string
  name: string
  mounts: Mount[]             // worktree, agent home, sidecar sockets
  env: Record<string, string>
  command: string[]
  services: ServiceSpec[]     // sidecar processes
  resources?: ResourceLimits  // CPU, memory caps
}

type Mount = {
  source: string              // host path
  target: string              // container path
  readonly: boolean
}

type ContainerState = {
  id: ContainerId
  status: "created" | "running" | "stopped" | "error"
  exitCode: number | null
  startedAt: string | null
  stoppedAt: string | null
}
```

### 2.1 Podman adapter

The default. Uses the Podman socket API to create, start, stop, and remove
containers. Rootless by default — agents run without root privileges on the
host, which limits the blast radius of a container escape. Mounts are bind
mounts. The agent's worktree is mounted at `/workspace`. The agent's home
directory is mounted at a configurable path (default `/home/agent`). Shadow
mounts (tmpfs) prevent access to `.telos` configuration and sibling
worktrees.

### 2.2 Kubernetes adapter

Runs agents as Pods. Each agent is a Pod with the harness as the main
container and sidecars (including the Telos MCP bridge) as additional
containers. Worktree provisioning uses init containers or CSI volumes. This
adapter is out of scope for the initial implementation but the interface is
designed to accommodate it.

---

## 3. Git worktree management

The runtime manages per-workspace git worktrees. This is the mechanism behind
section 5.2 of the PRD.

```
interface WorktreeManager {
  create(input: {
    repoPath: string          // path to the main repo
    branch: string            // e.g. "telos/add-dark-mode"
    baseBranch: string        // e.g. "main"
  }): Promise<WorktreeInfo>

  remove(worktreePath: string, deleteBranch: boolean): Promise<void>

  list(repoPath: string): Promise<WorktreeInfo[]>
}

type WorktreeInfo = {
  path: string                // absolute path to the worktree directory
  branch: string
  baseBranch: string
  head: string                // current commit SHA
}
```

### 3.1 Branch naming

Branches follow the convention `telos/<workspace-name>`, e.g.
`telos/add-dark-mode`. The prefix is configurable per installation. Collisions
are rejected at creation.

### 3.2 Worktree location

Worktrees are created outside the main repo's working directory to avoid
polluting it: `<repo-parent>/.telos_worktrees/<workspace-id>/`. Each
worktree is a full working directory checked out to its branch.

### 3.3 Lifecycle

- **Create:** `git worktree add` from the base branch. The worktree is
  empty of untracked files (no env files, secrets, or installed
  dependencies carry over from the main checkout).
- **Remove:** `git worktree remove` plus optional `git branch -d`. The
  coordination layer decides when to remove (section 5.7 of the PRD);
  the runtime executes it.

---

## 4. Harness adapters

A harness adapter integrates one provider into the runtime. It handles
everything provider-specific so the coordination layer sees a uniform
interface.

```
interface HarnessAdapter {
  name(): string

  // Build the container command to launch the harness.
  // `resume` indicates whether to continue a prior session.
  getCommand(input: {
    task: string
    resume: boolean
    baseArgs: string[]
  }): string[]

  // Return harness-specific environment variables.
  getEnv(input: {
    agentName: string
    agentHome: string
  }): Record<string, string>

  // Perform harness-specific setup in the agent's home directory
  // after templates are copied. Called once at agent creation.
  provision(input: {
    agentName: string
    agentHome: string        // host path to agent home dir
    workspacePath: string    // host path to worktree
  }): Promise<void>

  // Inject system prompt content into the harness's expected location.
  injectSystemPrompt(agentHome: string, content: string): Promise<void>

  // Inject agent instructions (rules, conventions) into the harness's
  // expected location.
  injectInstructions(agentHome: string, content: string): Promise<void>

  // Translate universal MCP server configs into the harness's native
  // MCP configuration format.
  applyMCPServers(
    agentHome: string,
    servers: Record<string, MCPServerConfig>
  ): Promise<void>

  // Resolve authentication: select the best auth method and return
  // the env vars and file mounts needed to inject credentials.
  resolveAuth(auth: AuthConfig): Promise<ResolvedAuth>

  // Whether this harness supports session suspend/resume.
  supportsResume(): boolean

  // The key sequence to interrupt the harness process (e.g. "Ctrl-C").
  interruptKey(): string
}
```

### 4.1 Claude Code adapter

- **Command:** `claude --dangerously-skip-permissions` (or with a
  permissions file). `--continue` on resume.
- **System prompt:** Written to `CLAUDE.md` in the agent home or workspace
  root.
- **MCP servers:** Written to `.claude.json` or `.claude/settings.json`.
- **Auth:** API key via `ANTHROPIC_API_KEY` env var, or Vertex AI / AWS
  Bedrock credentials.
- **Resume:** Supported. `--continue` flag resumes the last session.

### 4.2 Gemini CLI adapter

- **Command:** `gemini` with task as argument. `--resume` on resume.
- **System prompt:** Written to `.gemini/system_prompt.md`.
- **MCP servers:** Written to `.gemini/settings.json`.
- **Auth:** Google Cloud credentials via `GOOGLE_APPLICATION_CREDENTIALS` or
  `GEMINI_API_KEY`.
- **Resume:** Supported. `--resume` flag continues the session.

### 4.3 Codex adapter

- **Command:** `codex` with task as argument.
- **System prompt:** Written to `AGENTS.md` or provider-specific location.
- **MCP servers:** Provider-specific configuration.
- **Auth:** `OPENAI_API_KEY` env var.
- **Resume:** Not supported; starts fresh.

### 4.4 OpenCode adapter

- **Command:** `opencode` with task as argument.
- **System prompt:** Written to provider-specific location.
- **MCP servers:** Written to `opencode.json`.
- **Auth:** Provider-specific API key env var.
- **Resume:** Not supported; starts fresh.

### 4.5 Adding a new adapter

Implement the `HarnessAdapter` interface. Register it in the adapter
registry. No changes to the coordination layer or the container runtime.

---

## 5. Agent lifecycle

The runtime manages agent lifecycle through a state model and a set of
operations the coordination layer calls.

### 5.1 Agent state

Two dimensions, following the Scion pattern:

**Phase** — the container lifecycle:

| Phase | Meaning | Transitions |
| --- | --- | --- |
| `created` | Container spec built, not yet started. | → `provisioning` |
| `provisioning` | Harness adapter running `provision()`, template hydration. | → `starting`, → `error` |
| `starting` | Container starting, harness initializing. | → `running`, → `error` |
| `running` | Harness active, agent working. | → `stopping`, → `suspended`, → `error` |
| `stopping` | Graceful shutdown in progress (SIGTERM sent). | → `stopped` |
| `stopped` | Container exited cleanly. Session ended. | → `provisioning` (fresh start) |
| `suspended` | Container torn down with intent to resume. | → `starting` (resume) |
| `error` | Container exited with non-zero code or setup failed. | → `provisioning` (retry) |

**Activity** — what the agent is doing within the `running` phase:

| Activity | Meaning |
| --- | --- |
| `working` | Agent actively editing, running tools. |
| `thinking` | Agent reasoning (model inference in progress). |
| `waiting_for_input` | Agent waiting for human or Coordinator input. |
| `completed` | Agent finished its task (sticky until restart/stop). |
| `idle` | Agent running but not currently active. |

The coordination layer maps these to its own concepts: a `running` agent
with activity `completed` triggers the Coordinator to check subtask state.
A `stopped` or `error` phase triggers error handling in the run.

### 5.2 Lifecycle operations

```
interface AgentLifecycle {
  // Create an agent: build container spec, provision harness, copy
  // template, inject system prompt and MCP config. Does not start.
  create(input: {
    name: string
    workspace: WorkspaceRef
    template: TemplateRef
    systemPrompt: string
    instructions: string
    mcpServers: Record<string, MCPServerConfig>
    env: Record<string, string>
    services: ServiceSpec[]
  }): Promise<AgentRef>

  // Start a created or stopped agent. Fresh session.
  start(ref: AgentRef, task: string): Promise<void>

  // Resume a suspended agent. Continues the prior session.
  // Falls back to fresh start if the harness doesn't support resume.
  resume(ref: AgentRef, task?: string): Promise<void>

  // Graceful stop. Sends SIGTERM, waits for timeout, then SIGKILL.
  stop(ref: AgentRef, timeout?: Duration): Promise<void>

  // Suspend: stop with intent to resume.
  // Only for harnesses that support session resume.
  suspend(ref: AgentRef): Promise<void>

  // Remove agent: stop if running, delete container, optionally
  // delete home directory and worktree branch.
  delete(ref: AgentRef, cleanup?: { branch: boolean; home: boolean }): Promise<void>

  // Send a message to a running agent's input stream.
  message(ref: AgentRef, text: string): Promise<void>

  // Query current state.
  state(ref: AgentRef): Promise<{ phase: Phase; activity: Activity; detail?: string }>

  // Stream agent output.
  logs(ref: AgentRef, follow: boolean): AsyncStream<string>
}
```

### 5.3 Session management

Agents run inside a terminal multiplexer (tmux) within the container. This
gives:

- **Detached execution.** The agent runs in the background; the user or
  coordination layer attaches/detaches without interrupting work.
- **Session persistence.** On suspend, the tmux session's state (including
  the harness's conversation history, if the harness supports it) enables
  resume.
- **Input injection.** The `message` operation sends text into the tmux pane,
  which the harness reads as user input.

---

## 6. Templates

A template is a blueprint for agent configuration. The coordination layer's
specialists (section 8.4 of the PRD) map to templates: the specialist defines
the role semantically (actor capability, tool policy); the template defines
the configuration mechanically (system prompt file, env vars, MCP servers).

### 6.1 Template structure

```
templates/
  <template-name>/
    template.yaml           # metadata and configuration
    home/                   # files copied to the agent's home directory
      CLAUDE.md             # (or .gemini/system_prompt.md, etc.)
      ...
```

### 6.2 Template configuration

```yaml
name: implementor
harness: claude
description: "Implements a subtask against a frozen spec."

env:
  TELOS_ROLE: implementor

mcp_servers:
  telos:
    transport: stdio
    command: /usr/local/bin/telos-mcp-bridge
    args: ["--workspace", "${TELOS_WORKSPACE_ID}"]

services:
  - name: telos-bridge
    command: ["/usr/local/bin/telos-mcp-bridge", "--workspace", "${TELOS_WORKSPACE_ID}"]
    restart: always
    ready_check:
      type: tcp
      target: "localhost:7400"
      timeout: "10s"
```

### 6.3 Template resolution

Templates are resolved in order: project-level (`.telos/templates/`)
overrides global (`~/.telos/templates/`), which overrides built-in defaults.
The coordination layer can also pass inline configuration at agent creation
time, which overrides the template.

### 6.4 Built-in templates

The runtime ships default templates for each specialist role:

| Template | Harness | Role |
| --- | --- | --- |
| `planner` | configurable | Drafts spec artifacts during `draft`. |
| `coordinator` | configurable | Delegates subtasks, monitors execution. |
| `implementor` | configurable | Implements one subtask. |
| `verifier` | configurable | Runs verification checks. |
| `ralph` | configurable | Autonomous goal+verifier loop. |

Each template includes the Telos MCP bridge as a sidecar service and
pre-configures the MCP server declaration so the harness discovers it.
The harness itself (Claude Code, Gemini CLI, etc.) is configurable per
template.

---

## 7. Sidecar services

A sidecar service is a long-running process that runs alongside the harness
inside the agent's container. The runtime manages sidecar lifecycle: start
before the harness, health-check, restart on failure, stop on agent stop.

```
type ServiceSpec = {
  name: string
  command: string[]
  restart: "always" | "on-failure" | "never"
  env?: Record<string, string>
  readyCheck?: {
    type: "tcp" | "http" | "delay"
    target: string            // "localhost:7400", "http://localhost:8080/health", "3s"
    timeout: string           // max wait before giving up
  }
}
```

The harness does not start until all sidecar services with readiness checks
have reported ready. This ensures the Telos MCP bridge is available before
the agent begins working.

---

## 8. The Telos MCP bridge

The Telos MCP bridge is the key integration point between the runtime layer
and the coordination layer. It runs as a sidecar service inside each agent
container and exposes Telos-specific capabilities as MCP tools that the
harness (Claude Code, Gemini CLI, etc.) can call.

### 8.1 Why an MCP bridge

The runtime treats the harness as opaque — it does not intercept tool calls
or sit in the model's reasoning loop. But the coordination layer needs to
extend the agent's tool set with capabilities the harness doesn't natively
have (spec read, Context search, memory recall, subtask state transitions,
file claims). The MCP bridge resolves this: it's an MCP server the harness
connects to, indistinguishable from any other MCP tool. The coordination
layer's tools appear to the agent as standard MCP tools.

### 8.2 Tools exposed

| Tool | Description | Direction |
| --- | --- | --- |
| `telos_spec_read` | Fetch spec artifacts, rendered views, traceability, coverage. | Agent → Telos service |
| `telos_context_search` | Search retrieved sources in attached Contexts. | Agent → Telos service |
| `telos_context_get` | Fetch a pinned source from an attached Context. | Agent → Telos service |
| `telos_memory_recall` | Search agent memory for relevant learnings. | Agent → Telos service |
| `telos_subtask_state` | Transition the agent's own subtask state. | Agent → Telos service |
| `telos_file_claim` | Claim, renew, release an advisory file lease. | Agent → Telos service |
| `telos_ci_status` | Query CI pipeline runs, job results, and logs. | Agent → Telos service |

### 8.3 Architecture

```
┌─── Agent Container ─────────────────────────────────────┐
│                                                         │
│  ┌─────────────┐         ┌──────────────────────┐       │
│  │   Harness    │◄──MCP──►│  Telos MCP Bridge    │       │
│  │ (Claude Code │         │  (sidecar service)   │       │
│  │  Gemini CLI) │         └──────────┬───────────┘       │
│  └──────┬──────┘                     │                   │
│         │                            │ gRPC / HTTP       │
│    /workspace                        │                   │
│    (mounted worktree)                │                   │
└─────────────────────────────────────┼───────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │   Telos Coordination    │
                          │       Service           │
                          │                         │
                          │  Spec store             │
                          │  Context store          │
                          │  Operational store      │
                          │  Prompt assembly        │
                          │  Run management         │
                          └─────────────────────────┘
```

The bridge communicates with the Telos coordination service on the host via
gRPC or HTTP. The coordination service is the source of truth for spec
content, Context data, memory, subtask state, and file claims. The bridge
is stateless — it proxies requests and returns responses.

### 8.4 Authentication and scoping

Every bridge instance knows its agent's identity (workspace ID, agent ID,
run ID, specialist role) via environment variables injected at container
creation. The coordination service uses this identity to scope tool calls:
an Implementor's `telos_subtask_state` call can only transition its own
assigned subtask; a `telos_spec_read` call returns only the artifacts for
the agent's workspace.

### 8.5 Activity logging

The bridge logs every tool call and response as activity events, forwarded
to the coordination service. This is how Telos-level tool calls (spec reads,
Context searches, subtask transitions) enter the activity log even though
the runtime does not intercept the harness's native tool loop.

---

## 9. Agent provisioning flow

The full sequence from workspace creation to a running agent:

1. **Coordination layer** calls `WorktreeManager.create()` to provision the
   branch and worktree.

2. **Coordination layer** assembles the agent configuration: resolves the
   specialist to a template, composes the system prompt (section 8.3 of
   the PRD), gathers MCP server configs (including the Telos bridge), and
   collects environment variables (workspace ID, agent ID, run ID, etc.).

3. **Coordination layer** calls `AgentLifecycle.create()` with the assembled
   configuration.

4. **Runtime** resolves the template: copies home directory content, runs the
   harness adapter's `provision()` method, calls `injectSystemPrompt()` and
   `injectInstructions()`, calls `applyMCPServers()` to translate MCP
   configs into the harness's native format.

5. **Runtime** builds the `ContainerSpec`: image, mounts (worktree at
   `/workspace`, agent home, shadow mounts for isolation), env vars, sidecar
   services (including the Telos MCP bridge), and the harness command.

6. **Runtime** calls `ContainerRuntime.create()` and
   `ContainerRuntime.start()`.

7. **Runtime** starts sidecar services and waits for readiness checks.

8. **Runtime** starts the harness process inside the container with the task
   as input.

9. **Agent** begins working. The harness discovers the Telos MCP bridge as
   an available MCP server and can call its tools.

---

## 10. Container image

The runtime uses a base container image that includes:

- A shell and standard Unix tools.
- Git.
- A terminal multiplexer (tmux).
- The Telos MCP bridge binary.
- Common language runtimes and build tools (configurable per image variant).

The harness (Claude Code, Gemini CLI, etc.) is either pre-installed in the
image or installed during provisioning. Image variants per harness keep image
sizes manageable.

The image does not include the Telos coordination service, the spec store,
or any coordination logic. These run on the host and the bridge reaches them
over the network.

---

## 11. Configuration

### 11.1 Global configuration

```yaml
# ~/.telos/settings.yaml
runtime:
  backend: podman              # podman | kubernetes
  image: telos/agent:latest    # default base image

defaults:
  harness: claude
  template: implementor

worktrees:
  prefix: telos                # branch prefix: telos/<workspace-name>
  location: ../.telos_worktrees  # relative to repo root
```

### 11.2 Per-workspace overrides

```yaml
# Set via the coordination layer's workspace config (section 5.6 of PRD)
harness: gemini
template: implementor
image: telos/agent:gemini
env:
  CUSTOM_VAR: value
```

Global settings are the defaults. Per-workspace overrides take precedence.
Inline overrides at agent creation time take highest precedence.

---

## 12. Relationship to the Scion mapping

This runtime layer replaces the option of adopting Scion wholesale. The
mapping document (`docs/scion-runtime-mapping.md`) remains valid as a
reference for design decisions and as documentation of why we chose to build
our own thin runtime rather than depend on an external project.

Key decisions that diverge from "adopt Scion":

- **No Hub or Runtime Broker.** We build for local and single-machine use.
  Remote execution and multi-user collaboration remain non-goals (PRD
  section 3).
- **No agent-to-agent messaging.** Coordination is through the shared store,
  not inter-agent messages.
- **Thinner agent state model.** We adopt Scion's Phase × Activity pattern
  but with fewer states, since our coordination layer handles the
  higher-level orchestration state (runs, subtasks, verification).
- **Our own harness adapters.** We implement the same set of providers
  (Claude Code, Gemini CLI, Codex, OpenCode) but with adapters shaped to
  our needs, not forked from Scion's codebase.
- **The Telos MCP bridge.** Scion has no equivalent. This is our key
  architectural addition: the sidecar that connects the opaque harness to
  the coordination layer's tools and state.
