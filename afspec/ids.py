"""ID format validation for afspec.

Validates all spec-format ID types against the patterns defined in spec-format.md Appendix A.
"""
from __future__ import annotations

import re

from afspec.models import ValidationError

# ---------------------------------------------------------------------------
# Compiled regex patterns for each ID type.
#
# All patterns with embedded spec_id capture the spec_id in a named group
# ``sid`` so we can check it against expected_spec_id.  Numeric components
# are captured in named groups ``n`` and ``c`` for positive-integer checks.
# ---------------------------------------------------------------------------

# Subtask and verification IDs have no spec_id component.
_SUBTASK_RE = re.compile(r"^(?P<g>\d+)\.(?P<n>\d+)$")
_VERIFICATION_RE = re.compile(r"^(?P<g>\d+)\.V$")

# Patterns ordered from most-specific to least-specific within each family so
# that we try longer matches first.
_SPEC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # ---- Test-spec IDs (start with TS-) ----
    # TS-{sid}-SMOKE-{n}
    ("smoke_test", re.compile(r"^TS-(?P<sid>\d+(?:\.\d+)?)-SMOKE-(?P<n>\d+)$")),
    # TS-{sid}-P{n}
    ("property_test", re.compile(r"^TS-(?P<sid>\d+(?:\.\d+)?)-P(?P<n>\d+)$")),
    # TS-{sid}-E{n}
    ("edge_case_test", re.compile(r"^TS-(?P<sid>\d+(?:\.\d+)?)-E(?P<n>\d+)$")),
    # TS-{sid}-{n}
    ("test_case", re.compile(r"^TS-(?P<sid>\d+(?:\.\d+)?)-(?P<n>\d+)$")),
    # ---- Requirements-based IDs (sid-TYPE-n[.suffix]) ----
    # {sid}-REQ-{n}.E{c}   (edge case criterion)
    ("edge_case", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-REQ-(?P<n>\d+)\.E(?P<c>\d+)$")),
    # {sid}-REQ-{n}.{c}    (acceptance criterion)
    ("criterion", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-REQ-(?P<n>\d+)\.(?P<c>\d+)$")),
    # {sid}-REQ-{n}        (requirement)
    ("requirement", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-REQ-(?P<n>\d+)$")),
    # {sid}-PROP-{n}       (correctness property)
    ("property", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-PROP-(?P<n>\d+)$")),
    # {sid}-PATH-{n}       (execution path)
    ("path", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-PATH-(?P<n>\d+)$")),
    # {sid}-ERR-{n}        (error handling entry)
    ("error", re.compile(r"^(?P<sid>\d+(?:\.\d+)?)-ERR-(?P<n>\d+)$")),
]


def validate_id(id_str: str, expected_spec_id: str) -> list[ValidationError]:
    """Validate an ID string against spec-format patterns.

    Args:
        id_str: The ID to validate.
        expected_spec_id: The spec_id that the ID's embedded spec_id must match.

    Returns:
        List of ValidationError (empty if valid).
    """
    errors: list[ValidationError] = []

    # Subtask and verification IDs: no spec_id component, always valid format-wise.
    if _SUBTASK_RE.match(id_str) or _VERIFICATION_RE.match(id_str):
        return []

    # Try each spec-aware pattern.
    for kind, pattern in _SPEC_PATTERNS:
        m = pattern.match(id_str)
        if m is None:
            continue

        groups = m.groupdict()
        sid = groups.get("sid", "")

        # Check spec_id consistency.
        if sid != expected_spec_id:
            errors.append(
                ValidationError(
                    file="",
                    path=id_str,
                    rule="id-format",
                    message=(
                        f"spec_id mismatch in {kind} ID '{id_str}': "
                        f"found '{sid}' but expected '{expected_spec_id}'"
                    ),
                    severity="error",
                )
            )

        # Check that numeric components are positive integers.
        for key in ("n", "c"):
            if key in groups:
                val = int(groups[key])
                if val <= 0:
                    errors.append(
                        ValidationError(
                            file="",
                            path=id_str,
                            rule="id-format",
                            message=(
                                f"numeric component in {kind} ID '{id_str}' must be "
                                f"a positive integer, got {val}"
                            ),
                            severity="error",
                        )
                    )

        return errors

    # No pattern matched.
    errors.append(
        ValidationError(
            file="",
            path=id_str,
            rule="id-format",
            message=f"ID '{id_str}' does not match any known spec-format ID pattern",
            severity="error",
        )
    )
    return errors


def check_sequential(ids: list[str]) -> list[ValidationError]:
    """Check that a list of requirement IDs are sequentially numbered.

    Returns warnings (not blocking errors) for any numbering gaps.

    Args:
        ids: List of requirement-style IDs (e.g., ['05-REQ-1', '05-REQ-2', '05-REQ-5']).

    Returns:
        List of ValidationError with severity="warning" for each gap found.
    """
    # Extract the trailing numeric component from each ID.
    _suffix_re = re.compile(r".*-(\d+)$")
    numbers: list[int] = []
    for id_str in ids:
        m = _suffix_re.match(id_str)
        if m:
            numbers.append(int(m.group(1)))

    if len(numbers) < 2:
        return []

    numbers_sorted = sorted(numbers)
    lo, hi = numbers_sorted[0], numbers_sorted[-1]
    expected_set = set(range(lo, hi + 1))
    actual_set = set(numbers_sorted)
    gaps = sorted(expected_set - actual_set)

    if not gaps:
        return []

    return [
        ValidationError(
            file="",
            path="",
            rule="id-sequential",
            message=(
                f"IDs are not sequential: missing numbers {gaps} "
                f"(found {numbers_sorted})"
            ),
            severity="warning",
        )
    ]
