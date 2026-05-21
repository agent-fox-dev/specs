# Requirements Document

## Introduction

Audit Hub is a minimalistic Go-based HTTP service that ingests structured audit
events from agent-fox instances, validates them against a defined envelope
schema, and persists them in an embedded SQLite database. The service is
designed for single-instance Kubernetes deployment and exposes standard
health/readiness probes.

## Glossary

| Term | Definition |
|------|------------|
| Audit event | A structured JSON object conforming to the envelope schema, representing a single observable action in the agent-fox system |
| Envelope schema | The fixed set of top-level fields (`id`, `timestamp`, `run_id`, `event_type`, `node_id`, `session_id`, `archetype`, `severity`, `payload`) that every audit event must contain |
| Bearer token | An opaque authentication credential sent in the `Authorization` header as `Bearer <token>` |
| WAL mode | SQLite Write-Ahead Logging mode, which allows concurrent readers and a single writer without blocking |
| Liveness probe | A Kubernetes health check that verifies the process is running (`/healthz`) |
| Readiness probe | A Kubernetes health check that verifies the service can accept traffic (`/readyz`) |
| Retention period | The maximum age (in days) of stored events before they are purged by the retention process |
| TOML | Tom's Obvious Minimal Language — a configuration file format used for the service's runtime settings |
| Echo | A high-performance Go HTTP framework used as the service's HTTP layer |
| logrus | A structured logging library for Go that supports JSON output format |

## Requirements

### Requirement 1: Audit Event Ingestion

**User Story:** As an agent-fox instance, I want to send audit events to a
central service via HTTP POST, so that events are durably stored for later
analysis.

#### Acceptance Criteria

[01-REQ-1.1] WHEN an HTTP POST request is received at `/api/v1/audit` with a
valid Bearer token and a JSON body conforming to the envelope schema, THE
service SHALL store the event in the SQLite database AND return HTTP 201
Created with no response body.

[01-REQ-1.2] WHEN an HTTP POST request is received at `/api/v1/audit`, THE
service SHALL accept only the `application/json` content type AND return HTTP
415 Unsupported Media Type for any other content type.

[01-REQ-1.3] THE service SHALL listen for HTTP requests on the port specified
in the configuration file, defaulting to 8080 if not configured.

[01-REQ-1.4] THE service SHALL bind to the network address specified in the
configuration file, defaulting to `0.0.0.0` if not configured.

#### Edge Cases

[01-REQ-1.E1] IF the request body is empty, THEN THE service SHALL return HTTP
400 Bad Request.

[01-REQ-1.E2] IF the request body exceeds 1 MB, THEN THE service SHALL return
HTTP 413 Payload Too Large without reading the full body.

[01-REQ-1.E3] IF the request body is not valid JSON, THEN THE service SHALL
return HTTP 400 Bad Request.

---

### Requirement 2: Event Validation

**User Story:** As a service operator, I want incoming events to be validated
against the envelope schema, so that only well-formed events are stored.

#### Acceptance Criteria

[01-REQ-2.1] WHEN an event is received, THE service SHALL validate that all
required envelope fields are present: `id`, `timestamp`, `run_id`,
`event_type`, `severity`, and `payload`.

[01-REQ-2.2] WHEN an event is received, THE service SHALL validate that `id`
is a non-empty string, `timestamp` is a valid ISO 8601 datetime string,
`run_id` is a non-empty string, `event_type` is a non-empty string containing
at least one dot separator, `severity` is one of `info`, `warning`, `error`,
or `critical`, and `payload` is a JSON object.

[01-REQ-2.3] WHEN an event is received, THE service SHALL accept optional
envelope fields `node_id`, `session_id`, and `archetype` as strings, defaulting
to empty string if absent.

[01-REQ-2.4] IF any required field is missing or fails validation, THEN THE
service SHALL return HTTP 422 Unprocessable Entity.

#### Edge Cases

[01-REQ-2.E1] IF the `timestamp` field contains a valid ISO 8601 date but
without timezone information, THEN THE service SHALL reject the event with HTTP
422 Unprocessable Entity.

[01-REQ-2.E2] IF the `payload` field is `null` instead of an object, THEN THE
service SHALL reject the event with HTTP 422 Unprocessable Entity.

[01-REQ-2.E3] IF the `event_type` field contains no dot separator (e.g.,
`"start"` instead of `"run.start"`), THEN THE service SHALL reject the event
with HTTP 422 Unprocessable Entity.

---

### Requirement 3: SQLite Storage

**User Story:** As a service operator, I want events stored in an embedded
SQLite database with metadata columns, so that events can be queried
efficiently without external dependencies.

#### Acceptance Criteria

[01-REQ-3.1] THE service SHALL store each validated event in a SQLite table
with dedicated columns for envelope metadata: `id` (TEXT PRIMARY KEY),
`timestamp` (TEXT), `run_id` (TEXT), `event_type` (TEXT), `node_id` (TEXT),
`session_id` (TEXT), `archetype` (TEXT), `severity` (TEXT), and `payload`
(TEXT storing the raw JSON object), plus a `received_at` (TEXT) column
recording the server-side reception time in ISO 8601 UTC.

[01-REQ-3.2] THE service SHALL enable SQLite WAL mode on database
initialization to support concurrent write access.

[01-REQ-3.3] THE service SHALL create the database file and the events table
automatically on first startup if they do not exist, AND return the database
path to the caller for logging purposes.

[01-REQ-3.4] THE service SHALL use the database path from the configuration
file, defaulting to `./data/audit.db` if not configured, AND create parent
directories if they do not exist.

#### Edge Cases

[01-REQ-3.E1] IF a received event has an `id` that already exists in the
database, THEN THE service SHALL reject the event with HTTP 409 Conflict.

[01-REQ-3.E2] IF the database file cannot be opened or created (e.g.,
permission denied), THEN THE service SHALL log the error and exit with a
non-zero exit code.

---

### Requirement 4: Bearer Token Authentication

**User Story:** As a service operator, I want to restrict access to the ingest
endpoint using a Bearer token, so that only authorized agent-fox instances can
submit events.

#### Acceptance Criteria

[01-REQ-4.1] WHEN an HTTP request is received at `/api/v1/audit`, THE service
SHALL extract the Bearer token from the `Authorization` header and compare it
against the configured token value.

[01-REQ-4.2] IF the `Authorization` header is missing or does not start with
`Bearer `, THEN THE service SHALL return HTTP 401 Unauthorized.

[01-REQ-4.3] IF the Bearer token does not match the configured token, THEN THE
service SHALL return HTTP 401 Unauthorized.

[01-REQ-4.4] THE service SHALL read the expected Bearer token from the
`auth.bearer_token` field in the TOML configuration file.

[01-REQ-4.5] IF the `auth.bearer_token` field is missing or empty in the
configuration file, THEN THE service SHALL log an error and exit with a
non-zero exit code at startup.

#### Edge Cases

[01-REQ-4.E1] IF the `Authorization` header contains extra whitespace between
`Bearer` and the token value, THEN THE service SHALL trim the whitespace and
validate the token normally.

---

### Requirement 5: Kubernetes Health Endpoints

**User Story:** As a Kubernetes operator, I want standard health and readiness
endpoints, so that the cluster can monitor the service's availability.

#### Acceptance Criteria

[01-REQ-5.1] WHEN an HTTP GET request is received at `/healthz`, THE service
SHALL return HTTP 200 OK without requiring authentication.

[01-REQ-5.2] WHEN an HTTP GET request is received at `/readyz`, THE service
SHALL verify that the SQLite database is accessible by executing a lightweight
query (e.g., `SELECT 1`) AND return HTTP 200 OK if successful or HTTP 503
Service Unavailable if the check fails.

[01-REQ-5.3] THE service SHALL NOT require a Bearer token for `/healthz` or
`/readyz` requests.

#### Edge Cases

[01-REQ-5.E1] IF the database connection is lost after startup, THEN THE
service SHALL return HTTP 503 on `/readyz` while continuing to return HTTP 200
on `/healthz`.

---

### Requirement 6: TOML Configuration

**User Story:** As a service operator, I want to configure the service via a
TOML file, so that I can adjust runtime settings without recompilation.

#### Acceptance Criteria

[01-REQ-6.1] WHEN the service starts, THE service SHALL read the configuration
from a TOML file at the path specified by the `--config` command-line flag,
defaulting to `config.toml` in the current working directory.

[01-REQ-6.2] THE service SHALL support the following configuration sections and
fields with defaults: `server.port` (8080), `server.bind_address`
(`"0.0.0.0"`), `database.path` (`"./data/audit.db"`),
`database.retention_days` (30), `auth.bearer_token` (required, no default),
`logging.level` (`"info"`).

[01-REQ-6.3] IF the configuration file does not exist at the specified path,
THEN THE service SHALL log an error and exit with a non-zero exit code.

[01-REQ-6.4] IF the configuration file contains invalid TOML syntax, THEN THE
service SHALL log a descriptive parse error and exit with a non-zero exit code.

#### Edge Cases

[01-REQ-6.E1] IF `database.retention_days` is set to zero or a negative value,
THEN THE service SHALL log a warning and use the default value of 30 days.

[01-REQ-6.E2] IF `server.port` is outside the range 1–65535, THEN THE service
SHALL log an error and exit with a non-zero exit code.

---

### Requirement 7: Data Retention

**User Story:** As a service operator, I want events older than a configurable
period to be automatically purged, so that the database does not grow
unboundedly.

#### Acceptance Criteria

[01-REQ-7.1] THE service SHALL run a background retention process that
periodically deletes events whose `timestamp` is older than the configured
retention period.

[01-REQ-7.2] THE service SHALL execute the retention purge once every hour.

[01-REQ-7.3] WHEN the retention process runs, THE service SHALL delete all
events where `timestamp` is older than `now() - retention_days` AND log the
number of deleted events AND return the count of deleted rows to the caller.

[01-REQ-7.4] THE service SHALL default the retention period to 30 days if
`database.retention_days` is not configured.

#### Edge Cases

[01-REQ-7.E1] IF the retention process encounters a database error during
deletion, THEN THE service SHALL log the error and retry on the next scheduled
cycle without crashing.

---

### Requirement 8: Graceful Shutdown

**User Story:** As a Kubernetes operator, I want the service to shut down
gracefully on SIGTERM, so that in-flight requests complete and the database is
closed cleanly.

#### Acceptance Criteria

[01-REQ-8.1] WHEN the service receives a SIGTERM or SIGINT signal, THE service
SHALL stop accepting new connections, wait for in-flight requests to complete
(up to a 15-second timeout), stop the retention background process, close the
database connection, and then exit with code 0.

[01-REQ-8.2] IF in-flight requests do not complete within 15 seconds, THEN THE
service SHALL force-close remaining connections and exit with code 0.

#### Edge Cases

[01-REQ-8.E1] IF a second SIGTERM or SIGINT is received during the graceful
shutdown window, THEN THE service SHALL exit immediately with code 1.

---

### Requirement 9: Structured JSON Logging

**User Story:** As a service operator, I want structured JSON logs, so that
logs can be ingested by centralized logging systems in Kubernetes.

#### Acceptance Criteria

[01-REQ-9.1] THE service SHALL emit all log messages as JSON objects using the
logrus library with JSON formatter.

[01-REQ-9.2] THE service SHALL set the log level to the value specified in
`logging.level` configuration, defaulting to `info`.

[01-REQ-9.3] WHEN the service starts, THE service SHALL log a startup message
including the configured port, database path, and log level.

[01-REQ-9.4] WHEN an HTTP request is processed, THE service SHALL log the
request method, path, status code, and duration.

#### Edge Cases

[01-REQ-9.E1] IF the `logging.level` field contains an unrecognized value,
THEN THE service SHALL log a warning and default to `info`.

---

### Requirement 10: Concurrent Write Safety

**User Story:** As a service operator, I want the service to safely handle
concurrent audit event submissions, so that no events are lost under load.

#### Acceptance Criteria

[01-REQ-10.1] THE service SHALL enable SQLite WAL mode and configure connection
pooling so that concurrent HTTP requests can write to the database without
`SQLITE_BUSY` errors under normal load.

[01-REQ-10.2] IF a database write encounters a transient lock contention error,
THEN THE service SHALL retry the write up to 3 times with a busy timeout of 5
seconds before returning HTTP 503 Service Unavailable.

#### Edge Cases

[01-REQ-10.E1] IF the SQLite busy timeout is exhausted after all retries, THEN
THE service SHALL return HTTP 503 Service Unavailable and log the contention
event at `warning` level.
