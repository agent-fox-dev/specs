"""Lifecycle state machine for afspec.

Implements task group 10: lifecycle transition enforcement, intent hash
computation, and mutation guards for the five-state spec lifecycle
(draft → active → sealed → superseded/archived).
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
from typing import Any

from afspec.exceptions import LifecycleError
from afspec.models import PRDFrontmatter, Spec

# ---------------------------------------------------------------------------
# Legal lifecycle transition graph
# ---------------------------------------------------------------------------

_LEGAL_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("draft", "active"),
        ("active", "sealed"),
        ("sealed", "superseded"),
        ("sealed", "archived"),
        ("draft", "archived"),
    }
)

# Regexes for extracting the ## Intent section from a PRD body
_INTENT_HEADING = re.compile(r"^##\s+Intent\s*$", re.MULTILINE)
_NEXT_H2 = re.compile(r"^##\s+", re.MULTILINE)

# Deprecation banner text (embedded in prd.md body and JSON $comment)
_DEPRECATION_BANNER = "> **SUPERSEDED** — This spec has been superseded.\n\n"
_DEPRECATION_COMMENT = "SUPERSEDED: This spec has been superseded."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_intent_body(body: str) -> str:
    """Extract the text of the ## Intent section from a PRD markdown body.

    Returns the stripped content between the ``## Intent`` heading and the next
    ``##`` heading (or end of string).

    Args:
        body: Full PRD markdown body string (without frontmatter).

    Returns:
        Stripped intent section text.

    Raises:
        ValueError: If no ``## Intent`` section is found.
    """
    match = _INTENT_HEADING.search(body)
    if match is None:
        raise ValueError("PRD body does not contain a '## Intent' section")
    after_heading = body[match.end():]
    next_match = _NEXT_H2.search(after_heading)
    if next_match:
        section_body = after_heading[: next_match.start()]
    else:
        section_body = after_heading
    return section_body.strip()


def _compute_intent_hash(intent_text: str) -> str:
    """Compute the SHA-256 hex digest of the normalized intent section text.

    Normalization steps applied to ``intent_text``:
    1. Strip leading/trailing whitespace.
    2. Normalize CRLF and bare CR to LF.
    3. Collapse runs of 3 or more newlines to a single blank line (2 newlines).

    The resulting normalized string is encoded as UTF-8 and hashed with SHA-256.
    The returned digest is a 64-character lowercase hex string.

    Args:
        intent_text: The raw intent section body (extracted from PRD body).

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    # Step 1: strip
    normalized = intent_text.strip()
    # Step 2: normalize line endings
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    # Step 3: collapse multiple blank lines
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _check_transition(current_state: str, target_state: str) -> None:
    """Verify a lifecycle transition is legal; raise LifecycleError if not.

    Args:
        current_state: The spec's current lifecycle state.
        target_state: The requested target state.

    Raises:
        LifecycleError: If the transition is not in the legal transition graph.
    """
    if (current_state, target_state) not in _LEGAL_TRANSITIONS:
        raise LifecycleError(
            f"Illegal lifecycle transition: {current_state!r} → {target_state!r}",
            current_state=current_state,
            target_state=target_state,
        )


def _frontmatter_to_raw_dict(fm: PRDFrontmatter) -> dict[str, Any]:
    """Convert a PRDFrontmatter to a plain dict suitable for mutation comparison."""
    return {
        "spec_id": fm.spec_id,
        "spec_name": fm.spec_name,
        "title": fm.title,
        "status": fm.status,
        "created_at": fm.created_at,
        "updated_at": fm.updated_at,
        "owner": fm.owner,
        "source": fm.source,
        "supersedes": list(fm.supersedes),
        "tags": list(fm.tags),
        "intent_hash": fm.intent_hash,
        "schema_version": fm.schema_version,
    }


# ---------------------------------------------------------------------------
# Lifecycle mutation guard (called from saver.py before writing)
# ---------------------------------------------------------------------------


def check_save_permitted(spec: Spec) -> None:
    """Verify that saving this spec is allowed by its lifecycle state.

    Called by ``save_spec`` *before* writing any files.  Raises a
    ``LifecycleError`` if any lifecycle constraint is violated.

    Guards enforced:
    - **active**: The ``## Intent`` section body must still match the stored
      ``intent_hash`` (tamper detection).  Immutable fields ``created_at``,
      ``spec_id``, and ``spec_name`` must not have changed since the
      draft→active transition (compared against ``_raw_frontmatter``).
    - **sealed / superseded / archived**: All frontmatter fields (except
      ``updated_at``, which is auto-refreshed on save) must match the snapshot
      stored in ``_raw_frontmatter``.

    Args:
        spec: The spec to check.

    Raises:
        LifecycleError: If any lifecycle constraint is violated.
    """
    status = spec.prd.frontmatter.status

    if status == "active":
        _check_active_guards(spec)
    elif status in ("sealed", "superseded", "archived"):
        _check_immutable_guards(spec, status)


def _check_active_guards(spec: Spec) -> None:
    """Enforce active-state mutation guards."""
    fm = spec.prd.frontmatter

    # 1. Intent hash check: recompute from body and compare with stored hash.
    if fm.intent_hash is not None:
        try:
            intent_text = _extract_intent_body(spec.prd.body)
        except ValueError as exc:
            raise LifecycleError(
                f"Cannot verify intent hash: {exc}",
                current_state="active",
                field="intent",
            ) from exc
        actual_hash = _compute_intent_hash(intent_text)
        if actual_hash != fm.intent_hash:
            raise LifecycleError(
                "Intent section body has been tampered with: "
                f"stored hash {fm.intent_hash!r} does not match "
                f"recomputed hash {actual_hash!r}",
                current_state="active",
                field="intent",
            )

    # 2. Immutable field check: compare against _raw_frontmatter snapshot.
    if spec._raw_frontmatter is not None:
        raw = spec._raw_frontmatter
        for field in ("created_at", "spec_id", "spec_name"):
            current_val = getattr(fm, field)
            original_val = raw.get(field)
            if current_val != original_val:
                raise LifecycleError(
                    f"Immutable field {field!r} was mutated in active state: "
                    f"original={original_val!r}, current={current_val!r}",
                    current_state="active",
                    field=field,
                )


def _check_immutable_guards(spec: Spec, status: str) -> None:
    """Enforce sealed/superseded/archived mutation guards."""
    if spec._raw_frontmatter is None:
        # No baseline — cannot detect mutations; allow save.
        return

    fm = spec.prd.frontmatter
    raw = spec._raw_frontmatter

    # All fields except updated_at must remain unchanged.
    _CHECKED_FIELDS = (
        "spec_id",
        "spec_name",
        "title",
        "status",
        "created_at",
        "owner",
        "source",
        "supersedes",
        "tags",
        "intent_hash",
        "schema_version",
    )
    for field in _CHECKED_FIELDS:
        current_val = getattr(fm, field)
        original_val = raw.get(field)
        # Normalize lists for comparison
        if isinstance(current_val, list):
            current_val = list(current_val)
        if isinstance(original_val, list):
            original_val = list(original_val)
        if current_val != original_val:
            raise LifecycleError(
                f"Mutation rejected in {status!r} state: "
                f"field {field!r} changed from {original_val!r} to {current_val!r}",
                current_state=status,
                field=field,
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transition(spec: Spec, target_status: str) -> Spec:
    """Apply a lifecycle transition to a spec.

    Validates that the transition is legal, computes ``intent_hash`` when
    transitioning to ``active``, adds a deprecation banner when transitioning
    to ``superseded``, and returns a new ``Spec`` with the updated fields and
    a ``_raw_frontmatter`` snapshot anchored to the post-transition state.

    Args:
        spec: The spec to transition.
        target_status: One of "active", "sealed", "superseded", "archived".

    Returns:
        New ``Spec`` with updated status (and intent_hash if active).

    Raises:
        LifecycleError: If the transition is illegal.
    """
    current_status = spec.prd.frontmatter.status
    _check_transition(current_status, target_status)

    # Build new frontmatter with updated status
    new_fm = dataclasses.replace(spec.prd.frontmatter, status=target_status)
    new_prd = dataclasses.replace(spec.prd, frontmatter=new_fm)

    if target_status == "active":
        # Compute and store intent_hash at the draft→active transition
        intent_text = _extract_intent_body(spec.prd.body)
        intent_hash = _compute_intent_hash(intent_text)
        new_fm = dataclasses.replace(new_fm, intent_hash=intent_hash)
        new_prd = dataclasses.replace(new_prd, frontmatter=new_fm)

    if target_status == "superseded":
        # Prepend deprecation banner to the PRD body
        new_body = _DEPRECATION_BANNER + new_prd.body
        new_prd = dataclasses.replace(new_prd, body=new_body)

    # Build the _raw_frontmatter snapshot anchored to the post-transition state.
    # This snapshot is used by check_save_permitted to detect subsequent mutations.
    new_raw_fm = _frontmatter_to_raw_dict(new_prd.frontmatter)

    return dataclasses.replace(
        spec,
        prd=new_prd,
        _raw_frontmatter=new_raw_fm,
    )


__all__ = [
    "_compute_intent_hash",
    "_extract_intent_body",
    "_check_transition",
    "check_save_permitted",
    "transition",
]
