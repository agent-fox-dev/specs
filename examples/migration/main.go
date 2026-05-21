// Example: programmatic construction of the Audit Hub specification.
//
// This program builds the complete 01_audit_hub spec in memory using the
// speclib construction API, validates it, and writes it to disk at
// examples/01_audit_hub_new/.
package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	speclib "github.com/af/speclib"
)

func main() {
	spec := buildAuditHubSpec()

	errs := speclib.Validate(spec)

	var schemaErrs, warnings []speclib.ValidationError
	for _, e := range errs {
		if e.Rule == "schema" {
			schemaErrs = append(schemaErrs, e)
		} else {
			warnings = append(warnings, e)
		}
	}

	if len(warnings) > 0 {
		fmt.Fprintf(os.Stderr, "cross-file warnings: %d (glossary gaps, coverage gaps — expected for this example)\n", len(warnings))
	}

	if len(schemaErrs) > 0 {
		for _, e := range schemaErrs {
			fmt.Fprintf(os.Stderr, "schema error: [%s] %s\n", e.File, e.Message)
		}
		os.Exit(1)
	}

	outDir := filepath.Join("examples/migration", "01_audit_hub_go")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		log.Fatalf("creating output directory: %v", err)
	}

	if err := speclib.Save(spec, outDir); err != nil {
		log.Fatalf("saving spec: %v", err)
	}

	fmt.Printf("spec written to %s/\n", outDir)
}

func buildAuditHubSpec() *speclib.Spec {
	spec := speclib.NewSpec("01", "audit_hub")

	buildPRD(spec)
	buildRequirements(spec)
	buildTestSpec(spec)
	buildTasks(spec)

	return spec
}

// ---------------------------------------------------------------------------
// PRD
// ---------------------------------------------------------------------------

func buildPRD(spec *speclib.Spec) {
	spec.PRD = speclib.NewPRDDocument("01", "audit_hub", "Audit Hub")
	spec.PRD.Frontmatter.SchemaVersion = 1
	spec.PRD.Frontmatter.Source = ".agent-fox/specs/prd.md"
	spec.PRD.Frontmatter.Supersedes = []string{}
	spec.PRD.Frontmatter.Tags = []string{}
	spec.PRD.Body = prdBody
}

const prdBody = `# Product Requirements Document: Audit Hub

## Overview

A minimalistic Go-based HTTP service that receives audit events from agent-fox
instances via HTTP POST and stores them in a local embedded SQLite database.
The service is designed for single-instance deployment on Kubernetes.

## Core Functionality

### Audit Event Ingestion

- The service exposes a single write endpoint at ` + "`POST /api/v1/audit`" + `.
- Each request carries exactly one audit event in the JSON body, conforming to
  the envelope schema defined in ` + "`audit-format.md`" + `.
- The service validates incoming events against the envelope schema before
  storing them. Malformed or non-conformant events are rejected.
- This is a **write-only** service in version 0.0.1 — no query or retrieval
  endpoints are exposed.

### Storage

- Events are stored in an embedded SQLite database.
- The database schema decomposes envelope metadata into dedicated columns for
  efficient querying, while storing the ` + "`payload`" + ` field as a raw JSON text
  column.
- SQLite WAL (Write-Ahead Logging) mode is enabled to handle concurrent writes
  from multiple goroutines serving simultaneous requests.
- The database file is stored at a default location (` + "`./data/audit.db`" + `),
  configurable via the TOML configuration file.

### Authentication

- All requests to ` + "`POST /api/v1/audit`" + ` require a Bearer token in the
  ` + "`Authorization`" + ` header.
- The token is created when an agent-fox instance/repository is registered.
- For version 0.0.1, the token value is hardcoded in the configuration file.
- Requests without a valid token receive HTTP 401 Unauthorized.

### Kubernetes Health Endpoints

- ` + "`GET /healthz`" + ` — liveness probe. Returns HTTP 200 when the process is
  running.
- ` + "`GET /readyz`" + ` — readiness probe. Returns HTTP 200 when the service is ready
  to accept traffic (database connection is healthy).
- Health endpoints do **not** require authentication.

### Data Retention

- A background retention process periodically purges events older than a
  configurable retention period.
- Default retention period: 30 days.
- Retention is based on the event's ` + "`timestamp`" + ` field.

### Configuration

All runtime configuration is read from a local TOML file.

### Logging

- The service uses structured JSON logging via the logrus library.
- Log level is configurable via the TOML configuration file.

### Graceful Shutdown

- The service handles ` + "`SIGTERM`" + ` and ` + "`SIGINT`" + ` signals.
- On shutdown, the service stops accepting new connections, drains in-flight
  requests, and closes the database connection cleanly.

## Out of Scope (v0.0.1)

- Query/read API endpoints
- Multi-instance / distributed deployment
- Dynamic token management (registration API)
- Batch event ingestion
- Event forwarding or streaming
`

// ---------------------------------------------------------------------------
// Requirements
// ---------------------------------------------------------------------------

func buildRequirements(spec *speclib.Spec) {
	r := &spec.Requirements
	r.SchemaVersion = 1
	r.Introduction = "Audit Hub is a minimalistic Go-based HTTP service that ingests structured audit " +
		"events from agent-fox instances, validates them against a defined envelope " +
		"schema, and persists them in an embedded SQLite database. The service is " +
		"designed for single-instance Kubernetes deployment and exposes standard " +
		"health/readiness probes."

	addGlossary(r)
	addRequirements(r)
	addCorrectnessProperties(r)
	addExecutionPaths(r)
	addErrorHandling(r)
}

func addGlossary(r *speclib.Requirements) {
	entries := []struct{ term, def string }{
		{"Audit event", "A structured JSON object conforming to the envelope schema, representing a single observable action in the agent-fox system"},
		{"Envelope schema", "The fixed set of top-level fields (`id`, `timestamp`, `run_id`, `event_type`, `node_id`, `session_id`, `archetype`, `severity`, `payload`) that every audit event must contain"},
		{"Bearer token", "An opaque authentication credential sent in the `Authorization` header as `Bearer <token>`"},
		{"WAL mode", "SQLite Write-Ahead Logging mode, which allows concurrent readers and a single writer without blocking"},
		{"Liveness probe", "A Kubernetes health check that verifies the process is running (`/healthz`)"},
		{"Readiness probe", "A Kubernetes health check that verifies the service can accept traffic (`/readyz`)"},
		{"Retention period", "The maximum age (in days) of stored events before they are purged by the retention process"},
		{"TOML", "Tom's Obvious Minimal Language — a configuration file format used for the service's runtime settings"},
		{"Echo", "A high-performance Go HTTP framework used as the service's HTTP layer"},
		{"logrus", "A structured logging library for Go that supports JSON output format"},
	}
	for _, e := range entries {
		r.SetGlossaryEntry(e.term, e.def)
	}
}

func addRequirements(r *speclib.Requirements) {
	must(r.AddRequirement(req1()))
	must(r.AddRequirement(req2()))
	must(r.AddRequirement(req3()))
	must(r.AddRequirement(req4()))
	must(r.AddRequirement(req5()))
	must(r.AddRequirement(req6()))
	must(r.AddRequirement(req7()))
	must(r.AddRequirement(req8()))
	must(r.AddRequirement(req9()))
	must(r.AddRequirement(req10()))
}

func req1() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-1", "Audit Event Ingestion",
		speclib.NewUserStory(
			"an agent-fox instance",
			"send audit events to a central service via HTTP POST",
			"events are durably stored for later analysis",
		))

	must(req.AddCriterion(speclib.NewComplexEventCriterion(
		"01-REQ-1.1",
		"an HTTP POST request is received at `/api/v1/audit`",
		"a valid Bearer token and a JSON body conforming to the envelope schema",
		"THE service",
		"store the event in the SQLite database AND return HTTP 201 Created with no response body",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-1.2",
		"an HTTP POST request is received at `/api/v1/audit`",
		"THE service",
		"accept only the `application/json` content type AND return HTTP 415 Unsupported Media Type for any other content type",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-1.3",
		"THE service",
		"listen for HTTP requests on the port specified in the configuration file, defaulting to 8080 if not configured",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-1.4",
		"THE service",
		"bind to the network address specified in the configuration file, defaulting to `0.0.0.0` if not configured",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-1.E1",
		"the request body is empty",
		"THE service",
		"return HTTP 400 Bad Request",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-1.E2",
		"the request body exceeds 1 MB",
		"THE service",
		"return HTTP 413 Payload Too Large without reading the full body",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-1.E3",
		"the request body is not valid JSON",
		"THE service",
		"return HTTP 400 Bad Request",
	)))

	return req
}

func req2() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-2", "Event Validation",
		speclib.NewUserStory(
			"a service operator",
			"incoming events to be validated against the envelope schema",
			"only well-formed events are stored",
		))

	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-2.1",
		"an event is received",
		"THE service",
		"validate that all required envelope fields are present: `id`, `timestamp`, `run_id`, `event_type`, `severity`, and `payload`",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-2.2",
		"an event is received",
		"THE service",
		"validate that `id` is a non-empty string, `timestamp` is a valid ISO 8601 datetime string, `run_id` is a non-empty string, `event_type` is a non-empty string containing at least one dot separator, `severity` is one of `info`, `warning`, `error`, or `critical`, and `payload` is a JSON object",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-2.3",
		"an event is received",
		"THE service",
		"accept optional envelope fields `node_id`, `session_id`, and `archetype` as strings, defaulting to empty string if absent",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-2.4",
		"any required field is missing or fails validation",
		"THE service",
		"return HTTP 422 Unprocessable Entity",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-2.E1",
		"the `timestamp` field contains a valid ISO 8601 date but without timezone information",
		"THE service",
		"reject the event with HTTP 422 Unprocessable Entity",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-2.E2",
		"the `payload` field is `null` instead of an object",
		"THE service",
		"reject the event with HTTP 422 Unprocessable Entity",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-2.E3",
		"the `event_type` field contains no dot separator (e.g., `\"start\"` instead of `\"run.start\"`)",
		"THE service",
		"reject the event with HTTP 422 Unprocessable Entity",
	)))

	return req
}

func req3() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-3", "SQLite Storage",
		speclib.NewUserStory(
			"a service operator",
			"events stored in an embedded SQLite database with metadata columns",
			"events can be queried efficiently without external dependencies",
		))

	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-3.1",
		"THE service",
		"store each validated event in a SQLite table with dedicated columns for envelope metadata: `id` (TEXT PRIMARY KEY), `timestamp` (TEXT), `run_id` (TEXT), `event_type` (TEXT), `node_id` (TEXT), `session_id` (TEXT), `archetype` (TEXT), `severity` (TEXT), and `payload` (TEXT storing the raw JSON object), plus a `received_at` (TEXT) column recording the server-side reception time in ISO 8601 UTC",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-3.2",
		"THE service",
		"enable SQLite WAL mode on database initialization to support concurrent write access",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-3.3",
		"THE service",
		"create the database file and the events table automatically on first startup if they do not exist, AND return the database path to the caller for logging purposes",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-3.4",
		"THE service",
		"use the database path from the configuration file, defaulting to `./data/audit.db` if not configured, AND create parent directories if they do not exist",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-3.E1",
		"a received event has an `id` that already exists in the database",
		"THE service",
		"reject the event with HTTP 409 Conflict",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-3.E2",
		"the database file cannot be opened or created (e.g., permission denied)",
		"THE service",
		"log the error and exit with a non-zero exit code",
	)))

	return req
}

func req4() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-4", "Bearer Token Authentication",
		speclib.NewUserStory(
			"a service operator",
			"restrict access to the ingest endpoint using a Bearer token",
			"only authorized agent-fox instances can submit events",
		))

	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-4.1",
		"an HTTP request is received at `/api/v1/audit`",
		"THE service",
		"extract the Bearer token from the `Authorization` header and compare it against the configured token value",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-4.2",
		"the `Authorization` header is missing or does not start with `Bearer `",
		"THE service",
		"return HTTP 401 Unauthorized",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-4.3",
		"the Bearer token does not match the configured token",
		"THE service",
		"return HTTP 401 Unauthorized",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-4.4",
		"THE service",
		"read the expected Bearer token from the `auth.bearer_token` field in the TOML configuration file",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-4.5",
		"the `auth.bearer_token` field is missing or empty in the configuration file",
		"THE service",
		"log an error and exit with a non-zero exit code at startup",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-4.E1",
		"the `Authorization` header contains extra whitespace between `Bearer` and the token value",
		"THE service",
		"trim the whitespace and validate the token normally",
	)))

	return req
}

func req5() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-5", "Kubernetes Health Endpoints",
		speclib.NewUserStory(
			"a Kubernetes operator",
			"standard health and readiness endpoints",
			"the cluster can monitor the service's availability",
		))

	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-5.1",
		"an HTTP GET request is received at `/healthz`",
		"THE service",
		"return HTTP 200 OK without requiring authentication",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-5.2",
		"an HTTP GET request is received at `/readyz`",
		"THE service",
		"verify that the SQLite database is accessible by executing a lightweight query (e.g., `SELECT 1`) AND return HTTP 200 OK if successful or HTTP 503 Service Unavailable if the check fails",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-5.3",
		"THE service",
		"NOT require a Bearer token for `/healthz` or `/readyz` requests",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-5.E1",
		"the database connection is lost after startup",
		"THE service",
		"return HTTP 503 on `/readyz` while continuing to return HTTP 200 on `/healthz`",
	)))

	return req
}

func req6() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-6", "TOML Configuration",
		speclib.NewUserStory(
			"a service operator",
			"configure the service via a TOML file",
			"I can adjust runtime settings without recompilation",
		))

	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-6.1",
		"the service starts",
		"THE service",
		"read the configuration from a TOML file at the path specified by the `--config` command-line flag, defaulting to `config.toml` in the current working directory",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-6.2",
		"THE service",
		"support the following configuration sections and fields with defaults: `server.port` (8080), `server.bind_address` (`\"0.0.0.0\"`), `database.path` (`\"./data/audit.db\"`), `database.retention_days` (30), `auth.bearer_token` (required, no default), `logging.level` (`\"info\"`)",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-6.3",
		"the configuration file does not exist at the specified path",
		"THE service",
		"log an error and exit with a non-zero exit code",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-6.4",
		"the configuration file contains invalid TOML syntax",
		"THE service",
		"log a descriptive parse error and exit with a non-zero exit code",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-6.E1",
		"`database.retention_days` is set to zero or a negative value",
		"THE service",
		"log a warning and use the default value of 30 days",
	)))
	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-6.E2",
		"`server.port` is outside the range 1–65535",
		"THE service",
		"log an error and exit with a non-zero exit code",
	)))

	return req
}

func req7() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-7", "Data Retention",
		speclib.NewUserStory(
			"a service operator",
			"events older than a configurable period to be automatically purged",
			"the database does not grow unboundedly",
		))

	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-7.1",
		"THE service",
		"run a background retention process that periodically deletes events whose `timestamp` is older than the configured retention period",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-7.2",
		"THE service",
		"execute the retention purge once every hour",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-7.3",
		"the retention process runs",
		"THE service",
		"delete all events where `timestamp` is older than `now() - retention_days` AND log the number of deleted events AND return the count of deleted rows to the caller",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-7.4",
		"THE service",
		"default the retention period to 30 days if `database.retention_days` is not configured",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-7.E1",
		"the retention process encounters a database error during deletion",
		"THE service",
		"log the error and retry on the next scheduled cycle without crashing",
	)))

	return req
}

func req8() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-8", "Graceful Shutdown",
		speclib.NewUserStory(
			"a Kubernetes operator",
			"the service to shut down gracefully on SIGTERM",
			"in-flight requests complete and the database is closed cleanly",
		))

	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-8.1",
		"the service receives a SIGTERM or SIGINT signal",
		"THE service",
		"stop accepting new connections, wait for in-flight requests to complete (up to a 15-second timeout), stop the retention background process, close the database connection, and then exit with code 0",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-8.2",
		"in-flight requests do not complete within 15 seconds",
		"THE service",
		"force-close remaining connections and exit with code 0",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-8.E1",
		"a second SIGTERM or SIGINT is received during the graceful shutdown window",
		"THE service",
		"exit immediately with code 1",
	)))

	return req
}

func req9() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-9", "Structured JSON Logging",
		speclib.NewUserStory(
			"a service operator",
			"structured JSON logs",
			"logs can be ingested by centralized logging systems in Kubernetes",
		))

	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-9.1",
		"THE service",
		"emit all log messages as JSON objects using the logrus library with JSON formatter",
	)))
	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-9.2",
		"THE service",
		"set the log level to the value specified in `logging.level` configuration, defaulting to `info`",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-9.3",
		"the service starts",
		"THE service",
		"log a startup message including the configured port, database path, and log level",
	)))
	must(req.AddCriterion(speclib.NewEventDrivenCriterion(
		"01-REQ-9.4",
		"an HTTP request is processed",
		"THE service",
		"log the request method, path, status code, and duration",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-9.E1",
		"the `logging.level` field contains an unrecognized value",
		"THE service",
		"log a warning and default to `info`",
	)))

	return req
}

func req10() speclib.Requirement {
	req := speclib.NewRequirement("01-REQ-10", "Concurrent Write Safety",
		speclib.NewUserStory(
			"a service operator",
			"the service to safely handle concurrent audit event submissions",
			"no events are lost under load",
		))

	must(req.AddCriterion(speclib.NewUbiquitousCriterion(
		"01-REQ-10.1",
		"THE service",
		"enable SQLite WAL mode and configure connection pooling so that concurrent HTTP requests can write to the database without `SQLITE_BUSY` errors under normal load",
	)))
	must(req.AddCriterion(speclib.NewUnwantedCriterion(
		"01-REQ-10.2",
		"a database write encounters a transient lock contention error",
		"THE service",
		"retry the write up to 3 times with a busy timeout of 5 seconds before returning HTTP 503 Service Unavailable",
	)))

	must(req.AddEdgeCase(speclib.NewUnwantedCriterion(
		"01-REQ-10.E1",
		"the SQLite busy timeout is exhausted after all retries",
		"THE service",
		"return HTTP 503 Service Unavailable and log the contention event at `warning` level",
	)))

	return req
}

// ---------------------------------------------------------------------------
// Correctness Properties
// ---------------------------------------------------------------------------

func addCorrectnessProperties(r *speclib.Requirements) {
	p1 := speclib.NewCorrectnessProperty(
		"01-PROP-1", "Schema Validation Completeness",
		"JSON object submitted to `POST /api/v1/audit`",
		"the service accepts the event if and only if all required envelope fields (`id`, `timestamp`, `run_id`, `event_type`, `severity`, `payload`) are present and conform to their type constraints",
	)
	p1.Validates = []string{"01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4"}
	must(r.AddCorrectnessProperty(p1))

	p2 := speclib.NewCorrectnessProperty(
		"01-PROP-2", "Storage Integrity",
		"audit event that passes validation and receives HTTP 201",
		"the event is retrievable from the SQLite database with all envelope metadata fields matching the submitted values exactly, and the `payload` field matching the original JSON object",
	)
	p2.Validates = []string{"01-REQ-1.1", "01-REQ-3.1"}
	must(r.AddCorrectnessProperty(p2))

	p3 := speclib.NewCorrectnessProperty(
		"01-PROP-3", "Authentication Enforcement",
		"HTTP request to `/api/v1/audit`",
		"the service returns HTTP 401 if the Bearer token is missing, malformed, or does not match the configured value, and only proceeds to validation and storage when the token matches",
	)
	p3.Validates = []string{"01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3"}
	must(r.AddCorrectnessProperty(p3))

	p4 := speclib.NewCorrectnessProperty(
		"01-PROP-4", "Idempotent Rejection of Duplicates",
		"audit event with an `id` already present in the database",
		"the service returns HTTP 409 Conflict without modifying the existing stored event",
	)
	p4.Validates = []string{"01-REQ-3.E1"}
	must(r.AddCorrectnessProperty(p4))

	p5 := speclib.NewCorrectnessProperty(
		"01-PROP-5", "Retention Correctness",
		"event stored in the database",
		"after the retention process runs, the event is present if its `timestamp` is within the retention period, and absent if its `timestamp` is older than the retention period",
	)
	p5.Validates = []string{"01-REQ-7.1", "01-REQ-7.3"}
	must(r.AddCorrectnessProperty(p5))

	p6 := speclib.NewCorrectnessProperty(
		"01-PROP-6", "Health Probe Independence",
		"HTTP request to `/healthz` or `/readyz`",
		"the service returns a response regardless of the presence or absence of an Authorization header; `/healthz` always returns 200 when the process is running; `/readyz` returns 200 if and only if the database is accessible",
	)
	p6.Validates = []string{"01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.3"}
	must(r.AddCorrectnessProperty(p6))

	p7 := speclib.NewCorrectnessProperty(
		"01-PROP-7", "Configuration Validation Completeness",
		"TOML configuration file",
		"the service starts successfully if and only if the file is syntactically valid TOML, contains a non-empty `auth.bearer_token`, and all numeric fields are within valid ranges",
	)
	p7.Validates = []string{"01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4", "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2"}
	must(r.AddCorrectnessProperty(p7))

	p8 := speclib.NewCorrectnessProperty(
		"01-PROP-8", "Concurrent Write Safety",
		"set of N valid audit events submitted concurrently",
		"the service stores exactly N events in the database (assuming no duplicate IDs) without returning `SQLITE_BUSY` errors under normal load",
	)
	p8.Validates = []string{"01-REQ-10.1", "01-REQ-10.2"}
	must(r.AddCorrectnessProperty(p8))

	p9 := speclib.NewCorrectnessProperty(
		"01-PROP-9", "Graceful Shutdown Completeness",
		"in-flight request at the time SIGTERM is received",
		"the service either completes the request and returns a response, or terminates the connection after the 15-second timeout; in both cases, the database connection is closed before the process exits",
	)
	p9.Validates = []string{"01-REQ-8.1", "01-REQ-8.2"}
	must(r.AddCorrectnessProperty(p9))
}

// ---------------------------------------------------------------------------
// Execution Paths
// ---------------------------------------------------------------------------

func addExecutionPaths(r *speclib.Requirements) {
	path1 := speclib.NewExecutionPath("01-PATH-1", "Audit event ingestion (happy path)")
	path1.Steps = []speclib.PathStep{
		{Actor: "cmd/audit-hub/main.go", Action: "main() — starts Echo server"},
		{Actor: "internal/server/server.go", Action: "New(cfg, store) → *Server — creates Echo instance, registers routes and middleware"},
		{Actor: "internal/middleware/auth.go", Action: "BearerAuth(token) → echo.MiddlewareFunc — validates Authorization header"},
		{Actor: "internal/handler/audit.go", Action: "AuditHandler.Ingest(c) → error — reads and binds request body"},
		{Actor: "internal/validator/validator.go", Action: "Validate(event) → error — validates envelope fields"},
		{Actor: "internal/store/store.go", Action: "Store.InsertEvent(ctx, event) → error — inserts row into SQLite"},
		{Actor: "Side effect", Action: "event persisted in SQLite, HTTP 201 returned to caller"},
	}
	must(r.AddExecutionPath(path1))

	path2 := speclib.NewExecutionPath("01-PATH-2", "Health check (readiness)")
	path2.Steps = []speclib.PathStep{
		{Actor: "cmd/audit-hub/main.go", Action: "main() — starts Echo server"},
		{Actor: "internal/server/server.go", Action: "New(cfg, store) → *Server — registers health routes (no auth middleware)"},
		{Actor: "internal/health/health.go", Action: "HealthHandler.Readyz(c) → error — handles GET /readyz"},
		{Actor: "internal/store/store.go", Action: "Store.Ping(ctx) → error — executes `SELECT 1` against SQLite"},
		{Actor: "Side effect", Action: "HTTP 200 or 503 returned to caller"},
	}
	must(r.AddExecutionPath(path2))

	path3 := speclib.NewExecutionPath("01-PATH-3", "Data retention purge")
	path3.Steps = []speclib.PathStep{
		{Actor: "cmd/audit-hub/main.go", Action: "main() — starts retention ticker"},
		{Actor: "internal/retention/retention.go", Action: "StartRetention(ctx, store, interval, retentionDays) — launches goroutine with hourly ticker"},
		{Actor: "internal/store/store.go", Action: "Store.PurgeOlderThan(ctx, cutoff) → (int64, error) — deletes expired rows, returns count"},
		{Actor: "Side effect", Action: "expired rows deleted from SQLite, count logged"},
	}
	must(r.AddExecutionPath(path3))

	path4 := speclib.NewExecutionPath("01-PATH-4", "Graceful shutdown")
	path4.Steps = []speclib.PathStep{
		{Actor: "cmd/audit-hub/main.go", Action: "main() — listens for OS signals"},
		{Actor: "OS", Action: "delivers SIGTERM or SIGINT"},
		{Actor: "cmd/audit-hub/main.go", Action: "main() — cancels context, triggers Echo shutdown"},
		{Actor: "internal/server/server.go", Action: "Server.Shutdown(ctx) → error — drains in-flight requests with 15s timeout"},
		{Actor: "internal/retention/retention.go", Action: "StopRetention() — stops ticker goroutine via context cancellation"},
		{Actor: "internal/store/store.go", Action: "Store.Close() → error — closes SQLite connection"},
		{Actor: "Side effect", Action: "process exits with code 0"},
	}
	must(r.AddExecutionPath(path4))

	path5 := speclib.NewExecutionPath("01-PATH-5", "Configuration loading")
	path5.Steps = []speclib.PathStep{
		{Actor: "cmd/audit-hub/main.go", Action: "main() — reads --config flag"},
		{Actor: "internal/config/config.go", Action: "Load(path) → (*Config, error) — reads TOML file, applies defaults, validates"},
		{Actor: "Side effect", Action: "Config struct returned to main for dependency wiring; exits with non-zero code on validation error"},
	}
	must(r.AddExecutionPath(path5))
}

// ---------------------------------------------------------------------------
// Error Handling
// ---------------------------------------------------------------------------

func addErrorHandling(r *speclib.Requirements) {
	entries := []struct {
		condition, behavior, reqID string
	}{
		{"Empty request body", "HTTP 400 Bad Request", "01-REQ-1.E1"},
		{"Request body exceeds 1 MB", "HTTP 413 Payload Too Large", "01-REQ-1.E2"},
		{"Invalid JSON body", "HTTP 400 Bad Request", "01-REQ-1.E3"},
		{"Wrong content type", "HTTP 415 Unsupported Media Type", "01-REQ-1.2"},
		{"Missing/invalid envelope fields", "HTTP 422 Unprocessable Entity", "01-REQ-2.4"},
		{"Timestamp without timezone", "HTTP 422 Unprocessable Entity", "01-REQ-2.E1"},
		{"Payload is null", "HTTP 422 Unprocessable Entity", "01-REQ-2.E2"},
		{"Event type without dot", "HTTP 422 Unprocessable Entity", "01-REQ-2.E3"},
		{"Duplicate event ID", "HTTP 409 Conflict", "01-REQ-3.E1"},
		{"Database open failure", "Log error, exit non-zero", "01-REQ-3.E2"},
		{"Missing/empty bearer token in config", "Log error, exit non-zero", "01-REQ-4.5"},
		{"Missing Authorization header", "HTTP 401 Unauthorized", "01-REQ-4.2"},
		{"Invalid bearer token", "HTTP 401 Unauthorized", "01-REQ-4.3"},
		{"Database unreachable (readyz)", "HTTP 503 Service Unavailable", "01-REQ-5.E1"},
		{"Config file not found", "Log error, exit non-zero", "01-REQ-6.3"},
		{"Invalid TOML syntax", "Log parse error, exit non-zero", "01-REQ-6.4"},
		{"Invalid retention_days (<= 0)", "Log warning, use default 30", "01-REQ-6.E1"},
		{"Invalid port range", "Log error, exit non-zero", "01-REQ-6.E2"},
		{"Retention purge DB error", "Log error, retry next cycle", "01-REQ-7.E1"},
		{"Invalid logging.level value", "Log warning, default to info", "01-REQ-9.E1"},
		{"SQLite busy timeout exhausted", "HTTP 503, log at warning", "01-REQ-10.E1"},
		{"Shutdown timeout (15s) exceeded", "Force-close connections, exit 0", "01-REQ-8.2"},
		{"Second SIGTERM during shutdown", "Exit immediately with code 1", "01-REQ-8.E1"},
	}
	for i, e := range entries {
		must(r.AddErrorHandling(speclib.NewErrorHandlingEntry(
			fmt.Sprintf("01-ERR-%d", i+1), e.condition, e.behavior, e.reqID,
		)))
	}
}

// ---------------------------------------------------------------------------
// Test Spec
// ---------------------------------------------------------------------------

func buildTestSpec(spec *speclib.Spec) {
	ts := &spec.TestSpec
	ts.SchemaVersion = 1
	addTestCases(ts)
	addEdgeCaseTests(ts)
	addPropertyTests(ts)
	addSmokeTests(ts)
	addCoverage(ts)
}

func addTestCases(ts *speclib.TestSpec) {
	cases := []struct {
		id, reqID, kind, desc string
		preconditions         []string
		pseudocode            string
	}{
		{"TS-01-1", "01-REQ-1.1", "unit", "A valid audit event submitted with correct auth returns 201 and is stored.",
			[]string{"Store initialized with in-memory SQLite", "AuditHandler wired with store", "Bearer token set to \"test-token\""},
			"resp = POST(\"/api/v1/audit\", valid_event, auth=\"test-token\")\nASSERT resp.status == 201\nASSERT resp.body == \"\"\nrow = store.query(\"SELECT * FROM events WHERE id = ?\", event.id)\nASSERT row.id == event.id\nASSERT row.event_type == \"run.start\"\nASSERT row.severity == \"info\""},
		{"TS-01-2", "01-REQ-1.2", "unit", "A request with non-JSON content type is rejected.",
			[]string{"Server running with valid config"},
			"resp = POST(\"/api/v1/audit\", \"some text\", content_type=\"text/plain\", auth=\"test-token\")\nASSERT resp.status == 415"},
		{"TS-01-3", "01-REQ-2.1", "unit", "Events missing any required envelope field are rejected.",
			[]string{"Validator function available"},
			"FOR EACH field IN [id, timestamp, run_id, event_type, severity, payload]:\n    event = valid_event()\n    event[field] = zero_value\n    err = validator.Validate(event)\n    ASSERT err != nil"},
		{"TS-01-4", "01-REQ-2.2", "unit", "Field format constraints are enforced (timestamp ISO 8601, severity enum, event_type dot-separated, payload is object).",
			[]string{"Validator function available"},
			"cases = [(\"timestamp\", \"not-a-date\"), (\"severity\", \"fatal\"), (\"event_type\", \"start\")]\nFOR EACH (field, value) IN cases:\n    event = valid_event()\n    event[field] = value\n    err = validator.Validate(event)\n    ASSERT err != nil"},
		{"TS-01-5", "01-REQ-2.3", "unit", "Events without optional fields (node_id, session_id, archetype) are accepted with defaults.",
			[]string{"Store initialized, handler wired"},
			"event = valid_event_without_optionals()\nresp = POST(\"/api/v1/audit\", event, auth=\"test-token\")\nASSERT resp.status == 201\nrow = store.query(\"SELECT node_id, session_id, archetype FROM events WHERE id = ?\", event.id)\nASSERT row.node_id == \"\"\nASSERT row.session_id == \"\"\nASSERT row.archetype == \"\""},
		{"TS-01-6", "01-REQ-3.1", "unit", "Store initialization creates the events table and enables WAL mode.",
			[]string{"Temporary directory for database file"},
			"s, err = store.New(tmpdir + \"/test.db\")\nASSERT err == nil\nASSERT file_exists(tmpdir + \"/test.db\")\nrows = s.db.Query(\"SELECT name FROM sqlite_master WHERE type='table' AND name='events'\")\nASSERT rows.count == 1\nmode = s.db.QueryRow(\"PRAGMA journal_mode\").Scan()\nASSERT mode == \"wal\""},
		{"TS-01-7", "01-REQ-3.4", "unit", "Store creates parent directories and uses configured path.",
			[]string{"Temporary directory, subdirectory does not exist"},
			"path = tmpdir + \"/sub/dir/audit.db\"\ns, err = store.New(path)\nASSERT err == nil\nASSERT file_exists(path)"},
		{"TS-01-8", "01-REQ-4.1", "unit", "Requests without Authorization header receive 401.",
			[]string{"Echo instance with auth middleware configured, token = \"test-token\""},
			"resp = POST(\"/api/v1/audit\", valid_event, auth=None)\nASSERT resp.status == 401"},
		{"TS-01-9", "01-REQ-4.3", "unit", "Requests with incorrect Bearer token receive 401.",
			[]string{"Echo instance with auth middleware configured, token = \"test-token\""},
			"resp = POST(\"/api/v1/audit\", valid_event, auth=\"wrong-token\")\nASSERT resp.status == 401"},
		{"TS-01-10", "01-REQ-5.1", "unit", "Liveness probe always returns 200.",
			[]string{"Server running"},
			"resp = GET(\"/healthz\")\nASSERT resp.status == 200"},
		{"TS-01-11", "01-REQ-5.2", "unit", "Readiness probe returns 200 when database is accessible.",
			[]string{"Server running with healthy SQLite database"},
			"resp = GET(\"/readyz\")\nASSERT resp.status == 200"},
		{"TS-01-12", "01-REQ-5.3", "unit", "Health endpoints respond without requiring Authorization header.",
			[]string{"Server running with auth middleware active"},
			"resp1 = GET(\"/healthz\", auth=None)\nASSERT resp1.status == 200\nresp2 = GET(\"/readyz\", auth=None)\nASSERT resp2.status == 200"},
		{"TS-01-13", "01-REQ-6.1", "unit", "Configuration loads from TOML with correct defaults and overrides.",
			[]string{"Temporary TOML file with partial config (only `auth.bearer_token` set)"},
			"cfg, err = config.Load(tmpfile_with_token_only)\nASSERT err == nil\nASSERT cfg.Server.Port == 8080\nASSERT cfg.Server.BindAddress == \"0.0.0.0\"\nASSERT cfg.Database.Path == \"./data/audit.db\"\nASSERT cfg.Database.RetentionDays == 30\nASSERT cfg.Auth.BearerToken == \"my-token\"\nASSERT cfg.Logging.Level == \"info\""},
		{"TS-01-14", "01-REQ-6.2", "unit", "Explicit TOML values override defaults.",
			[]string{"TOML file with all fields set to non-default values"},
			"cfg, err = config.Load(custom_toml)\nASSERT err == nil\nASSERT cfg.Server.Port == 9090\nASSERT cfg.Server.BindAddress == \"127.0.0.1\"\nASSERT cfg.Database.Path == \"/tmp/custom.db\"\nASSERT cfg.Database.RetentionDays == 7\nASSERT cfg.Logging.Level == \"debug\""},
		{"TS-01-15", "01-REQ-7.1", "unit", "Purge deletes events older than retention period and returns count.",
			[]string{"Store with 3 events: one from 60 days ago, one from 15 days ago, one from today"},
			"store.InsertEvent(ctx, event_60_days_old)\nstore.InsertEvent(ctx, event_15_days_old)\nstore.InsertEvent(ctx, event_today)\ncount, err = store.PurgeOlderThan(ctx, now() - 30*day)\nASSERT err == nil\nASSERT count == 1\nremaining = store.query(\"SELECT COUNT(*) FROM events\")\nASSERT remaining == 2"},
		{"TS-01-16", "01-REQ-9.3", "unit", "HTTP requests produce structured log entries with required fields.",
			[]string{"Logrus configured with JSON formatter and a test hook to capture entries"},
			"hook = test.NewLogHook()\nlogrus.AddHook(hook)\nresp = POST(\"/api/v1/audit\", valid_event, auth=\"test-token\")\nentry = hook.LastEntry()\nASSERT entry.Data[\"method\"] == \"POST\"\nASSERT entry.Data[\"path\"] == \"/api/v1/audit\"\nASSERT entry.Data[\"status\"] == 201\nASSERT entry.Data[\"duration\"] != nil"},
		{"TS-01-17", "01-REQ-10.1", "integration", "Multiple concurrent inserts succeed without SQLITE_BUSY errors.",
			[]string{"Store initialized with file-backed SQLite (WAL mode)"},
			"wg = WaitGroup()\nerrors = []\nFOR i IN 1..20:\n    wg.Add(1)\n    GO func():\n        err = store.InsertEvent(ctx, unique_event(i))\n        IF err != nil: errors.append(err)\n        wg.Done()\nwg.Wait()\nASSERT len(errors) == 0\ncount = store.query(\"SELECT COUNT(*) FROM events\")\nASSERT count == 20"},
	}
	for _, c := range cases {
		tc := speclib.NewTestCase(c.id, c.reqID, c.kind, c.desc)
		tc.Preconditions = c.preconditions
		tc.AssertionPseudocode = c.pseudocode
		must(ts.AddTestCase(tc))
	}
}

func addEdgeCaseTests(ts *speclib.TestSpec) {
	cases := []struct {
		id, reqID, kind, desc string
		preconditions         []string
		pseudocode            string
	}{
		{"TS-01-E1", "01-REQ-1.E1", "unit", "POST with empty body is rejected.",
			[]string{"Server running with auth"},
			"resp = POST(\"/api/v1/audit\", body=\"\", auth=\"test-token\")\nASSERT resp.status == 400"},
		{"TS-01-E2", "01-REQ-1.E2", "unit", "Request body exceeding 1 MB is rejected.",
			[]string{"Server running with body size limit configured"},
			"large_body = \"x\" * (1024 * 1024 + 1)\nresp = POST(\"/api/v1/audit\", body=large_body, auth=\"test-token\")\nASSERT resp.status == 413"},
		{"TS-01-E3", "01-REQ-1.E3", "unit", "Malformed JSON body is rejected.",
			[]string{"Server running with auth"},
			"resp = POST(\"/api/v1/audit\", body=\"{invalid json\", auth=\"test-token\")\nASSERT resp.status == 400"},
		{"TS-01-E4", "01-REQ-2.E1", "unit", "ISO 8601 timestamp without timezone offset is rejected.",
			[]string{"Validator function available"},
			"event = valid_event()\nevent.timestamp = \"2026-04-27T10:00:00\"\nerr = validator.Validate(event)\nASSERT err != nil"},
		{"TS-01-E5", "01-REQ-2.E2", "unit", "Event with null payload is rejected.",
			[]string{"Validator function available"},
			"event = valid_event()\nevent.payload = null\nerr = validator.Validate(event)\nASSERT err != nil"},
		{"TS-01-E6", "01-REQ-2.E3", "unit", "Event type missing dot separator is rejected.",
			[]string{"Validator function available"},
			"event = valid_event()\nevent.event_type = \"start\"\nerr = validator.Validate(event)\nASSERT err != nil"},
		{"TS-01-E7", "01-REQ-3.E1", "unit", "Inserting an event with a duplicate ID returns conflict.",
			[]string{"Store with one event already inserted"},
			"store.InsertEvent(ctx, event)\nerr = store.InsertEvent(ctx, event_same_id)\nASSERT err != nil\nresp = POST(\"/api/v1/audit\", event_same_id_json, auth=\"test-token\")\nASSERT resp.status == 409"},
		{"TS-01-E8", "01-REQ-3.E2", "unit", "Store returns error when database path is not writable.",
			[]string{"Path to a read-only directory"},
			"_, err = store.New(\"/readonly/dir/audit.db\")\nASSERT err != nil"},
		{"TS-01-E9", "01-REQ-4.E1", "unit", "Extra whitespace between \"Bearer\" and token is handled.",
			[]string{"Auth middleware configured with token \"test-token\""},
			"resp = POST(\"/api/v1/audit\", valid_event, auth_header=\"Bearer   test-token\")\nASSERT resp.status != 401"},
		{"TS-01-E10", "01-REQ-4.5", "unit", "Config without bearer_token fails validation.",
			[]string{"TOML file with no `auth.bearer_token`"},
			"_, err = config.Load(toml_without_token)\nASSERT err != nil"},
		{"TS-01-E11", "01-REQ-5.E1", "unit", "Readiness probe returns 503 when database is inaccessible.",
			[]string{"HealthHandler with a store whose database has been closed"},
			"store.Close()\nresp = GET(\"/readyz\")\nASSERT resp.status == 503"},
		{"TS-01-E12", "01-REQ-6.3", "unit", "Missing config file returns error.",
			[]string{"Path to nonexistent file"},
			"_, err = config.Load(\"/nonexistent/config.toml\")\nASSERT err != nil"},
		{"TS-01-E13", "01-REQ-6.4", "unit", "Syntactically invalid TOML returns error.",
			[]string{"File with invalid TOML content"},
			"write_file(tmpfile, \"[invalid toml =\")\n_, err = config.Load(tmpfile)\nASSERT err != nil"},
		{"TS-01-E14", "01-REQ-6.E1", "unit", "Retention days <= 0 falls back to 30.",
			[]string{"TOML file with `database.retention_days = 0`"},
			"cfg, err = config.Load(toml_zero_retention)\nASSERT err == nil\nASSERT cfg.Database.RetentionDays == 30"},
		{"TS-01-E15", "01-REQ-6.E2", "unit", "Port outside 1-65535 returns error.",
			[]string{"TOML file with `server.port = 70000`"},
			"_, err = config.Load(toml_port_70000)\nASSERT err != nil"},
		{"TS-01-E16", "01-REQ-7.E1", "unit", "Retention purge gracefully handles database errors.",
			[]string{"Store whose database has been closed"},
			"store.Close()\n_, err = store.PurgeOlderThan(ctx, cutoff)\nASSERT err != nil"},
		{"TS-01-E17", "01-REQ-9.E1", "unit", "Unrecognized log level falls back to info.",
			[]string{"TOML file with `logging.level = \"verbose\"` (invalid)"},
			"cfg, err = config.Load(toml_bad_level)\nASSERT err == nil\nASSERT cfg.Logging.Level == \"info\""},
		{"TS-01-E18", "01-REQ-10.E1", "unit", "Exhausted busy timeout results in 503 response.",
			[]string{"Store configured with very short busy timeout", "Database locked by another connection"},
			"lock_database(store)\nerr = store.InsertEvent(ctx, event)\nASSERT err != nil"},
	}
	for _, c := range cases {
		et := speclib.NewEdgeCaseTest(c.id, c.reqID, c.kind, c.desc)
		et.Preconditions = c.preconditions
		et.AssertionPseudocode = c.pseudocode
		must(ts.AddEdgeCaseTest(et))
	}
}

func addPropertyTests(ts *speclib.TestSpec) {
	tests := []struct {
		id, propID, desc, forAny, invariant string
		validates                           []string
	}{
		{"TS-01-P1", "01-PROP-1", "Validation accepts iff all required fields are present and well-formed.",
			"Randomly generated AuditEvent structs with fields individually fuzzed",
			"`Validate(event)` returns nil iff `id` is non-empty, `timestamp` is valid ISO 8601 with timezone, `run_id` is non-empty, `event_type` contains a dot, `severity` is in {info, warning, error, critical}, and `payload` is a non-null JSON object.",
			[]string{"01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4"}},
		{"TS-01-P2", "01-PROP-2", "Every stored event is retrievable with identical field values.",
			"Valid AuditEvent structs with randomized field values (valid formats)",
			"After `InsertEvent(event)`, querying by `id` yields a row whose envelope metadata fields and payload match the original event exactly.",
			[]string{"01-REQ-1.1", "01-REQ-3.1"}},
		{"TS-01-P3", "01-PROP-3", "Only requests with the correct Bearer token pass auth.",
			"Random strings as token values",
			"The auth middleware returns 401 for any token that does not match the configured token, and passes through for exact matches.",
			[]string{"01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3"}},
		{"TS-01-P4", "01-PROP-4", "Duplicate IDs are always rejected without modifying existing data.",
			"Valid event pairs where the second has the same `id` but different payload",
			"Second insert fails. Original event's payload is unchanged.",
			[]string{"01-REQ-3.E1"}},
		{"TS-01-P5", "01-PROP-5", "After purge, only events within the retention window survive.",
			"Set of events with timestamps uniformly distributed across a 90-day range",
			"After `PurgeOlderThan(cutoff)`, all remaining events have `timestamp >= cutoff` and no event with `timestamp < cutoff` remains.",
			[]string{"01-REQ-7.1", "01-REQ-7.3"}},
		{"TS-01-P6", "01-PROP-6", "Health probes never return 401, regardless of auth header state.",
			"Random Authorization header values (including missing, empty, malformed, valid, invalid)",
			"`/healthz` returns 200 and `/readyz` returns 200 (when DB is up) regardless of auth.",
			[]string{"01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.3"}},
		{"TS-01-P7", "01-PROP-7", "Config loading succeeds iff TOML is valid and required fields are present.",
			"Randomly generated TOML content (some valid, some with missing token, some with invalid syntax, some with bad port ranges)",
			"`Load(path)` returns nil error iff the file is valid TOML with non-empty `auth.bearer_token` and port in 1–65535 (or absent, defaulting to 8080).",
			[]string{"01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4", "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2"}},
		{"TS-01-P8", "01-PROP-8", "N concurrent inserts with unique IDs all succeed.",
			"N in [2, 50], each event has a unique ID",
			"All N inserts succeed. Database contains exactly N rows.",
			[]string{"01-REQ-10.1", "01-REQ-10.2"}},
		{"TS-01-P9", "01-PROP-9", "In-flight requests complete before shutdown, and the database is closed.",
			"This is a deterministic scenario test rather than a generated property test",
			"After SIGTERM, pending requests either complete or are terminated within 15s. The database connection is closed.",
			[]string{"01-REQ-8.1", "01-REQ-8.2"}},
	}
	for _, t := range tests {
		pt := speclib.NewPropertyTest(t.id, t.propID, t.desc)
		pt.Validates = t.validates
		pt.ForAnyStrategy = t.forAny
		pt.InvariantCheck = t.invariant
		must(ts.AddPropertyTest(pt))
	}
}

func addSmokeTests(ts *speclib.TestSpec) {
	st1 := speclib.NewSmokeTest("TS-01-SMOKE-1", "01-PATH-1", "A valid event sent via HTTP POST is stored in the database and retrievable.")
	st1.Trigger = "HTTP POST to `/api/v1/audit` with valid event and correct Bearer token."
	st1.RealComponents = []string{"Store", "Echo server (httptest)", "Auth middleware", "Validator", "Handler"}
	st1.Mockable = []string{}
	st1.ExpectedEffects = []string{"HTTP 201 response", "Event row present in SQLite with matching field values", "`received_at` column populated with server-side timestamp"}
	must(ts.AddSmokeTest(st1))

	st2 := speclib.NewSmokeTest("TS-01-SMOKE-2", "01-PATH-2", "Readiness probe successfully queries the database.")
	st2.Trigger = "HTTP GET to `/readyz`."
	st2.RealComponents = []string{"Store", "Echo server (httptest)", "Health handler"}
	st2.Mockable = []string{}
	st2.ExpectedEffects = []string{"HTTP 200 response"}
	must(ts.AddSmokeTest(st2))

	st3 := speclib.NewSmokeTest("TS-01-SMOKE-3", "01-PATH-3", "Retention process deletes expired events and preserves recent ones.")
	st3.Trigger = "Start retention goroutine, wait for one cycle."
	st3.RealComponents = []string{"Store", "Retention process"}
	st3.Mockable = []string{}
	st3.ExpectedEffects = []string{"Events older than retention period are deleted", "Recent events remain"}
	must(ts.AddSmokeTest(st3))

	st4 := speclib.NewSmokeTest("TS-01-SMOKE-4", "01-PATH-5", "Configuration file is loaded and used to wire a functional server.")
	st4.Trigger = "Load config, create store, create server, send health check."
	st4.RealComponents = []string{"Config loader", "Store", "Echo server (httptest)"}
	st4.Mockable = []string{}
	st4.ExpectedEffects = []string{"Server starts without error", "`/healthz` returns 200"}
	must(ts.AddSmokeTest(st4))
}

func addCoverage(ts *speclib.TestSpec) {
	ts.Coverage = speclib.Coverage{
		RequirementsCovered: []string{
			"01-REQ-1.1", "01-REQ-1.2", "01-REQ-1.3", "01-REQ-1.4",
			"01-REQ-1.E1", "01-REQ-1.E2", "01-REQ-1.E3",
			"01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4",
			"01-REQ-2.E1", "01-REQ-2.E2", "01-REQ-2.E3",
			"01-REQ-3.1", "01-REQ-3.2", "01-REQ-3.3", "01-REQ-3.4",
			"01-REQ-3.E1", "01-REQ-3.E2",
			"01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3", "01-REQ-4.4", "01-REQ-4.5",
			"01-REQ-4.E1",
			"01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.3", "01-REQ-5.E1",
			"01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4",
			"01-REQ-6.E1", "01-REQ-6.E2",
			"01-REQ-7.1", "01-REQ-7.2", "01-REQ-7.3", "01-REQ-7.4", "01-REQ-7.E1",
			"01-REQ-8.1", "01-REQ-8.2", "01-REQ-8.E1",
			"01-REQ-9.1", "01-REQ-9.2", "01-REQ-9.3", "01-REQ-9.4", "01-REQ-9.E1",
			"01-REQ-10.1", "01-REQ-10.2", "01-REQ-10.E1",
		},
		PropertiesCovered: []string{
			"01-PROP-1", "01-PROP-2", "01-PROP-3", "01-PROP-4", "01-PROP-5",
			"01-PROP-6", "01-PROP-7", "01-PROP-8", "01-PROP-9",
		},
		PathsCovered: []string{
			"01-PATH-1", "01-PATH-2", "01-PATH-3", "01-PATH-4", "01-PATH-5",
		},
		Gaps: []string{},
	}
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

func buildTasks(spec *speclib.Spec) {
	t := &spec.Tasks
	t.SchemaVersion = 1
	t.TestCommands = speclib.TestCommands{
		SpecTests: "go test ./...",
		AllTests:  "go test -v -count=1 ./...",
		Linter:    "go vet ./...",
	}
	t.Dependencies = []speclib.TaskDependency{}

	addTaskGroups(t)
	addTraceability(t)
}

func addTaskGroups(t *speclib.Tasks) {
	// Group 1: Write failing spec tests
	g1 := speclib.NewTaskGroup(1, speclib.TaskGroupTests, "Write failing spec tests")
	addSubtask(&g1, "1.1", "Initialize Go module and project structure",
		[]string{"Run `go mod init github.com/agent-fox/audit-hub`", "Create directory structure", "Add initial dependencies"},
		nil, nil)
	addSubtask(&g1, "1.2", "Write config tests",
		[]string{"internal/config/config_test.go"},
		[]string{"TS-01-13", "TS-01-14", "TS-01-E10", "TS-01-E12", "TS-01-E13", "TS-01-E14", "TS-01-E15", "TS-01-E17", "TS-01-P7"}, nil)
	addSubtask(&g1, "1.3", "Write validator tests",
		[]string{"internal/validator/validator_test.go"},
		[]string{"TS-01-3", "TS-01-4", "TS-01-E4", "TS-01-E5", "TS-01-E6", "TS-01-P1"}, nil)
	addSubtask(&g1, "1.4", "Write store tests",
		[]string{"internal/store/store_test.go"},
		[]string{"TS-01-6", "TS-01-7", "TS-01-15", "TS-01-17", "TS-01-E7", "TS-01-E8", "TS-01-E16", "TS-01-E18", "TS-01-P2", "TS-01-P4", "TS-01-P5", "TS-01-P8"}, nil)
	addSubtask(&g1, "1.5", "Write middleware, handler, health, and server tests",
		[]string{"internal/middleware/auth_test.go", "internal/handler/audit_test.go", "internal/health/health_test.go", "internal/server/server_test.go"},
		[]string{"TS-01-1", "TS-01-2", "TS-01-5", "TS-01-8", "TS-01-9", "TS-01-10", "TS-01-11", "TS-01-12", "TS-01-16", "TS-01-E1", "TS-01-E2", "TS-01-E3", "TS-01-E9", "TS-01-E11", "TS-01-P3", "TS-01-P6"}, nil)
	addSubtask(&g1, "1.6", "Write integration smoke tests",
		[]string{"internal/integration_test.go"},
		[]string{"TS-01-SMOKE-1", "TS-01-SMOKE-2", "TS-01-SMOKE-3", "TS-01-SMOKE-4", "TS-01-P9"}, nil)
	g1.Verification = speclib.NewVerificationSubtask("1.V", []string{
		"All spec tests exist and are syntactically valid: `go build ./...`",
		"All spec tests FAIL (red) — no implementation yet: `go test ./... 2>&1 | grep FAIL`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g1))

	// Group 2: Implement data models and configuration
	g2 := speclib.NewTaskGroup(2, speclib.TaskGroupStandard, "Implement data models and configuration")
	addSubtask(&g2, "2.1", "Implement AuditEvent model",
		[]string{"Create `internal/model/event.go` with `AuditEvent` struct"},
		nil, []string{"01-REQ-3.1"})
	addSubtask(&g2, "2.2", "Implement Config model and loader",
		[]string{"Create `internal/config/config.go`", "Load(path string) (*Config, error)", "Apply defaults and validate"},
		nil, []string{"01-REQ-6.1", "01-REQ-6.2", "01-REQ-6.3", "01-REQ-6.4", "01-REQ-4.5", "01-REQ-6.E1", "01-REQ-6.E2", "01-REQ-9.E1"})
	g2.Verification = speclib.NewVerificationSubtask("2.V", []string{
		"Config tests pass: `go test -v ./internal/config/...`",
		"All existing tests still pass: `go test ./...`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g2))

	// Group 3: Implement SQLite store
	g3 := speclib.NewTaskGroup(3, speclib.TaskGroupStandard, "Implement SQLite store")
	addSubtask(&g3, "3.1", "Implement store initialization",
		[]string{"Create `internal/store/store.go`", "New(dbPath string) (*Store, error)", "WAL mode, table creation, indexes"},
		nil, []string{"01-REQ-3.1", "01-REQ-3.2", "01-REQ-3.3", "01-REQ-3.4"})
	addSubtask(&g3, "3.2", "Implement event insertion",
		[]string{"InsertEvent(ctx, event) error", "Handle UNIQUE constraint violation", "Configure busy timeout"},
		nil, []string{"01-REQ-1.1", "01-REQ-3.E1", "01-REQ-10.1", "01-REQ-10.2"})
	addSubtask(&g3, "3.3", "Implement health ping and retention purge",
		[]string{"Ping(ctx) error", "PurgeOlderThan(ctx, cutoff) (int64, error)", "Close() error"},
		nil, []string{"01-REQ-5.2", "01-REQ-7.1", "01-REQ-7.3"})
	g3.Verification = speclib.NewVerificationSubtask("3.V", []string{
		"Store tests pass: `go test -v ./internal/store/...`",
		"All existing tests still pass: `go test ./...`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g3))

	// Group 4: Implement validator and auth middleware
	g4 := speclib.NewTaskGroup(4, speclib.TaskGroupStandard, "Implement validator and auth middleware")
	addSubtask(&g4, "4.1", "Implement event validator",
		[]string{"Create `internal/validator/validator.go`", "Validate(event model.AuditEvent) error"},
		nil, []string{"01-REQ-2.1", "01-REQ-2.2", "01-REQ-2.3", "01-REQ-2.4", "01-REQ-2.E1", "01-REQ-2.E2", "01-REQ-2.E3"})
	addSubtask(&g4, "4.2", "Implement Bearer auth middleware",
		[]string{"Create `internal/middleware/auth.go`", "BearerAuth(token string) echo.MiddlewareFunc"},
		nil, []string{"01-REQ-4.1", "01-REQ-4.2", "01-REQ-4.3", "01-REQ-4.E1"})
	g4.Verification = speclib.NewVerificationSubtask("4.V", []string{
		"Validator tests pass: `go test -v ./internal/validator/...`",
		"Middleware tests pass: `go test -v ./internal/middleware/...`",
		"All existing tests still pass: `go test ./...`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g4))

	// Group 5: Implement HTTP handlers and server wiring
	g5 := speclib.NewTaskGroup(5, speclib.TaskGroupStandard, "Implement HTTP handlers and server wiring")
	addSubtask(&g5, "5.1", "Implement audit ingest handler",
		[]string{"Create `internal/handler/audit.go`", "AuditHandler.Ingest(c echo.Context) error"},
		nil, []string{"01-REQ-1.1", "01-REQ-1.2", "01-REQ-1.E1", "01-REQ-1.E2", "01-REQ-1.E3"})
	addSubtask(&g5, "5.2", "Implement health handlers",
		[]string{"Create `internal/health/health.go`", "Healthz(c) error", "Readyz(c) error"},
		nil, []string{"01-REQ-5.1", "01-REQ-5.2", "01-REQ-5.E1"})
	addSubtask(&g5, "5.3", "Implement server and route registration",
		[]string{"Create `internal/server/server.go`", "New(cfg, store) *Server", "Start() error, Shutdown(ctx) error"},
		nil, []string{"01-REQ-1.3", "01-REQ-1.4", "01-REQ-5.3", "01-REQ-9.4"})
	g5.Verification = speclib.NewVerificationSubtask("5.V", []string{
		"Handler tests pass: `go test -v ./internal/handler/...`",
		"Health tests pass: `go test -v ./internal/health/...`",
		"Server tests pass: `go test -v ./internal/server/...`",
		"All existing tests still pass: `go test ./...`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g5))

	// Group 6: Implement retention and application entry point
	g6 := speclib.NewTaskGroup(6, speclib.TaskGroupStandard, "Implement retention and application entry point")
	addSubtask(&g6, "6.1", "Implement retention background process",
		[]string{"Create `internal/retention/retention.go`", "StartRetention(ctx, store, interval, retentionDays)"},
		nil, []string{"01-REQ-7.1", "01-REQ-7.2", "01-REQ-7.3", "01-REQ-7.4", "01-REQ-7.E1"})
	addSubtask(&g6, "6.2", "Implement main entry point",
		[]string{"Create `cmd/audit-hub/main.go`", "Parse --config flag, load config, wire dependencies, handle signals"},
		nil, []string{"01-REQ-8.1", "01-REQ-8.2", "01-REQ-8.E1", "01-REQ-9.1", "01-REQ-9.2", "01-REQ-9.3"})
	addSubtask(&g6, "6.3", "Create example configuration file",
		[]string{"Create `config.example.toml` with all fields documented"},
		nil, nil)
	g6.Verification = speclib.NewVerificationSubtask("6.V", []string{
		"Integration smoke tests pass: `go test -v -run Smoke ./internal/...`",
		"Graceful shutdown test passes: `go test -v -run Shutdown ./internal/...`",
		"All existing tests still pass: `go test ./...`",
		"No linter warnings introduced: `go vet ./...`",
	})
	must(t.AddTaskGroup(g6))

	// Group 7: Checkpoint
	g7 := speclib.NewTaskGroup(7, speclib.TaskGroupCheckpoint, "Checkpoint — Core service complete")
	g7.Subtasks = []speclib.Subtask{}
	g7.Verification = speclib.NewVerificationSubtask("7.V", []string{
		"All tests pass: `go test -v -count=1 ./...`",
		"Ask the user if questions arise",
	})
	must(t.AddTaskGroup(g7))

	// Group 8: Wiring verification
	g8 := speclib.NewTaskGroup(8, speclib.TaskGroupWiringVerification, "Wiring verification")
	addSubtask(&g8, "8.1", "Trace every execution path from design.md end-to-end",
		[]string{"For each of the 5 execution paths, verify the entry point actually calls the next function in the chain"},
		nil, nil)
	addSubtask(&g8, "8.2", "Verify return values propagate correctly",
		[]string{"For every function that returns data consumed by a caller, confirm the caller receives and uses the return value"},
		nil, nil)
	addSubtask(&g8, "8.3", "Run the integration smoke tests",
		[]string{"`go test -v -run Smoke ./internal/...`"},
		[]string{"TS-01-SMOKE-1", "TS-01-SMOKE-2", "TS-01-SMOKE-3", "TS-01-SMOKE-4"}, nil)
	addSubtask(&g8, "8.4", "Stub / dead-code audit",
		[]string{"Search for return nil, TODO, stub, NotImplementedError, empty function bodies"},
		nil, nil)
	addSubtask(&g8, "8.5", "Cross-spec entry point verification",
		[]string{"Verify `cmd/audit-hub/main.go` is buildable: `go build ./cmd/audit-hub/`"},
		nil, nil)
	g8.Verification = speclib.NewVerificationSubtask("8.V", []string{
		"All smoke tests pass",
		"No unjustified stubs remain in touched files",
		"All execution paths from design.md are live",
		"All cross-spec entry points are called from production code",
		"All existing tests still pass: `go test -v -count=1 ./...`",
	})
	must(t.AddTaskGroup(g8))
}

func addSubtask(g *speclib.TaskGroup, id, title string, details, testRefs, reqRefs []string) {
	s := speclib.NewSubtask(id, title)
	if details == nil {
		details = []string{}
	}
	if testRefs == nil {
		testRefs = []string{}
	}
	if reqRefs == nil {
		reqRefs = []string{}
	}
	s.Details = details
	s.TestSpecRefs = testRefs
	s.RequirementRefs = reqRefs
	must(g.AddSubtask(s))
}

func addTraceability(t *speclib.Tasks) {
	entries := []struct{ reqID, tsID, taskID string }{
		{"01-REQ-1.1", "TS-01-1", "5.1"},
		{"01-REQ-1.2", "TS-01-2", "5.1"},
		{"01-REQ-1.3", "TS-01-13", "5.3"},
		{"01-REQ-1.4", "TS-01-13", "5.3"},
		{"01-REQ-1.E1", "TS-01-E1", "5.1"},
		{"01-REQ-1.E2", "TS-01-E2", "5.1"},
		{"01-REQ-1.E3", "TS-01-E3", "5.1"},
		{"01-REQ-2.1", "TS-01-3", "4.1"},
		{"01-REQ-2.2", "TS-01-4", "4.1"},
		{"01-REQ-2.3", "TS-01-5", "4.1"},
		{"01-REQ-2.4", "TS-01-4", "4.1"},
		{"01-REQ-2.E1", "TS-01-E4", "4.1"},
		{"01-REQ-2.E2", "TS-01-E5", "4.1"},
		{"01-REQ-2.E3", "TS-01-E6", "4.1"},
		{"01-REQ-3.1", "TS-01-6", "3.1"},
		{"01-REQ-3.2", "TS-01-6", "3.1"},
		{"01-REQ-3.3", "TS-01-6", "3.1"},
		{"01-REQ-3.4", "TS-01-7", "3.1"},
		{"01-REQ-3.E1", "TS-01-E7", "3.2"},
		{"01-REQ-3.E2", "TS-01-E8", "3.1"},
		{"01-REQ-4.1", "TS-01-8", "4.2"},
		{"01-REQ-4.2", "TS-01-8", "4.2"},
		{"01-REQ-4.3", "TS-01-9", "4.2"},
		{"01-REQ-4.4", "TS-01-13", "2.2"},
		{"01-REQ-4.5", "TS-01-E10", "2.2"},
		{"01-REQ-4.E1", "TS-01-E9", "4.2"},
		{"01-REQ-5.1", "TS-01-10", "5.2"},
		{"01-REQ-5.2", "TS-01-11", "5.2"},
		{"01-REQ-5.3", "TS-01-12", "5.3"},
		{"01-REQ-5.E1", "TS-01-E11", "5.2"},
		{"01-REQ-6.1", "TS-01-13", "2.2"},
		{"01-REQ-6.2", "TS-01-13", "2.2"},
		{"01-REQ-6.3", "TS-01-E12", "2.2"},
		{"01-REQ-6.4", "TS-01-E13", "2.2"},
		{"01-REQ-6.E1", "TS-01-E14", "2.2"},
		{"01-REQ-6.E2", "TS-01-E15", "2.2"},
		{"01-REQ-7.1", "TS-01-15", "6.1"},
		{"01-REQ-7.2", "TS-01-SMOKE-3", "6.1"},
		{"01-REQ-7.3", "TS-01-15", "3.3"},
		{"01-REQ-7.4", "TS-01-13", "2.2"},
		{"01-REQ-7.E1", "TS-01-E16", "6.1"},
		{"01-REQ-8.1", "TS-01-P9", "6.2"},
		{"01-REQ-8.2", "TS-01-P9", "6.2"},
		{"01-REQ-8.E1", "TS-01-P9", "6.2"},
		{"01-REQ-9.1", "TS-01-16", "6.2"},
		{"01-REQ-9.2", "TS-01-13", "6.2"},
		{"01-REQ-9.3", "TS-01-16", "6.2"},
		{"01-REQ-9.4", "TS-01-16", "5.3"},
		{"01-REQ-9.E1", "TS-01-E17", "2.2"},
		{"01-REQ-10.1", "TS-01-17", "3.1"},
		{"01-REQ-10.2", "TS-01-E18", "3.2"},
		{"01-REQ-10.E1", "TS-01-E18", "3.2"},
	}
	for _, e := range entries {
		must(t.AddTraceabilityEntry(speclib.NewTraceabilityEntry(e.reqID, e.tsID, e.taskID)))
	}
}

func must(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
