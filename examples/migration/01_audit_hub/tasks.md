# Implementation Plan: Audit Hub

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

The implementation follows a test-first approach. Task group 1 scaffolds the
Go module and writes all failing tests from `test_spec.md`. Subsequent groups
implement modules in dependency order: data models and config first (no
dependencies), then store (depends on models), then validator, middleware,
handlers, server wiring, retention, and finally the application entry point.

## Test Commands

- Spec tests: `go test ./...`
- Unit tests: `go test ./internal/... -short`
- Property tests: `go test ./internal/... -run Property`
- Integration tests: `go test ./internal/... -run Smoke`
- All tests: `go test -v -count=1 ./...`
- Linter: `go vet ./...`

## Tasks

- [x] 1. Write failing spec tests
  - [x] 1.1 Initialize Go module and project structure
    - Run `go mod init github.com/agent-fox/audit-hub`
    - Create directory structure: `cmd/audit-hub/`, `internal/config/`,
      `internal/model/`, `internal/store/`, `internal/validator/`,
      `internal/middleware/`, `internal/handler/`, `internal/health/`,
      `internal/retention/`, `internal/server/`
    - Add initial dependencies: `echo/v4`, `modernc.org/sqlite`,
      `github.com/BurntSushi/toml`, `github.com/sirupsen/logrus`,
      `pgregory.net/rapid`
    - _Test Spec: N/A (scaffolding)_

  - [x] 1.2 Write config tests
    - `internal/config/config_test.go`: TS-01-13 (defaults), TS-01-14
      (overrides), TS-01-E10 (missing token), TS-01-E12 (file not found),
      TS-01-E13 (invalid TOML), TS-01-E14 (retention zero), TS-01-E15
      (port out of range), TS-01-E17 (bad log level), TS-01-P7 (config
      property test)
    - _Test Spec: TS-01-13, TS-01-14, TS-01-E10, TS-01-E12, TS-01-E13, TS-01-E14, TS-01-E15, TS-01-E17, TS-01-P7_

  - [x] 1.3 Write validator tests
    - `internal/validator/validator_test.go`: TS-01-3 (missing fields),
      TS-01-4 (format constraints), TS-01-E4 (no timezone), TS-01-E5
      (null payload), TS-01-E6 (no dot in event_type), TS-01-P1 (schema
      validation property)
    - _Test Spec: TS-01-3, TS-01-4, TS-01-E4, TS-01-E5, TS-01-E6, TS-01-P1_

  - [x] 1.4 Write store tests
    - `internal/store/store_test.go`: TS-01-6 (table creation + WAL),
      TS-01-7 (directory creation), TS-01-15 (retention purge), TS-01-17
      (concurrent writes), TS-01-E7 (duplicate ID), TS-01-E8 (open failure),
      TS-01-E16 (purge error), TS-01-E18 (busy timeout), TS-01-P2 (storage
      integrity), TS-01-P4 (duplicate rejection), TS-01-P5 (retention
      correctness), TS-01-P8 (concurrent safety)
    - _Test Spec: TS-01-6, TS-01-7, TS-01-15, TS-01-17, TS-01-E7, TS-01-E8, TS-01-E16, TS-01-E18, TS-01-P2, TS-01-P4, TS-01-P5, TS-01-P8_

  - [x] 1.5 Write middleware, handler, health, and server tests
    - `internal/middleware/auth_test.go`: TS-01-8 (missing header), TS-01-9
      (wrong token), TS-01-E9 (extra whitespace), TS-01-P3 (auth property)
    - `internal/handler/audit_test.go`: TS-01-1 (happy path), TS-01-2
      (wrong content type), TS-01-5 (optional fields), TS-01-E1 (empty body),
      TS-01-E2 (oversized body), TS-01-E3 (invalid JSON)
    - `internal/health/health_test.go`: TS-01-10 (healthz), TS-01-11
      (readyz 200), TS-01-12 (skip auth), TS-01-E11 (readyz 503), TS-01-P6
      (probe independence)
    - `internal/server/server_test.go`: TS-01-16 (request logging)
    - _Test Spec: TS-01-1, TS-01-2, TS-01-5, TS-01-8, TS-01-9, TS-01-10, TS-01-11, TS-01-12, TS-01-16, TS-01-E1, TS-01-E2, TS-01-E3, TS-01-E9, TS-01-E11, TS-01-P3, TS-01-P6_

  - [x] 1.6 Write integration smoke tests
    - `internal/integration_test.go`: TS-01-SMOKE-1 (end-to-end ingestion),
      TS-01-SMOKE-2 (readiness check), TS-01-SMOKE-3 (retention cycle),
      TS-01-SMOKE-4 (config to running server), TS-01-P9 (graceful shutdown)
    - _Test Spec: TS-01-SMOKE-1, TS-01-SMOKE-2, TS-01-SMOKE-3, TS-01-SMOKE-4, TS-01-P9_

  - [x] 1.V Verify task group 1
    - [x] All spec tests exist and are syntactically valid: `go build ./...`
    - [x] All spec tests FAIL (red) — no implementation yet: `go test ./... 2>&1 | grep FAIL`
    - [x] No linter warnings introduced: `go vet ./...`

---

- [x] 2. Implement data models and configuration
  - [x] 2.1 Implement AuditEvent model
    - Create `internal/model/event.go` with `AuditEvent` struct
    - JSON tags for deserialization from request body
    - `json.RawMessage` for payload field
    - _Requirements: 01-REQ-3.1_

  - [x] 2.2 Implement Config model and loader
    - Create `internal/config/config.go` with `Config`, `ServerConfig`,
      `DatabaseConfig`, `AuthConfig`, `LoggingConfig` structs
    - `Load(path string) (*Config, error)` — reads TOML file, applies
      defaults, validates required fields
    - Apply defaults: port 8080, bind "0.0.0.0", db path "./data/audit.db",
      retention 30, log level "info"
    - Validate: bearer_token non-empty, port 1-65535, retention > 0 (warn
      and default), invalid log level (warn and default)
    - Support `--config` CLI flag (parsed in main, passed to Load)
    - _Requirements: 01-REQ-6.1, 01-REQ-6.2, 01-REQ-6.3, 01-REQ-6.4, 01-REQ-4.5, 01-REQ-6.E1, 01-REQ-6.E2, 01-REQ-9.E1_

  - [x] 2.V Verify task group 2
    - [x] Config tests pass: `go test -v ./internal/config/...`
    - [x] All existing tests still pass: `go test ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-6.1, 01-REQ-6.2, 01-REQ-6.3, 01-REQ-6.4, 01-REQ-4.5, 01-REQ-6.E1, 01-REQ-6.E2, 01-REQ-9.E1 acceptance criteria met

---

- [x] 3. Implement SQLite store
  - [x] 3.1 Implement store initialization
    - Create `internal/store/store.go` with `Store` struct wrapping `*sql.DB`
    - `New(dbPath string) (*Store, error)` — creates parent dirs, opens
      SQLite connection, enables WAL mode, creates events table and indexes
    - Use `modernc.org/sqlite` driver
    - _Requirements: 01-REQ-3.1, 01-REQ-3.2, 01-REQ-3.3, 01-REQ-3.4_

  - [x] 3.2 Implement event insertion
    - `InsertEvent(ctx, event) error` — inserts validated event, sets
      `received_at` to current UTC time
    - Handle UNIQUE constraint violation → return distinguishable error
    - Configure busy timeout (5 seconds) for concurrent write handling
    - _Requirements: 01-REQ-1.1, 01-REQ-3.E1, 01-REQ-10.1, 01-REQ-10.2_

  - [x] 3.3 Implement health ping and retention purge
    - `Ping(ctx) error` — executes `SELECT 1`
    - `PurgeOlderThan(ctx, cutoff) (int64, error)` — deletes expired rows,
      returns count
    - `Close() error` — closes database connection
    - _Requirements: 01-REQ-5.2, 01-REQ-7.1, 01-REQ-7.3_

  - [x] 3.V Verify task group 3
    - [x] Store tests pass: `go test -v ./internal/store/...`
    - [x] All existing tests still pass: `go test ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-3.1, 01-REQ-3.2, 01-REQ-3.3, 01-REQ-3.4, 01-REQ-3.E1, 01-REQ-3.E2, 01-REQ-10.1, 01-REQ-10.2, 01-REQ-10.E1 acceptance criteria met

---

- [x] 4. Implement validator and auth middleware
  - [x] 4.1 Implement event validator
    - Create `internal/validator/validator.go` with
      `Validate(event model.AuditEvent) error`
    - Check required fields non-empty, timestamp ISO 8601 with timezone,
      event_type contains dot, severity in enum, payload non-null
    - _Requirements: 01-REQ-2.1, 01-REQ-2.2, 01-REQ-2.3, 01-REQ-2.4, 01-REQ-2.E1, 01-REQ-2.E2, 01-REQ-2.E3_

  - [x] 4.2 Implement Bearer auth middleware
    - Create `internal/middleware/auth.go` with
      `BearerAuth(token string) echo.MiddlewareFunc`
    - Extract token from Authorization header, trim whitespace, compare
    - Return 401 on missing/invalid header
    - _Requirements: 01-REQ-4.1, 01-REQ-4.2, 01-REQ-4.3, 01-REQ-4.E1_

  - [x] 4.V Verify task group 4
    - [x] Validator tests pass: `go test -v ./internal/validator/...`
    - [x] Middleware tests pass: `go test -v ./internal/middleware/...`
    - [x] All existing tests still pass: `go test ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-2.*, 01-REQ-4.* acceptance criteria met

---

- [x] 5. Implement HTTP handlers and server wiring
  - [x] 5.1 Implement audit ingest handler
    - Create `internal/handler/audit.go` with `AuditHandler` struct
    - `Ingest(c echo.Context) error` — checks content type, reads body
      (limit 1 MB), parses JSON, calls validator, calls store, maps errors
      to HTTP status codes
    - _Requirements: 01-REQ-1.1, 01-REQ-1.2, 01-REQ-1.E1, 01-REQ-1.E2, 01-REQ-1.E3_

  - [x] 5.2 Implement health handlers
    - Create `internal/health/health.go` with `HealthHandler` struct
    - `Healthz(c) error` — returns 200
    - `Readyz(c) error` — calls store.Ping, returns 200 or 503
    - _Requirements: 01-REQ-5.1, 01-REQ-5.2, 01-REQ-5.E1_

  - [x] 5.3 Implement server and route registration
    - Create `internal/server/server.go` with `Server` struct
    - `New(cfg, store) *Server` — creates Echo instance, registers routes,
      wires auth middleware (only on `/api/v1/audit`), adds request logging
      middleware, configures body size limit
    - `Start() error`, `Shutdown(ctx) error`
    - _Requirements: 01-REQ-1.3, 01-REQ-1.4, 01-REQ-5.3, 01-REQ-9.4_

  - [x] 5.V Verify task group 5
    - [x] Handler tests pass: `go test -v ./internal/handler/...`
    - [x] Health tests pass: `go test -v ./internal/health/...`
    - [x] Server tests pass: `go test -v ./internal/server/...`
    - [x] All existing tests still pass: `go test ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-1.*, 01-REQ-5.* acceptance criteria met

---

- [x] 6. Implement retention and application entry point
  - [x] 6.1 Implement retention background process
    - Create `internal/retention/retention.go`
    - `StartRetention(ctx, store, interval, retentionDays)` — launches
      goroutine with hourly ticker, calls PurgeOlderThan, logs results
    - Stops on context cancellation
    - _Requirements: 01-REQ-7.1, 01-REQ-7.2, 01-REQ-7.3, 01-REQ-7.4, 01-REQ-7.E1_

  - [x] 6.2 Implement main entry point
    - Create `cmd/audit-hub/main.go`
    - Parse `--config` flag, load config, configure logrus (JSON formatter,
      log level), initialize store, create server, start retention, log
      startup message, listen for OS signals, graceful shutdown with 15s
      timeout
    - Handle double-signal (second SIGTERM → immediate exit code 1)
    - _Requirements: 01-REQ-8.1, 01-REQ-8.2, 01-REQ-8.E1, 01-REQ-9.1, 01-REQ-9.2, 01-REQ-9.3_

  - [x] 6.3 Create example configuration file
    - Create `config.example.toml` with all fields documented
    - _Requirements: N/A (developer experience)_

  - [x] 6.V Verify task group 6
    - [x] Integration smoke tests pass: `go test -v -run Smoke ./internal/...`
    - [x] Graceful shutdown test passes: `go test -v -run Shutdown ./internal/...`
    - [x] All existing tests still pass: `go test ./...`
    - [x] No linter warnings introduced: `go vet ./...`
    - [x] Requirements 01-REQ-7.*, 01-REQ-8.*, 01-REQ-9.* acceptance criteria met

---

- [x] 7. Checkpoint — Core service complete
  - [x] Ensure all tests pass: `go test -v -count=1 ./...`
  - [x] Ask the user if questions arise
  - [x] Create or update README.md with build/run/config instructions

---

- [x] 8. Wiring verification

  - [x] 8.1 Trace every execution path from design.md end-to-end
    - For each of the 5 execution paths, verify the entry point actually
      calls the next function in the chain (read the calling code, do not
      assume)
    - Confirm no function in the chain is a stub (`return nil`, `return 0`,
      empty function body) that was never replaced
    - Every path must be live in production code — errata or deferrals do
      not satisfy this check
    - _Requirements: all_

  - [x] 8.2 Verify return values propagate correctly
    - For every function in this spec that returns data consumed by a caller,
      confirm the caller receives and uses the return value
    - Grep for callers of each such function; confirm none discards the return
    - Specifically check: `Store.New` returns `(*Store, error)`,
      `Store.PurgeOlderThan` returns `(int64, error)`, `config.Load` returns
      `(*Config, error)`
    - _Requirements: all_

  - [x] 8.3 Run the integration smoke tests
    - All `TS-01-SMOKE-*` tests pass using real components (no stub bypass)
    - `go test -v -run Smoke ./internal/...`
    - _Test Spec: TS-01-SMOKE-1 through TS-01-SMOKE-4_

  - [x] 8.4 Stub / dead-code audit
    - Search all files touched by this spec for: `return nil` on non-Optional
      returns, `// TODO`, `// stub`, `NotImplementedError`, empty function
      bodies
    - Each hit must be either: (a) justified with a comment explaining why
      it is intentional, or (b) replaced with a real implementation
    - Document any intentional stubs here with rationale
    - **Result**: No stubs, TODOs, FIXMEs, or dead code found. All `return nil`
      instances are legitimate success-path returns (createSchema, InsertEvent
      success, Close nil-guard, middleware next-chain, validator success).

  - [x] 8.5 Cross-spec entry point verification
    - This is spec 01 with no upstream dependencies
    - Verify that `cmd/audit-hub/main.go` is the sole entry point and is
      buildable: `go build ./cmd/audit-hub/`
    - _Requirements: all_

  - [x] 8.V Verify wiring group
    - [x] All smoke tests pass
    - [x] No unjustified stubs remain in touched files
    - [x] All execution paths from design.md are live (traceable in code)
    - [x] All cross-spec entry points are called from production code
    - [x] All existing tests still pass: `go test -v -count=1 ./...`

---

### Checkbox States

| Syntax   | Meaning                |
|----------|------------------------|
| `- [ ]`  | Not started (required) |
| `- [ ]*` | Not started (optional) |
| `- [x]`  | Completed              |
| `- [-]`  | In progress            |
| `- [~]`  | Queued                 |

---

## Traceability

| Requirement | Test Spec Entry | Implemented By Task | Verified By Test |
|-------------|-----------------|---------------------|------------------|
| 01-REQ-1.1 | TS-01-1 | 5.1 | `TestIngestValidEvent` |
| 01-REQ-1.2 | TS-01-2 | 5.1 | `TestIngestWrongContentType` |
| 01-REQ-1.3 | TS-01-13 | 5.3, 2.2 | `TestConfigDefaults` |
| 01-REQ-1.4 | TS-01-13 | 5.3, 2.2 | `TestConfigDefaults` |
| 01-REQ-1.E1 | TS-01-E1 | 5.1 | `TestIngestEmptyBody` |
| 01-REQ-1.E2 | TS-01-E2 | 5.1 | `TestIngestOversizedBody` |
| 01-REQ-1.E3 | TS-01-E3 | 5.1 | `TestIngestInvalidJSON` |
| 01-REQ-2.1 | TS-01-3 | 4.1 | `TestValidateMissingFields` |
| 01-REQ-2.2 | TS-01-4 | 4.1 | `TestValidateFieldFormats` |
| 01-REQ-2.3 | TS-01-5 | 4.1, 5.1 | `TestOptionalFieldsDefault` |
| 01-REQ-2.4 | TS-01-4 | 4.1 | `TestValidateFieldFormats` |
| 01-REQ-2.E1 | TS-01-E4 | 4.1 | `TestTimestampNoTimezone` |
| 01-REQ-2.E2 | TS-01-E5 | 4.1 | `TestNullPayload` |
| 01-REQ-2.E3 | TS-01-E6 | 4.1 | `TestEventTypeNoDot` |
| 01-REQ-3.1 | TS-01-6 | 3.1 | `TestStoreCreatesTable` |
| 01-REQ-3.2 | TS-01-6 | 3.1 | `TestStoreWALMode` |
| 01-REQ-3.3 | TS-01-6, TS-01-7 | 3.1 | `TestStoreAutoCreateDB` |
| 01-REQ-3.4 | TS-01-7 | 3.1 | `TestStoreCreatesParentDirs` |
| 01-REQ-3.E1 | TS-01-E7 | 3.2 | `TestDuplicateEventID` |
| 01-REQ-3.E2 | TS-01-E8 | 3.1 | `TestStoreOpenFailure` |
| 01-REQ-4.1 | TS-01-8 | 4.2 | `TestAuthMissingHeader` |
| 01-REQ-4.2 | TS-01-8 | 4.2 | `TestAuthMissingHeader` |
| 01-REQ-4.3 | TS-01-9 | 4.2 | `TestAuthWrongToken` |
| 01-REQ-4.4 | TS-01-13 | 2.2 | `TestConfigDefaults` |
| 01-REQ-4.5 | TS-01-E10 | 2.2 | `TestConfigMissingToken` |
| 01-REQ-4.E1 | TS-01-E9 | 4.2 | `TestAuthExtraWhitespace` |
| 01-REQ-5.1 | TS-01-10 | 5.2 | `TestHealthz` |
| 01-REQ-5.2 | TS-01-11 | 5.2 | `TestReadyzHealthy` |
| 01-REQ-5.3 | TS-01-12 | 5.3 | `TestHealthSkipsAuth` |
| 01-REQ-5.E1 | TS-01-E11 | 5.2 | `TestReadyzDBDown` |
| 01-REQ-6.1 | TS-01-13 | 2.2 | `TestConfigDefaults` |
| 01-REQ-6.2 | TS-01-13, TS-01-14 | 2.2 | `TestConfigDefaults`, `TestConfigOverrides` |
| 01-REQ-6.3 | TS-01-E12 | 2.2 | `TestConfigFileNotFound` |
| 01-REQ-6.4 | TS-01-E13 | 2.2 | `TestConfigInvalidTOML` |
| 01-REQ-6.E1 | TS-01-E14 | 2.2 | `TestRetentionDaysZero` |
| 01-REQ-6.E2 | TS-01-E15 | 2.2 | `TestPortOutOfRange` |
| 01-REQ-7.1 | TS-01-15 | 6.1, 3.3 | `TestRetentionPurge` |
| 01-REQ-7.2 | TS-01-SMOKE-3 | 6.1 | `TestSmokeRetentionCycle` |
| 01-REQ-7.3 | TS-01-15 | 3.3 | `TestRetentionPurge` |
| 01-REQ-7.4 | TS-01-13 | 2.2 | `TestConfigDefaults` |
| 01-REQ-7.E1 | TS-01-E16 | 6.1 | `TestRetentionErrorRecovery` |
| 01-REQ-8.1 | TS-01-P9 | 6.2 | `TestGracefulShutdown` |
| 01-REQ-8.2 | TS-01-P9 | 6.2 | `TestGracefulShutdown` |
| 01-REQ-8.E1 | TS-01-P9 | 6.2 | `TestDoubleSignalExit` |
| 01-REQ-9.1 | TS-01-16 | 6.2 | `TestJSONLogging` |
| 01-REQ-9.2 | TS-01-13 | 6.2 | `TestConfigDefaults` |
| 01-REQ-9.3 | TS-01-16 | 6.2 | `TestStartupLog` |
| 01-REQ-9.4 | TS-01-16 | 5.3 | `TestRequestLogging` |
| 01-REQ-9.E1 | TS-01-E17 | 2.2 | `TestInvalidLogLevel` |
| 01-REQ-10.1 | TS-01-17 | 3.1, 3.2 | `TestConcurrentWrites` |
| 01-REQ-10.2 | TS-01-E18 | 3.2 | `TestBusyTimeout` |
| 01-REQ-10.E1 | TS-01-E18 | 3.2 | `TestBusyTimeoutExhausted` |
| Property 1 | TS-01-P1 | 4.1 | `TestPropertySchemaValidation` |
| Property 2 | TS-01-P2 | 3.2 | `TestPropertyStorageIntegrity` |
| Property 3 | TS-01-P3 | 4.2 | `TestPropertyAuthEnforcement` |
| Property 4 | TS-01-P4 | 3.2 | `TestPropertyDuplicateRejection` |
| Property 5 | TS-01-P5 | 3.3 | `TestPropertyRetention` |
| Property 6 | TS-01-P6 | 5.2, 5.3 | `TestPropertyHealthProbes` |
| Property 7 | TS-01-P7 | 2.2 | `TestPropertyConfigValidation` |
| Property 8 | TS-01-P8 | 3.2 | `TestPropertyConcurrentWrites` |
| Property 9 | TS-01-P9 | 6.2 | `TestPropertyGracefulShutdown` |

## Notes

- Use `modernc.org/sqlite` (pure Go) to avoid CGo dependency — critical for
  clean cross-compilation and container builds.
- All tests should use in-memory SQLite (`:memory:`) except where filesystem
  behavior is under test (directory creation, WAL file presence).
- Property tests use `pgregory.net/rapid` — the Go equivalent of Hypothesis.
- Integration smoke tests use `httptest.NewServer` with the real Echo router
  to avoid port conflicts and enable parallel test execution.
- The Dockerfile should use a multi-stage build: `golang:1.22-alpine` for
  building, `alpine:3.19` for the runtime image.
