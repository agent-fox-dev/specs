"""Exception hierarchy for the afspec library."""
from __future__ import annotations


class AfspecError(Exception):
    """Base class for all afspec errors."""


class SpecValidationError(AfspecError):
    """Raised when spec validation fails (schema or cross-file integrity).

    Attributes:
        errors: List of ValidationError instances describing all violations.
    """

    def __init__(self, message: str, errors: list[object] | None = None) -> None:
        super().__init__(message)
        self.errors: list[object] = errors or []


class LifecycleError(AfspecError):
    """Raised when a lifecycle transition or mutation guard is violated.

    Attributes:
        current_state: The spec's current lifecycle state.
        target_state: The requested target state (None for mutation-guard errors).
        field: The rejected field name (None for transition errors).
    """

    def __init__(
        self,
        message: str,
        current_state: str = "",
        target_state: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state
        self.field = field


class IncompleteSpecError(AfspecError):
    """Raised when a spec folder is missing one or more required files.

    Attributes:
        missing_files: List of file names that are absent.
    """

    def __init__(self, message: str, missing_files: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_files: list[str] = missing_files or []
