#!/usr/bin/env python3
"""Programmatic construction of the Audit Hub specification.

Builds an in-memory Spec that mirrors the content of
examples/01_audit_hub (prd.md, requirements.md, design.md,
test_spec.md, tasks.md) using the afspec construction API,
then writes it to disk under examples/01_audit_hub_new.
"""

from pathlib import Path

from afspec import (
    CorrectnessProperty,
    Coverage,
    EdgeCaseTest,
    ErrorHandlingEntry,
    ExecutionPath,
    PRDDocument,
    PRDFrontmatter,
    PathStep,
    PropertyTest,
    Requirement,
    Requirements,
    SmokeTest,
    Spec,
    Status,
    Subtask,
    SubtaskState,
    TaskGroup,
    TaskGroupKind,
    Tasks,
    TestCase,
    TestCommands,
    TestSpec,
    TraceabilityEntry,
    UserStory,
    VerificationSubtask,
    create_spec,
    complex_event_criterion,
    event_driven_criterion,
    render_combined,
    save,
    ubiquitous_criterion,
    unwanted_criterion,
    validate,
)
from afspec.mutate import (
    add_correctness_property,
    add_criterion,
    add_edge_case,
    add_edge_case_test,
    add_error_handling,
    add_execution_path,
    add_property_test,
    add_requirement,
    add_smoke_test,
    add_subtask,
    add_task_group,
    add_test_case,
    add_traceability_entry,
    set_glossary_entry,
)

# ── PRD body (markdown) ─────────────────────────────────────────────

PRD_BODY = """\
# Product Requirements Document: Audit Hub

## Overview

A minimalistic Go-based HTTP service that receives audit events from agent-fox
instances via HTTP POST and stores them in a local embedded SQLite database.
The service is designed for single-instance deployment on Kubernetes.

## Core Functionality

### Audit Event Ingestion

- The service exposes a single write endpoint at `POST /api/v1/audit`.
- Each request carries exactly one audit event in the JSON body, conforming to
  the envelope schema defined in `audit-format.md`.
- The service validates incoming events against the envelope schema before
  storing them. Malformed or non-conformant events are rejected.
- This is a **write-only** service in version 0.0.1 — no query or retrieval
  endpoints are exposed.

### Storage

- Events are stored in an embedded SQLite database.
- The database schema decomposes envelope metadata into dedicated columns for
  efficient querying, while storing the `payload` field as a raw JSON text
  column.
- SQLite WAL (Write-Ahead Logging) mode is enabled to handle concurrent writes
  from multiple goroutines serving simultaneous requests.
- The database file is stored at a default location (`./data/audit.db`),
  configurable via the TOML configuration file.

### Authentication

- All requests to `POST /api/v1/audit` require a Bearer token in the
  `Authorization` header.
- The token is created when an agent-fox instance/repository is registered.
- For version 0.0.1, the token value is hardcoded in the configuration file.
- Requests without a valid token receive HTTP 401 Unauthorized.

### Kubernetes Health Endpoints

- `GET /healthz` — liveness probe. Returns HTTP 200 when the process is
  running.
- `GET /readyz` — readiness probe. Returns HTTP 200 when the service is ready
  to accept traffic (database connection is healthy).
- Health endpoints do **not** require authentication.

### Data Retention

- A background retention process periodically purges events older than a
  configurable retention period.
- Default retention period: 30 days.
- Retention is based on the event's `timestamp` field.

### Configuration

All runtime configuration is read from a local TOML file. Configurable fields:

| Section    | Field            | Default          | Description                        |
|------------|------------------|------------------|------------------------------------|
| `server`   | `port`           | `8080`           | HTTP listen port                   |
| `server`   | `bind_address`   | `"0.0.0.0"`     | Network interface to bind to       |
| `database` | `path`           | `"./data/audit.db"` | SQLite database file path      |
| `database` | `retention_days` | `30`             | Event retention period in days     |
| `auth`     | `bearer_token`   | (required)       | Bearer token for API auth          |
| `logging`  | `level`          | `"info"`         | Log level (debug, info, warn, error) |

### Logging

- The service uses structured JSON logging via the logrus library.
- Log level is configurable via the TOML configuration file.

### Graceful Shutdown

- The service handles `SIGTERM` and `SIGINT` signals.
- On shutdown, the service stops accepting new connections, drains in-flight
  requests, and closes the database connection cleanly.

## Non-Functional Requirements

- **Concurrency**: The service must handle concurrent write requests safely
  using SQLite WAL mode.
- **Deployment**: Single-instance deployment on Kubernetes.
- **Framework**: Uses the Echo HTTP framework for Go.
- **Future extensibility**: Other use-cases will be added in future versions.

## Out of Scope (v0.0.1)

- Query/read API endpoints
- Multi-instance / distributed deployment
- Dynamic token management (registration API)
- Batch event ingestion
- Event forwarding or streaming

## Clarifications

1. **API endpoint path**: `POST /api/v1/audit`
2. **Single vs. batch**: Single event per request
3. **Payload validation**: Validate incoming events against the envelope schema
4. **Authentication**: Bearer token, hardcoded in config for v0.0.1
5. **Response format**: HTTP status codes only (no response body)
6. **Port**: Configurable, 8080 default
7. **K8s endpoints**: Standard `/healthz` and `/readyz`
8. **SQLite location**: Default `./data/audit.db`, configurable
9. **DB schema**: Envelope metadata as columns, payload as JSON text
10. **Retention**: Configurable, 30-day default based on event timestamp
11. **Config fields**: Server, database, auth, and logging settings in TOML
12. **Logging**: JSON structured logging via logrus
13. **Graceful shutdown**: Handle SIGTERM/SIGINT, drain requests, close DB
14. **Query API**: Write-only in v0.0.1
15. **Concurrency**: WAL mode for concurrent writes
16. **Deployment**: Single-instance
17. **Event ordering**: Timestamp-based ordering in the database

## Source

Source: .agent-fox/specs/prd.md
"""

# ── Architecture content (markdown) ────────────────────────────────

ARCHITECTURE_CONTENT = """\
# Architecture: Audit Hub

## Overview

Audit Hub is a single-binary Go service built on the Echo HTTP framework. It
receives agent-fox audit events via a single authenticated endpoint, validates
them against the envelope schema, and persists them in an embedded SQLite
database running in WAL mode. A background goroutine handles time-based data
retention. The service exposes unauthenticated Kubernetes health probes and
performs graceful shutdown on SIGTERM/SIGINT.

## Architecture

```mermaid
flowchart TD
    AF[agent-fox instances] -->|POST /api/v1/audit\\nBearer token| GW[Echo Router]
    K8S[Kubernetes] -->|GET /healthz, /readyz| GW

    GW --> AM[Auth Middleware]
    AM --> VL[Validator]
    VL --> SH[Store Handler]
    SH --> DB[(SQLite WAL)]

    GW --> HC[Health Controller]
    HC --> DB

    RT[Retention Ticker] -->|hourly| DB

    CFG[config.toml] -->|startup| APP[Application]
    APP --> GW
    APP --> DB
    APP --> RT
```

```mermaid
sequenceDiagram
    participant C as agent-fox
    participant E as Echo Router
    participant A as Auth Middleware
    participant V as Validator
    participant S as Store
    participant DB as SQLite

    C->>E: POST /api/v1/audit (Bearer token, JSON body)
    E->>A: Check Authorization header
    alt Invalid/missing token
        A-->>C: 401 Unauthorized
    end
    A->>V: Pass request body
    V->>V: Parse JSON, validate envelope fields
    alt Validation failure
        V-->>C: 422 Unprocessable Entity
    end
    V->>S: Validated AuditEvent struct
    S->>DB: INSERT INTO events (...)
    alt Duplicate id
        DB-->>S: UNIQUE constraint error
        S-->>C: 409 Conflict
    else Success
        DB-->>S: OK
        S-->>C: 201 Created
    end
```

### Module Responsibilities

1. **cmd/audit-hub** — Application entry point: parses CLI flags, loads config, wires dependencies, starts server, handles OS signals.
2. **internal/config** — TOML configuration loading, validation, and defaults.
3. **internal/server** — Echo server setup, route registration, middleware wiring, graceful shutdown.
4. **internal/middleware** — Bearer token authentication middleware for Echo.
5. **internal/handler** — HTTP request handler for the audit ingest endpoint.
6. **internal/validator** — Envelope schema validation logic for incoming audit events.
7. **internal/store** — SQLite database initialization (WAL mode, table creation), event insertion, health check query, retention purge.
8. **internal/retention** — Background ticker goroutine that triggers periodic purge via the store.
9. **internal/health** — Health and readiness endpoint handlers.
10. **internal/model** — Data types: `AuditEvent` struct, `Config` struct.

## Components and Interfaces

### CLI

```
audit-hub [--config <path>]

Flags:
  --config string   Path to TOML configuration file (default "config.toml")
```

### Core Data Types

```go
// internal/model/event.go

type AuditEvent struct {
    ID        string          `json:"id"`
    Timestamp string          `json:"timestamp"`
    RunID     string          `json:"run_id"`
    EventType string          `json:"event_type"`
    NodeID    string          `json:"node_id"`
    SessionID string          `json:"session_id"`
    Archetype string          `json:"archetype"`
    Severity  string          `json:"severity"`
    Payload   json.RawMessage `json:"payload"`
}
```

```go
// internal/config/config.go

type Config struct {
    Server   ServerConfig   `toml:"server"`
    Database DatabaseConfig `toml:"database"`
    Auth     AuthConfig     `toml:"auth"`
    Logging  LoggingConfig  `toml:"logging"`
}

type ServerConfig struct {
    Port        int    `toml:"port"`
    BindAddress string `toml:"bind_address"`
}

type DatabaseConfig struct {
    Path          string `toml:"path"`
    RetentionDays int    `toml:"retention_days"`
}

type AuthConfig struct {
    BearerToken string `toml:"bearer_token"`
}

type LoggingConfig struct {
    Level string `toml:"level"`
}
```

### Module Interfaces

```go
// internal/store/store.go

type Store struct { /* contains *sql.DB */ }

func New(dbPath string) (*Store, error)
func (s *Store) InsertEvent(ctx context.Context, event model.AuditEvent) error
func (s *Store) Ping(ctx context.Context) error
func (s *Store) PurgeOlderThan(ctx context.Context, cutoff time.Time) (int64, error)
func (s *Store) Close() error
```

```go
// internal/validator/validator.go

func Validate(event model.AuditEvent) error
```

```go
// internal/middleware/auth.go

func BearerAuth(token string) echo.MiddlewareFunc
```

```go
// internal/handler/audit.go

type AuditHandler struct { store *store.Store }

func NewAuditHandler(store *store.Store) *AuditHandler
func (h *AuditHandler) Ingest(c echo.Context) error
```

```go
// internal/health/health.go

type HealthHandler struct { store *store.Store }

func NewHealthHandler(store *store.Store) *HealthHandler
func (h *HealthHandler) Healthz(c echo.Context) error
func (h *HealthHandler) Readyz(c echo.Context) error
```

```go
// internal/retention/retention.go

func StartRetention(ctx context.Context, store *store.Store, interval time.Duration, retentionDays int)
```

```go
// internal/server/server.go

type Server struct { /* contains *echo.Echo */ }

func New(cfg *config.Config, store *store.Store) *Server
func (s *Server) Start() error
func (s *Server) Shutdown(ctx context.Context) error
```

```go
// internal/config/config.go

func Load(path string) (*Config, error)
```

## Data Models

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    run_id      TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    node_id     TEXT NOT NULL DEFAULT '',
    session_id  TEXT NOT NULL DEFAULT '',
    archetype   TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
```

### TOML Configuration Example

```toml
[server]
port = 8080
bind_address = "0.0.0.0"

[database]
path = "./data/audit.db"
retention_days = 30

[auth]
bearer_token = "your-secret-token-here"

[logging]
level = "info"
```

## Technology Stack

| Component | Technology | Version/Notes |
|-----------|-----------|---------------|
| Language | Go | 1.22+ |
| HTTP framework | Echo | v4 |
| Database | SQLite | via `modernc.org/sqlite` (pure Go, CGo-free) |
| Configuration | TOML | via `github.com/BurntSushi/toml` |
| Logging | logrus | `github.com/sirupsen/logrus` |
| Testing | Go stdlib | `testing`, `net/http/httptest` |
| Property testing | rapid | `pgregory.net/rapid` |
| Build | Go modules | `go.mod` |
| Container | Docker | Multi-stage build |

## Operational Readiness

### Observability

- **Structured logs**: All log output is JSON via logrus, suitable for
  ingestion by Kubernetes log aggregators (Fluentd, Loki, etc.).
- **Request logging**: Every HTTP request is logged with method, path, status
  code, and duration.
- **Retention logging**: Each purge cycle logs the number of deleted events.

### Rollout / Rollback

- Single binary deployment; rollback is a container image revert.
- Database schema is forward-only (single table, additive changes in future
  versions).
- Configuration changes require a pod restart (no hot-reload in v0.0.1).

### Migration / Compatibility

- v0.0.1 creates the schema on first run; no migration framework needed yet.
- Future schema changes should use a migration library (e.g., golang-migrate).
"""


# ── Requirements builders ───────────────────────────────────────────


def _build_req1() -> Requirement:
    r = Requirement(
        id="01-REQ-1",
        title="Audit Event Ingestion",
        user_story=UserStory(
            role="an agent-fox instance",
            goal="send audit events to a central service via HTTP POST",
            benefit="events are durably stored for later analysis",
        ),
    )
    r = add_criterion(
        r,
        complex_event_criterion(
            "01-REQ-1.1",
            "an HTTP POST request is received at `/api/v1/audit`",
            "a valid Bearer token and a JSON body conforming to the envelope schema",
            "THE service",
            "store the event in the SQLite database AND return HTTP 201 "
            "Created with no response body",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-1.2",
            "an HTTP POST request is received at `/api/v1/audit`",
            "THE service",
            "accept only the `application/json` content type AND return "
            "HTTP 415 Unsupported Media Type for any other content type",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-1.3",
            "THE service",
            "listen for HTTP requests on the port specified in the "
            "configuration file, defaulting to 8080 if not configured",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-1.4",
            "THE service",
            "bind to the network address specified in the configuration "
            "file, defaulting to `0.0.0.0` if not configured",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-1.E1",
            "the request body is empty",
            "THE service",
            "return HTTP 400 Bad Request",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-1.E2",
            "the request body exceeds 1 MB",
            "THE service",
            "return HTTP 413 Payload Too Large without reading the full body",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-1.E3",
            "the request body is not valid JSON",
            "THE service",
            "return HTTP 400 Bad Request",
        ),
    )
    return r


def _build_req2() -> Requirement:
    r = Requirement(
        id="01-REQ-2",
        title="Event Validation",
        user_story=UserStory(
            role="a service operator",
            goal="incoming events to be validated against the envelope schema",
            benefit="only well-formed events are stored",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-2.1",
            "an event is received",
            "THE service",
            "validate that all required envelope fields are present: "
            "`id`, `timestamp`, `run_id`, `event_type`, `severity`, and `payload`",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-2.2",
            "an event is received",
            "THE service",
            "validate that `id` is a non-empty string, `timestamp` is a valid "
            "ISO 8601 datetime string, `run_id` is a non-empty string, "
            "`event_type` is a non-empty string containing at least one dot "
            "separator, `severity` is one of `info`, `warning`, `error`, or "
            "`critical`, and `payload` is a JSON object",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-2.3",
            "an event is received",
            "THE service",
            "accept optional envelope fields `node_id`, `session_id`, and "
            "`archetype` as strings, defaulting to empty string if absent",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-2.4",
            "any required field is missing or fails validation",
            "THE service",
            "return HTTP 422 Unprocessable Entity",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-2.E1",
            "the `timestamp` field contains a valid ISO 8601 date but "
            "without timezone information",
            "THE service",
            "reject the event with HTTP 422 Unprocessable Entity",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-2.E2",
            "the `payload` field is `null` instead of an object",
            "THE service",
            "reject the event with HTTP 422 Unprocessable Entity",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-2.E3",
            'the `event_type` field contains no dot separator (e.g., '
            '`"start"` instead of `"run.start"`)',
            "THE service",
            "reject the event with HTTP 422 Unprocessable Entity",
        ),
    )
    return r


def _build_req3() -> Requirement:
    r = Requirement(
        id="01-REQ-3",
        title="SQLite Storage",
        user_story=UserStory(
            role="a service operator",
            goal="events stored in an embedded SQLite database with metadata columns",
            benefit="events can be queried efficiently without external dependencies",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-3.1",
            "THE service",
            "store each validated event in a SQLite table with dedicated "
            "columns for envelope metadata: `id` (TEXT PRIMARY KEY), "
            "`timestamp` (TEXT), `run_id` (TEXT), `event_type` (TEXT), "
            "`node_id` (TEXT), `session_id` (TEXT), `archetype` (TEXT), "
            "`severity` (TEXT), and `payload` (TEXT storing the raw JSON "
            "object), plus a `received_at` (TEXT) column recording the "
            "server-side reception time in ISO 8601 UTC",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-3.2",
            "THE service",
            "enable SQLite WAL mode on database initialization to support "
            "concurrent write access",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-3.3",
            "THE service",
            "create the database file and the events table automatically on "
            "first startup if they do not exist, AND return the database path "
            "to the caller for logging purposes",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-3.4",
            "THE service",
            "use the database path from the configuration file, defaulting to "
            "`./data/audit.db` if not configured, AND create parent directories "
            "if they do not exist",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-3.E1",
            "a received event has an `id` that already exists in the database",
            "THE service",
            "reject the event with HTTP 409 Conflict",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-3.E2",
            "the database file cannot be opened or created (e.g., permission denied)",
            "THE service",
            "log the error and exit with a non-zero exit code",
        ),
    )
    return r


def _build_req4() -> Requirement:
    r = Requirement(
        id="01-REQ-4",
        title="Bearer Token Authentication",
        user_story=UserStory(
            role="a service operator",
            goal="restrict access to the ingest endpoint using a Bearer token",
            benefit="only authorized agent-fox instances can submit events",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-4.1",
            "an HTTP request is received at `/api/v1/audit`",
            "THE service",
            "extract the Bearer token from the `Authorization` header and "
            "compare it against the configured token value",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-4.2",
            "the `Authorization` header is missing or does not start with `Bearer `",
            "THE service",
            "return HTTP 401 Unauthorized",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-4.3",
            "the Bearer token does not match the configured token",
            "THE service",
            "return HTTP 401 Unauthorized",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-4.4",
            "THE service",
            "read the expected Bearer token from the `auth.bearer_token` field "
            "in the TOML configuration file",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-4.5",
            "the `auth.bearer_token` field is missing or empty in the configuration file",
            "THE service",
            "log an error and exit with a non-zero exit code at startup",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-4.E1",
            "the `Authorization` header contains extra whitespace between "
            "`Bearer` and the token value",
            "THE service",
            "trim the whitespace and validate the token normally",
        ),
    )
    return r


def _build_req5() -> Requirement:
    r = Requirement(
        id="01-REQ-5",
        title="Kubernetes Health Endpoints",
        user_story=UserStory(
            role="a Kubernetes operator",
            goal="standard health and readiness endpoints",
            benefit="the cluster can monitor the service's availability",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-5.1",
            "an HTTP GET request is received at `/healthz`",
            "THE service",
            "return HTTP 200 OK without requiring authentication",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-5.2",
            "an HTTP GET request is received at `/readyz`",
            "THE service",
            "verify that the SQLite database is accessible by executing a "
            "lightweight query (e.g., `SELECT 1`) AND return HTTP 200 OK if "
            "successful or HTTP 503 Service Unavailable if the check fails",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-5.3",
            "THE service",
            "NOT require a Bearer token for `/healthz` or `/readyz` requests",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-5.E1",
            "the database connection is lost after startup",
            "THE service",
            "return HTTP 503 on `/readyz` while continuing to return HTTP 200 "
            "on `/healthz`",
        ),
    )
    return r


def _build_req6() -> Requirement:
    r = Requirement(
        id="01-REQ-6",
        title="TOML Configuration",
        user_story=UserStory(
            role="a service operator",
            goal="configure the service via a TOML file",
            benefit="I can adjust runtime settings without recompilation",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-6.1",
            "the service starts",
            "THE service",
            "read the configuration from a TOML file at the path specified by "
            "the `--config` command-line flag, defaulting to `config.toml` in "
            "the current working directory",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-6.2",
            "THE service",
            "support the following configuration sections and fields with "
            'defaults: `server.port` (8080), `server.bind_address` (`"0.0.0.0"`), '
            '`database.path` (`"./data/audit.db"`), `database.retention_days` (30), '
            "`auth.bearer_token` (required, no default), `logging.level` "
            '(`"info"`)',
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-6.3",
            "the configuration file does not exist at the specified path",
            "THE service",
            "log an error and exit with a non-zero exit code",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-6.4",
            "the configuration file contains invalid TOML syntax",
            "THE service",
            "log a descriptive parse error and exit with a non-zero exit code",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-6.E1",
            "`database.retention_days` is set to zero or a negative value",
            "THE service",
            "log a warning and use the default value of 30 days",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-6.E2",
            "`server.port` is outside the range 1–65535",
            "THE service",
            "log an error and exit with a non-zero exit code",
        ),
    )
    return r


def _build_req7() -> Requirement:
    r = Requirement(
        id="01-REQ-7",
        title="Data Retention",
        user_story=UserStory(
            role="a service operator",
            goal="events older than a configurable period to be automatically purged",
            benefit="the database does not grow unboundedly",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-7.1",
            "THE service",
            "run a background retention process that periodically deletes "
            "events whose `timestamp` is older than the configured retention period",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-7.2",
            "THE service",
            "execute the retention purge once every hour",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-7.3",
            "the retention process runs",
            "THE service",
            "delete all events where `timestamp` is older than "
            "`now() - retention_days` AND log the number of deleted events "
            "AND return the count of deleted rows to the caller",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-7.4",
            "THE service",
            "default the retention period to 30 days if "
            "`database.retention_days` is not configured",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-7.E1",
            "the retention process encounters a database error during deletion",
            "THE service",
            "log the error and retry on the next scheduled cycle without crashing",
        ),
    )
    return r


def _build_req8() -> Requirement:
    r = Requirement(
        id="01-REQ-8",
        title="Graceful Shutdown",
        user_story=UserStory(
            role="a Kubernetes operator",
            goal="the service to shut down gracefully on SIGTERM",
            benefit="in-flight requests complete and the database is closed cleanly",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-8.1",
            "the service receives a SIGTERM or SIGINT signal",
            "THE service",
            "stop accepting new connections, wait for in-flight requests to "
            "complete (up to a 15-second timeout), stop the retention "
            "background process, close the database connection, and then "
            "exit with code 0",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-8.2",
            "in-flight requests do not complete within 15 seconds",
            "THE service",
            "force-close remaining connections and exit with code 0",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-8.E1",
            "a second SIGTERM or SIGINT is received during the graceful "
            "shutdown window",
            "THE service",
            "exit immediately with code 1",
        ),
    )
    return r


def _build_req9() -> Requirement:
    r = Requirement(
        id="01-REQ-9",
        title="Structured JSON Logging",
        user_story=UserStory(
            role="a service operator",
            goal="structured JSON logs",
            benefit="logs can be ingested by centralized logging systems in Kubernetes",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-9.1",
            "THE service",
            "emit all log messages as JSON objects using the logrus library "
            "with JSON formatter",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-9.2",
            "THE service",
            "set the log level to the value specified in `logging.level` "
            "configuration, defaulting to `info`",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-9.3",
            "the service starts",
            "THE service",
            "log a startup message including the configured port, database "
            "path, and log level",
        ),
    )
    r = add_criterion(
        r,
        event_driven_criterion(
            "01-REQ-9.4",
            "an HTTP request is processed",
            "THE service",
            "log the request method, path, status code, and duration",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-9.E1",
            "the `logging.level` field contains an unrecognized value",
            "THE service",
            "log a warning and default to `info`",
        ),
    )
    return r


def _build_req10() -> Requirement:
    r = Requirement(
        id="01-REQ-10",
        title="Concurrent Write Safety",
        user_story=UserStory(
            role="a service operator",
            goal="the service to safely handle concurrent audit event submissions",
            benefit="no events are lost under load",
        ),
    )
    r = add_criterion(
        r,
        ubiquitous_criterion(
            "01-REQ-10.1",
            "THE service",
            "enable SQLite WAL mode and configure connection pooling so that "
            "concurrent HTTP requests can write to the database without "
            "`SQLITE_BUSY` errors under normal load",
        ),
    )
    r = add_criterion(
        r,
        unwanted_criterion(
            "01-REQ-10.2",
            "a database write encounters a transient lock contention error",
            "THE service",
            "retry the write up to 3 times with a busy timeout of 5 seconds "
            "before returning HTTP 503 Service Unavailable",
        ),
    )
    r = add_edge_case(
        r,
        unwanted_criterion(
            "01-REQ-10.E1",
            "the SQLite busy timeout is exhausted after all retries",
            "THE service",
            "return HTTP 503 Service Unavailable and log the contention event "
            "at `warning` level",
        ),
    )
    return r


# ── Glossary ─────────────────────────────────────────────────────────

GLOSSARY = {
    "Audit event": (
        "A structured JSON object conforming to the envelope schema, "
        "representing a single observable action in the agent-fox system"
    ),
    "Envelope schema": (
        "The fixed set of top-level fields (`id`, `timestamp`, `run_id`, "
        "`event_type`, `node_id`, `session_id`, `archetype`, `severity`, "
        "`payload`) that every audit event must contain"
    ),
    "Bearer token": (
        "An opaque authentication credential sent in the `Authorization` "
        "header as `Bearer <token>`"
    ),
    "WAL mode": (
        "SQLite Write-Ahead Logging mode, which allows concurrent readers "
        "and a single writer without blocking"
    ),
    "Liveness probe": (
        "A Kubernetes health check that verifies the process is running (`/healthz`)"
    ),
    "Readiness probe": (
        "A Kubernetes health check that verifies the service can accept "
        "traffic (`/readyz`)"
    ),
    "Retention period": (
        "The maximum age (in days) of stored events before they are purged "
        "by the retention process"
    ),
    "TOML": (
        "Tom's Obvious Minimal Language — a configuration file format used "
        "for the service's runtime settings"
    ),
    "Echo": (
        "A high-performance Go HTTP framework used as the service's HTTP layer"
    ),
    "logrus": (
        "A structured logging library for Go that supports JSON output format"
    ),
}


# ── Correctness properties (from design.md) ─────────────────────────


def _correctness_properties() -> list[CorrectnessProperty]:
    return [
        CorrectnessProperty(
            id="01-PROP-1",
            title="Schema Validation Completeness",
            for_any="JSON object submitted to `POST /api/v1/audit`",
            invariant=(
                "the service accepts the event if and only if all required "
                "envelope fields (`id`, `timestamp`, `run_id`, `event_type`, "
                "`severity`, `payload`) are present and conform to their type "
                "constraints"
            ),
            validates=[
                "01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4",
            ],
        ),
        CorrectnessProperty(
            id="01-PROP-2",
            title="Storage Integrity",
            for_any="audit event that passes validation and receives HTTP 201",
            invariant=(
                "the event is retrievable from the SQLite database with all "
                "envelope metadata fields matching the submitted values exactly, "
                "and the `payload` field matching the original JSON object"
            ),
            validates=["01-REQ-1.1", "01-REQ-3.1"],
        ),
        CorrectnessProperty(
            id="01-PROP-3",
            title="Authentication Enforcement",
            for_any="HTTP request to `/api/v1/audit`",
            invariant=(
                "the service returns HTTP 401 if the Bearer token is missing, "
                "malformed, or does not match the configured value, and only "
                "proceeds to validation and storage when the token matches"
            ),
            validates=["01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3"],
        ),
        CorrectnessProperty(
            id="01-PROP-4",
            title="Idempotent Rejection of Duplicates",
            for_any="audit event with an `id` already present in the database",
            invariant=(
                "the service returns HTTP 409 Conflict without modifying the "
                "existing stored event"
            ),
            validates=["01-REQ-3.E1"],
        ),
        CorrectnessProperty(
            id="01-PROP-5",
            title="Retention Correctness",
            for_any="event stored in the database",
            invariant=(
                "after the retention process runs, the event is present if its "
                "`timestamp` is within the retention period, and absent if its "
                "`timestamp` is older than the retention period"
            ),
            validates=["01-REQ-7.1", "01-REQ-7.3"],
        ),
        CorrectnessProperty(
            id="01-PROP-6",
            title="Health Probe Independence",
            for_any="HTTP request to `/healthz` or `/readyz`",
            invariant=(
                "the service returns a response regardless of the presence or "
                "absence of an Authorization header. `/healthz` always returns "
                "200 when the process is running. `/readyz` returns 200 if and "
                "only if the database is accessible"
            ),
            validates=["01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.3"],
        ),
        CorrectnessProperty(
            id="01-PROP-7",
            title="Configuration Validation Completeness",
            for_any="TOML configuration file",
            invariant=(
                "the service starts successfully if and only if the file is "
                "syntactically valid TOML, contains a non-empty "
                "`auth.bearer_token`, and all numeric fields are within valid "
                "ranges (`server.port` in 1–65535, `database.retention_days` > 0)"
            ),
            validates=[
                "01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4",
                "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2",
            ],
        ),
        CorrectnessProperty(
            id="01-PROP-8",
            title="Concurrent Write Safety",
            for_any="set of N valid audit events submitted concurrently",
            invariant=(
                "the service stores exactly N events in the database (assuming "
                "no duplicate IDs) without returning `SQLITE_BUSY` errors under "
                "normal load"
            ),
            validates=["01-REQ-10.1", "01-REQ-10.2"],
        ),
        CorrectnessProperty(
            id="01-PROP-9",
            title="Graceful Shutdown Completeness",
            for_any="in-flight request at the time SIGTERM is received",
            invariant=(
                "the service either completes the request and returns a "
                "response, or terminates the connection after the 15-second "
                "timeout. In both cases, the database connection is closed "
                "before the process exits"
            ),
            validates=["01-REQ-8.1", "01-REQ-8.2"],
        ),
    ]


# ── Execution paths (from design.md) ────────────────────────────────


def _execution_paths() -> list[ExecutionPath]:
    return [
        ExecutionPath(
            id="01-PATH-1",
            title="Audit event ingestion (happy path)",
            steps=[
                PathStep(actor="cmd/audit-hub/main.go", action="main() — starts Echo server"),
                PathStep(actor="internal/server/server.go", action="New(cfg, store) → *Server — creates Echo instance, registers routes and middleware"),
                PathStep(actor="internal/middleware/auth.go", action="BearerAuth(token) → echo.MiddlewareFunc — validates Authorization header"),
                PathStep(actor="internal/handler/audit.go", action="AuditHandler.Ingest(c) → error — reads and binds request body"),
                PathStep(actor="internal/validator/validator.go", action="Validate(event) → error — validates envelope fields"),
                PathStep(actor="internal/store/store.go", action="Store.InsertEvent(ctx, event) → error — inserts row into SQLite"),
                PathStep(actor="Side effect", action="event persisted in SQLite, HTTP 201 returned to caller"),
            ],
        ),
        ExecutionPath(
            id="01-PATH-2",
            title="Health check (readiness)",
            steps=[
                PathStep(actor="cmd/audit-hub/main.go", action="main() — starts Echo server"),
                PathStep(actor="internal/server/server.go", action="New(cfg, store) → *Server — registers health routes (no auth middleware)"),
                PathStep(actor="internal/health/health.go", action="HealthHandler.Readyz(c) → error — handles GET /readyz"),
                PathStep(actor="internal/store/store.go", action="Store.Ping(ctx) → error — executes `SELECT 1` against SQLite"),
                PathStep(actor="Side effect", action="HTTP 200 or 503 returned to caller"),
            ],
        ),
        ExecutionPath(
            id="01-PATH-3",
            title="Data retention purge",
            steps=[
                PathStep(actor="cmd/audit-hub/main.go", action="main() — starts retention ticker"),
                PathStep(actor="internal/retention/retention.go", action="StartRetention(ctx, store, interval, retentionDays) — launches goroutine with hourly ticker"),
                PathStep(actor="internal/store/store.go", action="Store.PurgeOlderThan(ctx, cutoff) → (int64, error) — deletes expired rows, returns count"),
                PathStep(actor="Side effect", action="expired rows deleted from SQLite, count logged"),
            ],
        ),
        ExecutionPath(
            id="01-PATH-4",
            title="Graceful shutdown",
            steps=[
                PathStep(actor="cmd/audit-hub/main.go", action="main() — listens for OS signals"),
                PathStep(actor="OS", action="delivers SIGTERM or SIGINT"),
                PathStep(actor="cmd/audit-hub/main.go", action="main() — cancels context, triggers Echo shutdown"),
                PathStep(actor="internal/server/server.go", action="Server.Shutdown(ctx) → error — drains in-flight requests with 15s timeout"),
                PathStep(actor="internal/retention/retention.go", action="StopRetention() — stops ticker goroutine via context cancellation"),
                PathStep(actor="internal/store/store.go", action="Store.Close() → error — closes SQLite connection"),
                PathStep(actor="Side effect", action="process exits with code 0"),
            ],
        ),
        ExecutionPath(
            id="01-PATH-5",
            title="Configuration loading",
            steps=[
                PathStep(actor="cmd/audit-hub/main.go", action="main() — reads --config flag"),
                PathStep(actor="internal/config/config.go", action="Load(path) → (*Config, error) — reads TOML file, applies defaults, validates"),
                PathStep(actor="Side effect", action="Config struct returned to main for dependency wiring; exits with non-zero code on validation error"),
            ],
        ),
    ]


# ── Error handling (from design.md) ──────────────────────────────────


def _error_handling() -> list[ErrorHandlingEntry]:
    return [
        ErrorHandlingEntry(id="01-ERR-1", condition="Empty request body", behavior="HTTP 400 Bad Request", requirement_id="01-REQ-1.E1"),
        ErrorHandlingEntry(id="01-ERR-2", condition="Request body exceeds 1 MB", behavior="HTTP 413 Payload Too Large", requirement_id="01-REQ-1.E2"),
        ErrorHandlingEntry(id="01-ERR-3", condition="Invalid JSON body", behavior="HTTP 400 Bad Request", requirement_id="01-REQ-1.E3"),
        ErrorHandlingEntry(id="01-ERR-4", condition="Wrong content type", behavior="HTTP 415 Unsupported Media Type", requirement_id="01-REQ-1.2"),
        ErrorHandlingEntry(id="01-ERR-5", condition="Missing/invalid envelope fields", behavior="HTTP 422 Unprocessable Entity", requirement_id="01-REQ-2.4"),
        ErrorHandlingEntry(id="01-ERR-6", condition="Timestamp without timezone", behavior="HTTP 422 Unprocessable Entity", requirement_id="01-REQ-2.E1"),
        ErrorHandlingEntry(id="01-ERR-7", condition="Payload is null", behavior="HTTP 422 Unprocessable Entity", requirement_id="01-REQ-2.E2"),
        ErrorHandlingEntry(id="01-ERR-8", condition="Event type without dot", behavior="HTTP 422 Unprocessable Entity", requirement_id="01-REQ-2.E3"),
        ErrorHandlingEntry(id="01-ERR-9", condition="Duplicate event ID", behavior="HTTP 409 Conflict", requirement_id="01-REQ-3.E1"),
        ErrorHandlingEntry(id="01-ERR-10", condition="Database open failure", behavior="Log error, exit non-zero", requirement_id="01-REQ-3.E2"),
        ErrorHandlingEntry(id="01-ERR-11", condition="Missing/empty bearer token in config", behavior="Log error, exit non-zero", requirement_id="01-REQ-4.5"),
        ErrorHandlingEntry(id="01-ERR-12", condition="Missing Authorization header", behavior="HTTP 401 Unauthorized", requirement_id="01-REQ-4.2"),
        ErrorHandlingEntry(id="01-ERR-13", condition="Invalid bearer token", behavior="HTTP 401 Unauthorized", requirement_id="01-REQ-4.3"),
        ErrorHandlingEntry(id="01-ERR-14", condition="Database unreachable (readyz)", behavior="HTTP 503 Service Unavailable", requirement_id="01-REQ-5.E1"),
        ErrorHandlingEntry(id="01-ERR-15", condition="Config file not found", behavior="Log error, exit non-zero", requirement_id="01-REQ-6.3"),
        ErrorHandlingEntry(id="01-ERR-16", condition="Invalid TOML syntax", behavior="Log parse error, exit non-zero", requirement_id="01-REQ-6.4"),
        ErrorHandlingEntry(id="01-ERR-17", condition="Invalid retention_days (<= 0)", behavior="Log warning, use default 30", requirement_id="01-REQ-6.E1"),
        ErrorHandlingEntry(id="01-ERR-18", condition="Invalid port range", behavior="Log error, exit non-zero", requirement_id="01-REQ-6.E2"),
        ErrorHandlingEntry(id="01-ERR-19", condition="Retention purge DB error", behavior="Log error, retry next cycle", requirement_id="01-REQ-7.E1"),
        ErrorHandlingEntry(id="01-ERR-20", condition="Invalid logging.level value", behavior="Log warning, default to info", requirement_id="01-REQ-9.E1"),
        ErrorHandlingEntry(id="01-ERR-21", condition="SQLite busy timeout exhausted", behavior="HTTP 503, log at warning", requirement_id="01-REQ-10.E1"),
        ErrorHandlingEntry(id="01-ERR-22", condition="Shutdown timeout (15s) exceeded", behavior="Force-close connections, exit 0", requirement_id="01-REQ-8.2"),
        ErrorHandlingEntry(id="01-ERR-23", condition="Second SIGTERM during shutdown", behavior="Exit immediately with code 1", requirement_id="01-REQ-8.E1"),
    ]


# ── Test cases ───────────────────────────────────────────────────────


def _test_cases() -> list[TestCase]:
    return [
        TestCase(
            id="TS-01-1",
            requirement_id="01-REQ-1.1",
            kind="unit",
            description="A valid audit event submitted with correct auth returns 201 and is stored.",
            preconditions=[
                "Store initialized with in-memory SQLite",
                "AuditHandler wired with store",
                'Bearer token set to "test-token"',
            ],
            expected="HTTP 201 Created, empty response body, event retrievable from database",
            assertion_pseudocode=(
                'resp = POST("/api/v1/audit", valid_event, auth="test-token")\n'
                "ASSERT resp.status == 201\n"
                'ASSERT resp.body == ""\n'
                'row = store.query("SELECT * FROM events WHERE id = ?", event.id)\n'
                "ASSERT row.id == event.id\n"
                'ASSERT row.event_type == "run.start"\n'
                'ASSERT row.severity == "info"'
            ),
        ),
        TestCase(
            id="TS-01-2",
            requirement_id="01-REQ-1.2",
            kind="unit",
            description="A request with non-JSON content type is rejected.",
            preconditions=["Server running with valid config"],
            expected="HTTP 415 Unsupported Media Type",
            assertion_pseudocode=(
                'resp = POST("/api/v1/audit", "some text", content_type="text/plain", auth="test-token")\n'
                "ASSERT resp.status == 415"
            ),
        ),
        TestCase(
            id="TS-01-3",
            requirement_id="01-REQ-2.1",
            kind="unit",
            description="Events missing any required envelope field are rejected.",
            preconditions=["Validator function available"],
            expected="Validate returns a non-nil error for each omitted field",
            assertion_pseudocode=(
                "FOR EACH field IN [id, timestamp, run_id, event_type, severity, payload]:\n"
                "    event = valid_event()\n"
                "    event[field] = zero_value\n"
                "    err = validator.Validate(event)\n"
                "    ASSERT err != nil"
            ),
        ),
        TestCase(
            id="TS-01-4",
            requirement_id="01-REQ-2.2",
            kind="unit",
            description="Field format constraints are enforced (timestamp ISO 8601, severity enum, event_type dot-separated, payload is object).",
            preconditions=["Validator function available"],
            expected="Validate returns non-nil error for each invalid value",
            assertion_pseudocode=(
                'cases = [("timestamp", "not-a-date"), ("severity", "fatal"), ("event_type", "start")]\n'
                "FOR EACH (field, value) IN cases:\n"
                "    event = valid_event()\n"
                "    event[field] = value\n"
                "    err = validator.Validate(event)\n"
                "    ASSERT err != nil\n"
                "event_null_payload = valid_event()\n"
                "event_null_payload.payload = nil\n"
                "err = validator.Validate(event_null_payload)\n"
                "ASSERT err != nil"
            ),
        ),
        TestCase(
            id="TS-01-5",
            requirement_id="01-REQ-2.3",
            kind="unit",
            description="Events without optional fields (node_id, session_id, archetype) are accepted with defaults.",
            preconditions=["Store initialized, handler wired"],
            expected="HTTP 201, stored row has empty strings for the three optional fields",
            assertion_pseudocode=(
                "event = valid_event_without_optionals()\n"
                'resp = POST("/api/v1/audit", event, auth="test-token")\n'
                "ASSERT resp.status == 201\n"
                'row = store.query("SELECT node_id, session_id, archetype FROM events WHERE id = ?", event.id)\n'
                'ASSERT row.node_id == ""\n'
                'ASSERT row.session_id == ""\n'
                'ASSERT row.archetype == ""'
            ),
        ),
        TestCase(
            id="TS-01-6",
            requirement_id="01-REQ-3.1",
            kind="unit",
            description="Store initialization creates the events table and enables WAL mode.",
            preconditions=["Temporary directory for database file"],
            expected="Database file created, table `events` exists, WAL mode enabled",
            assertion_pseudocode=(
                's, err = store.New(tmpdir + "/test.db")\n'
                "ASSERT err == nil\n"
                'ASSERT file_exists(tmpdir + "/test.db")\n'
                "rows = s.db.Query(\"SELECT name FROM sqlite_master WHERE type='table' AND name='events'\")\n"
                "ASSERT rows.count == 1\n"
                'mode = s.db.QueryRow("PRAGMA journal_mode").Scan()\n'
                'ASSERT mode == "wal"'
            ),
        ),
        TestCase(
            id="TS-01-7",
            requirement_id="01-REQ-3.4",
            kind="unit",
            description="Store creates parent directories and uses configured path.",
            preconditions=["Temporary directory, subdirectory does not exist"],
            expected="Parent directories created, database file at specified path",
            assertion_pseudocode=(
                'path = tmpdir + "/sub/dir/audit.db"\n'
                "s, err = store.New(path)\n"
                "ASSERT err == nil\n"
                "ASSERT file_exists(path)"
            ),
        ),
        TestCase(
            id="TS-01-8",
            requirement_id="01-REQ-4.1",
            kind="unit",
            description="Requests without Authorization header receive 401.",
            preconditions=['Echo instance with auth middleware configured, token = "test-token"'],
            expected="HTTP 401 Unauthorized",
            assertion_pseudocode=(
                'resp = POST("/api/v1/audit", valid_event, auth=None)\n'
                "ASSERT resp.status == 401"
            ),
        ),
        TestCase(
            id="TS-01-9",
            requirement_id="01-REQ-4.3",
            kind="unit",
            description="Requests with incorrect Bearer token receive 401.",
            preconditions=['Echo instance with auth middleware configured, token = "test-token"'],
            expected="HTTP 401 Unauthorized",
            assertion_pseudocode=(
                'resp = POST("/api/v1/audit", valid_event, auth="wrong-token")\n'
                "ASSERT resp.status == 401"
            ),
        ),
        TestCase(
            id="TS-01-10",
            requirement_id="01-REQ-5.1",
            kind="unit",
            description="Liveness probe always returns 200.",
            preconditions=["Server running"],
            expected="HTTP 200 OK",
            assertion_pseudocode=(
                'resp = GET("/healthz")\n'
                "ASSERT resp.status == 200"
            ),
        ),
        TestCase(
            id="TS-01-11",
            requirement_id="01-REQ-5.2",
            kind="unit",
            description="Readiness probe returns 200 when database is accessible.",
            preconditions=["Server running with healthy SQLite database"],
            expected="HTTP 200 OK",
            assertion_pseudocode=(
                'resp = GET("/readyz")\n'
                "ASSERT resp.status == 200"
            ),
        ),
        TestCase(
            id="TS-01-12",
            requirement_id="01-REQ-5.3",
            kind="unit",
            description="Health endpoints respond without requiring Authorization header.",
            preconditions=["Server running with auth middleware active"],
            expected="Both return HTTP 200 (not 401)",
            assertion_pseudocode=(
                'resp1 = GET("/healthz", auth=None)\n'
                "ASSERT resp1.status == 200\n"
                'resp2 = GET("/readyz", auth=None)\n'
                "ASSERT resp2.status == 200"
            ),
        ),
        TestCase(
            id="TS-01-13",
            requirement_id="01-REQ-6.1",
            kind="unit",
            description="Configuration loads from TOML with correct defaults and overrides.",
            preconditions=["Temporary TOML file with partial config (only `auth.bearer_token` set)"],
            expected="All defaults applied correctly",
            assertion_pseudocode=(
                "cfg, err = config.Load(tmpfile_with_token_only)\n"
                "ASSERT err == nil\n"
                "ASSERT cfg.Server.Port == 8080\n"
                'ASSERT cfg.Server.BindAddress == "0.0.0.0"\n'
                'ASSERT cfg.Database.Path == "./data/audit.db"\n'
                "ASSERT cfg.Database.RetentionDays == 30\n"
                'ASSERT cfg.Auth.BearerToken == "my-token"\n'
                'ASSERT cfg.Logging.Level == "info"'
            ),
        ),
        TestCase(
            id="TS-01-14",
            requirement_id="01-REQ-6.2",
            kind="unit",
            description="Explicit TOML values override defaults.",
            preconditions=["TOML file with all fields set to non-default values"],
            expected="All fields match the overridden values",
            assertion_pseudocode=(
                "cfg, err = config.Load(custom_toml)\n"
                "ASSERT err == nil\n"
                "ASSERT cfg.Server.Port == 9090\n"
                'ASSERT cfg.Server.BindAddress == "127.0.0.1"\n'
                'ASSERT cfg.Database.Path == "/tmp/custom.db"\n'
                "ASSERT cfg.Database.RetentionDays == 7\n"
                'ASSERT cfg.Logging.Level == "debug"'
            ),
        ),
        TestCase(
            id="TS-01-15",
            requirement_id="01-REQ-7.1",
            kind="unit",
            description="Purge deletes events older than retention period and returns count.",
            preconditions=["Store with 3 events: one from 60 days ago, one from 15 days ago, one from today"],
            expected="Returns count = 1 (the 60-day-old event), 2 events remain",
            assertion_pseudocode=(
                "store.InsertEvent(ctx, event_60_days_old)\n"
                "store.InsertEvent(ctx, event_15_days_old)\n"
                "store.InsertEvent(ctx, event_today)\n"
                "count, err = store.PurgeOlderThan(ctx, now() - 30*day)\n"
                "ASSERT err == nil\n"
                "ASSERT count == 1\n"
                'remaining = store.query("SELECT COUNT(*) FROM events")\n'
                "ASSERT remaining == 2"
            ),
        ),
        TestCase(
            id="TS-01-16",
            requirement_id="01-REQ-9.3",
            kind="unit",
            description="HTTP requests produce structured log entries with required fields.",
            preconditions=["Logrus configured with JSON formatter and a test hook to capture entries"],
            expected="Log entry contains fields: method, path, status, duration",
            assertion_pseudocode=(
                "hook = test.NewLogHook()\n"
                "logrus.AddHook(hook)\n"
                'resp = POST("/api/v1/audit", valid_event, auth="test-token")\n'
                "entry = hook.LastEntry()\n"
                'ASSERT entry.Data["method"] == "POST"\n'
                'ASSERT entry.Data["path"] == "/api/v1/audit"\n'
                'ASSERT entry.Data["status"] == 201\n'
                'ASSERT entry.Data["duration"] != nil'
            ),
        ),
        TestCase(
            id="TS-01-17",
            requirement_id="01-REQ-10.1",
            kind="integration",
            description="Multiple concurrent inserts succeed without SQLITE_BUSY errors.",
            preconditions=["Store initialized with file-backed SQLite (WAL mode)"],
            expected="All 20 inserts succeed, 20 events in database",
            assertion_pseudocode=(
                "wg = WaitGroup()\n"
                "errors = []\n"
                "FOR i IN 1..20:\n"
                "    wg.Add(1)\n"
                "    GO func():\n"
                "        err = store.InsertEvent(ctx, unique_event(i))\n"
                "        IF err != nil: errors.append(err)\n"
                "        wg.Done()\n"
                "wg.Wait()\n"
                "ASSERT len(errors) == 0\n"
                'count = store.query("SELECT COUNT(*) FROM events")\n'
                "ASSERT count == 20"
            ),
        ),
    ]


# ── Edge case tests ──────────────────────────────────────────────────


def _edge_case_tests() -> list[EdgeCaseTest]:
    return [
        EdgeCaseTest(
            id="TS-01-E1",
            requirement_id="01-REQ-1.E1",
            kind="unit",
            description="POST with empty body is rejected.",
            preconditions=["Server running with auth"],
            expected="HTTP 400 Bad Request",
            assertion_pseudocode='resp = POST("/api/v1/audit", body="", auth="test-token")\nASSERT resp.status == 400',
        ),
        EdgeCaseTest(
            id="TS-01-E2",
            requirement_id="01-REQ-1.E2",
            kind="unit",
            description="Request body exceeding 1 MB is rejected.",
            preconditions=["Server running with body size limit configured"],
            expected="HTTP 413 Payload Too Large",
            assertion_pseudocode='large_body = "x" * (1024 * 1024 + 1)\nresp = POST("/api/v1/audit", body=large_body, auth="test-token")\nASSERT resp.status == 413',
        ),
        EdgeCaseTest(
            id="TS-01-E3",
            requirement_id="01-REQ-1.E3",
            kind="unit",
            description="Malformed JSON body is rejected.",
            preconditions=["Server running with auth"],
            expected="HTTP 400 Bad Request",
            assertion_pseudocode='resp = POST("/api/v1/audit", body="{invalid json", auth="test-token")\nASSERT resp.status == 400',
        ),
        EdgeCaseTest(
            id="TS-01-E4",
            requirement_id="01-REQ-2.E1",
            kind="unit",
            description="ISO 8601 timestamp without timezone offset is rejected.",
            preconditions=["Validator function available"],
            expected="Validation error",
            assertion_pseudocode='event = valid_event()\nevent.timestamp = "2026-04-27T10:00:00"\nerr = validator.Validate(event)\nASSERT err != nil',
        ),
        EdgeCaseTest(
            id="TS-01-E5",
            requirement_id="01-REQ-2.E2",
            kind="unit",
            description="Event with null payload is rejected.",
            preconditions=["Validator function available"],
            expected="Validation error",
            assertion_pseudocode="event = valid_event()\nevent.payload = null\nerr = validator.Validate(event)\nASSERT err != nil",
        ),
        EdgeCaseTest(
            id="TS-01-E6",
            requirement_id="01-REQ-2.E3",
            kind="unit",
            description="Event type missing dot separator is rejected.",
            preconditions=["Validator function available"],
            expected="Validation error",
            assertion_pseudocode='event = valid_event()\nevent.event_type = "start"\nerr = validator.Validate(event)\nASSERT err != nil',
        ),
        EdgeCaseTest(
            id="TS-01-E7",
            requirement_id="01-REQ-3.E1",
            kind="unit",
            description="Inserting an event with a duplicate ID returns conflict.",
            preconditions=["Store with one event already inserted"],
            expected="InsertEvent returns error; HTTP handler returns 409 Conflict",
            assertion_pseudocode='store.InsertEvent(ctx, event)\nerr = store.InsertEvent(ctx, event_same_id)\nASSERT err != nil\nresp = POST("/api/v1/audit", event_same_id_json, auth="test-token")\nASSERT resp.status == 409',
        ),
        EdgeCaseTest(
            id="TS-01-E8",
            requirement_id="01-REQ-3.E2",
            kind="unit",
            description="Store returns error when database path is not writable.",
            preconditions=["Path to a read-only directory"],
            expected="Returns non-nil error",
            assertion_pseudocode='_, err = store.New("/readonly/dir/audit.db")\nASSERT err != nil',
        ),
        EdgeCaseTest(
            id="TS-01-E9",
            requirement_id="01-REQ-4.E1",
            kind="unit",
            description='Extra whitespace between "Bearer" and token is handled.',
            preconditions=['Auth middleware configured with token "test-token"'],
            expected="Request proceeds (not rejected as 401)",
            assertion_pseudocode='resp = POST("/api/v1/audit", valid_event, auth_header="Bearer   test-token")\nASSERT resp.status != 401',
        ),
        EdgeCaseTest(
            id="TS-01-E10",
            requirement_id="01-REQ-4.5",
            kind="unit",
            description="Config without bearer_token fails validation.",
            preconditions=["TOML file with no `auth.bearer_token`"],
            expected="Returns non-nil error",
            assertion_pseudocode="_, err = config.Load(toml_without_token)\nASSERT err != nil",
        ),
        EdgeCaseTest(
            id="TS-01-E11",
            requirement_id="01-REQ-5.E1",
            kind="unit",
            description="Readiness probe returns 503 when database is inaccessible.",
            preconditions=["HealthHandler with a store whose database has been closed"],
            expected="HTTP 503 Service Unavailable",
            assertion_pseudocode='store.Close()\nresp = GET("/readyz")\nASSERT resp.status == 503',
        ),
        EdgeCaseTest(
            id="TS-01-E12",
            requirement_id="01-REQ-6.3",
            kind="unit",
            description="Missing config file returns error.",
            preconditions=["Path to nonexistent file"],
            expected="Returns non-nil error",
            assertion_pseudocode='_, err = config.Load("/nonexistent/config.toml")\nASSERT err != nil',
        ),
        EdgeCaseTest(
            id="TS-01-E13",
            requirement_id="01-REQ-6.4",
            kind="unit",
            description="Syntactically invalid TOML returns error.",
            preconditions=["File with invalid TOML content"],
            expected="Returns non-nil error",
            assertion_pseudocode='write_file(tmpfile, "[invalid toml =")\n_, err = config.Load(tmpfile)\nASSERT err != nil',
        ),
        EdgeCaseTest(
            id="TS-01-E14",
            requirement_id="01-REQ-6.E1",
            kind="unit",
            description="Retention days <= 0 falls back to 30.",
            preconditions=["TOML file with `database.retention_days = 0`"],
            expected="cfg.Database.RetentionDays == 30",
            assertion_pseudocode="cfg, err = config.Load(toml_zero_retention)\nASSERT err == nil\nASSERT cfg.Database.RetentionDays == 30",
        ),
        EdgeCaseTest(
            id="TS-01-E15",
            requirement_id="01-REQ-6.E2",
            kind="unit",
            description="Port outside 1-65535 returns error.",
            preconditions=["TOML file with `server.port = 70000`"],
            expected="Returns non-nil error",
            assertion_pseudocode="_, err = config.Load(toml_port_70000)\nASSERT err != nil",
        ),
        EdgeCaseTest(
            id="TS-01-E16",
            requirement_id="01-REQ-7.E1",
            kind="unit",
            description="Retention purge gracefully handles database errors.",
            preconditions=["Store whose database has been closed"],
            expected="Returns non-nil error (does not panic)",
            assertion_pseudocode="store.Close()\n_, err = store.PurgeOlderThan(ctx, cutoff)\nASSERT err != nil",
        ),
        EdgeCaseTest(
            id="TS-01-E17",
            requirement_id="01-REQ-9.E1",
            kind="unit",
            description="Unrecognized log level falls back to info.",
            preconditions=['TOML file with `logging.level = "verbose"` (invalid)'],
            expected='cfg.Logging.Level == "info"',
            assertion_pseudocode='cfg, err = config.Load(toml_bad_level)\nASSERT err == nil\nASSERT cfg.Logging.Level == "info"',
        ),
        EdgeCaseTest(
            id="TS-01-E18",
            requirement_id="01-REQ-10.E1",
            kind="unit",
            description="Exhausted busy timeout results in 503 response.",
            preconditions=["Store configured with very short busy timeout", "Database locked by another connection"],
            expected="Returns error; handler returns HTTP 503",
            assertion_pseudocode="lock_database(store)\nerr = store.InsertEvent(ctx, event)\nASSERT err != nil",
        ),
    ]


# ── Property tests ───────────────────────────────────────────────────


def _property_tests() -> list[PropertyTest]:
    return [
        PropertyTest(
            id="TS-01-P1",
            property_id="01-PROP-1",
            validates=["01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4"],
            description="Validation accepts iff all required fields are present and well-formed.",
            for_any_strategy="Randomly generated AuditEvent structs with fields individually fuzzed",
            invariant_check=(
                "`Validate(event)` returns nil iff `id` is non-empty, `timestamp` is valid "
                "ISO 8601 with timezone, `run_id` is non-empty, `event_type` contains a dot, "
                "`severity` is in {info, warning, error, critical}, and `payload` is a "
                "non-null JSON object."
            ),
        ),
        PropertyTest(
            id="TS-01-P2",
            property_id="01-PROP-2",
            validates=["01-REQ-1.1", "01-REQ-3.1"],
            description="Every stored event is retrievable with identical field values.",
            for_any_strategy="Valid AuditEvent structs with randomized field values (valid formats)",
            invariant_check=(
                "After `InsertEvent(event)`, querying by `id` yields a row whose "
                "envelope metadata fields and payload match the original event exactly."
            ),
        ),
        PropertyTest(
            id="TS-01-P3",
            property_id="01-PROP-3",
            validates=["01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3"],
            description="Only requests with the correct Bearer token pass auth.",
            for_any_strategy="Random strings as token values",
            invariant_check=(
                "The auth middleware returns 401 for any token that does not "
                "match the configured token, and passes through for exact matches."
            ),
        ),
        PropertyTest(
            id="TS-01-P4",
            property_id="01-PROP-4",
            validates=["01-REQ-3.E1"],
            description="Duplicate IDs are always rejected without modifying existing data.",
            for_any_strategy="Valid event pairs where the second has the same `id` but different payload",
            invariant_check="Second insert fails. Original event's payload is unchanged.",
        ),
        PropertyTest(
            id="TS-01-P5",
            property_id="01-PROP-5",
            validates=["01-REQ-7.1", "01-REQ-7.3"],
            description="After purge, only events within the retention window survive.",
            for_any_strategy="Set of events with timestamps uniformly distributed across a 90-day range",
            invariant_check=(
                "After `PurgeOlderThan(cutoff)`, all remaining events have "
                "`timestamp >= cutoff` and no event with `timestamp < cutoff` remains."
            ),
        ),
        PropertyTest(
            id="TS-01-P6",
            property_id="01-PROP-6",
            validates=["01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.3"],
            description="Health probes never return 401, regardless of auth header state.",
            for_any_strategy="Random Authorization header values (including missing, empty, malformed, valid, invalid)",
            invariant_check="`/healthz` returns 200 and `/readyz` returns 200 (when DB is up) regardless of auth.",
        ),
        PropertyTest(
            id="TS-01-P7",
            property_id="01-PROP-7",
            validates=[
                "01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4",
                "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2",
            ],
            description="Config loading succeeds iff TOML is valid and required fields are present.",
            for_any_strategy="Randomly generated TOML content (some valid, some with missing token, some with invalid syntax, some with bad port ranges)",
            invariant_check=(
                "`Load(path)` returns nil error iff the file is valid TOML with "
                "non-empty `auth.bearer_token` and port in 1–65535 (or absent, defaulting to 8080)."
            ),
        ),
        PropertyTest(
            id="TS-01-P8",
            property_id="01-PROP-8",
            validates=["01-REQ-10.1", "01-REQ-10.2"],
            description="N concurrent inserts with unique IDs all succeed.",
            for_any_strategy="N in [2, 50], each event has a unique ID",
            invariant_check="All N inserts succeed. Database contains exactly N rows.",
        ),
        PropertyTest(
            id="TS-01-P9",
            property_id="01-PROP-9",
            validates=["01-REQ-8.1", "01-REQ-8.2"],
            description="In-flight requests complete before shutdown, and the database is closed.",
            for_any_strategy="This is a deterministic scenario test rather than a generated property test",
            invariant_check=(
                "After SIGTERM, pending requests either complete or are terminated "
                "within 15s. The database connection is closed."
            ),
        ),
    ]


# ── Smoke tests ──────────────────────────────────────────────────────


def _smoke_tests() -> list[SmokeTest]:
    return [
        SmokeTest(
            id="TS-01-SMOKE-1",
            execution_path_id="01-PATH-1",
            description="A valid event sent via HTTP POST is stored in the database and retrievable.",
            trigger="HTTP POST to `/api/v1/audit` with valid event and correct Bearer token.",
            real_components=["Store", "Echo server (httptest)", "Auth middleware", "Validator", "Handler"],
            mockable=[],
            expected_effects=[
                "HTTP 201 response",
                "Event row present in SQLite with matching field values",
                "`received_at` column populated with server-side timestamp",
            ],
        ),
        SmokeTest(
            id="TS-01-SMOKE-2",
            execution_path_id="01-PATH-2",
            description="Readiness probe successfully queries the database.",
            trigger="HTTP GET to `/readyz`.",
            real_components=["Store", "Echo server (httptest)", "Health handler"],
            mockable=[],
            expected_effects=["HTTP 200 response"],
        ),
        SmokeTest(
            id="TS-01-SMOKE-3",
            execution_path_id="01-PATH-3",
            description="Retention process deletes expired events and preserves recent ones.",
            trigger="Start retention goroutine, wait for one cycle.",
            real_components=["Store", "Retention process"],
            mockable=[],
            expected_effects=[
                "Events older than retention period are deleted",
                "Recent events remain",
            ],
        ),
        SmokeTest(
            id="TS-01-SMOKE-4",
            execution_path_id="01-PATH-5",
            description="Configuration file is loaded and used to wire a functional server.",
            trigger="Load config, create store, create server, send health check.",
            real_components=["Config loader", "Store", "Echo server (httptest)"],
            mockable=[],
            expected_effects=[
                "Server starts without error",
                "`/healthz` returns 200",
            ],
        ),
    ]


# ── Task groups ──────────────────────────────────────────────────────


def _task_groups() -> list[TaskGroup]:
    # Task group 1: Write failing spec tests
    g1 = TaskGroup(
        id=1,
        kind=TaskGroupKind.TESTS,
        title="Write failing spec tests",
        verification=VerificationSubtask(
            id="1.V",
            checks=[
                "All spec tests exist and are syntactically valid: `go build ./...`",
                "All spec tests FAIL (red) — no implementation yet: `go test ./... 2>&1 | grep FAIL`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="1.1", title="Initialize Go module and project structure", details=[
            "Run `go mod init github.com/agent-fox/audit-hub`",
            "Create directory structure for all internal packages",
            "Add initial dependencies: echo/v4, modernc.org/sqlite, BurntSushi/toml, logrus, rapid",
        ]),
        Subtask(id="1.2", title="Write config tests", details=[
            "internal/config/config_test.go",
        ], test_spec_refs=[
            "TS-01-13", "TS-01-14", "TS-01-E10", "TS-01-E12", "TS-01-E13",
            "TS-01-E14", "TS-01-E15", "TS-01-E17", "TS-01-P7",
        ]),
        Subtask(id="1.3", title="Write validator tests", details=[
            "internal/validator/validator_test.go",
        ], test_spec_refs=[
            "TS-01-3", "TS-01-4", "TS-01-E4", "TS-01-E5", "TS-01-E6", "TS-01-P1",
        ]),
        Subtask(id="1.4", title="Write store tests", details=[
            "internal/store/store_test.go",
        ], test_spec_refs=[
            "TS-01-6", "TS-01-7", "TS-01-15", "TS-01-17", "TS-01-E7", "TS-01-E8",
            "TS-01-E16", "TS-01-E18", "TS-01-P2", "TS-01-P4", "TS-01-P5", "TS-01-P8",
        ]),
        Subtask(id="1.5", title="Write middleware, handler, health, and server tests", details=[
            "internal/middleware/auth_test.go",
            "internal/handler/audit_test.go",
            "internal/health/health_test.go",
            "internal/server/server_test.go",
        ], test_spec_refs=[
            "TS-01-1", "TS-01-2", "TS-01-5", "TS-01-8", "TS-01-9", "TS-01-10",
            "TS-01-11", "TS-01-12", "TS-01-16", "TS-01-E1", "TS-01-E2", "TS-01-E3",
            "TS-01-E9", "TS-01-E11", "TS-01-P3", "TS-01-P6",
        ]),
        Subtask(id="1.6", title="Write integration smoke tests", details=[
            "internal/integration_test.go",
        ], test_spec_refs=[
            "TS-01-SMOKE-1", "TS-01-SMOKE-2", "TS-01-SMOKE-3", "TS-01-SMOKE-4", "TS-01-P9",
        ]),
    ]:
        g1 = add_subtask(g1, sub)

    # Task group 2: Implement data models and configuration
    g2 = TaskGroup(
        id=2,
        kind=TaskGroupKind.STANDARD,
        title="Implement data models and configuration",
        verification=VerificationSubtask(
            id="2.V",
            checks=[
                "Config tests pass: `go test -v ./internal/config/...`",
                "All existing tests still pass: `go test ./...`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="2.1", title="Implement AuditEvent model", requirement_refs=["01-REQ-3.1"], details=[
            "Create `internal/model/event.go` with `AuditEvent` struct",
            "JSON tags for deserialization from request body",
            "`json.RawMessage` for payload field",
        ]),
        Subtask(id="2.2", title="Implement Config model and loader", requirement_refs=[
            "01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4",
            "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2", "01-REQ-9.E1",
        ], details=[
            "Create `internal/config/config.go`",
            "Load(path string) (*Config, error)",
            "Apply defaults and validate",
        ]),
    ]:
        g2 = add_subtask(g2, sub)

    # Task group 3: Implement SQLite store
    g3 = TaskGroup(
        id=3,
        kind=TaskGroupKind.STANDARD,
        title="Implement SQLite store",
        verification=VerificationSubtask(
            id="3.V",
            checks=[
                "Store tests pass: `go test -v ./internal/store/...`",
                "All existing tests still pass: `go test ./...`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="3.1", title="Implement store initialization", requirement_refs=[
            "01-REQ-3.1", "01-REQ-3.2", "01-REQ-3.3", "01-REQ-3.4",
        ], details=[
            "Create `internal/store/store.go`",
            "New(dbPath string) (*Store, error)",
            "WAL mode, table creation, indexes",
        ]),
        Subtask(id="3.2", title="Implement event insertion", requirement_refs=[
            "01-REQ-1.1", "01-REQ-3.E1", "01-REQ-10.1", "01-REQ-10.2",
        ], details=[
            "InsertEvent(ctx, event) error",
            "Handle UNIQUE constraint violation",
            "Configure busy timeout",
        ]),
        Subtask(id="3.3", title="Implement health ping and retention purge", requirement_refs=[
            "01-REQ-5.2", "01-REQ-7.1", "01-REQ-7.3",
        ], details=[
            "Ping(ctx) error",
            "PurgeOlderThan(ctx, cutoff) (int64, error)",
            "Close() error",
        ]),
    ]:
        g3 = add_subtask(g3, sub)

    # Task group 4: Implement validator and auth middleware
    g4 = TaskGroup(
        id=4,
        kind=TaskGroupKind.STANDARD,
        title="Implement validator and auth middleware",
        verification=VerificationSubtask(
            id="4.V",
            checks=[
                "Validator tests pass: `go test -v ./internal/validator/...`",
                "Middleware tests pass: `go test -v ./internal/middleware/...`",
                "All existing tests still pass: `go test ./...`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="4.1", title="Implement event validator", requirement_refs=[
            "01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4",
            "01-REQ-2.E1", "01-REQ-2.E2", "01-REQ-2.E3",
        ], details=[
            "Create `internal/validator/validator.go`",
            "Validate(event model.AuditEvent) error",
        ]),
        Subtask(id="4.2", title="Implement Bearer auth middleware", requirement_refs=[
            "01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3", "01-REQ-4.E1",
        ], details=[
            "Create `internal/middleware/auth.go`",
            "BearerAuth(token string) echo.MiddlewareFunc",
        ]),
    ]:
        g4 = add_subtask(g4, sub)

    # Task group 5: Implement HTTP handlers and server wiring
    g5 = TaskGroup(
        id=5,
        kind=TaskGroupKind.STANDARD,
        title="Implement HTTP handlers and server wiring",
        verification=VerificationSubtask(
            id="5.V",
            checks=[
                "Handler tests pass: `go test -v ./internal/handler/...`",
                "Health tests pass: `go test -v ./internal/health/...`",
                "Server tests pass: `go test -v ./internal/server/...`",
                "All existing tests still pass: `go test ./...`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="5.1", title="Implement audit ingest handler", requirement_refs=[
            "01-REQ-1.1", "01-REQ-1.2", "01-REQ-1.E1", "01-REQ-1.E2", "01-REQ-1.E3",
        ], details=[
            "Create `internal/handler/audit.go`",
            "AuditHandler.Ingest(c echo.Context) error",
        ]),
        Subtask(id="5.2", title="Implement health handlers", requirement_refs=[
            "01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.E1",
        ], details=[
            "Create `internal/health/health.go`",
            "Healthz(c) error",
            "Readyz(c) error",
        ]),
        Subtask(id="5.3", title="Implement server and route registration", requirement_refs=[
            "01-REQ-1.3", "01-REQ-1.4", "01-REQ-5.3", "01-REQ-9.4",
        ], details=[
            "Create `internal/server/server.go`",
            "New(cfg, store) *Server",
            "Start() error, Shutdown(ctx) error",
        ]),
    ]:
        g5 = add_subtask(g5, sub)

    # Task group 6: Implement retention and application entry point
    g6 = TaskGroup(
        id=6,
        kind=TaskGroupKind.STANDARD,
        title="Implement retention and application entry point",
        verification=VerificationSubtask(
            id="6.V",
            checks=[
                "Integration smoke tests pass: `go test -v -run Smoke ./internal/...`",
                "Graceful shutdown test passes: `go test -v -run Shutdown ./internal/...`",
                "All existing tests still pass: `go test ./...`",
                "No linter warnings introduced: `go vet ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="6.1", title="Implement retention background process", requirement_refs=[
            "01-REQ-7.1", "01-REQ-7.2", "01-REQ-7.3", "01-REQ-7.4", "01-REQ-7.E1",
        ], details=[
            "Create `internal/retention/retention.go`",
            "StartRetention(ctx, store, interval, retentionDays)",
        ]),
        Subtask(id="6.2", title="Implement main entry point", requirement_refs=[
            "01-REQ-8.1", "01-REQ-8.2", "01-REQ-8.E1",
            "01-REQ-9.1", "01-REQ-9.2", "01-REQ-9.3",
        ], details=[
            "Create `cmd/audit-hub/main.go`",
            "Parse --config flag, load config, wire dependencies, handle signals",
        ]),
        Subtask(id="6.3", title="Create example configuration file", details=[
            "Create `config.example.toml` with all fields documented",
        ]),
    ]:
        g6 = add_subtask(g6, sub)

    # Task group 7: Checkpoint — Core service complete
    g7 = TaskGroup(
        id=7,
        kind=TaskGroupKind.CHECKPOINT,
        title="Checkpoint — Core service complete",
        verification=VerificationSubtask(
            id="7.V",
            checks=[
                "Ensure all tests pass: `go test -v -count=1 ./...`",
                "Ask the user if questions arise",
                "Create or update README.md with build/run/config instructions",
            ],
        ),
    )

    # Task group 8: Wiring verification
    g8 = TaskGroup(
        id=8,
        kind=TaskGroupKind.WIRING_VERIFICATION,
        title="Wiring verification",
        verification=VerificationSubtask(
            id="8.V",
            checks=[
                "All smoke tests pass",
                "No unjustified stubs remain in touched files",
                "All execution paths from design.md are live (traceable in code)",
                "All cross-spec entry points are called from production code",
                "All existing tests still pass: `go test -v -count=1 ./...`",
            ],
        ),
    )
    for sub in [
        Subtask(id="8.1", title="Trace every execution path from design.md end-to-end", details=[
            "For each of the 5 execution paths, verify the entry point actually calls the next function in the chain",
        ]),
        Subtask(id="8.2", title="Verify return values propagate correctly", details=[
            "For every function that returns data consumed by a caller, confirm the caller receives and uses the return value",
        ]),
        Subtask(id="8.3", title="Run the integration smoke tests", details=[
            "`go test -v -run Smoke ./internal/...`",
        ], test_spec_refs=[
            "TS-01-SMOKE-1", "TS-01-SMOKE-2", "TS-01-SMOKE-3", "TS-01-SMOKE-4",
        ]),
        Subtask(id="8.4", title="Stub / dead-code audit", details=[
            "Search for return nil, TODO, stub, NotImplementedError, empty function bodies",
        ]),
        Subtask(id="8.5", title="Cross-spec entry point verification", details=[
            "Verify `cmd/audit-hub/main.go` is buildable: `go build ./cmd/audit-hub/`",
        ]),
    ]:
        g8 = add_subtask(g8, sub)

    return [g1, g2, g3, g4, g5, g6, g7, g8]


# ── Traceability ─────────────────────────────────────────────────────


def _traceability() -> list[TraceabilityEntry]:
    return [
        TraceabilityEntry(requirement_id="01-REQ-1.1", test_spec_id="TS-01-1", task_id="5.1", test_path="TestIngestValidEvent"),
        TraceabilityEntry(requirement_id="01-REQ-1.2", test_spec_id="TS-01-2", task_id="5.1", test_path="TestIngestWrongContentType"),
        TraceabilityEntry(requirement_id="01-REQ-1.3", test_spec_id="TS-01-13", task_id="5.3", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-1.4", test_spec_id="TS-01-13", task_id="5.3", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-1.E1", test_spec_id="TS-01-E1", task_id="5.1", test_path="TestIngestEmptyBody"),
        TraceabilityEntry(requirement_id="01-REQ-1.E2", test_spec_id="TS-01-E2", task_id="5.1", test_path="TestIngestOversizedBody"),
        TraceabilityEntry(requirement_id="01-REQ-1.E3", test_spec_id="TS-01-E3", task_id="5.1", test_path="TestIngestInvalidJSON"),
        TraceabilityEntry(requirement_id="01-REQ-2.1", test_spec_id="TS-01-3", task_id="4.1", test_path="TestValidateMissingFields"),
        TraceabilityEntry(requirement_id="01-REQ-2.2", test_spec_id="TS-01-4", task_id="4.1", test_path="TestValidateFieldFormats"),
        TraceabilityEntry(requirement_id="01-REQ-2.3", test_spec_id="TS-01-5", task_id="4.1", test_path="TestOptionalFieldsDefault"),
        TraceabilityEntry(requirement_id="01-REQ-2.4", test_spec_id="TS-01-4", task_id="4.1", test_path="TestValidateFieldFormats"),
        TraceabilityEntry(requirement_id="01-REQ-2.E1", test_spec_id="TS-01-E4", task_id="4.1", test_path="TestTimestampNoTimezone"),
        TraceabilityEntry(requirement_id="01-REQ-2.E2", test_spec_id="TS-01-E5", task_id="4.1", test_path="TestNullPayload"),
        TraceabilityEntry(requirement_id="01-REQ-2.E3", test_spec_id="TS-01-E6", task_id="4.1", test_path="TestEventTypeNoDot"),
        TraceabilityEntry(requirement_id="01-REQ-3.1", test_spec_id="TS-01-6", task_id="3.1", test_path="TestStoreCreatesTable"),
        TraceabilityEntry(requirement_id="01-REQ-3.2", test_spec_id="TS-01-6", task_id="3.1", test_path="TestStoreWALMode"),
        TraceabilityEntry(requirement_id="01-REQ-3.3", test_spec_id="TS-01-6", task_id="3.1", test_path="TestStoreAutoCreateDB"),
        TraceabilityEntry(requirement_id="01-REQ-3.3", test_spec_id="TS-01-7", task_id="3.1", test_path="TestStoreAutoCreateDB"),
        TraceabilityEntry(requirement_id="01-REQ-3.4", test_spec_id="TS-01-7", task_id="3.1", test_path="TestStoreCreatesParentDirs"),
        TraceabilityEntry(requirement_id="01-REQ-3.E1", test_spec_id="TS-01-E7", task_id="3.2", test_path="TestDuplicateEventID"),
        TraceabilityEntry(requirement_id="01-REQ-3.E2", test_spec_id="TS-01-E8", task_id="3.1", test_path="TestStoreOpenFailure"),
        TraceabilityEntry(requirement_id="01-REQ-4.1", test_spec_id="TS-01-8", task_id="4.2", test_path="TestAuthMissingHeader"),
        TraceabilityEntry(requirement_id="01-REQ-4.2", test_spec_id="TS-01-8", task_id="4.2", test_path="TestAuthMissingHeader"),
        TraceabilityEntry(requirement_id="01-REQ-4.3", test_spec_id="TS-01-9", task_id="4.2", test_path="TestAuthWrongToken"),
        TraceabilityEntry(requirement_id="01-REQ-4.4", test_spec_id="TS-01-13", task_id="2.2", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-4.5", test_spec_id="TS-01-E10", task_id="2.2", test_path="TestConfigMissingToken"),
        TraceabilityEntry(requirement_id="01-REQ-4.E1", test_spec_id="TS-01-E9", task_id="4.2", test_path="TestAuthExtraWhitespace"),
        TraceabilityEntry(requirement_id="01-REQ-5.1", test_spec_id="TS-01-10", task_id="5.2", test_path="TestHealthz"),
        TraceabilityEntry(requirement_id="01-REQ-5.2", test_spec_id="TS-01-11", task_id="5.2", test_path="TestReadyzHealthy"),
        TraceabilityEntry(requirement_id="01-REQ-5.3", test_spec_id="TS-01-12", task_id="5.3", test_path="TestHealthSkipsAuth"),
        TraceabilityEntry(requirement_id="01-REQ-5.E1", test_spec_id="TS-01-E11", task_id="5.2", test_path="TestReadyzDBDown"),
        TraceabilityEntry(requirement_id="01-REQ-6.1", test_spec_id="TS-01-13", task_id="2.2", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-6.2", test_spec_id="TS-01-13", task_id="2.2", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-6.2", test_spec_id="TS-01-14", task_id="2.2", test_path="TestConfigOverrides"),
        TraceabilityEntry(requirement_id="01-REQ-6.3", test_spec_id="TS-01-E12", task_id="2.2", test_path="TestConfigFileNotFound"),
        TraceabilityEntry(requirement_id="01-REQ-6.4", test_spec_id="TS-01-E13", task_id="2.2", test_path="TestConfigInvalidTOML"),
        TraceabilityEntry(requirement_id="01-REQ-6.E1", test_spec_id="TS-01-E14", task_id="2.2", test_path="TestRetentionDaysZero"),
        TraceabilityEntry(requirement_id="01-REQ-6.E2", test_spec_id="TS-01-E15", task_id="2.2", test_path="TestPortOutOfRange"),
        TraceabilityEntry(requirement_id="01-REQ-7.1", test_spec_id="TS-01-15", task_id="6.1", test_path="TestRetentionPurge"),
        TraceabilityEntry(requirement_id="01-REQ-7.2", test_spec_id="TS-01-SMOKE-3", task_id="6.1", test_path="TestSmokeRetentionCycle"),
        TraceabilityEntry(requirement_id="01-REQ-7.3", test_spec_id="TS-01-15", task_id="3.3", test_path="TestRetentionPurge"),
        TraceabilityEntry(requirement_id="01-REQ-7.4", test_spec_id="TS-01-13", task_id="2.2", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-7.E1", test_spec_id="TS-01-E16", task_id="6.1", test_path="TestRetentionErrorRecovery"),
        TraceabilityEntry(requirement_id="01-REQ-8.1", test_spec_id="TS-01-P9", task_id="6.2", test_path="TestGracefulShutdown"),
        TraceabilityEntry(requirement_id="01-REQ-8.2", test_spec_id="TS-01-P9", task_id="6.2", test_path="TestGracefulShutdown"),
        TraceabilityEntry(requirement_id="01-REQ-8.E1", test_spec_id="TS-01-P9", task_id="6.2", test_path="TestDoubleSignalExit"),
        TraceabilityEntry(requirement_id="01-REQ-9.1", test_spec_id="TS-01-16", task_id="6.2", test_path="TestJSONLogging"),
        TraceabilityEntry(requirement_id="01-REQ-9.2", test_spec_id="TS-01-13", task_id="6.2", test_path="TestConfigDefaults"),
        TraceabilityEntry(requirement_id="01-REQ-9.3", test_spec_id="TS-01-16", task_id="6.2", test_path="TestStartupLog"),
        TraceabilityEntry(requirement_id="01-REQ-9.4", test_spec_id="TS-01-16", task_id="5.3", test_path="TestRequestLogging"),
        TraceabilityEntry(requirement_id="01-REQ-9.E1", test_spec_id="TS-01-E17", task_id="2.2", test_path="TestInvalidLogLevel"),
        TraceabilityEntry(requirement_id="01-REQ-10.1", test_spec_id="TS-01-17", task_id="3.1", test_path="TestConcurrentWrites"),
        TraceabilityEntry(requirement_id="01-REQ-10.2", test_spec_id="TS-01-E18", task_id="3.2", test_path="TestBusyTimeout"),
        TraceabilityEntry(requirement_id="01-REQ-10.E1", test_spec_id="TS-01-E18", task_id="3.2", test_path="TestBusyTimeoutExhausted"),
    ]


# ── Assembly ─────────────────────────────────────────────────────────


def build_spec() -> Spec:
    """Build the complete Audit Hub specification programmatically."""
    spec = create_spec("01", "audit_hub")

    # ── PRD ──────────────────────────────────────────────────────
    prd = PRDDocument(
        frontmatter=PRDFrontmatter(
            spec_id="01",
            spec_name="audit_hub",
            title="Audit Hub",
            status=Status.DRAFT,
            source=".agent-fox/specs/prd.md",
        ),
        body=PRD_BODY,
    )

    # ── Requirements ─────────────────────────────────────────────
    req = spec.requirements
    req = req.model_copy(update={
        "introduction": (
            "Audit Hub is a minimalistic Go-based HTTP service that ingests "
            "structured audit events from agent-fox instances, validates them "
            "against a defined envelope schema, and persists them in an "
            "embedded SQLite database. The service is designed for "
            "single-instance Kubernetes deployment and exposes standard "
            "health/readiness probes."
        ),
    })

    for term, definition in GLOSSARY.items():
        req = set_glossary_entry(req, term, definition)

    for builder in [
        _build_req1, _build_req2, _build_req3, _build_req4, _build_req5,
        _build_req6, _build_req7, _build_req8, _build_req9, _build_req10,
    ]:
        req = add_requirement(req, builder())

    for prop in _correctness_properties():
        req = add_correctness_property(req, prop)

    for path in _execution_paths():
        req = add_execution_path(req, path)

    for entry in _error_handling():
        req = add_error_handling(req, entry)

    # ── Test spec ────────────────────────────────────────────────
    ts = spec.test_spec

    for tc in _test_cases():
        ts = add_test_case(ts, tc)

    for et in _edge_case_tests():
        ts = add_edge_case_test(ts, et)

    for pt in _property_tests():
        ts = add_property_test(ts, pt)

    for st in _smoke_tests():
        ts = add_smoke_test(ts, st)

    all_req_ids = []
    for r in req.requirements:
        for c in r.acceptance_criteria:
            all_req_ids.append(c.id)
        for c in r.edge_cases:
            all_req_ids.append(c.id)

    ts = ts.model_copy(update={
        "coverage": Coverage(
            requirements_covered=all_req_ids,
            properties_covered=[p.id for p in req.correctness_properties],
            paths_covered=[p.id for p in req.execution_paths],
            gaps=[],
        ),
    })

    # ── Tasks ────────────────────────────────────────────────────
    tasks = spec.tasks
    tasks = tasks.model_copy(update={
        "test_commands": TestCommands(
            spec_tests="go test ./...",
            all_tests="go test -v -count=1 ./...",
            linter="go vet ./...",
        ),
    })

    for group in _task_groups():
        tasks = add_task_group(tasks, group)

    for entry in _traceability():
        tasks = add_traceability_entry(tasks, entry)

    # ── Assemble ─────────────────────────────────────────────────
    return Spec(
        prd=prd,
        requirements=req,
        test_spec=ts,
        tasks=tasks,
        architecture=ARCHITECTURE_CONTENT,
    )


def main() -> None:
    spec = build_spec()

    # Write to disk
    out_dir = Path(__file__).resolve().parent / "01_audit_hub_python"
    out_dir.mkdir(exist_ok=True)
    save(spec, out_dir)
    print(f"Spec written to {out_dir}")

    # Print summary statistics
    req = spec.requirements
    ts = spec.test_spec
    tasks = spec.tasks

    print(f"\nSpec: {spec.prd.frontmatter.spec_id} — {spec.prd.frontmatter.title}")
    print(f"  Requirements:          {len(req.requirements)}")
    print(f"  Acceptance criteria:   {sum(len(r.acceptance_criteria) for r in req.requirements)}")
    print(f"  Edge case criteria:    {sum(len(r.edge_cases) for r in req.requirements)}")
    print(f"  Glossary terms:        {len(req.glossary)}")
    print(f"  Correctness properties:{len(req.correctness_properties)}")
    print(f"  Execution paths:       {len(req.execution_paths)}")
    print(f"  Error handling entries: {len(req.error_handling)}")
    print(f"  Test cases:            {len(ts.test_cases)}")
    print(f"  Edge case tests:       {len(ts.edge_case_tests)}")
    print(f"  Property tests:        {len(ts.property_tests)}")
    print(f"  Smoke tests:           {len(ts.smoke_tests)}")
    print(f"  Task groups:           {len(tasks.task_groups)}")
    print(f"  Traceability entries:  {len(tasks.traceability)}")


if __name__ == "__main__":
    main()
