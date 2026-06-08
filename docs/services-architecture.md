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
   daemon process, one SQLite database, containers on the local Docker. No
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
The container runtime (Docker, Podman) must be available on the host, but
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
TELOS_DAEMON_HOST=host.docker.internal
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
  worktrees/                   # Managed by the runtime engine
    <workspace-id>/            # git worktree directory
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
  provider, model, status, parent_agent_id, started_at, ended_at
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

Everything on one machine. Docker (or Podman) for containers. SQLite for
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

## 11. Deferred components

These are identified as needed but not specified here:

- **Web dashboard.** A read-only web frontend against the daemon's HTTP API.
  Shows workspace status, run progress, activity timeline, and spec content.
  The daemon already serves HTTP; the dashboard is a static frontend.
- **Context retrieval engine.** An indexing and vector-search service for
  "retrieved" Context sources. Until built, all sources must be `pinned`.
  Could run as a sidecar to the daemon or as a standalone service.
- **CI/CD bridge.** A pluggable adapter (same pattern as issue tracker and
  web search) that lets agents query CI pipeline status. GitHub Actions and
  GitLab CI are the initial targets.
- **Notification service.** Alerts the Operator when a run completes, a
  verification fails, or a circuit breaker fires. Desktop notifications,
  Slack, email — behind a pluggable interface.
