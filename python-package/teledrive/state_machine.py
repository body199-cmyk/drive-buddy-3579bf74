"""State machine enforcing legal MediaItem transitions per Constitution D4."""
from __future__ import annotations

from .models import STATES


LEGAL: dict[str, set[str]] = {
    "Pending":     {"Analyzing", "Downloading", "Skipped", "Deleted", "Stopped"},
    "Analyzing":   {"Pending", "Failed", "Skipped"},
    "Downloading": {"Downloaded", "Paused", "Failed", "NeedsRetry", "Stopped"},
    "Downloaded":  {"Uploading", "Paused", "NeedsRetry", "Stopped"},
    "Uploading":   {"Verifying", "Paused", "Failed", "NeedsRetry", "Stopped"},
    "Verifying":   {"UploadedPendingCheckpoint", "Failed", "NeedsRetry", "Stopped"},
    "UploadedPendingCheckpoint": {"Uploaded", "Failed", "NeedsRetry"},
    "Uploaded":    {"Deleted"},
    "Paused":      {"Downloading", "Uploading", "Pending", "Stopped"},
    "NeedsRetry":  {"Pending", "Downloading", "Uploading", "Failed", "Stopped"},
    "Failed":      {"NeedsRetry", "Stopped", "Deleted"},
    "Skipped":     {"Pending", "Deleted"},
    # Stopped is FINAL (Phase C). A stopped item is never silently resurrected;
    # the operator must re-analyze/enqueue it to try again.
    "Stopped":     {"Deleted"},
    "Deleted":     set(),
}


class IllegalTransition(Exception):
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        super().__init__(f"illegal transition {from_state} -> {to_state} {reason}".strip())
        self.from_state = from_state
        self.to_state = to_state


def assert_transition(from_state: str, to_state: str) -> None:
    if from_state not in LEGAL:
        raise IllegalTransition(from_state, to_state, "(unknown from-state)")
    if to_state not in STATES:
        raise IllegalTransition(from_state, to_state, "(unknown to-state)")
    if to_state not in LEGAL[from_state]:
        raise IllegalTransition(from_state, to_state)


def can_transition(from_state: str, to_state: str) -> bool:
    return from_state in LEGAL and to_state in LEGAL.get(from_state, set())


def terminal(state: str) -> bool:
    return not LEGAL.get(state)
