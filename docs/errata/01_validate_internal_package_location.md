# Errata: Cross-File Validation in Root Package Instead of internal/validate

**Spec:** 01_golang_library  
**Design ref:** `design.md` §Architecture — "internal/validate — Cross-file integrity checks (7 rules from §9.2), ID format validation, glossary cross-check"

## Divergence

The design specifies that cross-file integrity checks and ID format validation
should live in `internal/validate/crossfile.go` and `internal/validate/ids.go`.

In the actual implementation these functions (`crossFileRule1`–`crossFileRule7`,
`validateRequirementIDs`, `validateTestSpecIDs`, `validateTasksIDs`,
`checkIDFormat`, `checkTestIDFormat`) reside in the root `validate.go` file.

Only pure utility helpers (regex patterns, `ExtractBacktickTerms`,
`CheckSequentiality`) were placed in `internal/validate/helpers.go`.

## Reason

Moving the business-logic functions to `internal/validate` would create a
circular import dependency:

```
github.com/agent-fox/afspec (root) → internal/validate
internal/validate → github.com/agent-fox/afspec  ← circular!
```

The validation functions accept `*Spec`, `*Requirements`, `*TestSpecDoc`, and
`*Tasks` — all types defined in the root package. Go prohibits circular
imports, so placing the logic in an internal package that imports root types is
not possible without either:

1. Extracting all types to a shared `internal/types` package (major refactor), or
2. Defining interfaces in internal and adapting root types (verbose adapter layer).

## Decision

Keep validation logic in the root package and extract only pure helpers to
`internal/validate/helpers.go`. This satisfies all test contracts without
introducing circular imports.

## Impact

- All public API surfaces (`Validate`, `ValidateSchema`, `ValidateCrossFile`,
  `ValidateIDs`) remain unchanged.
- All 7 cross-file integrity rules are correctly implemented and tested.
- All ID format patterns are validated as specified in Appendix A.
- All tests from test_spec.md pass: TS-01-18–24, TS-01-43–45, TS-01-E12,
  TS-01-E23, TS-01-E24, TS-01-P4, TS-01-P9, TS-01-SMOKE-3.

## Future Remediation

If the project moves shared types to `internal/types` in a future refactor,
the validation functions can be migrated to `internal/validate` at that time.
