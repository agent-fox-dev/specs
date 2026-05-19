"""Tests for afspec saver and round-trip behaviour (TS-02-9 through TS-02-13, TS-02-E8, TS-02-E9)."""
from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone

import pytest

from afspec import load_spec, save_spec
from afspec.loader import _load_json, _load_prd
from afspec.models import TestSpec

# ---------------------------------------------------------------------------
# TS-02-9
# ---------------------------------------------------------------------------


def test_deterministic_json(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-9: Save spec produces deterministic JSON with sorted keys and 2-space indent."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    save_spec(spec, dst)

    content = (dst / "requirements.json").read_text(encoding="utf-8")

    # Must end with a newline
    assert content.endswith("\n"), "requirements.json must end with a trailing newline"

    parsed = json.loads(content)
    keys = list(parsed.keys())
    assert keys == sorted(keys), (
        f"Top-level keys must be sorted alphabetically; got {keys}"
    )

    lines = content.split("\n")
    # Find the first line that is indented with spaces (not the top-level "{")
    indented = next((ln for ln in lines if ln.startswith("  ")), None)
    assert indented is not None, "No indented line found; expected 2-space indentation"
    assert indented.startswith("  "), "Indented lines must use 2-space indentation"


# ---------------------------------------------------------------------------
# TS-02-10
# ---------------------------------------------------------------------------

_EXPECTED_FM_FIELDS = [
    "spec_id",
    "spec_name",
    "title",
    "status",
    "created_at",
    "updated_at",
    "owner",
    "source",
    "supersedes",
    "tags",
    "intent_hash",
    "schema_version",
]


def test_deterministic_yaml(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-10: Save spec produces YAML frontmatter fields in the fixed canonical order."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    save_spec(spec, dst)

    content = (dst / "prd.md").read_text(encoding="utf-8")
    lines = content.split("\n")

    # Locate the YAML block between the first and second "---" delimiters
    assert lines[0] == "---", "prd.md must start with '---'"
    fm_start = 1
    fm_end = lines.index("---", fm_start)
    fm_lines = lines[fm_start:fm_end]

    # Extract top-level field names (lines that contain ":" and are not indented)
    field_names = [
        ln.split(":")[0].strip()
        for ln in fm_lines
        if ":" in ln and not ln.startswith(" ")
    ]

    assert field_names == _EXPECTED_FM_FIELDS, (
        f"Frontmatter field order mismatch.\n"
        f"  expected: {_EXPECTED_FM_FIELDS}\n"
        f"  got:      {field_names}"
    )


# ---------------------------------------------------------------------------
# TS-02-11
# ---------------------------------------------------------------------------

_JSON_ARTIFACTS = ["requirements.json", "test_spec.json", "tasks.json"]


def test_idempotent_roundtrip(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-11: Load → save produces byte-identical JSON files; in-memory state is equivalent."""
    dst = tmp_path / "out"
    dst.mkdir()

    spec1 = load_spec(tmp_spec_dir)
    save_spec(spec1, dst)

    # JSON files must be byte-identical after one round-trip
    for filename in _JSON_ARTIFACTS:
        src_bytes = (tmp_spec_dir / filename).read_bytes()
        dst_bytes = (dst / filename).read_bytes()
        assert src_bytes == dst_bytes, (
            f"{filename}: content differs after round-trip"
        )

    # In-memory model equivalence (ignoring updated_at)
    spec2 = load_spec(dst)
    assert spec1.requirements == spec2.requirements
    assert spec1.test_spec.test_cases == spec2.test_spec.test_cases
    assert spec1.tasks.task_groups == spec2.tasks.task_groups
    assert spec1.prd.body == spec2.prd.body


# ---------------------------------------------------------------------------
# TS-02-12
# ---------------------------------------------------------------------------


def test_auto_updated_at(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-12: Save auto-updates updated_at to approximately the current UTC timestamp."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    before = datetime.now(timezone.utc)
    save_spec(spec, dst)
    after = datetime.now(timezone.utc)

    prd = _load_prd(dst / "prd.md")
    raw_ts = prd.frontmatter.updated_at
    # Normalise "Z" suffix to "+00:00" for fromisoformat compatibility
    saved_time = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))

    assert before <= saved_time <= after, (
        f"updated_at={raw_ts!r} is outside the [{before.isoformat()}, {after.isoformat()}] window"
    )


# ---------------------------------------------------------------------------
# TS-02-13
# ---------------------------------------------------------------------------


def test_auto_computed_coverage(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-13: Save auto-computes coverage reflecting actual test case coverage."""
    # The fixture has test cases for 05-REQ-1.1 (via TS-05-1) and 05-REQ-1.E1 (via TS-05-E1).
    # After saving the library must recompute and persist the coverage field.
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    save_spec(spec, dst)

    ts = _load_json(dst / "test_spec.json", TestSpec)
    assert ts.coverage is not None, "coverage must be present in saved test_spec.json"
    assert "05-REQ-1.1" in ts.coverage.requirements_covered, (
        "05-REQ-1.1 must appear in coverage.requirements_covered"
    )


# ---------------------------------------------------------------------------
# TS-02-E8
# ---------------------------------------------------------------------------


def test_nonexistent_dir_error(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-E8: Save to a non-existent directory raises an error without creating it."""
    spec = load_spec(tmp_spec_dir)
    bad_path = tmp_path / "does_not_exist"

    assert not bad_path.exists(), "Precondition: target directory must not exist"

    with pytest.raises(Exception):
        save_spec(spec, bad_path)

    assert not bad_path.exists(), (
        "save_spec must not create the target directory when it does not exist"
    )


# ---------------------------------------------------------------------------
# TS-02-E9
# ---------------------------------------------------------------------------


def test_write_failure_cleanup(tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """TS-02-E9: Write failure leaves no .tmp files in the target directory."""
    spec = load_spec(tmp_spec_dir)
    dst = tmp_path / "out"
    dst.mkdir()

    # Make the directory read-only to inject a write failure
    os.chmod(str(dst), 0o444)
    try:
        with pytest.raises(Exception):
            save_spec(spec, dst)
    finally:
        os.chmod(str(dst), 0o755)

    tmp_files = [f for f in dst.iterdir() if ".tmp" in f.name]
    assert len(tmp_files) == 0, (
        f"Temporary files must be cleaned up after write failure; found: {tmp_files}"
    )


# ---------------------------------------------------------------------------
# Additional round-trip: second save must also be idempotent (no drift)
# ---------------------------------------------------------------------------


def test_double_roundtrip_json_stable(
    tmp_spec_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """Supplementary: two consecutive saves produce identical JSON artifacts."""
    dst1 = tmp_path / "pass1"
    dst2 = tmp_path / "pass2"
    dst1.mkdir()
    dst2.mkdir()

    spec1 = load_spec(tmp_spec_dir)
    save_spec(spec1, dst1)
    spec2 = load_spec(dst1)
    save_spec(spec2, dst2)

    for filename in _JSON_ARTIFACTS:
        assert (dst1 / filename).read_bytes() == (dst2 / filename).read_bytes(), (
            f"{filename}: content drifted between first and second save"
        )
