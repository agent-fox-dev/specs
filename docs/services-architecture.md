# Services Architecture

**Status:** Draft
**Parent:** Agentic Harness Core PRD v1.0, section 15

This document specifies the deployable components of a Telos installation:
the daemon, CLI, runtime engine, MCP bridge, and memory service. It covers
how they communicate, how state is persisted, and how the system starts,
stops, and recovers.

---

## 1. Design principles

1. **Local-first.** The default deployment is everything on one machine: one
   daemon process, one SQLite database, containers on local Podman. No
   network services, no cloud dependencies, no accounts.

2. **Single stateful process.** The daemon owns all mutable state. The CLI,
   the MCP bridge, and the runtime engine are stateless or ephemeral. This
   makes reasoning about consistency simple: one writer, many readers.

3. **Process boundaries follow trust boundaries.** The daemon runs on the
   host with full access. The MCP bridge runs inside the agent container
   with scoped identity. The harness (Claude Code, etc.) runs inside the
   container with no direct access to Telos state.

4. **Pluggable where the PRD says pluggable.** Memory, issue tracker, web
   search, and the container runtime are behind interfaces. Everything else
   is built-in.

---

## 2. The Telos daemon

### 2.1 Responsibilities

The daemon is the coordination service. It owns:

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
  constraints.
- **Agent memory.** Drives the memory service through `recall` (at prompt
  assembly and behind the MCP tool) and `consolidate` (at session end).
- **File claims.** Manages the advisory lease table. Enforces atomic
  acquisition and expiry.
- **Activity log.** Receives events from the MCP bridge, the runtime engine,
  and internal operations. Appends to the operational store.
- **Coordination API.** Serves the Operator-facing API (section 12.1 of the
  PRD) over a local socket or TCP.
- **MCP bridge API.** Serves the agent-facing API over gRPC, accepting
  connections from MCP bridge instances inside agent containers.

### 2.2 Process model

The daemon is a single long-running process. It starts when the Operator
invokes `telos daemon start` (or automatically on the first CLI command that
needs it) and runs until explicitly stopped or until the machine shuts down.

It listens on two interfaces:

- **CLI socket.** A Unix domain socket (default `~/.telos/daemon.sock`) for
  CLI-to-daemon communication. HTTP/JSON over the socket. Local only; no
  network exposure.
- **Bridge port.** A TCP port (default `localhost:7400`) for MCP bridge
  connections from agent containers. gRPC with per-agent identity tokens
  for authentication. Bound to localhost by default; bindable to a network
  interface for remote container runtimes.

### 2.3 Startup and shutdown

**Startup:**
1. Open or create the SQLite database (`~/.telos/telos.db`).
2. Run schema migrations if needed.
3. Verify the spec store directory exists (`~/.telos/specs/`).
4. Start listening on the CLI socket and bridge port.
5. Recover in-flight runs: re-evaluate workspace and agent state against the
   runtime engine. Agents that were running when the daemon last stopped are
   detected via the container runtime (containers may still be alive) and
   their state is reconciled.

**Shutdown:**
1. Stop accepting new CLI and bridge connections.
2. For each active run: commit partial work, transition in-flight subtasks
   to a recoverable state, log a `daemon_shutdown` activity event.
3. Close the database.
4. Exit.

Agents in containers are not stopped on daemon shutdown by default — they
continue running and reconnect to the bridge when the daemon restarts. The
Operator can choose to stop all agents before stopping the daemon.

### 2.4 Crash recovery

The daemon is the single writer to the operational store. SQLite's WAL mode
ensures the database is consistent after a crash. On restart, the daemon:

1. Opens the database (SQLite recovers the WAL automatically).
2. Scans for runs marked `running` in the operational store.
3. Queries the container runtime for the actual state of each agent.
4. Reconciles: agents still running reconnect through the bridge; agents
   that exited while the daemon was down are transitioned to `stopped` or
   `error` based on exit code.
5. File claims held by dead agents are expired.

No data is lost. The activity log may have a gap (events that occurred
between daemon crash and restart are lost if the bridge couldn't reach the
daemon), but the operational store state is consistent.

---

## 3. The Telos CLI

### 3.1 Responsibilities

The CLI is the Operator's interface. It is stateless: every command talks
to the daemon, which owns all state. The CLI never reads or writes the
database directly.

### 3.2 Command structure

Commands mirror the Operator-facing API (section 12.1 of the PRD):

```
telos workspace create [--origin <path|url>] [--context <id>...] [--campaign <id>]
telos workspace list [--status <status>] [--campaign <id>]
telos workspace get <id>
telos workspace archive <id>
telos workspace reopen <id>
telos workspace delete <id>

telos spec create <workspace-id>
telos spec author <workspace-id> <spec-id> --patch <file>
telos spec approve <workspace-id> <spec-id>
telos spec seal <workspace-id> <spec-id>
telos spec supersede <workspace-id> <spec-id> --new-spec <new-id>
telos spec show <workspace-id> <spec-id> [--artifact <name>] [--rendered]
telos spec validate <workspace-id> <spec-id>
telos spec coverage <workspace-id> <spec-id>

telos context create --name <name> --instruction <text>
telos context list
telos context get <id>
telos context source add <context-id> --type <type> --locator <loc>
telos context source remove <context-id> <source-id>
telos context attach <workspace-id> <context-id> [--pin-mode <pinned|live>]
telos context detach <workspace-id> <context-id>

telos run start <workspace-id> <spec-id>
telos run start-ralph <workspace-id> --goal <text> --verifier <command>
telos run list <workspace-id>
telos run get <run-id>
telos run stop <run-id>

telos agent list <workspace-id>
telos agent get <agent-id>
telos agent stop <agent-id>
telos agent logs <agent-id> [--follow]
telos agent message <agent-id> <text>

telos campaign create --goal <file>
telos campaign register <campaign-id> <workspace-id> [--depends-on <spec:group>...]
telos campaign status <campaign-id>
telos campaign abandon <campaign-id>

telos activity <workspace-id> [--run <id>] [--agent <id>] [--type <type>...] [--follow]

telos daemon start [--foreground]
telos daemon stop
telos daemon status
```

### 3.3 PRD authoring

The CLI supports PRD authoring through two modes:

- **Direct edit.** `telos spec author` applies a JSON Patch to a spec
  artifact, validated by the daemon. For PRD text, the patch replaces the
  body content.
- **Editor integration.** `telos spec edit <workspace-id> <spec-id>
  --artifact prd` opens the artifact in `$EDITOR`. On save, the CLI diffs
  against the stored version, constructs a patch, and submits it to the
  daemon for validation. This gives the Operator a comfortable editing
  experience for the PRD without bypassing the spec store.

Agent-assisted PRD authoring (section 10.1, phase 3 of the PRD) works by
starting a temporary agent with a drafting template, feeding it the
Operator's brief and attached Contexts, and writing the agent's output into
the spec store through the normal authoring API.

---

## 4. The runtime engine

The runtime engine (specified in `docs/runtime-layer.md`) runs as a library
embedded in the daemon, not as a separate process. The daemon calls it to
create containers, start agents, manage worktrees, and orchestrate sidecars.

This means the daemon process is the only thing the Operator needs to start.
The container runtime (Podman) must be available on the host, but
the Operator interacts with it only through the Telos CLI, never directly.

### 4.1 Runtime lifecycle within the daemon

- On daemon startup: the runtime engine initializes, connects to the
  container backend, and inventories existing containers.
- On workspace create: the runtime creates the worktree.
- On run start: the runtime provisions and starts agent containers with
  templates, MCP bridge sidecars, and mounted worktrees.
- On agent stop/suspend: the runtime stops or suspends the container.
- On workspace delete: the runtime removes containers and optionally the
  worktree and branch.

---

## 5. The Telos MCP bridge

Specified in `docs/runtime-layer.md`, section 8. One instance per running
agent, inside the agent's container.

### 5.1 Daemon connection

The bridge connects to the daemon's bridge port (`localhost:7400` by default)
on startup. The connection parameters are injected via environment variables:

```
TELOS_DAEMON_HOST=host.containers.internal
TELOS_DAEMON_PORT=7400
TELOS_AGENT_TOKEN=<jwt>
TELOS_WORKSPACE_ID=<uuid>
TELOS_AGENT_ID=<uuid>
TELOS_RUN_ID=<uuid>
```

The agent token is a short-lived JWT issued by the daemon at container
creation, encoding the agent's identity (workspace, agent, run, specialist
role). The daemon validates it on every bridge request and scopes the
response accordingly.

### 5.2 Reconnection

If the daemon restarts while an agent is running, the bridge retries
connection with exponential backoff. While disconnected, the harness can
still work (editing files, running commands) but Telos-specific tool calls
(spec read, Context search, etc.) return errors. The bridge logs a
`bridge_disconnected` event locally and replays it to the daemon on
reconnect.

### 5.3 Health reporting

The bridge reports agent activity to the daemon via a periodic heartbeat
(default every 30 seconds). The heartbeat includes the agent's current
activity (working, thinking, waiting, etc.) derived from the harness's
observable behavior (output activity, tool calls). The daemon uses
heartbeats for stall detection: an agent whose heartbeat arrives but whose
activity hasn't changed for a configurable duration (default 5 minutes) is
flagged as stalled.

---

## 6. The memory service

### 6.1 Embedded mode (default)

The memory service runs in-process within the daemon. Learnings are stored
in the SQLite database alongside the operational store (in a separate set of
tables). Recall uses a simple keyword and embedding-based similarity search
over stored learnings.

This is sufficient for single-user, single-machine use. No external
dependencies.

### 6.2 External mode

The daemon connects to an external memory service over gRPC, using the
`AgentMemory` interface (section 8.6 of the PRD). The external service owns
storage, retrieval, and distillation. The daemon passes through `recall` and
`consolidate` calls.

This mode is for deployments that want shared memory across machines, more
sophisticated retrieval (vector search, re-ranking), or integration with an
existing knowledge base.

### 6.3 Configuration

```yaml
# ~/.telos/settings.yaml
memory:
  backend: embedded            # embedded | external
  # For external mode:
  # endpoint: localhost:7401
  # auth: token
```

---

## 7. Storage layout

### 7.1 Filesystem layout

```
~/.telos/
  daemon.sock                  # CLI-to-daemon Unix socket
  telos.db                     # SQLite database (operational + Context stores)
  settings.yaml                # Global configuration
  specs/                       # Spec store
    <workspace-id>/
      <spec-id>/
        prd.md
        requirements.json
        test_spec.json
        tasks.json
        architecture.md        # optional
      archive/                 # superseded and archived specs
        <spec-id>/
          ...
  templates/                   # Global templates
    planner/
    coordinator/
    implementor/
    verifier/
    ralph/
  # Worktrees live near the repo, not here — see runtime-layer.md section 3.2
  # Location: <repo-parent>/.telos_worktrees/<workspace-id>/
```

### 7.2 Database schema (SQLite)

The operational store tables map directly to the entities in section 11.3
of the PRD:

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

The entire Telos state is in `~/.telos/`: one SQLite file, one specs
directory, and configuration. Backup is `cp -r ~/.telos/ <backup-path>`.
Moving to a new machine is the same copy plus re-creating worktrees (which
are tied to the local git repo path).

---

## 8. Communication protocols

### 8.1 CLI ↔ Daemon

HTTP/JSON over Unix domain socket. The CLI sends requests; the daemon
responds. For streaming operations (activity follow, agent logs), the daemon
uses server-sent events (SSE) over the same connection.

The socket path is `~/.telos/daemon.sock` by default, overridable via
`TELOS_DAEMON_SOCK` or `--daemon-sock`.

### 8.2 MCP bridge ↔ Daemon

gRPC over TCP. The bridge is the client; the daemon is the server. Each RPC
includes the agent token in metadata for authentication and scoping.

Services:

```protobuf
service TelosBridge {
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

### 8.3 Daemon ↔ Runtime engine

In-process function calls. The runtime engine is a Go library (or equivalent)
linked into the daemon binary. No IPC.

### 8.4 Daemon ↔ Memory service (external mode)

gRPC over TCP. The daemon is the client; the memory service is the server.
Uses the `AgentMemory` interface from section 8.6 of the PRD, translated to
protobuf.

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

The daemon validates the token on every bridge request. An Implementor
cannot read another workspace's spec. An Archetype cannot transition another
agent's subtask. The token is the enforcement mechanism for the actor
capability model (section 8.4 of the PRD) at the bridge boundary.

### 9.2 Container isolation

Detailed in `docs/runtime-layer.md`. The key guarantee: an agent container
sees only its mounted worktree, its agent home directory, and the MCP bridge
socket. It cannot see the Telos database, other agents' homes, or the spec
store on the host filesystem.

### 9.3 Daemon access

The CLI socket is file-permission-protected (owner-only). The bridge port
is localhost-only by default. No authentication is needed for the CLI socket
(the Operator has host access); the bridge port uses agent tokens.

---

## 10. Deployment modes

### 10.1 Local (default)

Everything on one machine. Podman for containers. SQLite for
storage. Embedded memory service. The Operator runs `telos daemon start` and
uses the CLI.

### 10.2 Future: remote daemon

The daemon runs on a remote machine (a beefy server, a cloud VM). The CLI
connects over TCP instead of a Unix socket. The bridge port is exposed on the
network with TLS. Agent containers run on the same remote machine. This
requires adding TLS and Operator authentication to the daemon — the gRPC and
HTTP interfaces already support it structurally.

### 10.3 Future: distributed

Multiple machines each running a daemon instance, coordinated by a central
registry (analogous to Scion's Hub). Out of scope for this document.

---

## 11. Context retrieval engine

### 11.1 Purpose

The PRD defines two resolution strategies for Context sources (section 7.10):
`pinned` (full content in the prompt every turn) and `retrieved` (indexed,
only relevant chunks pulled in per turn). Pinned sources work for small
documents but cannot scale to a full repository or a large document set.
The retrieval engine makes `retrieved` sources practical.

### 11.2 Interface

The daemon calls the retrieval engine when an agent invokes the Context
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

**Embedded (default).** The engine runs in-process within the daemon.
Embeddings are computed using a local model (e.g. a small ONNX embedding
model shipped with the daemon). The index is stored in SQLite (using a
vector extension) or in a local file-based index (e.g. HNSW). No external
dependencies.

**External.** The daemon connects to a standalone retrieval service over
gRPC, using the same interface. This mode supports GPU-accelerated
embeddings, larger indices, and shared retrieval across multiple daemon
instances.

### 11.4 Indexing lifecycle

- When a Context revision is cut: the daemon calls `index()` for each
  `retrieved` source in the revision.
- When a workspace attaches a Context: the daemon verifies the pinned
  revision is indexed. If not (e.g. the engine was added after the
  revision was cut), it triggers indexing.
- When a `live` source re-resolves: the daemon calls `index()` with the
  new content, then `remove()` for the old revision once no workspace
  pins it.
- When a source is removed from a Context: `remove()` on all revisions.

### 11.5 Storage

Embedded mode adds to the daemon's storage:

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

The PRD (section 3) states the harness "reads CI status and drives PRs but
does not run pipelines itself." The CI/CD bridge is the read-only adapter
that fulfills the first half: agents can query pipeline status so the
Verifier can confirm CI passed as part of the wiring verification gate and
the PR Shepherd can wait for green CI before marking a PR merge-ready.

### 12.2 Interface

Defined in the PRD (section 8.5). The `CIProvider` interface is pluggable,
the same pattern as `IssueTracker` and `WebSearch`:

```
interface CIProvider {
  listRuns(ref: CIRef): Promise<PipelineRun[]>
  getRun(runId: string): Promise<PipelineRun>
  getJobLog(jobId: string): Promise<string>
}
```

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

The CI/CD bridge is exposed to agents through the Telos MCP bridge as the
`telos_ci_status` tool. Queries and results are logged as activity events.
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

The notification service subscribes to the daemon's activity event stream
and matches events against a set of triggers. When a trigger fires, it
delivers a notification through one or more configured channels.

```
interface NotificationService {
  // Register a channel for delivery.
  addChannel(channel: NotificationChannel): void

  // Configure which events trigger notifications.
  setTriggers(triggers: NotificationTrigger[]): void
}

interface NotificationChannel {
  name: string
  deliver(notification: Notification): Promise<void>
}

type NotificationTrigger = {
  event: string                 // activity event type or pattern
  filter?: {                    // optional narrowing
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

Out of the box, the notification service fires on:

| Trigger | Priority | When |
| --- | --- | --- |
| `spec_ready_for_review` | action_required | A Planner has drafted a spec and it is ready for Operator approval (phase 4). |
| `run_complete` | info | A spec-driven run completed successfully (all verification passed). |
| `run_failed` | action_required | A run stopped due to error or unrecoverable verification failure. |
| `ralph_complete` | info | A Ralph loop exited cleanly (verifier passed). |
| `ralph_stopped` | action_required | A Ralph loop hit a circuit breaker. |
| `campaign_workspace_unblocked` | action_required | A Campaign dependency gate cleared; a workspace is ready for PRD authoring. |
| `verification_failed` | info | A verification gate failed; the Coordinator will re-delegate. |
| `agent_stalled` | info | An agent has been stalled for longer than the configured threshold. |

The Operator can add, remove, or modify triggers through configuration.

### 13.5 Deployment

The notification service runs inside the daemon process as an event
subscriber — not a separate service. It reads from the activity event
stream (the same stream the observability API exposes) and evaluates
triggers. This keeps the deployment model simple: no additional process
to manage.

### 13.6 Configuration

```yaml
# ~/.telos/settings.yaml
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
operations (create workspace, approve spec, start run) remain CLI-driven.

### 14.2 Architecture

The dashboard is a static single-page application (SPA) served by the daemon
over its HTTP interface. It consumes the same Operator-facing API (section
12.1 of the PRD) and observability API (section 12.3) that the CLI uses.
No additional backend logic — the daemon already serves everything the
dashboard needs.

```
Browser ──► Daemon HTTP ──► Same API endpoints as CLI
                     └──► SSE streams for live updates
```

### 14.3 Views

| View | Content |
| --- | --- |
| **Home** | List of active workspaces with status, current run, agent count. Campaigns shown as collapsible groups with their dependency graphs. |
| **Workspace detail** | Workspace state, attached Contexts (with pinned revisions), spec lifecycle, git status, file listing. |
| **Spec viewer** | Rendered combined view of the spec (PRD, requirements, test spec, tasks). Coverage and traceability tables. Diff against previous spec (for superseded specs). |
| **Run timeline** | Gantt-style view of a run: phases, agent lifetimes, subtask state transitions, verification outcomes. Clickable for detail. |
| **Activity stream** | Filterable, scrollable event log. Live updates via SSE. Filter by workspace, run, agent, event type. |
| **Agent detail** | Agent state (phase, activity), conversation history, tool call log, assigned subtask and its state. |
| **Campaign graph** | Dependency graph across specs in a Campaign. Node color by workspace status (blocked, active, sealed). Clicking a node navigates to the workspace detail. |

### 14.4 Live updates

The dashboard subscribes to the daemon's SSE activity stream for real-time
updates. Workspace status changes, subtask transitions, verification
outcomes, and agent state changes appear without polling.

### 14.5 Deployment

The daemon serves the dashboard's static assets (HTML, CSS, JS) from a
built-in directory. No separate web server. The dashboard is available at
`http://localhost:<daemon-http-port>/` when the daemon is running.

For remote access (when the daemon binds to a network interface), the same
TLS and authentication requirements as the remote daemon mode apply.

### 14.6 Scope boundary

The dashboard is read-only. It does not provide forms for creating
workspaces, authoring specs, or starting runs. Those workflows involve
validation, editor integration, and multi-step interactions that are better
served by the CLI. If write support is added later, it routes through the
same API — the dashboard never bypasses the daemon.

---

## 15. Deferred

One component remains architecturally anticipated but not specified:

- **Remote daemon / Hub.** Running the daemon on a remote machine with TLS,
  Operator authentication, and multi-tenant isolation. The gRPC and HTTP
  interfaces already support remote access structurally; what's missing is
  the auth layer and tenant separation. This is the path to shared
  deployments and team collaboration.
