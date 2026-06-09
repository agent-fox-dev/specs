# Erratum: accept_prd() Does Not Allow init State

**Spec:** 02_campaign_session
**Requirements:** 02-REQ-4.2, 02-REQ-4.4
**Status:** Intentional divergence

## Issue

Requirement 02-REQ-4.2 lists `init -> prd_accepted` as a legal transition
(one-shot mode). Requirement 02-REQ-4.4 states:

> WHEN `accept_prd()` is called while the session is in `init`, `assessing`,
> or `refining` state, THE system SHALL transition the state to `prd_accepted`.

The implementation only allows `accept_prd()` from `assessing` or `refining`
states, raising `SessionError` from `init`.

## Root Cause

The design document contains a contradiction between the `accept_prd()`
docstring (which mentions init for one-shot mode) and Property 6:

> **Property 6:** accept_prd() is only callable from assessing or refining
> states. *For any* `SpecSession` in a state other than `assessing` or
> `refining`, calling `accept_prd()` SHALL raise a `SessionError`.

The legal transitions list in the state machine section also includes
`init -> prd_accepted (one-shot mode)`, but the state diagram and Property 6
exclude it.

The test specification (TS-02-P6) follows Property 6, requiring `accept_prd()`
to fail from init state.

## Resolution

The implementation follows the design's Property 6 and the test specification
(TS-02-P6). The `_ACCEPT_PRD_STATES` frozenset only includes `ASSESSING` and
`REFINING`.

If one-shot mode (init -> prd_accepted) is needed in the future, this
transition should be added to `_ACCEPT_PRD_STATES` and the test updated
accordingly.

## Impact

No functional impact for current usage. The interactive workflow always
transitions through `assessing` before accepting a PRD. One-shot mode
callers would need to transition to `assessing` before calling `accept_prd()`.
