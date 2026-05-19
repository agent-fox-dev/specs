"""Tests for lifecycle state machine management.

Covers: TS-02-29, TS-02-30, TS-02-31, TS-02-32, TS-02-33, TS-02-E16, TS-02-E17
"""
from __future__ import annotations

import hashlib
import pathlib

import pytest

from afspec import load_spec, save_spec, transition
from afspec.exceptions import LifecycleError
from afspec.lifecycle import _compute_intent_hash


def test_legal_transition_draft_to_active(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: draft→active is a legal transition."""
    spec = load_spec(tmp_spec_dir)
    assert spec.prd.frontmatter.status == "draft"
    active = transition(spec, "active")
    assert active.prd.frontmatter.status == "active"


def test_legal_transition_active_to_sealed(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: active→sealed is a legal transition."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    assert sealed.prd.frontmatter.status == "sealed"


def test_legal_transition_sealed_to_superseded(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: sealed→superseded is a legal transition."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    superseded = transition(sealed, "superseded")
    assert superseded.prd.frontmatter.status == "superseded"


def test_legal_transition_sealed_to_archived(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: sealed→archived is a legal transition."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    archived = transition(sealed, "archived")
    assert archived.prd.frontmatter.status == "archived"


def test_legal_transition_draft_to_archived(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: draft→archived is a legal transition."""
    spec = load_spec(tmp_spec_dir)
    archived = transition(spec, "archived")
    assert archived.prd.frontmatter.status == "archived"


def test_illegal_transition_draft_to_sealed(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: draft→sealed is illegal, raises LifecycleError."""
    spec = load_spec(tmp_spec_dir)
    with pytest.raises(LifecycleError):
        transition(spec, "sealed")


def test_illegal_transition_active_to_draft(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: active→draft is illegal, raises LifecycleError."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    with pytest.raises(LifecycleError):
        transition(active, "draft")


def test_illegal_transition_sealed_to_draft(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-29: sealed→draft is illegal, raises LifecycleError."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    with pytest.raises(LifecycleError):
        transition(sealed, "draft")


def test_intent_hash_computed_at_draft_to_active(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-30: draft→active computes and stores intent_hash."""
    spec = load_spec(tmp_spec_dir)
    assert spec.prd.frontmatter.intent_hash is None
    active = transition(spec, "active")
    assert active.prd.frontmatter.intent_hash is not None
    assert len(active.prd.frontmatter.intent_hash) == 64  # SHA-256 hex


def test_intent_hash_matches_manual_computation(tmp_spec_dir: pathlib.Path) -> None:
    """TS-02-30: computed intent_hash matches manual SHA-256 of normalized body."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    # Extract intent body from prd
    body = spec.prd.body
    intent_start = body.index("## Intent") + len("## Intent")
    # Find next ## section or end of string
    remaining = body[intent_start:]
    next_section = remaining.find("\n## ")
    if next_section >= 0:
        intent_text = remaining[:next_section].strip()
    else:
        intent_text = remaining.strip()
    expected = _compute_intent_hash(intent_text)
    assert active.prd.frontmatter.intent_hash == expected


def test_active_state_rejects_intent_mutation(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-31: saving active spec with modified Intent body raises LifecycleError."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    # Tamper with the body to change the Intent section
    tampered_body = active.prd.body.replace(
        "Build a thing for testing purposes.",
        "Completely different intent text.",
    )
    tampered_prd = dataclasses.replace(active.prd, body=tampered_body)
    tampered_spec = dataclasses.replace(active, prd=tampered_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(tampered_spec, out)


def test_active_state_rejects_created_at_mutation(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-31: saving active spec with modified created_at raises LifecycleError."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    new_fm = dataclasses.replace(active.prd.frontmatter, created_at="2000-01-01T00:00:00Z")
    new_prd = dataclasses.replace(active.prd, frontmatter=new_fm)
    tampered = dataclasses.replace(active, prd=new_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(tampered, out)


def test_sealed_rejects_all_mutations(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-32: sealed spec rejects all mutations."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    new_fm = dataclasses.replace(sealed.prd.frontmatter, title="New Title")
    new_prd = dataclasses.replace(sealed.prd, frontmatter=new_fm)
    modified = dataclasses.replace(sealed, prd=new_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(modified, out)


def test_superseded_rejects_all_mutations(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-32: superseded spec rejects all mutations."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    superseded = transition(sealed, "superseded")
    new_fm = dataclasses.replace(superseded.prd.frontmatter, title="New Title")
    new_prd = dataclasses.replace(superseded.prd, frontmatter=new_fm)
    modified = dataclasses.replace(superseded, prd=new_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(modified, out)


def test_archived_rejects_all_mutations(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-32: archived spec rejects all mutations."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    archived = transition(spec, "archived")
    new_fm = dataclasses.replace(archived.prd.frontmatter, title="New Title")
    new_prd = dataclasses.replace(archived.prd, frontmatter=new_fm)
    modified = dataclasses.replace(archived, prd=new_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(modified, out)


def test_superseding_adds_deprecation_banner(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-33: transitioning to superseded adds deprecation banner to files."""
    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    sealed = transition(active, "sealed")
    superseded = transition(sealed, "superseded")
    out = tmp_path / "out"
    out.mkdir()
    save_spec(superseded, out)
    # All four files should contain a deprecation marker
    for fname in ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]:
        content = (out / fname).read_text()
        assert "SUPERSEDED" in content


def test_illegal_transition_names_states() -> None:
    """TS-02-E16: LifecycleError names current and target states."""
    from afspec.lifecycle import _check_transition

    with pytest.raises(LifecycleError) as exc_info:
        _check_transition("draft", "sealed")
    error = exc_info.value
    assert error.current_state == "draft"
    assert error.target_state == "sealed"


def test_intent_hash_tamper_detection(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """TS-02-E17: saving active spec with tampered intent body raises LifecycleError."""
    import dataclasses

    spec = load_spec(tmp_spec_dir)
    active = transition(spec, "active")
    # Replace intent section with different content
    new_body = active.prd.body.replace(
        "Build a thing for testing purposes.",
        "Totally different intent that was tampered with.",
    )
    tampered_prd = dataclasses.replace(active.prd, body=new_body)
    tampered = dataclasses.replace(active, prd=tampered_prd)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(LifecycleError):
        save_spec(tampered, out)


def test_intent_hash_stability() -> None:
    """TS-02-30: _compute_intent_hash is stable across multiple calls."""
    text = "Build a thing for testing purposes."
    h1 = _compute_intent_hash(text)
    h2 = _compute_intent_hash(text)
    assert h1 == h2
    assert len(h1) == 64


def test_intent_hash_changes_with_content() -> None:
    """TS-02-30: different content produces different hash."""
    h1 = _compute_intent_hash("intent one")
    h2 = _compute_intent_hash("intent two")
    assert h1 != h2


def test_intent_hash_is_sha256() -> None:
    """TS-02-30: hash is a valid SHA-256 hex digest."""
    text = "Build a thing."
    result = _compute_intent_hash(text)
    # Verify manually
    normalized = text.strip()
    expected = hashlib.sha256(normalized.encode()).hexdigest()
    assert result == expected
