# Test Specification: Audit Hub

## Overview

This test specification defines concrete, language-agnostic test contracts for
every acceptance criterion, correctness property, and edge case in the Audit Hub
specification. Test cases map 1:1 to requirements and properties. The coding
agent translates these contracts into failing Go tests as task group 1.

All tests use in-memory SQLite (`:memory:`) unless filesystem behavior is
specifically under test. HTTP handler tests use `httptest.NewRecorder` with
a real Echo context.

---

## Test Cases

### TS-01-1: Valid event ingestion returns 201

**Requirement:** 01-REQ-1.1
**Type:** unit
**Description:** A valid audit event submitted with correct auth returns 201 and is stored.

**Preconditions:**
- Store initialized with in-memory SQLite
- AuditHandler wired with store
- Bearer token set to `"test-token"`

**Input:**
- HTTP POST to `/api/v1/audit`
- Header: `Authorization: Bearer test-token`
- Header: `Content-Type: application/json`
- Body:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-27T10:00:00+00:00",
  "run_id": "20260427_100000_abc123",
  "event_type": "run.start",
  "node_id": "",
  "session_id": "",
  "archetype": "",
  "severity": "info",
  "payload": {"plan_hash": "abc", "total_nodes": 5, "parallel": true}
}
```

**Expected:**
- HTTP 201 Created
- Empty response body
- Event retrievable from database with matching field values

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", valid_event, auth="test-token")
ASSERT resp.status == 201
ASSERT resp.body == ""
row = store.query("SELECT * FROM events WHERE id = ?", event.id)
ASSERT row.id == event.id
ASSERT row.event_type == "run.start"
ASSERT row.severity == "info"
```

---

### TS-01-2: Wrong content type returns 415

**Requirement:** 01-REQ-1.2
**Type:** unit
**Description:** A request with non-JSON content type is rejected.

**Preconditions:**
- Server running with valid config

**Input:**
- HTTP POST to `/api/v1/audit`
- Header: `Authorization: Bearer test-token`
- Header: `Content-Type: text/plain`
- Body: `"some text"`

**Expected:**
- HTTP 415 Unsupported Media Type

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", "some text", content_type="text/plain", auth="test-token")
ASSERT resp.status == 415
```

---

### TS-01-3: Validation rejects missing required fields

**Requirement:** 01-REQ-2.1
**Type:** unit
**Description:** Events missing any required envelope field are rejected.

**Preconditions:**
- Validator function available

**Input:**
- For each required field (`id`, `timestamp`, `run_id`, `event_type`, `severity`, `payload`):
  submit an event with that field omitted.

**Expected:**
- Validate returns a non-nil error for each omitted field

**Assertion pseudocode:**
```
FOR EACH field IN [id, timestamp, run_id, event_type, severity, payload]:
    event = valid_event()
    event[field] = zero_value
    err = validator.Validate(event)
    ASSERT err != nil
```

---

### TS-01-4: Validation checks field format constraints

**Requirement:** 01-REQ-2.2
**Type:** unit
**Description:** Field format constraints are enforced (timestamp ISO 8601, severity enum, event_type dot-separated, payload is object).

**Preconditions:**
- Validator function available

**Input:**
- `timestamp`: `"not-a-date"` — invalid
- `severity`: `"fatal"` — not in enum
- `event_type`: `"start"` — no dot
- `payload`: `"string"` — not an object

**Expected:**
- Validate returns non-nil error for each invalid value

**Assertion pseudocode:**
```
cases = [
    ("timestamp", "not-a-date"),
    ("severity", "fatal"),
    ("event_type", "start"),
]
FOR EACH (field, value) IN cases:
    event = valid_event()
    event[field] = value
    err = validator.Validate(event)
    ASSERT err != nil

event_null_payload = valid_event()
event_null_payload.payload = nil
err = validator.Validate(event_null_payload)
ASSERT err != nil
```

---

### TS-01-5: Optional fields default to empty string

**Requirement:** 01-REQ-2.3
**Type:** unit
**Description:** Events without optional fields (node_id, session_id, archetype) are accepted with defaults.

**Preconditions:**
- Store initialized, handler wired

**Input:**
- Valid event JSON with `node_id`, `session_id`, `archetype` fields omitted

**Expected:**
- HTTP 201
- Stored row has empty strings for the three optional fields

**Assertion pseudocode:**
```
event = valid_event_without_optionals()
resp = POST("/api/v1/audit", event, auth="test-token")
ASSERT resp.status == 201
row = store.query("SELECT node_id, session_id, archetype FROM events WHERE id = ?", event.id)
ASSERT row.node_id == ""
ASSERT row.session_id == ""
ASSERT row.archetype == ""
```

---

### TS-01-6: Store creates table and sets WAL mode

**Requirement:** 01-REQ-3.1, 01-REQ-3.2, 01-REQ-3.3
**Type:** unit
**Description:** Store initialization creates the events table and enables WAL mode.

**Preconditions:**
- Temporary directory for database file

**Input:**
- Call `store.New(tmpdir + "/test.db")`

**Expected:**
- Database file created
- Table `events` exists with all expected columns
- WAL mode enabled
- Database path returned (implicitly, no error)

**Assertion pseudocode:**
```
s, err = store.New(tmpdir + "/test.db")
ASSERT err == nil
ASSERT file_exists(tmpdir + "/test.db")

rows = s.db.Query("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
ASSERT rows.count == 1

mode = s.db.QueryRow("PRAGMA journal_mode").Scan()
ASSERT mode == "wal"
```

---

### TS-01-7: Store uses configured path with default

**Requirement:** 01-REQ-3.4
**Type:** unit
**Description:** Store creates parent directories and uses configured path.

**Preconditions:**
- Temporary directory, subdirectory does not exist

**Input:**
- Call `store.New(tmpdir + "/sub/dir/audit.db")`

**Expected:**
- Parent directories created
- Database file at specified path

**Assertion pseudocode:**
```
path = tmpdir + "/sub/dir/audit.db"
s, err = store.New(path)
ASSERT err == nil
ASSERT file_exists(path)
```

---

### TS-01-8: Bearer auth rejects missing header

**Requirement:** 01-REQ-4.1, 01-REQ-4.2
**Type:** unit
**Description:** Requests without Authorization header receive 401.

**Preconditions:**
- Echo instance with auth middleware configured, token = `"test-token"`

**Input:**
- HTTP POST to `/api/v1/audit` with no Authorization header

**Expected:**
- HTTP 401 Unauthorized

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", valid_event, auth=None)
ASSERT resp.status == 401
```

---

### TS-01-9: Bearer auth rejects wrong token

**Requirement:** 01-REQ-4.3
**Type:** unit
**Description:** Requests with incorrect Bearer token receive 401.

**Preconditions:**
- Echo instance with auth middleware configured, token = `"test-token"`

**Input:**
- Header: `Authorization: Bearer wrong-token`

**Expected:**
- HTTP 401 Unauthorized

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", valid_event, auth="wrong-token")
ASSERT resp.status == 401
```

---

### TS-01-10: Healthz returns 200

**Requirement:** 01-REQ-5.1
**Type:** unit
**Description:** Liveness probe always returns 200.

**Preconditions:**
- Server running

**Input:**
- HTTP GET to `/healthz` (no auth header)

**Expected:**
- HTTP 200 OK

**Assertion pseudocode:**
```
resp = GET("/healthz")
ASSERT resp.status == 200
```

---

### TS-01-11: Readyz returns 200 when DB healthy

**Requirement:** 01-REQ-5.2
**Type:** unit
**Description:** Readiness probe returns 200 when database is accessible.

**Preconditions:**
- Server running with healthy SQLite database

**Input:**
- HTTP GET to `/readyz` (no auth header)

**Expected:**
- HTTP 200 OK

**Assertion pseudocode:**
```
resp = GET("/readyz")
ASSERT resp.status == 200
```

---

### TS-01-12: Health endpoints skip auth

**Requirement:** 01-REQ-5.3
**Type:** unit
**Description:** Health endpoints respond without requiring Authorization header.

**Preconditions:**
- Server running with auth middleware active

**Input:**
- HTTP GET to `/healthz` without Authorization header
- HTTP GET to `/readyz` without Authorization header

**Expected:**
- Both return HTTP 200 (not 401)

**Assertion pseudocode:**
```
resp1 = GET("/healthz", auth=None)
ASSERT resp1.status == 200
resp2 = GET("/readyz", auth=None)
ASSERT resp2.status == 200
```

---

### TS-01-13: Config loads from TOML file

**Requirement:** 01-REQ-6.1, 01-REQ-6.2
**Type:** unit
**Description:** Configuration loads from TOML with correct defaults and overrides.

**Preconditions:**
- Temporary TOML file with partial config (only `auth.bearer_token` set)

**Input:**
- Call `config.Load(tmpfile)`

**Expected:**
- `Server.Port` == 8080 (default)
- `Server.BindAddress` == "0.0.0.0" (default)
- `Database.Path` == "./data/audit.db" (default)
- `Database.RetentionDays` == 30 (default)
- `Auth.BearerToken` == configured value
- `Logging.Level` == "info" (default)

**Assertion pseudocode:**
```
cfg, err = config.Load(tmpfile_with_token_only)
ASSERT err == nil
ASSERT cfg.Server.Port == 8080
ASSERT cfg.Server.BindAddress == "0.0.0.0"
ASSERT cfg.Database.Path == "./data/audit.db"
ASSERT cfg.Database.RetentionDays == 30
ASSERT cfg.Auth.BearerToken == "my-token"
ASSERT cfg.Logging.Level == "info"
```

---

### TS-01-14: Config override values

**Requirement:** 01-REQ-6.2
**Type:** unit
**Description:** Explicit TOML values override defaults.

**Preconditions:**
- TOML file with all fields set to non-default values

**Input:**
```toml
[server]
port = 9090
bind_address = "127.0.0.1"

[database]
path = "/tmp/custom.db"
retention_days = 7

[auth]
bearer_token = "custom-token"

[logging]
level = "debug"
```

**Expected:**
- All fields match the overridden values

**Assertion pseudocode:**
```
cfg, err = config.Load(custom_toml)
ASSERT err == nil
ASSERT cfg.Server.Port == 9090
ASSERT cfg.Server.BindAddress == "127.0.0.1"
ASSERT cfg.Database.Path == "/tmp/custom.db"
ASSERT cfg.Database.RetentionDays == 7
ASSERT cfg.Logging.Level == "debug"
```

---

### TS-01-15: Retention purges old events

**Requirement:** 01-REQ-7.1, 01-REQ-7.3
**Type:** unit
**Description:** Purge deletes events older than retention period and returns count.

**Preconditions:**
- Store with 3 events: one from 60 days ago, one from 15 days ago, one from today

**Input:**
- Call `store.PurgeOlderThan(ctx, now - 30 days)`

**Expected:**
- Returns count = 1 (the 60-day-old event)
- 2 events remain in database

**Assertion pseudocode:**
```
store.InsertEvent(ctx, event_60_days_old)
store.InsertEvent(ctx, event_15_days_old)
store.InsertEvent(ctx, event_today)

count, err = store.PurgeOlderThan(ctx, now() - 30*day)
ASSERT err == nil
ASSERT count == 1

remaining = store.query("SELECT COUNT(*) FROM events")
ASSERT remaining == 2
```

---

### TS-01-16: Request logging captures method, path, status, duration

**Requirement:** 01-REQ-9.3, 01-REQ-9.4
**Type:** unit
**Description:** HTTP requests produce structured log entries with required fields.

**Preconditions:**
- Logrus configured with JSON formatter and a test hook to capture entries

**Input:**
- Send a valid POST request to `/api/v1/audit`

**Expected:**
- Log entry contains fields: `method`, `path`, `status`, `duration`

**Assertion pseudocode:**
```
hook = test.NewLogHook()
logrus.AddHook(hook)
resp = POST("/api/v1/audit", valid_event, auth="test-token")
entry = hook.LastEntry()
ASSERT entry.Data["method"] == "POST"
ASSERT entry.Data["path"] == "/api/v1/audit"
ASSERT entry.Data["status"] == 201
ASSERT entry.Data["duration"] != nil
```

---

### TS-01-17: WAL mode enables concurrent writes

**Requirement:** 01-REQ-10.1
**Type:** integration
**Description:** Multiple concurrent inserts succeed without SQLITE_BUSY errors.

**Preconditions:**
- Store initialized with file-backed SQLite (WAL mode)

**Input:**
- 20 goroutines each inserting one unique event concurrently

**Expected:**
- All 20 inserts succeed (no errors)
- 20 events in database

**Assertion pseudocode:**
```
wg = WaitGroup()
errors = []
FOR i IN 1..20:
    wg.Add(1)
    GO func():
        err = store.InsertEvent(ctx, unique_event(i))
        IF err != nil: errors.append(err)
        wg.Done()
wg.Wait()
ASSERT len(errors) == 0
count = store.query("SELECT COUNT(*) FROM events")
ASSERT count == 20
```

---

## Edge Case Tests

### TS-01-E1: Empty request body returns 400

**Requirement:** 01-REQ-1.E1
**Type:** unit
**Description:** POST with empty body is rejected.

**Preconditions:**
- Server running with auth

**Input:**
- HTTP POST to `/api/v1/audit` with empty body
- Header: `Content-Type: application/json`
- Header: `Authorization: Bearer test-token`

**Expected:**
- HTTP 400 Bad Request

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", body="", auth="test-token")
ASSERT resp.status == 400
```

---

### TS-01-E2: Oversized body returns 413

**Requirement:** 01-REQ-1.E2
**Type:** unit
**Description:** Request body exceeding 1 MB is rejected.

**Preconditions:**
- Server running with body size limit configured

**Input:**
- HTTP POST with body > 1 MB

**Expected:**
- HTTP 413 Payload Too Large

**Assertion pseudocode:**
```
large_body = "x" * (1024 * 1024 + 1)
resp = POST("/api/v1/audit", body=large_body, auth="test-token")
ASSERT resp.status == 413
```

---

### TS-01-E3: Invalid JSON returns 400

**Requirement:** 01-REQ-1.E3
**Type:** unit
**Description:** Malformed JSON body is rejected.

**Preconditions:**
- Server running with auth

**Input:**
- Body: `{invalid json`

**Expected:**
- HTTP 400 Bad Request

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", body="{invalid json", auth="test-token")
ASSERT resp.status == 400
```

---

### TS-01-E4: Timestamp without timezone returns 422

**Requirement:** 01-REQ-2.E1
**Type:** unit
**Description:** ISO 8601 timestamp without timezone offset is rejected.

**Preconditions:**
- Validator function available

**Input:**
- Event with `timestamp`: `"2026-04-27T10:00:00"` (no timezone)

**Expected:**
- Validation error

**Assertion pseudocode:**
```
event = valid_event()
event.timestamp = "2026-04-27T10:00:00"
err = validator.Validate(event)
ASSERT err != nil
```

---

### TS-01-E5: Null payload returns 422

**Requirement:** 01-REQ-2.E2
**Type:** unit
**Description:** Event with null payload is rejected.

**Preconditions:**
- Validator function available

**Input:**
- Event with `payload`: `null`

**Expected:**
- Validation error

**Assertion pseudocode:**
```
event = valid_event()
event.payload = null
err = validator.Validate(event)
ASSERT err != nil
```

---

### TS-01-E6: Event type without dot returns 422

**Requirement:** 01-REQ-2.E3
**Type:** unit
**Description:** Event type missing dot separator is rejected.

**Preconditions:**
- Validator function available

**Input:**
- Event with `event_type`: `"start"`

**Expected:**
- Validation error

**Assertion pseudocode:**
```
event = valid_event()
event.event_type = "start"
err = validator.Validate(event)
ASSERT err != nil
```

---

### TS-01-E7: Duplicate event ID returns 409

**Requirement:** 01-REQ-3.E1
**Type:** unit
**Description:** Inserting an event with a duplicate ID returns conflict.

**Preconditions:**
- Store with one event already inserted

**Input:**
- Insert a second event with the same `id`

**Expected:**
- InsertEvent returns an error indicating uniqueness violation
- HTTP handler returns 409 Conflict

**Assertion pseudocode:**
```
store.InsertEvent(ctx, event)
err = store.InsertEvent(ctx, event_same_id)
ASSERT err != nil

resp = POST("/api/v1/audit", event_same_id_json, auth="test-token")
ASSERT resp.status == 409
```

---

### TS-01-E8: Database open failure exits non-zero

**Requirement:** 01-REQ-3.E2
**Type:** unit
**Description:** Store returns error when database path is not writable.

**Preconditions:**
- Path to a read-only directory

**Input:**
- Call `store.New("/readonly/dir/audit.db")`

**Expected:**
- Returns non-nil error

**Assertion pseudocode:**
```
_, err = store.New("/readonly/dir/audit.db")
ASSERT err != nil
```

---

### TS-01-E9: Auth header with extra whitespace accepted

**Requirement:** 01-REQ-4.E1
**Type:** unit
**Description:** Extra whitespace between "Bearer" and token is handled.

**Preconditions:**
- Auth middleware configured with token `"test-token"`

**Input:**
- Header: `Authorization: Bearer   test-token` (extra spaces)

**Expected:**
- Request proceeds (not rejected as 401)

**Assertion pseudocode:**
```
resp = POST("/api/v1/audit", valid_event, auth_header="Bearer   test-token")
ASSERT resp.status != 401
```

---

### TS-01-E10: Missing bearer token in config exits

**Requirement:** 01-REQ-4.5
**Type:** unit
**Description:** Config without bearer_token fails validation.

**Preconditions:**
- TOML file with no `auth.bearer_token`

**Input:**
- Call `config.Load(toml_without_token)`

**Expected:**
- Returns non-nil error

**Assertion pseudocode:**
```
_, err = config.Load(toml_without_token)
ASSERT err != nil
```

---

### TS-01-E11: Readyz returns 503 when DB unavailable

**Requirement:** 01-REQ-5.E1
**Type:** unit
**Description:** Readiness probe returns 503 when database is inaccessible.

**Preconditions:**
- HealthHandler with a store whose database has been closed

**Input:**
- HTTP GET to `/readyz`

**Expected:**
- HTTP 503 Service Unavailable

**Assertion pseudocode:**
```
store.Close()
resp = GET("/readyz")
ASSERT resp.status == 503
```

---

### TS-01-E12: Config file not found exits

**Requirement:** 01-REQ-6.3
**Type:** unit
**Description:** Missing config file returns error.

**Preconditions:**
- Path to nonexistent file

**Input:**
- Call `config.Load("/nonexistent/config.toml")`

**Expected:**
- Returns non-nil error

**Assertion pseudocode:**
```
_, err = config.Load("/nonexistent/config.toml")
ASSERT err != nil
```

---

### TS-01-E13: Invalid TOML syntax exits

**Requirement:** 01-REQ-6.4
**Type:** unit
**Description:** Syntactically invalid TOML returns error.

**Preconditions:**
- File with invalid TOML content

**Input:**
- Call `config.Load(invalid_toml_file)`

**Expected:**
- Returns non-nil error

**Assertion pseudocode:**
```
write_file(tmpfile, "[invalid toml =")
_, err = config.Load(tmpfile)
ASSERT err != nil
```

---

### TS-01-E14: Retention days zero uses default

**Requirement:** 01-REQ-6.E1
**Type:** unit
**Description:** Retention days <= 0 falls back to 30.

**Preconditions:**
- TOML file with `database.retention_days = 0`

**Input:**
- Call `config.Load(toml_with_zero_retention)`

**Expected:**
- `cfg.Database.RetentionDays` == 30

**Assertion pseudocode:**
```
cfg, err = config.Load(toml_zero_retention)
ASSERT err == nil
ASSERT cfg.Database.RetentionDays == 30
```

---

### TS-01-E15: Port out of range exits

**Requirement:** 01-REQ-6.E2
**Type:** unit
**Description:** Port outside 1-65535 returns error.

**Preconditions:**
- TOML file with `server.port = 70000`

**Input:**
- Call `config.Load(toml_bad_port)`

**Expected:**
- Returns non-nil error

**Assertion pseudocode:**
```
_, err = config.Load(toml_port_70000)
ASSERT err != nil
```

---

### TS-01-E16: Retention error does not crash service

**Requirement:** 01-REQ-7.E1
**Type:** unit
**Description:** Retention purge gracefully handles database errors.

**Preconditions:**
- Store whose database has been closed

**Input:**
- Call `store.PurgeOlderThan(ctx, cutoff)` on closed store

**Expected:**
- Returns non-nil error (does not panic)

**Assertion pseudocode:**
```
store.Close()
_, err = store.PurgeOlderThan(ctx, cutoff)
ASSERT err != nil
```

---

### TS-01-E17: Invalid log level defaults to info

**Requirement:** 01-REQ-9.E1
**Type:** unit
**Description:** Unrecognized log level falls back to info.

**Preconditions:**
- TOML file with `logging.level = "verbose"` (invalid)

**Input:**
- Call `config.Load(toml_bad_level)`

**Expected:**
- `cfg.Logging.Level` == "info"

**Assertion pseudocode:**
```
cfg, err = config.Load(toml_bad_level)
ASSERT err == nil
ASSERT cfg.Logging.Level == "info"
```

---

### TS-01-E18: SQLite busy timeout returns 503

**Requirement:** 01-REQ-10.E1
**Type:** unit
**Description:** Exhausted busy timeout results in 503 response.

**Preconditions:**
- Store configured with very short busy timeout
- Database locked by another connection

**Input:**
- Attempt InsertEvent while database is locked

**Expected:**
- Returns error
- Handler returns HTTP 503

**Assertion pseudocode:**
```
lock_database(store)
err = store.InsertEvent(ctx, event)
ASSERT err != nil
```

---

## Property Test Cases

### TS-01-P1: Schema validation completeness

**Property:** Property 1 from design.md
**Validates:** 01-REQ-2.1, 01-REQ-2.2, 01-REQ-2.3, 01-REQ-2.4
**Type:** property
**Description:** Validation accepts iff all required fields are present and well-formed.

**For any:** Randomly generated AuditEvent structs with fields individually
fuzzed (empty strings, invalid timestamps, bad severity values, null payloads,
missing dots in event_type).
**Invariant:** `Validate(event)` returns nil iff `id` is non-empty, `timestamp`
is valid ISO 8601 with timezone, `run_id` is non-empty, `event_type` contains
a dot, `severity` is in {info, warning, error, critical}, and `payload` is a
non-null JSON object.

**Assertion pseudocode:**
```
FOR ANY event IN rapid.Make[AuditEvent]:
    err = validator.Validate(event)
    expected_valid = (
        event.id != "" AND
        is_iso8601_with_tz(event.timestamp) AND
        event.run_id != "" AND
        strings.Contains(event.event_type, ".") AND
        event.severity IN ["info","warning","error","critical"] AND
        event.payload != nil AND len(event.payload) > 0
    )
    ASSERT (err == nil) == expected_valid
```

---

### TS-01-P2: Storage integrity round-trip

**Property:** Property 2 from design.md
**Validates:** 01-REQ-1.1, 01-REQ-3.1
**Type:** property
**Description:** Every stored event is retrievable with identical field values.

**For any:** Valid AuditEvent structs with randomized field values (valid
formats).
**Invariant:** After `InsertEvent(event)`, querying by `id` yields a row whose
envelope metadata fields and payload match the original event exactly.

**Assertion pseudocode:**
```
FOR ANY event IN rapid.Make[ValidAuditEvent]:
    store.InsertEvent(ctx, event)
    row = store.query("SELECT * FROM events WHERE id = ?", event.id)
    ASSERT row.id == event.id
    ASSERT row.timestamp == event.timestamp
    ASSERT row.run_id == event.run_id
    ASSERT row.event_type == event.event_type
    ASSERT row.node_id == event.node_id
    ASSERT row.session_id == event.session_id
    ASSERT row.archetype == event.archetype
    ASSERT row.severity == event.severity
    ASSERT json.Equal(row.payload, event.payload)
```

---

### TS-01-P3: Authentication enforcement

**Property:** Property 3 from design.md
**Validates:** 01-REQ-4.1, 01-REQ-4.2, 01-REQ-4.3
**Type:** property
**Description:** Only requests with the correct Bearer token pass auth.

**For any:** Random strings as token values.
**Invariant:** The auth middleware returns 401 for any token that does not
match the configured token, and passes through for exact matches.

**Assertion pseudocode:**
```
configured_token = "correct-token"
FOR ANY candidate IN rapid.String():
    resp = POST("/api/v1/audit", valid_event, auth=candidate)
    IF candidate == configured_token:
        ASSERT resp.status != 401
    ELSE:
        ASSERT resp.status == 401
```

---

### TS-01-P4: Idempotent duplicate rejection

**Property:** Property 4 from design.md
**Validates:** 01-REQ-3.E1
**Type:** property
**Description:** Duplicate IDs are always rejected without modifying existing data.

**For any:** Valid event pairs where the second has the same `id` but different
payload.
**Invariant:** Second insert fails. Original event's payload is unchanged.

**Assertion pseudocode:**
```
FOR ANY (event1, event2) IN rapid.Make[EventPairSameId]:
    store.InsertEvent(ctx, event1)
    err = store.InsertEvent(ctx, event2)
    ASSERT err != nil
    row = store.query("SELECT payload FROM events WHERE id = ?", event1.id)
    ASSERT json.Equal(row.payload, event1.payload)
```

---

### TS-01-P5: Retention correctness

**Property:** Property 5 from design.md
**Validates:** 01-REQ-7.1, 01-REQ-7.3
**Type:** property
**Description:** After purge, only events within the retention window survive.

**For any:** Set of events with timestamps uniformly distributed across a
90-day range.
**Invariant:** After `PurgeOlderThan(cutoff)`, all remaining events have
`timestamp >= cutoff` and no event with `timestamp < cutoff` remains.

**Assertion pseudocode:**
```
FOR ANY events IN rapid.Make[EventsWithVariedTimestamps]:
    FOR EACH event IN events:
        store.InsertEvent(ctx, event)
    cutoff = now() - 30*day
    count, _ = store.PurgeOlderThan(ctx, cutoff)
    remaining = store.query("SELECT timestamp FROM events")
    FOR EACH row IN remaining:
        ASSERT parse(row.timestamp) >= cutoff
    deleted = store.query("SELECT COUNT(*) FROM events WHERE timestamp < ?", cutoff)
    ASSERT deleted == 0
```

---

### TS-01-P6: Health probe independence

**Property:** Property 6 from design.md
**Validates:** 01-REQ-5.1, 01-REQ-5.2, 01-REQ-5.3
**Type:** property
**Description:** Health probes never return 401, regardless of auth header state.

**For any:** Random Authorization header values (including missing, empty,
malformed, valid, invalid).
**Invariant:** `/healthz` returns 200 and `/readyz` returns 200 (when DB is
up) regardless of auth.

**Assertion pseudocode:**
```
FOR ANY auth_header IN rapid.OneOf(nil, "", "Bearer wrong", "Bearer test-token", "Basic xyz"):
    resp1 = GET("/healthz", auth_header=auth_header)
    ASSERT resp1.status == 200
    resp2 = GET("/readyz", auth_header=auth_header)
    ASSERT resp2.status == 200
```

---

### TS-01-P7: Configuration validation completeness

**Property:** Property 7 from design.md
**Validates:** 01-REQ-6.1, 01-REQ-6.2, 01-REQ-6.3, 01-REQ-6.4, 01-REQ-4.5, 01-REQ-6.E1, 01-REQ-6.E2
**Type:** property
**Description:** Config loading succeeds iff TOML is valid and required fields are present.

**For any:** Randomly generated TOML content (some valid, some with missing
token, some with invalid syntax, some with bad port ranges).
**Invariant:** `Load(path)` returns nil error iff the file is valid TOML with
non-empty `auth.bearer_token` and port in 1–65535 (or absent, defaulting to 8080).

**Assertion pseudocode:**
```
FOR ANY toml_content IN rapid.Make[TomlVariants]:
    write_file(tmpfile, toml_content)
    cfg, err = config.Load(tmpfile)
    IF is_valid_toml(toml_content) AND has_bearer_token(toml_content) AND port_in_range(toml_content):
        ASSERT err == nil
    ELSE:
        ASSERT err != nil
```

---

### TS-01-P8: Concurrent write safety

**Property:** Property 8 from design.md
**Validates:** 01-REQ-10.1, 01-REQ-10.2
**Type:** property
**Description:** N concurrent inserts with unique IDs all succeed.

**For any:** N in [2, 50], each event has a unique ID.
**Invariant:** All N inserts succeed. Database contains exactly N rows.

**Assertion pseudocode:**
```
FOR ANY n IN rapid.IntRange(2, 50):
    events = generate_unique_events(n)
    errors = parallel_insert(store, events)
    ASSERT len(errors) == 0
    count = store.query("SELECT COUNT(*) FROM events")
    ASSERT count == n
```

---

### TS-01-P9: Graceful shutdown completeness

**Property:** Property 9 from design.md
**Validates:** 01-REQ-8.1, 01-REQ-8.2
**Type:** integration
**Description:** In-flight requests complete before shutdown, and the database is closed.

**For any:** This is a deterministic scenario test rather than a generated
property test.
**Invariant:** After SIGTERM, pending requests either complete or are terminated
within 15s. The database connection is closed.

**Assertion pseudocode:**
```
server = start_server()
start_slow_request(server)
send_signal(server.process, SIGTERM)
wait_for_exit(server, timeout=20s)
ASSERT server.exit_code == 0
ASSERT database_is_closed(store)
```

---

## Integration Smoke Tests

### TS-01-SMOKE-1: End-to-end event ingestion

**Execution Path:** Path 1 from design.md
**Description:** A valid event sent via HTTP POST is stored in the database and retrievable.

**Setup:** In-memory SQLite store, real Echo server (httptest), real auth
middleware, real validator, real handler. No mocks.

**Trigger:** HTTP POST to `/api/v1/audit` with valid event and correct Bearer token.

**Expected side effects:**
- HTTP 201 response
- Event row present in SQLite with matching field values
- `received_at` column populated with server-side timestamp

**Must NOT satisfy with:** Mocking Store.InsertEvent, mocking Validator.Validate, mocking auth middleware.

**Assertion pseudocode:**
```
store = store.New(":memory:")
server = server.New(cfg, store)   // real server
ts = httptest.NewServer(server.Echo())

resp = http.POST(ts.URL + "/api/v1/audit", valid_event_json, auth="test-token")
ASSERT resp.StatusCode == 201

row = store.db.QueryRow("SELECT id, event_type, severity FROM events WHERE id = ?", event_id)
ASSERT row.id == event_id
ASSERT row.event_type == "run.start"
ASSERT row.received_at != ""
```

---

### TS-01-SMOKE-2: Health check readiness

**Execution Path:** Path 2 from design.md
**Description:** Readiness probe successfully queries the database.

**Setup:** In-memory SQLite store, real Echo server (httptest), real health handler.

**Trigger:** HTTP GET to `/readyz`.

**Expected side effects:**
- HTTP 200 response

**Must NOT satisfy with:** Mocking Store.Ping.

**Assertion pseudocode:**
```
store = store.New(":memory:")
server = server.New(cfg, store)
ts = httptest.NewServer(server.Echo())

resp = http.GET(ts.URL + "/readyz")
ASSERT resp.StatusCode == 200
```

---

### TS-01-SMOKE-3: Retention purge cycle

**Execution Path:** Path 3 from design.md
**Description:** Retention process deletes expired events and preserves recent ones.

**Setup:** In-memory SQLite store with pre-inserted events spanning 60 days.
Real retention process with short interval (100ms for testing).

**Trigger:** Start retention goroutine, wait for one cycle.

**Expected side effects:**
- Events older than retention period are deleted
- Recent events remain

**Must NOT satisfy with:** Mocking Store.PurgeOlderThan.

**Assertion pseudocode:**
```
store = store.New(":memory:")
store.InsertEvent(ctx, event_60_days_ago)
store.InsertEvent(ctx, event_today)

ctx, cancel = context.WithTimeout(ctx, 500ms)
retention.StartRetention(ctx, store, 100*ms, 30)
time.Sleep(300ms)
cancel()

count = store.query("SELECT COUNT(*) FROM events")
ASSERT count == 1
remaining = store.query("SELECT id FROM events")
ASSERT remaining[0].id == event_today.id
```

---

### TS-01-SMOKE-4: Configuration to running server

**Execution Path:** Path 5 from design.md
**Description:** Configuration file is loaded and used to wire a functional server.

**Setup:** Real TOML config file on filesystem, real config loader, real
store, real server.

**Trigger:** Load config, create store, create server, send health check.

**Expected side effects:**
- Server starts without error
- `/healthz` returns 200

**Must NOT satisfy with:** Mocking config.Load, using hardcoded config values.

**Assertion pseudocode:**
```
write_file(tmpfile, valid_toml_with_token)
cfg, err = config.Load(tmpfile)
ASSERT err == nil

store, err = store.New(cfg.Database.Path)
ASSERT err == nil

server = server.New(cfg, store)
ts = httptest.NewServer(server.Echo())

resp = http.GET(ts.URL + "/healthz")
ASSERT resp.StatusCode == 200
```

---

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 01-REQ-1.1 | TS-01-1 | unit |
| 01-REQ-1.2 | TS-01-2 | unit |
| 01-REQ-1.3 | TS-01-13, TS-01-14 | unit |
| 01-REQ-1.4 | TS-01-13, TS-01-14 | unit |
| 01-REQ-1.E1 | TS-01-E1 | unit |
| 01-REQ-1.E2 | TS-01-E2 | unit |
| 01-REQ-1.E3 | TS-01-E3 | unit |
| 01-REQ-2.1 | TS-01-3 | unit |
| 01-REQ-2.2 | TS-01-4 | unit |
| 01-REQ-2.3 | TS-01-5 | unit |
| 01-REQ-2.4 | TS-01-4 | unit |
| 01-REQ-2.E1 | TS-01-E4 | unit |
| 01-REQ-2.E2 | TS-01-E5 | unit |
| 01-REQ-2.E3 | TS-01-E6 | unit |
| 01-REQ-3.1 | TS-01-6 | unit |
| 01-REQ-3.2 | TS-01-6 | unit |
| 01-REQ-3.3 | TS-01-6, TS-01-7 | unit |
| 01-REQ-3.4 | TS-01-7 | unit |
| 01-REQ-3.E1 | TS-01-E7 | unit |
| 01-REQ-3.E2 | TS-01-E8 | unit |
| 01-REQ-4.1 | TS-01-8 | unit |
| 01-REQ-4.2 | TS-01-8 | unit |
| 01-REQ-4.3 | TS-01-9 | unit |
| 01-REQ-4.4 | TS-01-13 | unit |
| 01-REQ-4.5 | TS-01-E10 | unit |
| 01-REQ-4.E1 | TS-01-E9 | unit |
| 01-REQ-5.1 | TS-01-10 | unit |
| 01-REQ-5.2 | TS-01-11 | unit |
| 01-REQ-5.3 | TS-01-12 | unit |
| 01-REQ-5.E1 | TS-01-E11 | unit |
| 01-REQ-6.1 | TS-01-13 | unit |
| 01-REQ-6.2 | TS-01-13, TS-01-14 | unit |
| 01-REQ-6.3 | TS-01-E12 | unit |
| 01-REQ-6.4 | TS-01-E13 | unit |
| 01-REQ-6.E1 | TS-01-E14 | unit |
| 01-REQ-6.E2 | TS-01-E15 | unit |
| 01-REQ-7.1 | TS-01-15 | unit |
| 01-REQ-7.2 | TS-01-SMOKE-3 | integration |
| 01-REQ-7.3 | TS-01-15 | unit |
| 01-REQ-7.4 | TS-01-13 | unit |
| 01-REQ-7.E1 | TS-01-E16 | unit |
| 01-REQ-8.1 | TS-01-P9 | integration |
| 01-REQ-8.2 | TS-01-P9 | integration |
| 01-REQ-8.E1 | TS-01-P9 | integration |
| 01-REQ-9.1 | TS-01-16 | unit |
| 01-REQ-9.2 | TS-01-13 | unit |
| 01-REQ-9.3 | TS-01-16 | unit |
| 01-REQ-9.4 | TS-01-16 | unit |
| 01-REQ-9.E1 | TS-01-E17 | unit |
| 01-REQ-10.1 | TS-01-17 | integration |
| 01-REQ-10.2 | TS-01-E18 | unit |
| 01-REQ-10.E1 | TS-01-E18 | unit |
| Property 1 | TS-01-P1 | property |
| Property 2 | TS-01-P2 | property |
| Property 3 | TS-01-P3 | property |
| Property 4 | TS-01-P4 | property |
| Property 5 | TS-01-P5 | property |
| Property 6 | TS-01-P6 | property |
| Property 7 | TS-01-P7 | property |
| Property 8 | TS-01-P8 | property |
| Property 9 | TS-01-P9 | integration |
