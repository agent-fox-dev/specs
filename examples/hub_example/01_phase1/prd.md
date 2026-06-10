# PRD

## Intent

Enable the first external users to self-onboard to af-hub and authenticate AF instances against it via time-bound API keys.

## Background

af-hub is a service to collect telemetry and audit data from running agent-fox instances. Over time, it will also serve as a "gateway" to control individual agent-fox (AF) instances running on, e.g. VPSs or in Kubernetes pods.

For this, it must maintain an inventory of:

- GitHub repos (or other Git-forges) "under management" i.e. which are implemented or maintained by AF.
- Users accessing the "hub". We keep a minimal record only: username/email, GitHub/GitLab ID, which repo they have access to.
- API keys for users & repos that can be used to a) access the hub API and b) by AF instances to report data.

## Ownership

**DRI:** The dev-team is collectively responsible for this PRD and for escalation decisions during implementation.

## Goals

- All API endpoints for user management, API key management, and multi-tenant (repo-scoped) access are implemented and validated through end-to-end tests.
- A new external user can self-onboard via OAuth and receive a working API key without admin intervention.
- All API endpoints return HTTP 401 for expired or invalid tokens within a single request cycle.

## Non-Goals

The following are explicitly out of scope for Phase 1:

- Billing and subscription management.
- Advanced RBAC roles beyond the `editor` role (e.g. `viewer`, `admin`, `read-only`).
- AF instance gateway / control-plane features (remote control of AF instances).
- Audit log querying UI or any frontend beyond the CLI.
- Organisation or workspace-level tenant grouping (multiple repos under a shared tenant entity).
- Formal performance SLOs or SLAs — Phase 1 targets best-effort availability and latency only.

## Multi-Tenancy Model

**Repo is the tenant boundary.** Every database table is keyed by a `repo_id`. All API calls are scoped to a single repo, derived from the bearer token presented with the request. There is no higher-level organisation or workspace concept in Phase 1.

A user may have access to multiple repos, but each access grant is stored as a discrete record associating `(user_id, repo_id)`.

## Requirements

### Bootstrap / Initialization

- On first initialization, af-hub creates an admin user and a long-lived bootstrap API key. This key acts as the "root" credential for initial setup.
- The bootstrap token is printed to stdout **once** at initialization time and never stored in plaintext; subsequent retrieval is not possible without generating a new token.
- The bootstrap token has a configurable expiry (default: 90 days) and can be rotated by the admin via the `POST /v1/admin/bootstrap-token/rotate` endpoint. On rotation, a new token is issued immediately and the previous token is invalidated with no grace period. The new plaintext token is returned in the response body once and never retrievable again.

### User Management

- User records are minimal: `username`, `email`, `oauth_provider`, `provider_account_id`, `created_at`, `created_by`.
- **Identity federation:** Email is the canonical identity. If a user authenticates via a second OAuth provider using the same email address, the new provider is automatically linked to the existing account (auto-merge). No duplicate accounts are created.
- Users can be created or modified via the API (admin-only for direct manipulation).
- All database entries carry provenance fields: `repo_id`, `created_by` (user ID), `created_at`.

#### Admin User Creation — Request Body Schema

The `POST /v1/users` endpoint accepts the following JSON body:

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Unique display name for the user |
| `email` | string | Yes | Canonical email address (must be unique) |
| `oauth_provider` | string | No | Initial OAuth provider (`github`, `gitlab`, `google`, `keycloak`) |
| `provider_account_id` | string | No | Provider-issued account ID; required if `oauth_provider` is set |

A request body that omits `username` or `email`, or that sets `oauth_provider` without `provider_account_id` (or vice-versa), must be rejected with HTTP `422` and error code `validation_error`.

### Authentication & OAuth Onboarding

- User self-signup and login are strictly via OAuth through external identity providers. Supported providers in Phase 1: **GitHub, GitLab, Google, Keycloak**.
- On first login (new email), an account is automatically provisioned.
- On subsequent logins, the session is resumed and any new OAuth provider for the same email is linked to the existing account.
- OAuth scopes required: at minimum `email` and `profile` (or provider equivalent) to obtain a verified email address.

#### CLI OAuth Flow

The CLI uses the **OAuth 2.0 Device Authorization Grant** (RFC 8628) for both `signup` and `login` commands. This flow is chosen because it is well-suited to headless and terminal environments and does not require a local HTTP server or browser redirect.

Flow steps:
1. The CLI calls the af-hub device authorization endpoint and receives a `device_code`, `user_code`, and `verification_uri`.
2. The CLI prints the `verification_uri` and `user_code` to the terminal and instructs the user to visit the URL in a browser.
3. The user authenticates with the selected OAuth provider in the browser and enters the displayed code.
4. The CLI polls the token endpoint until authorization is granted or the `device_code` expires.
5. On success, the CLI receives a session token and persists it to disk (see [CLI Session Token Storage](#cli-session-token-storage)).

### API Key Management

- API keys are **time-bound** and carry an explicit expiration date.
- Keys are stored as **bcrypt or argon2 hashes only**; the plaintext key is shown to the user **once** at creation time and is never retrievable afterwards.
- The plaintext key presented to the user is encoded as **base64url** (URL-safe, no padding), derived from a minimum of 256 bits (32 random bytes) of cryptographically secure random data.
- On renewal, a **new key is issued** and the **old key is immediately invalidated** — there is no grace period.
- Keys can be created, updated, and expired (revoked) via the API. The `update key` operation (`PATCH /v1/keys/{key_id}`) supports only the following attribute changes: extending the `expires_at` date. No other key attributes may be modified. Only the key owner or an admin may call this endpoint.
- Possessing an API key for a repo grants `editor` role: full read/write access to that repo's resources.

### RBAC

- Phase 1 defines a single role: **`editor`** — full read/write access scoped to a repo.
- The role model is designed to be extensible; additional roles and permission policies will be added in future phases without requiring a schema migration.

### API Design

#### Versioning

All Phase 1 API endpoints are prefixed with `/v1/`. This prefix is mandatory for all routes and ensures future phases can introduce `/v2/` endpoints without breaking existing CLI or AF-instance clients.

#### Endpoints

All API calls must be **user- and repo-aware**: the bearer token presented with each request determines both the user identity and the repo scope.

Endpoints required in Phase 1:

| Method | Path | Description | Authorization |
|---|---|---|---|
| `POST` | `/v1/users` | Create a user (admin only) | Admin token |
| `PATCH` | `/v1/users/{user_id}` | Modify a user (admin only) | Admin token |
| `POST` | `/v1/keys` | Create a new API key | Authenticated user |
| `PATCH` | `/v1/keys/{key_id}` | Update key (extend expiry only) | Key owner or admin |
| `DELETE` | `/v1/keys/{key_id}` | Expire / revoke a key | Key owner or admin |
| `POST` | `/v1/admin/bootstrap-token/rotate` | Rotate the bootstrap token | Admin token |

#### Error Response Format

All error responses **must** conform to the following JSON schema:

```json
{
  "error": "<human-readable message>",
  "code":  "<machine-readable code>"
}
```

- The HTTP status code conveys the error class (e.g. `401`, `403`, `404`, `422`, `500`).
- The `error` field provides a human-readable description suitable for display in CLI output.
- The `code` field provides a stable, machine-readable identifier that CLI and AF-instance clients can use for programmatic error handling and retry logic.
- All endpoints must return HTTP `401` with `code: "token_expired"` or `code: "token_invalid"` (as appropriate) for expired, revoked, or malformed bearer tokens.
- Error response bodies are always `application/json`, even when the success response for the same endpoint is a different content type.

#### Machine-Readable Error Code Vocabulary

The following is the exhaustive, canonical list of `code` values for Phase 1. Implementations **must not** introduce codes outside this list without a PRD amendment. New codes added in future phases must be appended here.

| Code | HTTP Status | Description |
|---|---|---|
| `token_expired` | 401 | The bearer token or API key has passed its `expires_at` timestamp. |
| `token_invalid` | 401 | The bearer token or API key is malformed, unrecognised, or has been revoked. |
| `permission_denied` | 403 | The authenticated principal does not have the required role for the requested operation. |
| `user_not_found` | 404 | The referenced user does not exist. |
| `key_not_found` | 404 | The referenced API key does not exist. |
| `repo_not_found` | 404 | The referenced repo does not exist or is not accessible to the caller. |
| `conflict` | 409 | The request conflicts with existing state (e.g. duplicate email on user creation). |
| `validation_error` | 422 | The request body or parameters failed schema validation (missing required fields, invalid types, etc.). |
| `internal_error` | 500 | An unexpected server-side error occurred. Details are logged server-side and not exposed in the response body. |

### CLI

The af-hub CLI is in scope for Phase 1 with the following commands only:

| Command | Description |
|---|---|
| `signup` | Initiate OAuth-based user self-signup flow (device authorization grant) |
| `login` | Authenticate an existing user via OAuth (device authorization grant) and store a local session token |
| `logout` | Invalidate the local session token and delete the token file |

Additional CLI commands (e.g. repo management, key rotation helpers) are deferred to future phases.

#### CLI Session Token Storage

After a successful `login` or `signup`, the CLI persists the session token as a **plain text file** at the following well-known path:

- **Linux / macOS:** `~/.config/af-hub/token`
- **Windows:** `%APPDATA%\af-hub\token`

Security requirements for the token file:
- The file **must** be created with permissions `0600` (owner read/write only) on POSIX systems.
- The directory `~/.config/af-hub/` (or its platform equivalent) must be created with permissions `0700` if it does not already exist.
- On Windows, the file ACL must restrict access to the current user only.
- The `logout` command must delete the token file. If the file does not exist, `logout` exits successfully without error.

The token stored in the file is the opaque session token returned by the server after device authorization completes. The CLI reads this file on every command invocation that requires authentication and passes the token as a `Bearer` token in the `Authorization` header.

## Non-Functional Requirements

### Performance & Availability

No formal SLOs or SLAs are defined for Phase 1. The service operates on a best-effort basis. Infrastructure sizing and load testing are deferred to a future phase when external traffic volumes are known.

### Security

- API keys are stored exclusively as **bcrypt or argon2** hashes. Plaintext is displayed once at creation and never persisted.
- Plaintext keys use **base64url** encoding over a minimum of 256 bits (32 random bytes) of cryptographically secure entropy.
- The API **must** enforce TLS for all endpoints in production deployments. For the purposes of this requirement, a **production deployment** is any environment reachable from the public internet or from external users. Local development and CI environments are exempt and may use plain HTTP.
- TLS termination may occur at the load balancer or reverse proxy layer (e.g. nginx, AWS ALB); the application itself is not required to terminate TLS directly. Mutual TLS and HSTS headers are out of scope for Phase 1.
- API keys must have sufficient entropy (minimum 256 bits / 32 random bytes before encoding).
- The CLI token file must be stored with owner-only permissions (`0600` on POSIX; restricted ACL on Windows), as specified in the [CLI Session Token Storage](#cli-session-token-storage) section.

### Extensibility

- The RBAC model and database schema must be designed to accommodate additional roles and tenant-hierarchy levels without breaking changes.
- The `/v1/` URL prefix strategy must be honoured throughout so that future `/v2/` routes can coexist without requiring clients to reconfigure base URLs.
- The machine-readable error code vocabulary is designed to be append-only; existing codes must not be renamed or removed in future phases.