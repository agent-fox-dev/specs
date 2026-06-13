## Background

This is a greenfield project — no prior scaffold or template exists for Go services in this repository. The motivation is simply to establish a minimal, working Go service as a starting point ("get the ball rolling") for future development. No existing service is being replaced or migrated.

---

## Intent

Provide a minimal, runnable Go service using the Echo framework that serves as a clean starting point for further development. This is a standalone starter service, not a reusable template library.

---

## Goals

- Expose a `/ping` endpoint that returns a simple, successful response.
- Expose `/healthz` and `/readyz` endpoints compatible with Kubernetes liveness and readiness probes.
- Use the Echo framework with a standard middleware stack (Logger, Recovery, CORS).
- Follow idiomatic Go project layout (`cmd/`, `internal/`, and root-level reusable packages).
- Use Go module path `github.com/agent-fox-dev/srv-skafolding` targeting Go 1.25+.
- Keep the codebase as simple as possible — no unnecessary abstractions or dependencies.

---

## Non-Goals

- No business logic beyond the `/ping` endpoint.
- No authentication or authorisation.
- No database integration.
- No configuration management or environment variable parsing.
- No deployment manifests (Kubernetes YAML, Helm charts, etc.).
- No metrics or observability endpoints (e.g., `/metrics`).
- No rate limiting or advanced security middleware beyond CORS.
- This is not intended to be a reusable template library consumed by other projects.

---

## Endpoints

| Method | Path       | Description                                      | Kubernetes Probe |
|--------|------------|--------------------------------------------------|------------------|
| GET    | `/ping`    | Returns a simple pong response (e.g., `{"message":"pong"}`). | — |
| GET    | `/healthz` | Liveness probe — confirms the process is alive. Returns `200 OK`. | Liveness |
| GET    | `/readyz`  | Readiness probe — confirms the service is ready to accept traffic. Returns `200 OK`. | Readiness |

---

## Middleware Stack

The Echo instance must be configured with the following middleware, applied globally in this order:

1. **Logger** (`echo/middleware.Logger`) — structured request/response logging.
2. **Recovery** (`echo/middleware.Recover`) — catches panics and returns a `500` response to prevent process crashes.
3. **CORS** (`echo/middleware.CORS`) — enables cross-origin resource sharing with Echo's default CORS configuration.

No additional middleware (e.g., rate limiting, Helmet, JWT) is in scope.

---

## Project Layout

The repository must follow standard Go project conventions:

```
srv-skafolding/
├── cmd/
│   └── server/
│       └── main.go          # Entry point — wires up Echo, middleware, routes, and starts the HTTP server.
├── internal/
│   └── handler/
│       └── handler.go       # Internal HTTP handler implementations (ping, healthz, readyz).
├── go.mod                   # Module: github.com/agent-fox-dev/srv-skafolding, Go 1.25+
├── go.sum
└── README.md
```

- `cmd/` contains only entry points (i.e., `main` packages).
- `internal/` contains all code that is private to this service and must not be imported by external projects.
- Any code intended to be reusable by other projects in future (e.g., an `api/` or `auth/` package) would live in dedicated root-level folders. No such packages are in scope for this initial scaffold.

---

## Technical Specification

- **Language:** Go 1.25+
- **Module path:** `github.com/agent-fox-dev/srv-skafolding`
- **Framework:** [Echo](https://echo.labstack.com/) (latest stable v4)
- **Middleware:** Logger, Recovery, CORS (Echo built-ins only)
- **Configuration:** None — no environment variable parsing or config struct. The HTTP server may use a hardcoded default address (e.g., `:8080`).
- **Dependencies:** Minimal — only Echo and its standard library dependencies.

---

## Acceptance Criteria

1. `go build ./...` succeeds with no errors.
2. Running `cmd/server/main.go` starts an HTTP server.
3. `GET /ping` returns `200 OK` with a JSON body (e.g., `{"message":"pong"}`).
4. `GET /healthz` returns `200 OK`.
5. `GET /readyz` returns `200 OK`.
6. Logger, Recovery, and CORS middleware are active for all routes.
7. A panic in a handler does not crash the process (Recovery middleware catches it).
8. The project structure matches the layout defined above.

---

# Requirements: 01_skafolding

## Introduction

This artifact defines the requirements for the srv-skafolding service — a minimal, greenfield Go service built on the Echo framework. It serves as a clean starting point for future development by exposing three HTTP endpoints (/ping, /healthz, /readyz), applying a standard middleware stack (Logger, Recovery, CORS), and following idiomatic Go project layout conventions. No business logic, authentication, database integration, or deployment infrastructure is in scope.

## Glossary

| Term | Definition |
|------|-----------|
| /healthz | An HTTP GET endpoint used as a Kubernetes liveness probe; returns 200 OK to confirm the process is alive. |
| /ping | An HTTP GET endpoint that returns a JSON pong response, confirming the service is reachable. |
| /readyz | An HTTP GET endpoint used as a Kubernetes readiness probe; returns 200 OK to confirm the service is ready to accept traffic. |
| CORS | Cross-Origin Resource Sharing — Echo's built-in middleware (echo/middleware.CORS) that adds the appropriate HTTP headers to allow browsers to make cross-origin requests to the service. |
| Echo | A high-performance, minimalist Go web framework (labstack/echo v4) used to define routes, apply middleware, and serve HTTP requests. |
| Logger | Echo's built-in middleware (echo/middleware.Logger) that emits structured request/response log lines for every HTTP transaction. |
| Recovery | Echo's built-in middleware (echo/middleware.Recover) that catches panics occurring inside handlers and returns a 500 Internal Server Error response, preventing process crashes. |
| cmd/ | A top-level directory that contains only main packages (entry points) for the service. |
| go.mod | The Go module definition file declaring the module path (github.com/agent-fox-dev/srv-skafolding) and the minimum Go version (1.25+). |
| go.sum | The Go checksum database file that records the expected cryptographic hashes of module dependencies. |
| handler.go | The file at internal/handler/handler.go that contains all HTTP handler implementations for the ping, healthz, and readyz endpoints. |
| hardcoded default address | The fixed listen address (e.g., :8080) used by the HTTP server in the absence of any configuration management or environment variable parsing. |
| internal/ | A top-level directory whose packages are private to this module and cannot be imported by external projects, as enforced by the Go toolchain. |
| liveness probe | A Kubernetes mechanism that periodically calls /healthz to determine whether the container process should be restarted. |
| main.go | The service entry point located at cmd/server/main.go; responsible for wiring up Echo, registering middleware and routes, and starting the HTTP server. |
| middleware | Functions that wrap HTTP handlers to provide cross-cutting concerns such as logging, panic recovery, and CORS enforcement, applied globally to all routes in a defined order. |
| module path | The canonical import path of the Go module, declared in go.mod as github.com/agent-fox-dev/srv-skafolding. |
| panic | A Go runtime condition in which a goroutine terminates abnormally; the Recovery middleware catches panics in handlers so the server process continues running. |
| pong response | The JSON payload {"message":"pong"} returned by the /ping endpoint. |
| readiness probe | A Kubernetes mechanism that periodically calls /readyz to determine whether the container should receive incoming traffic. |

## Requirements

### REQ-001: 

**User Story:** As a developer, I want have a minimal Go service scaffold that compiles and runs out of the box, so that I can use it as a clean starting point for further development without setting up boilerplate from scratch.

#### Acceptance Criteria

1. [REQ-001-AC-01] THE The repository SHALL must contain a valid `go.mod` file declaring module path `github.com/agent-fox-dev/srv-skafolding` and a minimum Go version of 1.25 or higher
2. [REQ-001-AC-02] THE The build command `go build ./...` SHALL must complete successfully with zero errors against the repository root
3. [REQ-001-AC-03] THE The repository SHALL must follow the prescribed project layout: `cmd/server/main.go`, `internal/handler/handler.go`, `go.mod`, `go.sum`, and `README.md` present at their specified paths
4. [REQ-001-AC-04] THE `cmd/` directory SHALL must contain only `main` packages (entry points) and no library code
5. [REQ-001-AC-05] THE `internal/` directory SHALL must contain all service-private code and must not be importable by external Go modules

#### Edge Cases

1. [REQ-001-EC-01] IF a third-party dependency other than Echo (labstack/echo v4) or its own transitive dependencies is added to go.mod, THEN THE The repository SHALL must not introduce any dependency beyond the Echo framework and its transitive standard-library dependencies

### REQ-002: 

**User Story:** As a API consumer, I want call GET /ping and receive a JSON pong response, so that I can verify that the service is reachable and responding correctly.

#### Acceptance Criteria

1. [REQ-002-AC-01] WHEN a client sends GET /ping, THE The service SHALL must return HTTP status 200 OK with a JSON body `{"message":"pong"}` and a `Content-Type: application/json` header AND return HTTP 200 OK; body: {"message":"pong"}; Content-Type: application/json
2. [REQ-002-AC-02] THE The `/ping` handler SHALL must be implemented inside `internal/handler/handler.go` and registered on the `Echo` instance in `main.go`

#### Edge Cases

1. [REQ-002-EC-01] IF a client sends a non-GET HTTP method (e.g., POST, PUT, DELETE) to /ping, THEN THE The `/ping` endpoint SHALL must return HTTP 405 Method Not Allowed AND return HTTP 405 Method Not Allowed

### REQ-003: 

**User Story:** As a Kubernetes operator, I want have a GET /healthz endpoint that returns 200 OK, so that the liveness probe can confirm the process is alive and avoid unnecessary restarts.

#### Acceptance Criteria

1. [REQ-003-AC-01] WHEN a client sends GET /healthz, THE The service SHALL must return HTTP status 200 OK AND return HTTP 200 OK
2. [REQ-003-AC-02] THE The `/healthz` handler SHALL must be implemented inside `internal/handler/handler.go` and registered on the `Echo` instance in `main.go`

#### Edge Cases

1. [REQ-003-EC-01] IF a client sends a non-GET HTTP method to /healthz, THEN THE The `/healthz` endpoint SHALL must return HTTP 405 Method Not Allowed AND return HTTP 405 Method Not Allowed

### REQ-004: 

**User Story:** As a Kubernetes operator, I want have a GET /readyz endpoint that returns 200 OK, so that the readiness probe can confirm the service is ready to accept traffic before routing requests to it.

#### Acceptance Criteria

1. [REQ-004-AC-01] WHEN a client sends GET /readyz, THE The service SHALL must return HTTP status 200 OK AND return HTTP 200 OK
2. [REQ-004-AC-02] THE The `/readyz` handler SHALL must be implemented inside `internal/handler/handler.go` and registered on the `Echo` instance in `main.go`

#### Edge Cases

1. [REQ-004-EC-01] IF a client sends a non-GET HTTP method to /readyz, THEN THE The `/readyz` endpoint SHALL must return HTTP 405 Method Not Allowed AND return HTTP 405 Method Not Allowed

### REQ-005: 

**User Story:** As a developer, I want have Logger, Recovery, and CORS middleware applied globally to all routes in the correct order, so that every request is logged, panics are caught without crashing the process, and cross-origin requests are handled correctly.

#### Acceptance Criteria

1. [REQ-005-AC-01] THE The `Echo` instance in `main.go` SHALL must register `Logger` middleware first, `Recovery` middleware second, and `CORS` middleware third, all using Echo's built-in middleware package
2. [REQ-005-AC-02] WHEN any HTTP request is received, THE The `Logger` middleware SHALL must emit a structured log line containing at minimum the HTTP method, request path, and response status code
3. [REQ-005-AC-03] WHEN a handler panics during request processing, THE The `Recovery` middleware SHALL must catch the `panic`, return HTTP 500 Internal Server Error to the client, and allow the server process to continue handling subsequent requests AND return HTTP 500 Internal Server Error; server process remains running
4. [REQ-005-AC-04] WHEN a cross-origin HTTP request or preflight OPTIONS request is received, THE The `CORS` middleware SHALL must respond with the appropriate CORS headers using Echo's default CORS configuration AND return Appropriate Access-Control-* response headers present
5. [REQ-005-AC-05] THE The middleware stack SHALL must not include any middleware beyond Logger, Recovery, and CORS (e.g., no rate limiting, Helmet, or JWT middleware)

#### Edge Cases

1. [REQ-005-EC-01] IF a `panic` occurs in any registered handler, THEN THE The server process SHALL must not terminate or become unresponsive AND return Server process remains alive; subsequent requests are handled normally
2. [REQ-005-EC-02] WHEN a handler panics and Recovery returns a 500 response, THE The `Logger` middleware SHALL must still emit a log entry for the failed request, including the resulting 500 status code

### REQ-006: 

**User Story:** As a developer, I want have the HTTP server start and listen on a hardcoded default address without any configuration, so that the service can be run immediately with go run ./cmd/server without needing to set environment variables or config files.

#### Acceptance Criteria

1. [REQ-006-AC-01] WHEN the service binary is executed, THE `main.go` SHALL must start an HTTP server listening on the `hardcoded default address` `:8080` and begin accepting connections AND return HTTP server listening on :8080
2. [REQ-006-AC-02] THE The service SHALL must perform no environment variable parsing, flag parsing, or configuration file reading at startup

#### Edge Cases

1. [REQ-006-EC-01] IF port :8080 is already in use when the service starts, THEN THE `main.go` SHALL must surface the error (e.g., log it) and exit with a non-zero status code AND return Non-zero exit code; error message surfaced to stderr or the logger

## Correctness Properties

### CP-001: 

*For any* HTTP request sent to any registered route
*Invariant:* All three middleware components — `Logger`, `Recovery`, and `CORS` — are executed for every request before the route handler is invoked, in the order Logger → Recovery → CORS.

**Validates:** REQ-005-AC-01, REQ-005-AC-02, REQ-005-AC-04

### CP-002: 

*For any* execution of any handler registered on the `Echo` instance
*Invariant:* A `panic` in the handler never propagates beyond the `Recovery` middleware; the server process remains running and the response to the panicking request is always HTTP 500.

**Validates:** REQ-005-AC-03, REQ-005-EC-01, EH-001

### CP-003: 

*For any* GET request to `/ping`
*Invariant:* The response status is always 200 OK and the body is always the JSON object `{"message":"pong"}` with `Content-Type: application/json`.

**Validates:** REQ-002-AC-01

### CP-004: 

*For any* GET request to `/healthz` or `/readyz`
*Invariant:* The response status is always 200 OK, regardless of when during the process lifetime the probe is issued.

**Validates:** REQ-003-AC-01, REQ-004-AC-01

### CP-005: 

*For any* build invocation `go build ./...`
*Invariant:* The command exits with status 0 and produces no error output, confirming the module path, Go version constraint, and all source files are consistent.

**Validates:** REQ-001-AC-01, REQ-001-AC-02

### CP-006: 

*For any* package within the `internal/` directory
*Invariant:* No external Go module can import that package; the Go toolchain enforces this boundary via the `internal` import restriction.

**Validates:** REQ-001-AC-05

## Execution Paths

### EP-001: 

1. **Client** Sends GET /ping to the service on :8080
2. **Logger middleware** Records the incoming request
3. **Recovery middleware** Wraps the handler execution to catch any panic
4. **CORS middleware** Evaluates origin and adds CORS response headers
5. **Ping handler (internal/handler/handler.go)** Constructs and returns JSON body {"message":"pong"} with HTTP 200 OK
6. **Logger middleware** Records the response status 200 and completes the log entry
7. **Client** Receives HTTP 200 OK with body {"message":"pong"}

### EP-002: 

1. **Kubernetes liveness probe** Sends GET /healthz to the service on :8080
2. **Logger middleware** Records the incoming request
3. **Recovery middleware** Wraps the handler execution to catch any panic
4. **CORS middleware** Evaluates origin and adds CORS response headers
5. **Healthz handler (internal/handler/handler.go)** Returns HTTP 200 OK
6. **Logger middleware** Records the response status 200
7. **Kubernetes liveness probe** Receives HTTP 200 OK and marks the container as alive

### EP-003: 

1. **Kubernetes readiness probe** Sends GET /readyz to the service on :8080
2. **Logger middleware** Records the incoming request
3. **Recovery middleware** Wraps the handler execution to catch any panic
4. **CORS middleware** Evaluates origin and adds CORS response headers
5. **Readyz handler (internal/handler/handler.go)** Returns HTTP 200 OK
6. **Logger middleware** Records the response status 200
7. **Kubernetes readiness probe** Receives HTTP 200 OK and marks the container as ready to receive traffic

### EP-004: 

1. **Client** Sends a request to a handler that triggers a panic
2. **Logger middleware** Records the incoming request
3. **Recovery middleware** Catches the panic from the handler
4. **Recovery middleware** Returns HTTP 500 Internal Server Error to the client
5. **Logger middleware** Records the response status 500
6. **Server process** Continues running and accepts the next incoming request normally

### EP-005: 

1. **Developer** Runs `go build ./...` from the repository root
2. **Go toolchain** Resolves the module path github.com/agent-fox-dev/srv-skafolding from go.mod
3. **Go toolchain** Compiles cmd/server/main.go and internal/handler/handler.go
4. **Go toolchain** Links the binary with Echo and its transitive dependencies
5. **Go toolchain** Exits with status 0 and no error output

## Error Handling

| ID | Condition | Behavior | Requirement |
|----|-----------|----------|-------------|
| EH-001 | A `panic` occurs inside any registered HTTP handler | The `Recovery` middleware catches the panic, logs the stack trace, and writes an HTTP 500 Internal Server Error response to the client. The server process does not crash and continues to handle subsequent requests. | REQ-005 |
| EH-002 | The `hardcoded default address` `:8080` is already bound by another process when the service starts | `main.go` receives a non-nil error from the Echo Start call, surfaces the error message (e.g., via log.Fatal or Echo's error logger), and exits with a non-zero status code. | REQ-006 |
| EH-003 | A client sends an HTTP method other than GET to `/ping`, `/healthz`, or `/readyz` | Echo's router returns HTTP 405 Method Not Allowed. No handler logic is invoked. | REQ-002 |
| EH-004 | A client requests a path not registered on the `Echo` instance | Echo's default not-found handler returns HTTP 404 Not Found. | REQ-002 |

---

# Test Specification: 01_skafolding

## Test Cases

### TC-001: 

**Requirement:** REQ-002-AC-01
**Type:** functional

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "GET",
  "path": "/ping"
}`

**Expected:** `{
  "body": {
    "message": "pong"
  },
  "headers": {
    "Content-Type": "application/json"
  },
  "status": 200
}`

**Assertion pseudocode:**

```
resp = httpGet(':8080/ping'); assert resp.status == 200; assert json(resp.body) == {"message":"pong"}; assert resp.headers['Content-Type'] contains 'application/json'
```

### TC-002: 

**Requirement:** REQ-003-AC-01
**Type:** functional

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "GET",
  "path": "/healthz"
}`

**Expected:** `{
  "status": 200
}`

**Assertion pseudocode:**

```
resp = httpGet(':8080/healthz'); assert resp.status == 200
```

### TC-003: 

**Requirement:** REQ-004-AC-01
**Type:** functional

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "GET",
  "path": "/readyz"
}`

**Expected:** `{
  "status": 200
}`

**Assertion pseudocode:**

```
resp = httpGet(':8080/readyz'); assert resp.status == 200
```

### TC-004: 

**Requirement:** REQ-005-AC-02
**Type:** functional

**Preconditions:**

- Service is running
- Logger middleware is active
- Log output is captured

**Input:** `{
  "method": "GET",
  "path": "/ping"
}`

**Expected:** `{
  "log_line_contains": [
    "GET",
    "/ping",
    "200"
  ]
}`

**Assertion pseudocode:**

```
capturedLogs = captureStdout(); httpGet(':8080/ping'); assert capturedLogs contains 'GET'; assert capturedLogs contains '/ping'; assert capturedLogs contains '200'
```

### TC-005: 

**Requirement:** REQ-005-AC-03
**Type:** functional

**Preconditions:**

- Service is running with Recovery middleware active
- A test route /panic-test is registered that calls panic('test panic')

**Input:** `{
  "method": "GET",
  "path": "/panic-test"
}`

**Expected:** `{
  "server_still_running": true,
  "status": 500
}`

**Assertion pseudocode:**

```
resp = httpGet(':8080/panic-test'); assert resp.status == 500; resp2 = httpGet(':8080/ping'); assert resp2.status == 200
```

### TC-006: 

**Requirement:** REQ-005-AC-04
**Type:** functional

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "headers": {
    "Access-Control-Request-Method": "GET",
    "Origin": "http://example.com"
  },
  "method": "OPTIONS",
  "path": "/ping"
}`

**Expected:** `{
  "headers_present": [
    "Access-Control-Allow-Origin"
  ]
}`

**Assertion pseudocode:**

```
resp = httpOptions(':8080/ping', headers={'Origin':'http://example.com','Access-Control-Request-Method':'GET'}); assert 'Access-Control-Allow-Origin' in resp.headers
```

### TC-007: 

**Requirement:** REQ-001-AC-02
**Type:** functional

**Preconditions:**

- Repository root is the working directory
- Go toolchain 1.25+ is installed

**Input:** `{
  "command": "go build ./..."
}`

**Expected:** `{
  "exit_code": 0,
  "stderr": ""
}`

**Assertion pseudocode:**

```
result = exec('go build ./...'); assert result.exit_code == 0; assert result.stderr == ''
```

### TC-008: 

**Requirement:** REQ-001-AC-01
**Type:** functional

**Preconditions:**

- go.mod is present at the repository root

**Input:** `{
  "file": "go.mod"
}`

**Expected:** `{
  "go_version_min": "1.25",
  "module": "github.com/agent-fox-dev/srv-skafolding"
}`

**Assertion pseudocode:**

```
content = readFile('go.mod'); assert content contains 'module github.com/agent-fox-dev/srv-skafolding'; assert goVersionAtLeast(content, '1.25')
```

### TC-009: 

**Requirement:** REQ-001-AC-03
**Type:** functional

**Preconditions:**

- Repository has been cloned or checked out

**Input:** `{
  "paths_to_check": [
    "cmd/server/main.go",
    "internal/handler/handler.go",
    "go.mod",
    "go.sum",
    "README.md"
  ]
}`

**Expected:** `{
  "all_paths_exist": true
}`

**Assertion pseudocode:**

```
for path in ['cmd/server/main.go','internal/handler/handler.go','go.mod','go.sum','README.md']: assert fileExists(path)
```

### TC-010: 

**Requirement:** REQ-001-AC-04
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "directory": "cmd/"
}`

**Expected:** `{
  "all_packages_are_main": true
}`

**Assertion pseudocode:**

```
pkgs = goListPackages('cmd/...'); for pkg in pkgs: assert pkg.packageName == 'main'
```

### TC-011: 

**Requirement:** REQ-006-AC-01
**Type:** functional

**Preconditions:**

- Port :8080 is free
- Service binary has been built

**Input:** `{
  "action": "run service binary"
}`

**Expected:** `{
  "accepts_connections": true,
  "listening_on": ":8080"
}`

**Assertion pseudocode:**

```
proc = startService(); sleep(500ms); resp = httpGet(':8080/ping'); assert resp.status == 200; proc.stop()
```

### TC-012: 

**Requirement:** REQ-006-AC-02
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "file": "cmd/server/main.go"
}`

**Expected:** `{
  "no_config_file_reading": true,
  "no_env_var_parsing": true,
  "no_flag_parsing": true
}`

**Assertion pseudocode:**

```
src = readFile('cmd/server/main.go'); assert 'os.Getenv' not in src; assert 'flag.Parse' not in src; assert 'os.Open' not in src
```

### TC-013: 

**Requirement:** REQ-005-AC-01
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "file": "cmd/server/main.go"
}`

**Expected:** `{
  "middleware_order": [
    "Logger",
    "Recover",
    "CORS"
  ]
}`

**Assertion pseudocode:**

```
src = readFile('cmd/server/main.go'); posLogger = src.indexOf('middleware.Logger'); posRecover = src.indexOf('middleware.Recover'); posCORS = src.indexOf('middleware.CORS'); assert posLogger < posRecover; assert posRecover < posCORS
```

### TC-014: 

**Requirement:** REQ-002-AC-02
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "files": [
    "internal/handler/handler.go",
    "cmd/server/main.go"
  ]
}`

**Expected:** `{
  "ping_handler_in_internal": true,
  "ping_registered_in_main": true
}`

**Assertion pseudocode:**

```
handlerSrc = readFile('internal/handler/handler.go'); assert handlerSrc defines a ping handler function; mainSrc = readFile('cmd/server/main.go'); assert mainSrc registers GET /ping route
```

### TC-015: 

**Requirement:** REQ-003-AC-02
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "files": [
    "internal/handler/handler.go",
    "cmd/server/main.go"
  ]
}`

**Expected:** `{
  "healthz_handler_in_internal": true,
  "healthz_registered_in_main": true
}`

**Assertion pseudocode:**

```
handlerSrc = readFile('internal/handler/handler.go'); assert handlerSrc defines a healthz handler function; mainSrc = readFile('cmd/server/main.go'); assert mainSrc registers GET /healthz route
```

### TC-016: 

**Requirement:** REQ-004-AC-02
**Type:** functional

**Preconditions:**

- Repository source is available

**Input:** `{
  "files": [
    "internal/handler/handler.go",
    "cmd/server/main.go"
  ]
}`

**Expected:** `{
  "readyz_handler_in_internal": true,
  "readyz_registered_in_main": true
}`

**Assertion pseudocode:**

```
handlerSrc = readFile('internal/handler/handler.go'); assert handlerSrc defines a readyz handler function; mainSrc = readFile('cmd/server/main.go'); assert mainSrc registers GET /readyz route
```

## Property Tests

### PT-001: 

**Property:** CP-003

**Validates:** REQ-002-AC-01, CP-003

**For any:** Any valid HTTP GET request to /ping (varying headers, query params, user-agents)

**Invariant check:** assert response.status == 200 AND json(response.body) == {"message":"pong"} AND response.headers['Content-Type'] contains 'application/json'

### PT-002: 

**Property:** CP-004

**Validates:** REQ-003-AC-01, REQ-004-AC-01, CP-004

**For any:** Any valid HTTP GET request to /healthz or /readyz (varying headers, timing during server lifetime)

**Invariant check:** assert response.status == 200

### PT-003: 

**Property:** CP-001

**Validates:** REQ-005-AC-01, REQ-005-AC-02, REQ-005-AC-04, CP-001

**For any:** Any HTTP request to any registered route (/ping, /healthz, /readyz)

**Invariant check:** assert Logger middleware emitted a log line AND CORS headers present in response AND (if panic occurred: Recovery returned 500)

### PT-004: 

**Property:** CP-002

**Validates:** REQ-005-AC-03, REQ-005-EC-01, CP-002

**For any:** Any handler that calls panic() with any value (string, error, nil, integer)

**Invariant check:** assert response.status == 500 AND server process is still alive (subsequent GET /ping returns 200)

### PT-005: 

**Property:** CP-005

**Validates:** REQ-001-AC-01, REQ-001-AC-02, CP-005

**For any:** Any state of the repository after any code change (property: build must not regress)

**Invariant check:** assert exec('go build ./...').exit_code == 0

### PT-006: 

**Property:** CP-006

**Validates:** REQ-001-AC-05, CP-006

**For any:** Any external Go module path attempting to import any package under internal/

**Invariant check:** assert go build of external module exits non-zero with 'use of internal package' error

## Edge Case Tests

### ECT-001: 

**Requirement:** REQ-002-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "POST",
  "path": "/ping"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpPost(':8080/ping', body={}); assert resp.status == 405
```

### ECT-002: 

**Requirement:** REQ-002-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "PUT",
  "path": "/ping"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpPut(':8080/ping', body={}); assert resp.status == 405
```

### ECT-003: 

**Requirement:** REQ-002-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "DELETE",
  "path": "/ping"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpDelete(':8080/ping'); assert resp.status == 405
```

### ECT-004: 

**Requirement:** REQ-003-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "POST",
  "path": "/healthz"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpPost(':8080/healthz', body={}); assert resp.status == 405
```

### ECT-005: 

**Requirement:** REQ-004-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "POST",
  "path": "/readyz"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpPost(':8080/readyz', body={}); assert resp.status == 405
```

### ECT-006: 

**Requirement:** REQ-005-EC-01
**Type:** negative

**Preconditions:**

- Service is running with Recovery middleware active
- A test route /panic-test is registered that calls panic('simulated failure')

**Input:** `[
  {
    "method": "GET",
    "path": "/panic-test"
  },
  {
    "method": "GET",
    "path": "/ping"
  }
]`

**Expected:** `{
  "first_response_status": 500,
  "second_response_status": 200,
  "server_process_alive": true
}`

**Assertion pseudocode:**

```
resp1 = httpGet(':8080/panic-test'); assert resp1.status == 500; resp2 = httpGet(':8080/ping'); assert resp2.status == 200
```

### ECT-007: 

**Requirement:** REQ-005-EC-02
**Type:** negative

**Preconditions:**

- Service is running
- Log output is captured
- A test route /panic-test panics

**Input:** `{
  "method": "GET",
  "path": "/panic-test"
}`

**Expected:** `{
  "log_contains_500": true
}`

**Assertion pseudocode:**

```
capturedLogs = captureStdout(); httpGet(':8080/panic-test'); assert capturedLogs contains '500'
```

### ECT-008: 

**Requirement:** REQ-006-EC-01
**Type:** negative

**Preconditions:**

- Port :8080 is already bound by another process

**Input:** `{
  "action": "start the service binary"
}`

**Expected:** `{
  "error_message_surfaced": true,
  "exit_code_nonzero": true
}`

**Assertion pseudocode:**

```
bindPort(':8080'); result = startService(); waitForExit(result); assert result.exit_code != 0; assert result.stderr or result.stdout contains error message about :8080
```

### ECT-009: 

**Requirement:** REQ-001-EC-01
**Type:** negative

**Preconditions:**

- go.mod is present

**Input:** `{
  "file": "go.mod"
}`

**Expected:** `{
  "only_echo_and_transitive_deps": true
}`

**Assertion pseudocode:**

```
deps = goListModDependencies('go.mod'); nonEchoDeps = [d for d in deps if not isEchoOrTransitive(d)]; assert len(nonEchoDeps) == 0
```

### ECT-010: 

**Requirement:** REQ-005-AC-05
**Type:** negative

**Preconditions:**

- Repository source is available

**Input:** `{
  "file": "cmd/server/main.go"
}`

**Expected:** `{
  "no_extra_middleware": true
}`

**Assertion pseudocode:**

```
src = readFile('cmd/server/main.go'); forbiddenMiddleware = ['RateLimiter','Helmet','JWT','BasicAuth','KeyAuth','BodyLimit']; for m in forbiddenMiddleware: assert m not in src
```

### ECT-011: 

**Requirement:** REQ-001-AC-05
**Type:** negative

**Preconditions:**

- An external test module exists that attempts to import github.com/agent-fox-dev/srv-skafolding/internal/handler

**Input:** `{
  "command": "go build <external-module>"
}`

**Expected:** `{
  "error_contains": "use of internal package",
  "exit_code": 1
}`

**Assertion pseudocode:**

```
result = exec('go build <external-module-importing-internal>'); assert result.exit_code != 0; assert 'use of internal package' in result.stderr
```

### ECT-012: 

**Requirement:** REQ-002-EC-01
**Type:** negative

**Preconditions:**

- Service is running and listening on :8080

**Input:** `{
  "method": "PATCH",
  "path": "/ping"
}`

**Expected:** `{
  "status": 405
}`

**Assertion pseudocode:**

```
resp = httpPatch(':8080/ping', body={}); assert resp.status == 405
```

## Smoke Tests

### ST-001: 

**Execution Path:** EP-001

**Trigger:** `Send GET /ping to the running service on :8080`

**Real components:** cmd/server/main.go, internal/handler/handler.go, Echo router, Logger middleware, Recovery middleware, CORS middleware

**Expected effects:**

- HTTP 200 OK status code returned
- Response body is {"message":"pong"}
- Content-Type header is application/json
- Logger middleware emits a log line containing GET, /ping, and 200

### ST-002: 

**Execution Path:** EP-002

**Trigger:** `Send GET /healthz to the running service on :8080`

**Real components:** cmd/server/main.go, internal/handler/handler.go, Echo router, Logger middleware, Recovery middleware, CORS middleware

**Expected effects:**

- HTTP 200 OK status code returned
- Logger middleware emits a log line containing GET, /healthz, and 200

### ST-003: 

**Execution Path:** EP-003

**Trigger:** `Send GET /readyz to the running service on :8080`

**Real components:** cmd/server/main.go, internal/handler/handler.go, Echo router, Logger middleware, Recovery middleware, CORS middleware

**Expected effects:**

- HTTP 200 OK status code returned
- Logger middleware emits a log line containing GET, /readyz, and 200

### ST-004: 

**Execution Path:** EP-004

**Trigger:** `Send a request to a handler that deliberately calls panic()`

**Real components:** cmd/server/main.go, Echo router, Recovery middleware, Logger middleware

**Mockable:** panicking handler stub registered on a test route

**Expected effects:**

- HTTP 500 Internal Server Error returned to the client
- Server process continues running and accepts subsequent requests
- Logger middleware emits a log entry with status 500

### ST-005: 

**Execution Path:** EP-005

**Trigger:** `Run `go build ./...` from the repository root`

**Real components:** go.mod, cmd/server/main.go, internal/handler/handler.go, Go toolchain

**Expected effects:**

- Command exits with status code 0
- No error output on stderr
- Binary artifact produced without warnings

## Coverage

**Requirements covered:** REQ-001-AC-01, REQ-001-AC-02, REQ-001-AC-03, REQ-001-AC-04, REQ-001-AC-05, REQ-001-EC-01, REQ-002-AC-01, REQ-002-AC-02, REQ-002-EC-01, REQ-003-AC-01, REQ-003-AC-02, REQ-003-EC-01, REQ-004-AC-01, REQ-004-AC-02, REQ-004-EC-01, REQ-005-AC-01, REQ-005-AC-02, REQ-005-AC-03, REQ-005-AC-04, REQ-005-AC-05, REQ-005-EC-01, REQ-005-EC-02, REQ-006-AC-01, REQ-006-AC-02, REQ-006-EC-01

**Properties covered:** CP-001, CP-002, CP-003, CP-004, CP-005, CP-006

**Paths covered:** EP-001, EP-002, EP-003, EP-004, EP-005

**Gaps:** EH-004 (404 for unregistered paths) — not explicitly covered by a dedicated test case; Echo's default behaviour is implicitly trusted but could be added as ECT-013 if desired., Concurrent panic recovery (multiple simultaneous panicking requests) — not modelled; could be added as a load/stress property test., Logger output format validation beyond the presence of method/path/status fields — format is implementation-defined by Echo and not fully specified in the PRD.

---

# Implementation Plan: 01_skafolding

## Test Commands

- Spec tests: `go test ./... -v -run 'TestPing|TestHealthz|TestReadyz|TestMiddleware|TestLayout|TestBuild'`
- All tests: `go build ./... && go test ./... -v -count=1`
- Linter: `golangci-lint run ./...`

## Dependencies

| Depends On | From Group | To Group | Relationship |
|------------|-----------|----------|--------------|
|  | 1 | 2 | TASK-001 (go.mod + Echo dependency) and TASK-002 (directory layout) must be complete before handler implementations in group 2 can be written. |
|  | 2 | 3 | Handler implementations (TASK-004, TASK-005, TASK-006) must exist before `main.go` can import and register them (TASK-007, TASK-008, TASK-009). |
|  | 3 | 4 | All source files (`main.go`, `handler.go`, `go.mod`) must be complete before wiring verification checks can be run. |
|  | 4 | 5 | Wiring verification must pass before the full test suite (group 5) is authored and executed against the implementation. |
|  | 5 | 6 | All tests in group 5 must pass before the final checkpoint (group 6) can be signed off. |

## Tasks

- [ ] 1. 
  - [ ] TASK-001 
    - Create `go.mod` at the repository root declaring module path `github.com/agent-fox-dev/srv-skafolding`.
    - Set the minimum Go version directive to `go 1.25` or higher.
    - Run `go mod tidy` to generate an initial `go.sum` file after Echo is added as a dependency.
    - _Test Spec: TC-008_
    - _Requirements: REQ-001-AC-01_
  - [ ] TASK-002 
    - Create the directory tree: `cmd/server/`, `internal/handler/`.
    - Create stub (empty/minimal) files: `cmd/server/main.go`, `internal/handler/handler.go`, `README.md`.
    - Verify all required paths exist: `cmd/server/main.go`, `internal/handler/handler.go`, `go.mod`, `go.sum`, `README.md`.
    - _Test Spec: TC-009_
    - _Requirements: REQ-001-AC-03_
  - [ ] TASK-003 
    - Add Echo v4 (`github.com/labstack/echo/v4`) as the sole direct dependency in `go.mod`.
    - Confirm no other third-party direct dependencies are introduced.
    - Run `go mod tidy` and inspect `go.mod` to ensure only Echo and its transitive standard-library dependencies are listed.
    - _Test Spec: ECT-009_
    - _Requirements: REQ-001-EC-01_

- [ ] 2. 
  - [ ] TASK-004 
    - In `internal/handler/handler.go`, implement a `Ping` handler function with signature `func Ping(c echo.Context) error`.
    - The handler must return HTTP 200 OK with JSON body `{"message":"pong"}` using `c.JSON(http.StatusOK, ...)`.
    - Ensure the `Content-Type: application/json` header is set automatically by Echo's JSON helper.
    - _Test Spec: TC-001, TC-014_
    - _Requirements: REQ-002-AC-01, REQ-002-AC-02_
  - [ ] TASK-005 
    - In `internal/handler/handler.go`, implement a `Healthz` handler function with signature `func Healthz(c echo.Context) error`.
    - The handler must return HTTP 200 OK with no required body (e.g., `c.NoContent(http.StatusOK)` or a minimal OK body).
    - _Test Spec: TC-002, TC-015_
    - _Requirements: REQ-003-AC-01, REQ-003-AC-02_
  - [ ] TASK-006 
    - In `internal/handler/handler.go`, implement a `Readyz` handler function with signature `func Readyz(c echo.Context) error`.
    - The handler must return HTTP 200 OK with no required body (e.g., `c.NoContent(http.StatusOK)` or a minimal OK body).
    - _Test Spec: TC-003, TC-016_
    - _Requirements: REQ-004-AC-01, REQ-004-AC-02_

- [ ] 3. 
  - [ ] TASK-007 
    - In `cmd/server/main.go`, create an `echo.New()` instance.
    - Register middleware in order: first `middleware.Logger()`, second `middleware.Recover()`, third `middleware.CORS()` — all via `e.Use(...)`.
    - Do not register any additional middleware (no rate limiting, Helmet, JWT, BasicAuth, KeyAuth, BodyLimit, etc.).
    - Use only Echo's built-in `echo/middleware` package for all three middleware components.
    - _Test Spec: TC-013, TC-004, TC-005, TC-006, ECT-010_
    - _Requirements: REQ-005-AC-01, REQ-005-AC-02, REQ-005-AC-03, REQ-005-AC-04, REQ-005-AC-05_
  - [ ] TASK-008 
    - In `cmd/server/main.go`, register the three routes on the Echo instance after middleware setup:
    -   `e.GET("/ping", handler.Ping)`
    -   `e.GET("/healthz", handler.Healthz)`
    -   `e.GET("/readyz", handler.Readyz)`
    - Import `internal/handler` using the full module path `github.com/agent-fox-dev/srv-skafolding/internal/handler`.
    - _Test Spec: TC-014, TC-015, TC-016_
    - _Requirements: REQ-002-AC-02, REQ-003-AC-02, REQ-004-AC-02_
  - [ ] TASK-009 
    - In `cmd/server/main.go`, start the HTTP server using `e.Start(":8080")` with a hardcoded address.
    - Do not read any environment variables, parse CLI flags, or open configuration files at startup.
    - Handle the error returned by `e.Start()`: if non-nil, surface it (e.g., via `e.Logger.Fatal(err)`) and allow the process to exit with a non-zero status code.
    - Confirm `os.Getenv`, `flag.Parse`, and `os.Open` (or equivalent config reads) are absent from `main.go`.
    - _Test Spec: TC-011, TC-012, ECT-008_
    - _Requirements: REQ-006-AC-01, REQ-006-AC-02_

- [ ] 4. 
  - [ ] WV-001 Verify task group 4
    - REQ-001-AC-01: `go.mod` declares module `github.com/agent-fox-dev/srv-skafolding` and `go 1.25` or higher.
    - REQ-001-AC-02: `go build ./...` exits with code 0 and no stderr output.
    - REQ-001-AC-03: Files `cmd/server/main.go`, `internal/handler/handler.go`, `go.mod`, `go.sum`, `README.md` all exist at their specified paths.
    - REQ-001-AC-04: All packages under `cmd/` declare `package main`.
    - REQ-001-AC-05: No external module can import `internal/handler`; toolchain enforces the boundary.
    - REQ-001-EC-01: Only `labstack/echo/v4` and its transitive deps appear as direct dependencies in `go.mod`.
    - REQ-005-AC-01: Middleware registration order in `main.go` is Logger → Recover → CORS.
    - REQ-005-AC-05: No forbidden middleware identifiers (RateLimiter, Helmet, JWT, BasicAuth, KeyAuth, BodyLimit) present in `main.go`.
    - REQ-006-AC-02: `os.Getenv`, `flag.Parse`, and config-file reads are absent from `main.go`.

- [ ] 5. 
  - [ ] TASK-010 
    - Write a CI/shell-level test that runs `go build ./...` from the repository root and asserts exit code 0 with empty stderr.
    - This test must be re-run after every code change to guard against build regressions (property test PT-005).
    - _Test Spec: TC-007, PT-005_
    - _Requirements: REQ-001-AC-02_
  - [ ] TASK-011 
    - Write a Go test (or shell script) that reads `go.mod` and asserts the module path and minimum Go version (TC-008).
    - Write file-existence checks for all required paths: `cmd/server/main.go`, `internal/handler/handler.go`, `go.mod`, `go.sum`, `README.md` (TC-009).
    - Use `go list ./cmd/...` to assert all packages under `cmd/` declare `package main` (TC-010).
    - _Test Spec: TC-008, TC-009, TC-010_
    - _Requirements: REQ-001-AC-01, REQ-001-AC-03, REQ-001-AC-04_
  - [ ] TASK-012 
    - Write a static-analysis / source-inspection test that reads `cmd/server/main.go` and:
    -   1. Asserts `middleware.Logger` appears before `middleware.Recover`, and `middleware.Recover` before `middleware.CORS` (TC-013).
    -   2. Asserts absence of `os.Getenv`, `flag.Parse`, `os.Open` (TC-012).
    -   3. Asserts absence of forbidden middleware identifiers: RateLimiter, Helmet, JWT, BasicAuth, KeyAuth, BodyLimit (ECT-010).
    - _Test Spec: TC-013, TC-012, ECT-010_
    - _Requirements: REQ-005-AC-01, REQ-006-AC-02, REQ-005-AC-05_
  - [ ] TASK-013 
    - Write Go integration tests in a `_test` package that spin up the Echo server (or use `httptest.NewServer`) and assert:
    -   TC-001 / PT-001: GET /ping → 200 OK, body `{"message":"pong"}`, Content-Type `application/json`.
    -   TC-002 / PT-002: GET /healthz → 200 OK.
    -   TC-003 / PT-002: GET /readyz → 200 OK.
    -   TC-014: Source-level check that `Ping` is defined in `internal/handler/handler.go` and registered in `main.go`.
    -   TC-015: Source-level check that `Healthz` is defined in `internal/handler/handler.go` and registered in `main.go`.
    -   TC-016: Source-level check that `Readyz` is defined in `internal/handler/handler.go` and registered in `main.go`.
    - _Test Spec: TC-001, TC-002, TC-003, TC-014, TC-015, TC-016, PT-001, PT-002_
    - _Requirements: REQ-002-AC-01, REQ-002-AC-02, REQ-003-AC-01, REQ-003-AC-02, REQ-004-AC-01, REQ-004-AC-02_
  - [ ] TASK-014 
    - TC-004: Capture log output during a GET /ping request and assert log line contains 'GET', '/ping', '200'.
    - TC-005 / ECT-006 / PT-004: Register a test-only panic route; assert GET to that route returns 500, then assert GET /ping still returns 200 (server alive).
    - TC-006 / PT-003: Send an OPTIONS preflight with `Origin: http://example.com` to /ping; assert `Access-Control-Allow-Origin` header is present in the response.
    - ECT-007: After a panic request, assert the captured log contains '500'.
    - _Test Spec: TC-004, TC-005, TC-006, ECT-006, ECT-007, PT-003, PT-004_
    - _Requirements: REQ-005-AC-02, REQ-005-AC-03, REQ-005-AC-04, REQ-005-EC-01, REQ-005-EC-02_
  - [ ] TASK-015 
    - ECT-001: POST /ping → assert 405 Method Not Allowed.
    - ECT-002: PUT /ping → assert 405 Method Not Allowed.
    - ECT-003: DELETE /ping → assert 405 Method Not Allowed.
    - ECT-012: PATCH /ping → assert 405 Method Not Allowed.
    - ECT-004: POST /healthz → assert 405 Method Not Allowed.
    - ECT-005: POST /readyz → assert 405 Method Not Allowed.
    - _Test Spec: ECT-001, ECT-002, ECT-003, ECT-004, ECT-005, ECT-012_
    - _Requirements: REQ-002-EC-01, REQ-003-EC-01, REQ-004-EC-01_
  - [ ] TASK-016 
    - TC-011: Start the compiled service binary (port :8080 free), wait ~500ms, send GET /ping, assert 200, stop the process.
    - ECT-008: Pre-bind port :8080 with a dummy listener, then start the service binary, wait for it to exit, assert non-zero exit code and error message referencing :8080 in stderr/stdout.
    - _Test Spec: TC-011, ECT-008_
    - _Requirements: REQ-006-AC-01, REQ-006-EC-01_
  - [ ] TASK-017 
    - Create a temporary external Go module in a temp directory that attempts to import `github.com/agent-fox-dev/srv-skafolding/internal/handler`.
    - Run `go build` on that external module and assert exit code is non-zero and stderr contains 'use of internal package'.
    - This validates the Go toolchain enforces the `internal/` boundary (PT-006).
    - _Test Spec: ECT-011, PT-006_
    - _Requirements: REQ-001-AC-05_
  - [ ] TASK-018 
    - Parse `go.mod` and extract all direct `require` directives.
    - Assert the only direct dependency is `github.com/labstack/echo/v4` (plus `github.com/labstack/gommon` and other Echo-owned transitive deps as allowed).
    - Fail if any unrelated third-party direct dependency is found.
    - _Test Spec: ECT-009_
    - _Requirements: REQ-001-EC-01_

- [ ] 6. 
  - [ ] TASK-019 
    - All task groups 1–5 are complete and all tests pass.
    - `go build ./...` exits 0 with no errors (TC-007, ST-005).
    - GET /ping returns 200 with `{"message":"pong"}` and `Content-Type: application/json` (TC-001, ST-001).
    - GET /healthz returns 200 (TC-002, ST-002).
    - GET /readyz returns 200 (TC-003, ST-003).
    - Logger, Recovery, CORS middleware active in correct order for all routes (TC-013, TC-004, TC-005, TC-006).
    - Panic in handler returns 500 and server remains alive (TC-005, ECT-006, ST-004).
    - Non-GET methods on /ping, /healthz, /readyz return 405 (ECT-001 through ECT-005, ECT-012).
    - Project layout matches specification (TC-009).
    - No extra dependencies or middleware (ECT-009, ECT-010).
    - Internal package import boundary enforced by Go toolchain (ECT-011, PT-006).
    - Server starts on :8080 without config (TC-011); exits non-zero on port conflict (ECT-008).
    - _Test Spec: TC-001, TC-002, TC-003, TC-004, TC-005, TC-006, TC-007, TC-008, TC-009, TC-010, TC-011, TC-012, TC-013, TC-014, TC-015, TC-016, ECT-001, ECT-002, ECT-003, ECT-004, ECT-005, ECT-006, ECT-007, ECT-008, ECT-009, ECT-010, ECT-011, ECT-012, PT-001, PT-002, PT-003, PT-004, PT-005, PT-006, ST-001, ST-002, ST-003, ST-004, ST-005_
    - _Requirements: REQ-001-AC-01, REQ-001-AC-02, REQ-001-AC-03, REQ-001-AC-04, REQ-001-AC-05, REQ-001-EC-01, REQ-002-AC-01, REQ-002-AC-02, REQ-002-EC-01, REQ-003-AC-01, REQ-003-AC-02, REQ-003-EC-01, REQ-004-AC-01, REQ-004-AC-02, REQ-004-EC-01, REQ-005-AC-01, REQ-005-AC-02, REQ-005-AC-03, REQ-005-AC-04, REQ-005-AC-05, REQ-005-EC-01, REQ-005-EC-02, REQ-006-AC-01, REQ-006-AC-02, REQ-006-EC-01_

## Traceability

| Requirement | Test Spec Entry | Task | Test Path |
|-------------|-----------------|------|-----------|
| REQ-001-AC-01 | TC-008 | TASK-001 | TC-008 |
| REQ-001-AC-02 | TC-007 | TASK-010 | TC-007 |
| REQ-001-AC-03 | TC-009 | TASK-002 | TC-009 |
| REQ-001-AC-04 | TC-010 | TASK-011 | TC-010 |
| REQ-001-AC-05 | ECT-011 | TASK-017 | ECT-011 |
| REQ-001-EC-01 | ECT-009 | TASK-018 | ECT-009 |
| REQ-002-AC-01 | TC-001 | TASK-004 | TC-001 |
| REQ-002-AC-02 | TC-014 | TASK-004 | TC-014 |
| REQ-002-EC-01 | ECT-001 | TASK-015 | ECT-001 |
| REQ-003-AC-01 | TC-002 | TASK-005 | TC-002 |
| REQ-003-AC-02 | TC-015 | TASK-005 | TC-015 |
| REQ-003-EC-01 | ECT-004 | TASK-015 | ECT-004 |
| REQ-004-AC-01 | TC-003 | TASK-006 | TC-003 |
| REQ-004-AC-02 | TC-016 | TASK-006 | TC-016 |
| REQ-004-EC-01 | ECT-005 | TASK-015 | ECT-005 |
| REQ-005-AC-01 | TC-013 | TASK-007 | TC-013 |
| REQ-005-AC-02 | TC-004 | TASK-007 | TC-004 |
| REQ-005-AC-03 | TC-005 | TASK-007 | TC-005 |
| REQ-005-AC-04 | TC-006 | TASK-007 | TC-006 |
| REQ-005-AC-05 | ECT-010 | TASK-012 | ECT-010 |
| REQ-005-EC-01 | ECT-006 | TASK-014 | ECT-006 |
| REQ-005-EC-02 | ECT-007 | TASK-014 | ECT-007 |
| REQ-006-AC-01 | TC-011 | TASK-009 | TC-011 |
| REQ-006-AC-02 | TC-012 | TASK-009 | TC-012 |
| REQ-006-EC-01 | ECT-008 | TASK-016 | ECT-008 |

