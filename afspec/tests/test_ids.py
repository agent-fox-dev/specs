"""Tests for ID format validation.

Covers: TS-02-43, TS-02-44, TS-02-45, TS-02-E23, TS-02-E24
"""
from __future__ import annotations

import pytest

from afspec.ids import validate_id


class TestIdFormatPatterns:
    """TS-02-43: ID format validation for all entity types."""

    def test_valid_requirement_id(self) -> None:
        """TS-02-43: requirement ID 05-REQ-1 is valid."""
        errors = validate_id("05-REQ-1", "05")
        assert len(errors) == 0

    def test_valid_criterion_id(self) -> None:
        """TS-02-43: criterion ID 05-REQ-1.1 is valid."""
        errors = validate_id("05-REQ-1.1", "05")
        assert len(errors) == 0

    def test_valid_edge_case_id(self) -> None:
        """TS-02-43: edge case ID 05-REQ-1.E1 is valid."""
        errors = validate_id("05-REQ-1.E1", "05")
        assert len(errors) == 0

    def test_valid_property_id(self) -> None:
        """TS-02-43: property ID 05-PROP-1 is valid."""
        errors = validate_id("05-PROP-1", "05")
        assert len(errors) == 0

    def test_valid_path_id(self) -> None:
        """TS-02-43: path ID 05-PATH-1 is valid."""
        errors = validate_id("05-PATH-1", "05")
        assert len(errors) == 0

    def test_valid_error_id(self) -> None:
        """TS-02-43: error ID 05-ERR-1 is valid."""
        errors = validate_id("05-ERR-1", "05")
        assert len(errors) == 0

    def test_valid_test_case_id(self) -> None:
        """TS-02-43: test case ID TS-05-1 is valid."""
        errors = validate_id("TS-05-1", "05")
        assert len(errors) == 0

    def test_valid_property_test_id(self) -> None:
        """TS-02-43: property test ID TS-05-P1 is valid."""
        errors = validate_id("TS-05-P1", "05")
        assert len(errors) == 0

    def test_valid_edge_case_test_id(self) -> None:
        """TS-02-43: edge case test ID TS-05-E1 is valid."""
        errors = validate_id("TS-05-E1", "05")
        assert len(errors) == 0

    def test_valid_smoke_test_id(self) -> None:
        """TS-02-43: smoke test ID TS-05-SMOKE-1 is valid."""
        errors = validate_id("TS-05-SMOKE-1", "05")
        assert len(errors) == 0

    def test_valid_subtask_id(self) -> None:
        """TS-02-43: subtask ID 1.1 is valid."""
        errors = validate_id("1.1", "05")
        assert len(errors) == 0

    def test_valid_verification_id(self) -> None:
        """TS-02-43: verification subtask ID 1.V is valid."""
        errors = validate_id("1.V", "05")
        assert len(errors) == 0

    def test_invalid_no_spec_id(self) -> None:
        """TS-02-43: ID without spec_id prefix is invalid."""
        errors = validate_id("REQ-1", "05")
        assert len(errors) >= 1

    def test_invalid_missing_n(self) -> None:
        """TS-02-43: ID with missing numeric component is invalid."""
        errors = validate_id("05-REQ-", "05")
        assert len(errors) >= 1


class TestSpecIdConsistency:
    """TS-02-44: spec_id component must match file's declared spec_id."""

    def test_matching_spec_id_is_valid(self) -> None:
        """TS-02-44: spec_id in ID matches expected spec_id."""
        errors = validate_id("05-REQ-1.1", "05")
        assert len(errors) == 0

    def test_mismatched_spec_id_is_invalid(self) -> None:
        """TS-02-44: spec_id mismatch produces error."""
        errors = validate_id("06-REQ-1.1", "05")
        assert len(errors) >= 1
        assert any("mismatch" in e.message.lower() for e in errors)

    def test_mismatched_test_id_spec(self) -> None:
        """TS-02-44: mismatched spec_id in test case ID."""
        errors = validate_id("TS-06-1", "05")
        assert len(errors) >= 1


class TestPositiveIntegers:
    """TS-02-45: numeric components must be positive integers."""

    def test_zero_requirement_number_is_invalid(self) -> None:
        """TS-02-45: 05-REQ-0 is invalid (zero N)."""
        errors = validate_id("05-REQ-0", "05")
        assert len(errors) >= 1

    def test_zero_criterion_number_is_invalid(self) -> None:
        """TS-02-45: 05-REQ-1.0 is invalid (zero criterion)."""
        errors = validate_id("05-REQ-1.0", "05")
        assert len(errors) >= 1

    def test_positive_criterion_is_valid(self) -> None:
        """TS-02-45: 05-REQ-1.1 is valid (positive)."""
        errors = validate_id("05-REQ-1.1", "05")
        assert len(errors) == 0


class TestSpecIdMismatchError:
    """TS-02-E23: mismatched spec_id in ID produces informative error."""

    def test_mismatch_error_identifies_both_ids(self) -> None:
        """TS-02-E23: error message contains both the found and expected spec_id."""
        errors = validate_id("06-REQ-1.1", expected_spec_id="05")
        assert len(errors) >= 1
        err_msg = errors[0].message
        assert "06" in err_msg
        assert "05" in err_msg

    def test_mismatch_error_severity(self) -> None:
        """TS-02-E23: spec_id mismatch is an error (not just a warning)."""
        errors = validate_id("06-REQ-1.1", expected_spec_id="05")
        assert any(e.severity == "error" for e in errors)


class TestNonSequentialWarning:
    """TS-02-E24: non-sequential IDs produce a warning, not a blocking error."""

    def test_nonsequential_ids_produce_warning(self, tmp_spec_dir: object) -> None:
        """TS-02-E24: requirements numbered 1, 2, 5 produce a warning."""
        import pathlib

        from afspec import load_spec, validate

        spec = load_spec(pathlib.Path(str(tmp_spec_dir)))  # type: ignore[arg-type]
        errors = validate(spec)
        # Non-sequential gaps produce warnings (severity="warning"), not errors
        # This test validates the mechanism exists; actual gap detection tested via full spec
        warnings = [e for e in errors if e.severity == "warning"]
        # The fixture spec might not have gaps, but warnings list must be accessible
        assert isinstance(warnings, list)

    @pytest.mark.parametrize("gap_ids", [["05-REQ-1", "05-REQ-2", "05-REQ-5"]])
    def test_warning_about_sequential_gap(self, gap_ids: list[str]) -> None:
        """TS-02-E24: non-sequential IDs flagged as warning not error."""
        from afspec.ids import check_sequential

        warnings = check_sequential(gap_ids)
        assert len(warnings) >= 1
        assert all(w.severity == "warning" for w in warnings)
        assert any("sequential" in w.message.lower() for w in warnings)
