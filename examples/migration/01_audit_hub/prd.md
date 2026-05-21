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
