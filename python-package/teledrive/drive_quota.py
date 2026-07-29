"""Drive quota preflight helper."""
from __future__ import annotations

from dataclasses import dataclass

from .config import DRIVE_QUOTA_WARN_RATIO


@dataclass
class QuotaReport:
    limit: int
    usage: int
    free: int
    ratio_used: float
    warn: bool
    ok: bool
    message_key: str


def evaluate(quota: dict[str, int], required_bytes: int) -> QuotaReport:
    limit = int(quota.get("limit", 0) or 0)
    usage = int(quota.get("usage", 0) or 0)
    free = max(0, limit - usage) if limit else 10**18  # unlimited plan
    ratio = (usage / limit) if limit else 0.0
    warn = limit > 0 and ratio >= DRIVE_QUOTA_WARN_RATIO
    ok = required_bytes <= free
    if not ok:
        return QuotaReport(limit, usage, free, ratio, warn, False, "err.drive_full")
    if warn:
        return QuotaReport(limit, usage, free, ratio, True, True, "warn.drive_almost_full")
    return QuotaReport(limit, usage, free, ratio, False, True, "ok.quota")


def preflight_or_raise(drive, required_bytes: int) -> QuotaReport:
    q = drive.storage_quota()
    r = evaluate(q, required_bytes)
    if not r.ok:
        raise RuntimeError(f"Drive insufficient storage: need {required_bytes}, free {r.free}")
    return r
