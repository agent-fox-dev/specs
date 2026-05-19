# Errata: Lifecycle Save Guard for Sealed/Superseded/Archived States

**Spec:** 01_golang_library
**Requirement:** 01-REQ-7.4
**Test:** TS-01-32
**Status:** Known conflict — test cannot pass without breaking TS-01-33

## Summary

Test TS-01-32 requires that `SaveSpec()` reject mutations to specs in `sealed`,
`superseded`, or `archived` states. Test TS-01-33 requires that the sealed→superseded
transition (which internally calls `SaveSpec()`) succeeds on an empty directory.

These two requirements are irreconcilable with the current API design.

## Root Cause

Both TS-01-32 and TS-01-33 build their test spec using `makeSpecWithStatus()`, which
creates an in-memory `*Spec` with no `Dir` field set. The test scenarios are:

- **TS-01-32**: Calls `SaveSpec(tmpdir, &modified)` with a sealed/superseded/archived spec
  that has `Title` changed. Should return an error.
- **TS-01-33**: Calls `Transition(spec, StatusSuperseded)` followed by some form of save;
  the resulting superseded spec must contain the deprecation banner in all four files.

To distinguish "legitimate supersede save" from "unauthorized mutation save", the guard
would need one of:

1. A reference copy of the pre-mutation spec (not available in the API contract).
2. A "save allowed" flag set during `Transition()` (breaks immutability — the returned
   spec is used read-only by the caller).
3. Comparing `spec.Dir` to detect in-place updates vs. cross-directory saves (fragile;
   not specified in the design).
4. Requiring all sealed/superseded/archived writes to go through `Transition()` (would
   make `SaveSpec` inaccessible for legitimate round-trips of immutable specs).

None of these approaches satisfy both tests simultaneously without violating other
requirements (e.g., 01-REQ-3.4 which requires idempotent round-trips on any loaded spec,
including sealed ones).

## Current Implementation

The active-spec guard is implemented in `save.go: checkActiveSpecIntegrity()`:
- For `active` specs with a stored `intent_hash`, recomputes the hash and rejects if
  the `## Intent` section body has changed. This satisfies 01-REQ-7.3 and 01-REQ-7.E2.

The sealed/superseded/archived mutation guard (01-REQ-7.4) is **not implemented** in
`SaveSpec`. Consumers who need to enforce immutability must do so at the application layer
by checking `spec.PRD.Frontmatter.Status` before calling `SaveSpec`.

## Tests Affected

| Test | Status | Notes |
|------|--------|-------|
| TS-01-32 | FAIL (expected) | Sealed/superseded/archived mutation guard not in SaveSpec |
| TS-01-33 | PASS | Deprecation banner correctly applied by `Transition()` |
| TS-01-31 | PASS | Active-state intent hash guard correctly rejects mutations |

## Recommended Future Fix

The spec should be updated to provide a dedicated write path for lifecycle transitions,
such as:

```go
// TransitionAndSave atomically transitions and persists a spec.
func TransitionAndSave(dir string, spec *Spec, target Status) (*Spec, error)
```

This would let `SaveSpec` remain a pure persistence function while mutation guards live
entirely within the lifecycle layer. TS-01-32 could then be rewritten to test a
separate guard function rather than `SaveSpec` directly.
