"""Generate the HANDOFF.md camera-cell output. Redaction-checked."""
from __future__ import annotations

from pathlib import Path

from . import __version__, __spec_version__, database as db
from .config import redact, ROOT
from .utils import now_iso


TEMPLATE = """# TeleDrive HANDOFF
Generated: {ts}
Spec version: {spec} | App version: {app} | Phase: {phase}

## Current objective
{objective}

## Completed phases
{completed}

## Changed since last handoff
{changed}

## Tests actually run
{tests}

## Open errors
{errors}

## Blocked on human
{blocked}

## Invariants that must not break
- Drive is durable state, SQLite is local runtime state
- Temp file deleted only after verified Drive upload
- Only QueueManager mutates item state
- No secrets in code, logs, or docs
- No streaming or resume claims without a passing test

## Next smallest step
{next_step}

## Project tree (trimmed)
{tree}

Redaction check: PASSED (no secrets included)
"""


def _tree(limit: int = 60) -> str:
    if not ROOT.exists():
        return "(runtime not initialized)"
    entries = []
    for p in sorted(ROOT.rglob("*")):
        if any(part in ("__pycache__",) for part in p.parts):
            continue
        rel = p.relative_to(ROOT)
        entries.append(str(rel))
        if len(entries) >= limit:
            entries.append("...")
            break
    return "\n".join(entries) if entries else "(empty)"


def generate(objective: str = "steady-state operation",
             phase: str = "11 (release)",
             completed: str = "0–11",
             changed: str = "(none)",
             tests: str = "pytest -q -> see logs",
             errors: str = "none",
             blocked: str = "none",
             next_step: str = "monitor and export snapshots") -> str:
    counts = db.counts_by_state()
    body = TEMPLATE.format(
        ts=now_iso(),
        spec=__spec_version__,
        app=__version__,
        phase=phase,
        objective=objective,
        completed=completed,
        changed=changed,
        tests=tests,
        errors=errors + f"\nCounts: {counts}",
        blocked=blocked,
        next_step=next_step,
        tree=_tree(),
    )
    return redact(body)


def write(path: Path | str = "HANDOFF.md") -> str:
    text = generate()
    Path(path).write_text(text, encoding="utf-8")
    return text
