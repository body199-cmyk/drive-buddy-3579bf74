"""Static gate: no Telegram/Drive credential literal may enter the tree.

The test never prints a matched value — only the offending path and line — so a
failing run can be pasted into a report without leaking anything.
"""
from __future__ import annotations

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent   # python-package/
REPO_ROOT = PACKAGE_ROOT.parent

SCAN_ROOTS = (
    PACKAGE_ROOT / "teledrive",
    PACKAGE_ROOT / "notebook",
    REPO_ROOT / "public",
)
SCAN_SUFFIXES = (".py", ".ipynb", ".json", ".md")

# api_id = ... / "api_id": "..." / api_hash = "..."
# phone  = ... / password = ...
PATTERNS = (
    re.compile(r"""\bapi_id["']?\s*[:=]\s*["']?\d{5,}""", re.I),
    re.compile(r"""\bapi_hash["']?\s*[:=]\s*["'][0-9a-f]{16,}["']""", re.I),
    re.compile(r"""\bphone["']?\s*[:=]\s*["']\+\d{6,}["']""", re.I),
    re.compile(r"""\b(2fa_)?password["']?\s*[:=]\s*["'][^"'\s]{4,}["']""", re.I),
)


def _files():
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in SCAN_SUFFIXES:
                yield path


def test_no_hardcoded_credentials_anywhere_in_the_shipped_tree():
    offenders: list[str] = []
    for path in _files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert not offenders, (
        "credential literal(s) found — remove the value, never commit it: "
        + ", ".join(sorted(set(offenders)))
    )
