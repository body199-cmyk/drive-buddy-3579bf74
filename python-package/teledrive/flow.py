"""Derived UI flow state (M20-T03).

The UI must never guess where the user is. This service reads the live
ApplicationContext and reports, without inventing anything, which of the five
steps is current and which ones have genuinely been satisfied.

No Gradio import here: this is an application service, exactly like the ones in
services.py. Rendering lives in ui_flow_view.py.
"""
from __future__ import annotations

from dataclasses import dataclass

STEP_ORDER = ("connect", "analyze", "select", "queue", "monitor")

QUEUED_STATES = ("Pending", "NeedsRetry", "Downloaded", "Paused")
ACTIVE_STATES = ("Downloading", "Uploading")


@dataclass(frozen=True)
class FlowState:
    telegram_ready: bool = False
    drive_ready: bool = False
    folder_ready: bool = False
    analyzed: int = 0
    visible: int = 0
    selected: int = 0
    selected_bytes: int = 0
    queued: int = 0
    active: int = 0
    done: int = 0
    failed: int = 0
    running: bool = False
    folder_id: str = ""
    step: str = "connect"


class FlowService:
    """Read-only view over the live context. Never mutates anything."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # -- individual probes, each defensive: a half-built context must not
    #    crash the whole shell on page load.

    def _telegram_ready(self) -> bool:
        auth = getattr(self.ctx, "telegram_auth", None)
        return bool(auth is not None and getattr(auth, "authorized", False))

    def _drive_ready(self) -> bool:
        auth = getattr(self.ctx, "drive_auth", None)
        return bool(auth is not None and getattr(auth, "connected", False))

    def _folder_id(self) -> str:
        folder_id = getattr(self.ctx.config, "drive_folder_id", None)
        if folder_id:
            return str(folder_id)
        folders = getattr(self.ctx, "drive_folders", None)
        selected = getattr(folders, "selected", None)
        if selected is not None:
            try:
                value = selected() if callable(selected) else selected
            except Exception:  # pragma: no cover - defensive
                value = None
            identifier = getattr(value, "id", None)
            if identifier:
                return str(identifier)
        return ""

    def _counts(self) -> dict:
        try:
            from . import database as db

            return dict(db.counts_by_state() or {})
        except Exception:  # pragma: no cover - defensive
            return {}

    def state(self) -> FlowState:
        selection = getattr(self.ctx, "selection", None)
        candidates = list(getattr(selection, "candidates", []) or [])
        try:
            visible = list(selection.visible()) if selection is not None else []
        except Exception:  # pragma: no cover - defensive
            visible = []
        try:
            chosen = list(selection.selected_items()) if selection is not None else []
        except Exception:  # pragma: no cover - defensive
            chosen = []

        counts = self._counts()
        queued = sum(int(counts.get(name, 0)) for name in QUEUED_STATES)
        active = sum(int(counts.get(name, 0)) for name in ACTIVE_STATES)
        done = int(counts.get("Uploaded", 0)) + int(counts.get("Skipped", 0))
        failed = int(counts.get("Failed", 0))

        manager = getattr(self.ctx, "queue_manager", None)
        try:
            running = bool(manager is not None and manager.running())
        except Exception:  # pragma: no cover - defensive
            running = False

        telegram_ready = self._telegram_ready()
        drive_ready = self._drive_ready()
        folder_id = self._folder_id()
        connected = telegram_ready and drive_ready and bool(folder_id)

        if not connected:
            step = "connect"
        elif not candidates:
            step = "analyze"
        elif not chosen and queued == 0 and active == 0:
            step = "select"
        elif not running and active == 0:
            step = "queue"
        else:
            step = "monitor"

        return FlowState(
            telegram_ready=telegram_ready,
            drive_ready=drive_ready,
            folder_ready=bool(folder_id),
            analyzed=len(candidates),
            visible=len(visible),
            selected=len(chosen),
            selected_bytes=sum(int(getattr(i, "size_bytes", 0) or 0) for i in chosen),
            queued=queued,
            active=active,
            done=done,
            failed=failed,
            running=running,
            folder_id=folder_id,
            step=step,
        )
