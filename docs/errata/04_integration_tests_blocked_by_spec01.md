# Errata: TS-04-14, TS-04-17, TestSmoke1 Blocked by Spec 01 Stub Tests

**Spec:** 04_build_and_release  
**Date:** 2026-05-19  
**Author:** Coder (task group 4)

## Summary

Three CI tests remain failing because they invoke `make test-go` (or `make check`
which calls `make test-go`), and `make test-go` runs `go test -count=1 ./...` across
the entire Go module. The root package (`github.com/agent-fox/afspec`) contains
intentionally failing stub tests from spec 01 (Go library), whose implementation
has not yet been completed.

## Affected Tests

| Test | Root Cause |
|------|-----------|
| `TestTS04_14` | `make test-go` exits non-zero (spec 01 stubs fail) |
| `TestTS04_17` | `make check` exits non-zero (spec 01 stubs fail via `make test-go`) |
| `TestSmoke1` | `make check` exits non-zero (same) |

## Spec vs Implementation Divergence

**Spec assumes:** By the time group 4 is verified, `go test ./...` passes.

**Reality:** Spec 01 (Go library) is implemented test-first; the root package
contains over 40 stub test cases that return "not implemented" until spec 01's
implementation groups are completed.

## Mitigation

These tests will automatically pass once spec 01's implementation groups (2+) are
completed, as the root package tests will no longer return "not implemented" errors.

No changes are required in the spec 04 test files or workflow files. The core
group 4 deliverables (`scripts/check-version.sh` and `.github/workflows/release.yml`)
are fully implemented and all directly-scoped tests pass:

- TS-04-6 through TS-04-13 ✅
- TS-04-E3, TS-04-E4, TS-04-E5 ✅
- TS-04-P1, TS-04-P2 ✅
- TestSmoke3, TestSmoke4 ✅
