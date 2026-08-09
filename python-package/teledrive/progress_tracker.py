"""Global + per-item progress tracking with speed and ETA."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class ItemProgress:
    item_id: str = ""
    name: str = ""
    total: int = 0
    downloaded: int = 0
    uploaded: int = 0
    phase: str = "idle"  # download | upload | idle
    updated_at: float = field(default_factory=time.monotonic)


class ProgressTracker:
    def __init__(self):
        # RLock: snapshot() holds the lock while composing speeds/ETA, and those
        # helpers acquire the SAME lock — a plain Lock self-deadlocks on the
        # first snapshot() call (found by real execution in M15-T04).
        self._lock = threading.RLock()
        self._items: dict[str, ItemProgress] = {}
        self._done_bytes = 0
        self._done_files = 0
        self._failed_files = 0
        self._skipped_files = 0
        self._total_files = 0
        self._total_bytes = 0
        self._speed_samples: deque[tuple[float, int]] = deque(maxlen=30)
        self._session_start = time.monotonic()

    def register_totals(self, files: int, bytes_: int) -> None:
        with self._lock:
            self._total_files = files
            self._total_bytes = bytes_

    def start_item(self, item_id: str, name: str, total: int, phase: str) -> None:
        with self._lock:
            self._items[item_id] = ItemProgress(item_id=item_id, name=name, total=total, phase=phase)

    def update(self, item_id: str, current: int, phase: str | None = None) -> None:
        with self._lock:
            p = self._items.get(item_id)
            if not p:
                return
            if phase:
                p.phase = phase
            if phase == "upload":
                delta = current - p.uploaded
                p.uploaded = current
            else:
                delta = current - p.downloaded
                p.downloaded = current
            p.updated_at = time.monotonic()
            self._speed_samples.append((p.updated_at, max(0, delta)))

    def finish_item(self, item_id: str, ok: bool, skipped: bool = False) -> None:
        with self._lock:
            p = self._items.pop(item_id, None)
            if skipped:
                self._skipped_files += 1
                return
            if ok:
                self._done_files += 1
                if p:
                    self._done_bytes += p.total
            else:
                self._failed_files += 1

    def instant_speed(self) -> float:
        now = time.monotonic()
        with self._lock:
            recent = [(t, b) for (t, b) in self._speed_samples if now - t <= 5.0]
        if not recent:
            return 0.0
        span = max(0.001, recent[-1][0] - recent[0][0])
        return sum(b for _, b in recent) / span

    def average_speed(self) -> float:
        elapsed = max(0.001, time.monotonic() - self._session_start)
        return self._done_bytes / elapsed

    def eta_seconds(self) -> float:
        remaining = max(0, self._total_bytes - self._done_bytes)
        spd = self.instant_speed() or self.average_speed()
        if spd <= 0:
            return -1.0
        return remaining / spd

    def snapshot(self) -> dict:
        with self._lock:
            active = list(self._items.values())
            return {
                "session_start": self._session_start,
                "done_files": self._done_files,
                "failed_files": self._failed_files,
                "skipped_files": self._skipped_files,
                "total_files": self._total_files,
                "done_bytes": self._done_bytes,
                "total_bytes": self._total_bytes,
                "instant_speed": self.instant_speed(),
                "average_speed": self.average_speed(),
                "eta_seconds": self.eta_seconds(),
                "active": [
                    {
                        "id": p.item_id, "name": p.name, "phase": p.phase,
                        "downloaded": p.downloaded, "uploaded": p.uploaded, "total": p.total,
                        "pct_download": (p.downloaded / p.total * 100) if p.total else 0.0,
                        "pct_upload": (p.uploaded / p.total * 100) if p.total else 0.0,
                    }
                    for p in active
                ],
            }


PROGRESS = ProgressTracker()
