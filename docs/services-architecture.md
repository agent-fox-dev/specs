# Services Architecture

**Version:** 1.0
**Status:** Draft

This document specifies the deployable components of an af installation:
the hub, CLI, runtime engine, MCP bridge, and memory service. It covers
how they communicate, how state is persisted, and how the system starts,
stops, and recovers.

The coordination layer (domain model, spec package, agents, orchestration)
is specified in [coordination-layer.md](coordination-layer.md). The runtime
layer (containers, worktrees, adapters, agent lifecycle) is specified in
[runtime-layer.md](runtime-layer.md).

---

## 1. Design principles

1. **Local-first.** The default deployment is everything on one machine: one
   hub process, one SQLite database, containers on local Podman. No
   network services, no cloud dependencies, no accounts.

2. **Single stateful process.** The hub owns all mutable state. The CLI,
   the MCP bridge, and the runtime engine are stateless or ephemeral. This
   makes reasoning about consistency simple: one writer, many readers.

3. **Process boundaries follow trust boundaries.** The hub runs on the
   host with full access. The MCP bridge runs inside the agent container
   with scoped identity. The harness (Claude Code, etc.) runs inside the
   container with no direct access to harness state.

4. **Pluggable where the coordination layer says pluggable.** Memory, issue
   tracker, web search, and the container runtime are behind interfaces.
   Everything else is built-in.

---

## 2. The af hub

### 2.1 Responsibilities

The hub is the coordination service. It owns:

- **Spec store.** Persists spec artifacts on the filesystem. Serves reads to
  the MCP bridge and the CLI. Accepts writes (JSON Patch) from the CLI during
  `draft`. Enforces the freeze on `active` specs.
- **Context store.** Persists Context metadata, source descriptors,
  instructions, and revisions. Serves Context reads to the MCP bridge.
  Accepts Context edits from the CLI (Operator actions).
- **Operational store.** Persists workspace state, campaigns, runs, agents,
  subtask execution, verification outcomes, file claims, messages, and the
  activity log.
- **Spec lifecycle.** Enforces the state machine (`draft → active → sealed /
  superseded`), intent hashing, and the freeze contract.
- **Run management.** Creates and tracks runs (spec-driven and Ralph).
  Manages the Coordinator pattern: delegates subtasks, monitors state,
  triggers verification, applies bounce-backs.
- **Prompt assembly.** Composes the system prompt for each agent from the
  specialist role, Context sources, spec slice, recalled memory, and actor
  constraints (see [coordination-layer.md §6.3](coordination-layer.md#63-prompt-assembly)).
- **Agent memory.** Drives the memory service through `recall` (at prompt
  assembly and behind the MCP tool) and `consolidate` (at session end).
  See [coordination-layer.md §6.6](coordination-layer.md#66-the-agent-memory-contract).
- **File claims.** Manages the advisory lease table. Enforces atomic
  acquisition and expiry.
- **Activity log.** Receives events from the MCP bridge, the runtime engine,
  and internal operations. Appends to the operational store.
- **Coordination API.** Serves the Operator-facing API (see
  [coordination-layer.md §10.1](coordination-layer.md#101-operator-facing-api))
  over a local socket or TCP.
- **MCP bridge API.** Serves the agent-facing API over gRPC, accepting
  connections from MCP bridge instances inside agent containers.

### 2.2 Process model

The hub is a single long-running process. It starts when the Operator
invokes `af hub start` (or automatically on the first CLI command that
needs it) and runs until explicitly stopped or until the machine shuts down.

It listens on two interfaces:

- **CLI socket.** A Unix domain socket (default `<data_dir>/hub.sock`) for
  CLI-to-hub communication. HTTP/JSON over the socket. Local only; no
  network exposure.
- **Bridge port.** A TCP port (default `localhost:7400`) for MCP bridge
  connections from agent containers. gRPC with per-agent identity tokens
  for authentication. Bound to localhost by default; bindable to a network
  interface for remote container runtimes.

### 2.3 Startup and shutdown

**Startup:**
1. Resolve the data directory: `AF_DATA_DIR` env var, then `data_dir` in
   `~/.af/settings.yaml`, then the default `~/.local/share/af/`. Create it
   if it does not exist.
2. Open or create the SQLite database (`<data_dir>/af.db`).
3. Run schema migrations if needed.
4. Verify the spec store directory exists (`<data_dir>/specs/`).
5. Start listening on the CLI socket and bridge port.
6. Recover in-flight runs: re-evaluate workspace and agent state against the
   runtime engine. Agents that were running when the hub last stopped are
   detected via the container runtime (containers may still be alive) and
   their state is reconciled.

**Shutdown:**
1. Stop accepting new CLI and bridge connections.
2. For each active run: commit partial work, transition in-flight subtasks
   to a recoverable state, log a `hub_shutdown` activity event.
3. Close the database.
4. Exit.

Agents in containers are not stopped on hub shutdown by default — they
continue running and reconnect to the bridge when the hub restarts. The
Operator can choose to stop all agents before stopping the hub.

### 2.4 Crash recovery

The hub is the single writer to the operational store. SQLite's WAL mode
ensures the database is consistent after a crash. On restart, the hub:

1. Opens the database (SQLite recovers the WAL automatically).
2. Scans for runs marked `running` in the operational store.
3. Queries the container runtime for the actual state of each agent.
4. Reconciles: agents still running reconnect through the bridge; agents
   that exited while the hub was down are transitioned to `stopped` or
   `error` based on exit code.
5. File claims held by dead agents are expired.

No data is lost. The activity log may have a gap (events that occurred
between hub crash and restart are lost if the bridge couldn't reach the
hub), but the operational store state is consistent.

---

## 3. The af CLI

### 3.1 Responsibilities

The CLI is the Operator's interface. It is stateless: every command talks
to the hub, which owns all state. The CLI never reads or writes the
database directly.

### 3.2 Command structure

Commands mirror the Operator-facing API (see
[coordination-layer.md §10.1](coordination-layer.md#101-operator-facing-api)):

```
af workspace create [--origin <path|url>] [--context <id>...] [--campaign <id>]
af workspace list [--status <status>] [--campaign <id>]
af workspace get <id>
af workspace archive <id>
af workspace reopen <id>
af workspace delete <id>

af spec create <workspace-id>
af spec author <workspace-id> <spec-id> --patch <file>
af spec approve <workspace-id> <spec-id>
af spec seal <workspace-id> <spec-id>
af spec supersede <workspace-id> <spec-id> --new-spec <new-id>
af spec show <workspace-id> <spec-id> [--artifact <name>] [--rendered]
af spec validate <workspace-id> <spec-id>
af spec coverage <workspace-id> <spec-id>

af context create --name <name> --instruction <text>
af context list
af context get <id>
af context source add <context-id> --type <type> --locator <loc>
af context source remove <context-id> <source-id>
af context attach <workspace-id> <context-id> [--pin-mode <pinned|live>]
af context detach <workspace-id> <context-id>

af run start <workspace-id> <spec-id>
af run start-ralph <workspace-id> --goal <text> --verifier <command>
af run list <workspace-id>
af run get <run-id>
af run stop <run-id>

af agent list <workspace-id>
af agent get <agent-id>
af agent stop <agent-id>
af agent logs <agent-id> [--follow]
af agent message <agent-id> <text>

af campaign create --goal <file>
af campaign register <campaign-id> <workspace-id> [--depends-on <spec:group>...]
af campaign status <campaign-id>
af campaign abandon <campaign-id>

af activity <workspace-id> [--run <id>] [--agent <id>] [--type <type>...] [--follow]

af hub start [--foreground]
af hub stop
af hub status
```

### 3.3 PRD authoring

The CLI supports PRD authoring through two modes:

- **Direct edit.** `af spec author` applies a JSON Patch to a spec
  artifact, validated by the hub. For PRD text, the patch replaces the
  body content.
- **Editor integration.** `af spec edit <workspace-id> <spec-id>
  --artifact prd` opens the artifact in `$EDITOR`. On save, the CLI diffs
  against the stored version, constructs a patch, and submits it to the
  hub for validation.

Agent-assisted PRD authoring (see
[coordination-layer.md §8.1](coordination-layer.md#81-the-generic-spec-driven-flow),
phase 3) works by starting a temporary agent with a drafting template,
feeding it the Operator's brief and attached Contexts, and writing the
agent's output through the normal authoring API.

---

## 4. The runtime engine

The runtime engine (specified in [runtime-layer.md](runtime-layer.md)) runs
as a library embedded in the hub, not as a separate process. The hub
calls it to create containers, start agents, manage worktrees, and
orchestrate sidecars.

This means the hub process is the only thing the Operator needs to start.
The container runtime (Podman) must be available on the host, but
the Operator interacts with it only through the af CLI, never directly.

### 4.1 Runtime lifecycle within the hub

- On hub startup: the runtime engine initializes, connects to the
  container backend, and inventories existing containers.
- On workspace create: the runtime creates the worktree.
- On run start: the runtime provisions and starts agent containers with
  templates, MCP bridge sidecars, and mounted worktrees.
- On agent stop/suspend: the runtime stops or suspends the container.
- On workspace delete: the runtime removes containers and optionally the
  worktree and branch.

---

## 5. The af MCP bridge

Specified in [runtime-layer.md §8](runtime-layer.md#8-the-af-mcp-bridge).
One instance per running agent, inside the agent's container.

### 5.1 Hub connection

The bridge connects to the hub's bridge port (`localhost:7400` by default)
on startup. The connection parameters are injected via environment variables:

```
AF_HUB_HOST=host.containers.internal
AF_HUB_PORT=7400
AF_AGENT_TOKEN=<jwt>
AF_WORKSPACE_ID=<uuid>
AF_AGENT_ID=<uuid>
AF_RUN_ID=<uuid>
```

The agent token is a short-lived JWT issued by the hub at container
creation, encoding the agent's identity (workspace, agent, run, specialist
role). The hub validates it on every bridge request and scopes the
response accordingly.

### 5.2 Reconnection

If the hub restarts while an agent is running, the bridge retries
connection with exponential backoff. While disconnected, the harness can
still work (editing files, running commands) but harness-specific tool calls
(spec read, Context search, etc.) return errors. The bridge logs a
`bridge_disconnected` event locally and replays it to the hub on
reconnect.

### 5.3 Health reporting

The bridge reports agent activity to the hub via a periodic heartbeat
(default every 30 seconds). The heartbeat includes the agent's current
activity (working, thinking, waiting, etc.) derived from the harness's
observable behavior (output activity, tool calls). The hub uses
heartbeats for stall detection: an agent whose heartbeat arrives but whose
activity hasn't changed for a configurable duration (default 5 minutes) is
flagged as stalled.

---

## 6. The memory service

### 6.1 Embedded mode (default)

The memory service runs in-process within the hub. Learnings are stored
in the SQLite database alongside the operational store (in a separate set of
tables). Recall uses a simple keyword and embedding-based similarity search
over stored learnings.

This is sufficient for single-user, single-machine use. No external
dependencies.

### 6.2 External mode

The hub connects to an external memory service over gRPC, using the
`AgentMemory` interface (see
[coordination-layer.md §6.6](coordination-layer.md#66-the-agent-memory-contract)).
The external service owns storage, retrieval, and distillation. The hub
passes through `recall` and `consolidate` calls.

This mode is for deployments that want shared memory across machines, more
sophisticated retrieval (vector search, re-ranking), or integration with an
existing knowledge base.

### 6.3 Configuration

```yaml
# ~/.af/settings.yaml
memory:
  backend: embedded            # embedded | external
  # For external mode:
  # endpoint: localhost:7401
  # auth: token
```

---

## 7. Storage layout

Configuration and data are stored in separate directory trees.

- **Config directory** (`~/.af/`) — global configuration only. Contains
  `settings.yaml` and nothing else that changes at runtime.
- **Data directory** (`<data_dir>`) — all runtime artifacts: the SQLite
  database, spec store, templates, and the hub socket. Resolved in order:
  `AF_DATA_DIR` env var → `data_dir` key in `~/.af/settings.yaml` →
  default `~/.local/share/af/`.

### 7.1 Filesystem layout

```
~/.af/                             # Config directory (global configuration)
  settings.yaml                    # Global configuration

<data_dir>/                        # Data directory (default: ~/.local/share/af/)
  hub.sock                         # CLI-to-hub Unix socket
  af.db                            # SQLite database (operational + Context stores)
  specs/                           # Spec store
    <workspace-id>/
      <spec-id>/
        prd.md
        requirements.json
        test_spec.json
        tasks.json
        architecture.md            # optional
      archive/                     # superseded and archived specs
        <spec-id>/
          ...
  templates/                       # Global templates
    planner/
    coordinator/
    implementor/
    verifier/
    ralph/
  # Worktrees live near the repo, not here — see runtime-layer.md §3.2
  # Location: <repo-parent>/.af_worktrees/<workspace-id>/
```

### 7.2 Database schema (SQLite)

The operational store tables map directly to the entities in
[coordination-layer.md §9.3](coordination-layer.md#93-operational-store):

- `workspaces` — id, name, status, owner, origin, branch, worktree_path,
  base_branch, remote, campaign_id, created_at, updated_at
- `workspace_configs` — workspace_id, setup_scripts (JSON), default_provider,
  default_model
- `campaigns` — id, name, status, goal_document, shared_context_ids (JSON),
  created_at, updated_at
- `campaign_members` — campaign_id, workspace_id, spec_id, dependency_edges
  (JSON)
- `spec_refs` — workspace_id, spec_id, spec_name, status, intent_hash,
  schema_version, supersedes, created_at, updated_at
- `context_attachments` — workspace_id, context_id, pinned_revision,
  pin_mode, attached_at
- `runs` — id, workspace_id, spec_id, kind, status, circuit_breaker_state
  (JSON), started_at, ended_at
- `agents` — id, workspace_id, run_id, specialist_role, actor_capability,
  provider, model, phase, activity, parent_agent_id, started_at, ended_at
- `subtask_executions` — workspace_id, spec_id, subtask_id, run_id,
  assigned_agent_id, state, drop_rationale, started_at, completed_at
- `verification_outcomes` — workspace_id, spec_id, run_id, group_id,
  verification_subtask_id, check_id, result, detail, recorded_at
- `file_claims` — workspace_id, file_path, holder_agent_id, run_id,
  acquired_at, lease_expiry, state
- `managed_scripts` — workspace_id, agent_id, run_id, command, pid, status,
  started_at, stopped_at
- `messages` — id, agent_id, role, content, parent_message_id, created_at
- `activity_events` — id, workspace_id, run_id, agent_id, type, payload
  (JSON), created_at

Context store tables:

- `contexts` — id, name, owner_principal, access_policy (JSON), instruction,
  current_revision, created_at, updated_at
- `sources` — id, context_id, type, locator, resolution_strategy,
  freshness_contract, revision

Memory tables (embedded mode only):

- `memory_pins` — workspace_id, run_id, principal, namespace,
  pinned_revision, recorded_at
- `learnings` — id, principal, namespace, content, provenance, kind,
  revision, confidence, recorded_at
- `learning_embeddings` — learning_id, embedding (blob)

### 7.3 Backup and portability

Harness state is split between the config directory (`~/.af/`) and the data
directory (`<data_dir>`). Backup requires copying both:
`cp -r ~/.af/ <backup>/config && cp -r <data_dir> <backup>/data`. Moving
to a new machine is the same copy plus re-creating worktrees (which are
tied to the local git repo path) and setting `data_dir` in the new
machine's `~/.af/settings.yaml`.

---

## 8. Communication protocols

### 8.1 CLI ↔ Hub

HTTP/JSON over Unix domain socket. The CLI sends requests; the hub
responds. For streaming operations (activity follow, agent logs), the hub
uses server-sent events (SSE) over the same connection.

The socket path is `<data_dir>/hub.sock` by default, overridable via
`AF_HUB_SOCK` or `--hub-sock`.

### 8.2 MCP bridge ↔ Hub

gRPC over TCP. The bridge is the client; the hub is the server. Each RPC
includes the agent token in metadata for authentication and scoping.

Services:

```protobuf
service AfBridge {
  // Spec access
  rpc ReadSpec(ReadSpecRequest) returns (ReadSpecResponse);
  rpc RenderSpec(RenderSpecRequest) returns (RenderSpecResponse);
  rpc GetTraceability(TraceabilityRequest) returns (TraceabilityResponse);

  // Context access
  rpc SearchContext(SearchContextRequest) returns (SearchContextResponse);
  rpc GetSource(GetSourceRequest) returns (GetSourceResponse);

  // Memory
  rpc RecallMemory(RecallMemoryRequest) returns (RecallMemoryResponse);

  // Subtask state
  rpc TransitionSubtask(TransitionRequest) returns (TransitionResponse);

  // File claims
  rpc ClaimFile(ClaimRequest) returns (ClaimResponse);
  rpc ReleaseClaim(ReleaseRequest) returns (ReleaseResponse);

  // Activity logging
  rpc LogEvent(LogEventRequest) returns (LogEventResponse);

  // CI/CD status
  rpc ListCIRuns(ListCIRunsRequest) returns (ListCIRunsResponse);
  rpc GetCIRun(GetCIRunRequest) returns (GetCIRunResponse);
  rpc GetCIJobLog(GetCIJobLogRequest) returns (GetCIJobLogResponse);

  // Issue tracker
  rpc SearchIssues(SearchIssuesRequest) returns (SearchIssuesResponse);
  rpc GetIssue(GetIssueRequest) returns (GetIssueResponse);
  rpc CreateIssue(CreateIssueRequest) returns (CreateIssueResponse);
  rpc CommentIssue(CommentIssueRequest) returns (CommentIssueResponse);
  rpc UpdateIssue(UpdateIssueRequest) returns (UpdateIssueResponse);

  // Web search
  rpc WebSearch(WebSearchRequest) returns (WebSearchResponse);
  rpc WebFetch(WebFetchRequest) returns (WebFetchResponse);

  // Heartbeat
  rpc Heartbeat(HeartbeatRequest) returns (HeartbeatResponse);
}
```

### 8.3 Hub ↔ Runtime engine

In-process function calls. The runtime engine is a Go library (or equivalent)
linked into the hub binary. No IPC.

### 8.4 Hub ↔ Memory service (external mode)

gRPC over TCP. The hub is the client; the memory service is the server.
Uses the `AgentMemory` interface from
[coordination-layer.md §6.6](coordination-layer.md#66-the-agent-memory-contract),
translated to protobuf.

---

## 9. Security and isolation

### 9.1 Agent identity

Each agent receives a short-lived JWT at container creation. The token
encodes:

- `workspace_id` — scopes all data access
- `agent_id` — identifies the agent
- `run_id` — scopes the run
- `role` — the specialist role (used for actor capability checks)
- `exp` — expiry (refreshed via bridge heartbeat)

The hub validates the token on every bridge request. An Implementor
cannot read another workspace's spec. An Archetype cannot transition another
agent's subtask. The token is the enforcement mechanism for the actor
capability model (see
[coordination-layer.md §6.4](coordination-layer.md#64-specialists-actor-capabilities-and-instruction-precedence))
at the bridge boundary.

### 9.2 Container isolation

Detailed in [runtime-layer.md](runtime-layer.md). The key guarantee: an
agent container sees only its mounted worktree, its agent home directory,
and the MCP bridge socket. It cannot see the af database, other agents'
homes, or the spec store on the host filesystem.

### 9.3 Hub access

The CLI socket is file-permission-protected (owner-only). The bridge port
is localhost-only by default. No authentication is needed for the CLI socket
(the Operator has host access); the bridge port uses agent tokens.

---

## 10. Deployment modes

### 10.1 Local (default)

Everything on one machine. Podman for containers. SQLite for
storage. Embedded memory service. The Operator runs `af hub start` and
uses the CLI.

### 10.2 Future: remote hub

The hub runs on a remote machine (a beefy server, a cloud VM). The CLI
connects over TCP instead of a Unix socket. The bridge port is exposed on the
network with TLS. Agent containers run on the same remote machine. This
requires adding TLS and Operator authentication to the hub — the gRPC and
HTTP interfaces already support it structurally.

### 10.3 Future: distributed

Multiple machines each running a hub instance, coordinated by a central
registry (analogous to Scion's Hub). Out of scope for this document.

---

## 11. Context retrieval engine

### 11.1 Purpose

The coordination layer defines two resolution strategies for Context sources
(see [coordination-layer.md §5.9](coordination-layer.md#59-grounding-the-context)):
`pinned` (full content in the prompt every turn) and `retrieved` (indexed,
only relevant chunks pulled in per turn). Pinned sources work for small
documents but cannot scale to a full repository or a large document set.
The retrieval engine makes `retrieved` sources practical.

### 11.2 Interface

The hub calls the retrieval engine when an agent invokes the Context
search tool and the target source has resolution strategy `retrieved`.

```
interface RetrievalEngine {
  // Index a source. Called when a Context revision is cut or when a live
  // source's origin changes. The engine reads the content, chunks it,
  // computes embeddings, and stores the index.
  index(input: {
    contextId: string
    sourceId: string
    revision: string
    content: ContentStream       // the source content, streamed
    contentType: string          // e.g. "repository", "file", "blob"
  }): Promise<void>

  // Search a source. Returns the chunks most relevant to the query,
  // ranked by similarity.
  search(input: {
    contextId: string
    sourceId: string
    revision: string             // must match the pinned revision
    query: string
    maxResults?: number          // default 10
    maxTokens?: number           // budget for total returned content
  }): Promise<RetrievalResult[]>

  // Remove an index. Called when a source is removed from a Context
  // or when a revision is superseded and no workspace pins it.
  remove(input: {
    contextId: string
    sourceId: string
    revision: string
  }): Promise<void>
}

type RetrievalResult = {
  chunk: string                  // the retrieved text
  path?: string                  // file path within a repository source
  score: number                  // similarity score, 0-1
  startLine?: number             // position in the source, if applicable
  endLine?: number
}
```

### 11.3 Deployment

**Embedded (default).** The engine runs in-process within the hub.
Embeddings are computed using a local model (e.g. a small ONNX embedding
model shipped with the hub). The index is stored in SQLite (using a
vector extension) or in a local file-based index (e.g. HNSW). No external
dependencies.

**External.** The hub connects to a standalone retrieval service over
gRPC, using the same interface. This mode supports GPU-accelerated
embeddings, larger indices, and shared retrieval across multiple hub
instances.

### 11.4 Indexing lifecycle

- When a Context revision is cut: the hub calls `index()` for each
  `retrieved` source in the revision.
- When a workspace attaches a Context: the hub verifies the pinned
  revision is indexed. If not (e.g. the engine was added after the
  revision was cut), it triggers indexing.
- When a `live` source re-resolves: the hub calls `index()` with the
  new content, then `remove()` for the old revision once no workspace
  pins it.
- When a source is removed from a Context: `remove()` on all revisions.

### 11.5 Storage

Embedded mode adds to the hub's storage:

- `retrieval_indices` — context_id, source_id, revision, status
  (indexing/ready/failed), chunk_count, indexed_at
- `retrieval_chunks` — index_id, chunk_text, path, start_line, end_line,
  embedding (blob)

The embedding dimension is fixed per installation (determined by the
embedding model). A vector similarity index (exact or approximate) is
maintained over the embeddings for search.

---

## 12. CI/CD bridge

### 12.1 Purpose

The harness reads CI status and drives PRs but does not run pipelines itself.
The CI/CD bridge is the read-only adapter that lets agents query pipeline
status so the Verifier can confirm CI passed as part of the wiring
verification gate (see
[coordination-layer.md §7.5](coordination-layer.md#75-verification-gate))
and the PR Shepherd can wait for green CI before marking a PR merge-ready.

### 12.2 Interface

Defined in the coordination layer (see
[coordination-layer.md §6.5](coordination-layer.md#65-tools-available-to-agents)).
The `CIProvider` interface is pluggable, the same pattern as `IssueTracker`
and `WebSearch`.

### 12.3 Adapters

**GitHub Actions adapter.** Uses the GitHub REST API
(`GET /repos/{owner}/{repo}/actions/runs`, `GET .../jobs`,
`GET .../jobs/{id}/logs`). Authenticates with the workspace's configured
GitHub token (the same token used by the Git tool for PR operations).

**GitLab CI adapter.** Uses the GitLab REST API
(`GET /projects/{id}/pipelines`, `GET .../jobs`, `GET .../jobs/{id}/trace`).
Authenticates with a GitLab access token.

Adding a new CI provider means implementing the `CIProvider` interface.

### 12.4 Configuration

```yaml
# Per-workspace or global
ci:
  provider: github              # github | gitlab
  # Provider-specific settings are inherited from the Git tool's
  # configuration (remote URL, auth token). No separate config needed
  # for the common case where CI runs on the same platform as the repo.
```

### 12.5 Agent access

The CI/CD bridge is exposed to agents through the af MCP bridge as the
`af_ci_status` tool. Queries and results are logged as activity events.
The tool is read-only — agents cannot trigger pipelines or modify CI
configuration.

---

## 13. Notification service

### 13.1 Purpose

The Operator is not always watching the terminal. The notification service
alerts the Operator when events of interest occur, so they can step in at
the right moments (approve a drafted spec, review a completed run, handle a
circuit breaker).

### 13.2 Interface

The notification service subscribes to the hub's activity event stream
and matches events against a set of triggers. When a trigger fires, it
delivers a notification through one or more configured channels.

```
interface NotificationService {
  addChannel(channel: NotificationChannel): void
  setTriggers(triggers: NotificationTrigger[]): void
}

interface NotificationChannel {
  name: string
  deliver(notification: Notification): Promise<void>
}

type NotificationTrigger = {
  event: string                 // activity event type or pattern
  filter?: {
    workspaceId?: string
    runId?: string
    campaignId?: string
  }
  priority: "info" | "action_required"
}

type Notification = {
  title: string
  body: string
  priority: "info" | "action_required"
  source: {
    workspaceId: string
    runId?: string
    agentId?: string
  }
  timestamp: string
  actionUrl?: string            // deep link to the CLI command or dashboard
}
```

### 13.3 Built-in channels

**Desktop notification.** Uses the OS notification system (macOS
Notification Center, Linux `notify-send`). Zero configuration for local
deployments.

**Webhook.** HTTP POST to a configured URL with the notification payload as
JSON. The building block for integrations — Slack incoming webhooks, Discord
webhooks, PagerDuty, or a custom endpoint.

**Log.** Writes notifications to a file or stdout. Useful for headless
servers or CI environments where no interactive notification is possible.

### 13.4 Default triggers

| Trigger | Priority | When |
| --- | --- | --- |
| `spec_ready_for_review` | action_required | A Planner has drafted a spec ready for Operator approval. |
| `run_complete` | info | A spec-driven run completed successfully. |
| `run_failed` | action_required | A run stopped due to error or unrecoverable failure. |
| `ralph_complete` | info | A Ralph loop exited cleanly (verifier passed). |
| `ralph_stopped` | action_required | A Ralph loop hit a circuit breaker. |
| `campaign_workspace_unblocked` | action_required | A Campaign dependency gate cleared. |
| `verification_failed` | info | A verification gate failed; the Coordinator will re-delegate. |
| `agent_stalled` | info | An agent has been stalled beyond the configured threshold. |

The Operator can add, remove, or modify triggers through configuration.

### 13.5 Deployment

The notification service runs inside the hub process as an event
subscriber — not a separate service.

### 13.6 Configuration

```yaml
# ~/.af/settings.yaml
notifications:
  channels:
    - type: desktop
    - type: webhook
      url: https://hooks.slack.com/services/T.../B.../xxx
  triggers:
    # Override or extend the defaults
    - event: run_complete
      priority: action_required   # escalate from info to action_required
    - event: agent_stalled
      filter:
        workspaceId: "abc-123"
      priority: action_required
```

---

## 14. Web dashboard

### 14.1 Purpose

A read-only web frontend for observing system state without the CLI. Shows
what's happening across workspaces, runs, agents, and Campaigns at a glance.
The Operator uses it alongside the CLI, not instead of it — all write
operations remain CLI-driven.

### 14.2 Architecture

The dashboard is a static single-page application (SPA) served by the hub
over its HTTP interface. It consumes the same Operator-facing API and
observability API that the CLI uses. No additional backend logic.

```
Browser ──► Hub HTTP ──► Same API endpoints as CLI
                     └──► SSE streams for live updates
```

### 14.3 Views

| View | Content |
| --- | --- |
| **Home** | Active workspaces with status, current run, agent count. Campaigns as collapsible groups with dependency graphs. |
| **Workspace detail** | State, attached Contexts, spec lifecycle, git status, file listing. |
| **Spec viewer** | Rendered combined view. Coverage and traceability tables. Diff against previous spec. |
| **Run timeline** | Gantt-style view: phases, agent lifetimes, subtask transitions, verification outcomes. |
| **Activity stream** | Filterable, scrollable event log with live SSE updates. |
| **Agent detail** | State, conversation history, tool call log, assigned subtask. |
| **Campaign graph** | Dependency graph across specs. Node color by status. |

### 14.4 Live updates

The dashboard subscribes to the hub's SSE activity stream for real-time
updates. Workspace status changes, subtask transitions, verification
outcomes, and agent state changes appear without polling.

### 14.5 Deployment

The hub serves the dashboard's static assets from a built-in directory.
No separate web server. Available at
`http://localhost:<hub-http-port>/` when the hub is running.

### 14.6 Scope boundary

The dashboard is read-only. It does not provide forms for creating
workspaces, authoring specs, or starting runs. If write support is added
later, it routes through the same API.

---

## 15. Deferred

One component remains architecturally anticipated but not specified:

- **Remote hub.** Running the hub on a remote machine with TLS,
  Operator authentication, and multi-tenant isolation. The gRPC and HTTP
  interfaces already support remote access structurally; what's missing is
  the auth layer and tenant separation.
