# Erratum 02: Intent Hash Normalization

**Spec:** 02_python_library
**Requirement:** 02-REQ-7.2 (intent_hash computation)
**Date:** 2026-05-19

## Issue

The requirements glossary defines `intent_normalization` as:
> LF line endings, collapse multiple blank lines, lower-case, trim whitespace.

However, `spec-format.md §4.2` specifies only:
> trimmed of leading/trailing whitespace.

Lowercasing is absent from the canonical spec-format definition. If implemented as described
in the glossary (with lowercasing), the Python library would produce different SHA-256 digests
from the Go library for any intent body containing uppercase letters. This would break
cross-library golden fixture consistency.

## Resolution

**Implement intent normalization per spec-format.md §4.2 only:**
- Trim leading/trailing whitespace from the Intent section body.
- Do **not** lowercase or collapse blank lines beyond what trimming provides.

The test `test_intent_hash_is_sha256` in `test_lifecycle.py` reflects this:
it computes `sha256(intent_text.strip().encode())` without any lowercasing.

The glossary definition in the requirements document is incorrect; spec-format.md
is the authoritative source for cross-library semantics.

## Impact on Tests

`TS-02-30` tests that `intent_hash` is a 64-char SHA-256 hex digest. The test
uses `_compute_intent_hash(intent_text)` and verifies the result against
`hashlib.sha256(normalized.encode()).hexdigest()` where `normalized = text.strip()`.
No lowercasing is applied. Implementation must follow this contract.
