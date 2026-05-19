"""Lifecycle state machine for afspec.

STUB — real implementation in task group 10.
"""
from __future__ import annotations

from afspec.models import Spec


def _compute_intent_hash(body: str) -> str:
    """Compute SHA-256 of the normalized Intent section body.

    STUB: raises NotImplementedError. Implemented in task group 10.
    """
    raise NotImplementedError("_compute_intent_hash not yet implemented (task group 10)")


def _check_transition(current_state: str, target_state: str) -> None:
    """Verify a lifecycle transition is legal; raise LifecycleError if not.

    STUB: raises NotImplementedError. Implemented in task group 10.
    """
    raise NotImplementedError("_check_transition not yet implemented (task group 10)")


def transition(spec: Spec, target_status: str) -> Spec:
    """Apply a lifecycle transition to a spec.

    STUB: raises NotImplementedError. Implemented in task group 10.
    """
    raise NotImplementedError("transition not yet implemented (task group 10)")
