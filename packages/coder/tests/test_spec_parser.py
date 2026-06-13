"""Tests for the spec pack parser.

Covers: TS-13-3, TS-13-E3, TS-13-E4, TS-13-E5.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from afspec.models import SpecMeta
from coder.errors import SpecParseError
from coder.spec_parser import SpecParser
from conftest import (
    create_spec_pack,
    make_requirements_json,
    make_tasks_json,
    make_test_spec_json,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_spec_pack(tmp_path: Path) -> tuple[Path, SpecMeta]:
    """Create a spec pack with all four valid artifacts.

    Returns (spec_dir, spec_meta).
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign,
        folder_name="01_base_app",
        spec_id="1",
        spec_name="base_app",
        status="active",
    )
    meta = SpecMeta(
        spec_id="1",
        spec_name="base_app",
        status="active",
        dir=str(campaign / "01_base_app"),
    )
    return campaign / "01_base_app", meta


@pytest.fixture()
def spec_pack_no_requirements(tmp_path: Path) -> tuple[Path, SpecMeta]:
    """Create a spec pack missing requirements.json.

    Has prd.md, test_spec.json, tasks.json but no requirements.json.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    spec_dir = campaign / "01_missing_req"
    spec_dir.mkdir()

    # Write prd.md
    from conftest import make_prd_md

    (spec_dir / "prd.md").write_text(
        make_prd_md("1", "missing_req"), encoding="utf-8"
    )
    # Write test_spec.json and tasks.json but NOT requirements.json
    (spec_dir / "test_spec.json").write_text(
        make_test_spec_json("1", "missing_req"), encoding="utf-8"
    )
    (spec_dir / "tasks.json").write_text(
        make_tasks_json("1", "missing_req"), encoding="utf-8"
    )

    meta = SpecMeta(
        spec_id="1",
        spec_name="missing_req",
        status="active",
        dir=str(spec_dir),
    )
    return spec_dir, meta


@pytest.fixture()
def spec_pack_invalid_json(tmp_path: Path) -> tuple[Path, SpecMeta]:
    """Create a spec pack with malformed requirements.json.

    The requirements.json contains invalid JSON syntax.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    spec_dir = campaign / "01_bad_json"
    spec_dir.mkdir()

    from conftest import make_prd_md

    (spec_dir / "prd.md").write_text(
        make_prd_md("1", "bad_json"), encoding="utf-8"
    )
    # Write invalid JSON
    (spec_dir / "requirements.json").write_text(
        "{invalid json content", encoding="utf-8"
    )
    (spec_dir / "test_spec.json").write_text(
        make_test_spec_json("1", "bad_json"), encoding="utf-8"
    )
    (spec_dir / "tasks.json").write_text(
        make_tasks_json("1", "bad_json"), encoding="utf-8"
    )

    meta = SpecMeta(
        spec_id="1",
        spec_name="bad_json",
        status="active",
        dir=str(spec_dir),
    )
    return spec_dir, meta


@pytest.fixture()
def spec_pack_no_prd(tmp_path: Path) -> tuple[Path, SpecMeta]:
    """Create a spec pack missing prd.md.

    Has all JSON artifacts but no prd.md.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    spec_dir = campaign / "01_no_prd"
    spec_dir.mkdir()

    # Write JSON artifacts only, no prd.md
    (spec_dir / "requirements.json").write_text(
        make_requirements_json("1", "no_prd"), encoding="utf-8"
    )
    (spec_dir / "test_spec.json").write_text(
        make_test_spec_json("1", "no_prd"), encoding="utf-8"
    )
    (spec_dir / "tasks.json").write_text(
        make_tasks_json("1", "no_prd"), encoding="utf-8"
    )

    meta = SpecMeta(
        spec_id="1",
        spec_name="no_prd",
        status="active",
        dir=str(spec_dir),
    )
    return spec_dir, meta


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestSpecParser:
    """Tests for SpecParser.parse()."""

    def test_parse_all_artifacts(
        self, valid_spec_pack: tuple[Path, SpecMeta]
    ) -> None:
        """TS-13-3: Parse spec pack loads all artifacts.

        Requirement: 13-REQ-2.1, 13-REQ-2.2, 13-REQ-2.3, 13-REQ-2.4,
                     13-REQ-2.5, 13-REQ-5.2
        Verify all spec artifacts are parsed into models and the
        resulting ParsedSpec contains non-null fields.
        """
        _spec_dir, meta = valid_spec_pack
        parser = SpecParser()
        parsed = parser.parse(meta)

        assert parsed.requirements is not None
        assert parsed.test_spec is not None
        assert parsed.tasks is not None
        assert len(parsed.prd_text) > 0
        assert parsed.meta.spec_id == "1"
        assert parsed.meta.spec_name == "base_app"

    def test_missing_json_raises_spec_parse_error(
        self, spec_pack_no_requirements: tuple[Path, SpecMeta]
    ) -> None:
        """TS-13-E3: Missing JSON artifact raises SpecParseError.

        Requirement: 13-REQ-2.E1
        Verify missing required JSON files are caught and reported.
        """
        _spec_dir, meta = spec_pack_no_requirements
        parser = SpecParser()

        with pytest.raises(SpecParseError, match="requirements.json"):
            parser.parse(meta)

    def test_invalid_json_raises_spec_parse_error(
        self, spec_pack_invalid_json: tuple[Path, SpecMeta]
    ) -> None:
        """TS-13-E4: Invalid JSON raises SpecParseError.

        Requirement: 13-REQ-2.E2
        Verify malformed JSON is caught and reported.
        """
        _spec_dir, meta = spec_pack_invalid_json
        parser = SpecParser()

        with pytest.raises(SpecParseError):
            parser.parse(meta)

    def test_missing_prd_warns_and_uses_empty(
        self,
        spec_pack_no_prd: tuple[Path, SpecMeta],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-13-E5: Missing prd.md warns and uses empty string.

        Requirement: 13-REQ-2.E3
        Verify missing PRD is handled gracefully with a warning and
        prd_text set to empty string.
        """
        _spec_dir, meta = spec_pack_no_prd
        parser = SpecParser()

        with caplog.at_level(logging.WARNING):
            parsed = parser.parse(meta)

        assert parsed.prd_text == ""
        assert any("prd.md" in record.message for record in caplog.records)
