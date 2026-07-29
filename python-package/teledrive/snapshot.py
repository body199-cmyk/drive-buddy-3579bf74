"""Human-readable project snapshot for the maintenance cell."""
from __future__ import annotations

from . import database as db, __version__, __spec_version__
from .config import CONFIG


def generate() -> str:
    counts = db.counts_by_state()
    lines = [
        f"TeleDrive v{__version__} (spec {__spec_version__})",
        f"Language: {CONFIG.language}",
        f"Concurrency: {CONFIG.concurrency} ({CONFIG.concurrency_value()})",
        "",
        "Counts by state:",
    ]
    for k in sorted(counts):
        lines.append(f"  {k}: {counts[k]}")
    return "\n".join(lines)
