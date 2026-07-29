"""Permanent guard for Constitution Section 3.

Only `teledrive/async_runtime.py` may create or run an event loop. Any other
package file containing `asyncio.new_event_loop()` or `asyncio.run(` is a
build-breaking bug.
"""
from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "teledrive"
ALLOWED = {"async_runtime.py"}
FORBIDDEN = ("asyncio.new_event_loop(", "asyncio.run(", "run_until_complete(")


def _python_files():
    return sorted(p for p in PACKAGE_DIR.rglob("*.py"))


def test_package_dir_exists():
    assert PACKAGE_DIR.is_dir(), PACKAGE_DIR


def test_no_ad_hoc_event_loops():
    offenders = []
    for path in _python_files():
        if path.name in ALLOWED:
            continue
        source = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN:
            if needle in source:
                offenders.append(f"{path.relative_to(PACKAGE_DIR)}: {needle}")
    assert not offenders, "ad-hoc event loops found: " + "; ".join(offenders)


def test_async_runtime_is_the_single_owner():
    source = (PACKAGE_DIR / "async_runtime.py").read_text(encoding="utf-8")
    assert "asyncio.new_event_loop()" in source
    assert "run_coroutine_threadsafe" in source
