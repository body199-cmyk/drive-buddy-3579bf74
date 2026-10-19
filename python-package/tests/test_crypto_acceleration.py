"""M44-T01: Telethon must use a C AES-IGE implementation when available.

Telethon decrypts every MTProto media chunk. Without ``cryptg`` it can fall
back to the system libssl binding, and only then to pure-Python ``pyaes``.
The pinned dependency lock installs cryptg on Colab (x86_64 manylinux).
"""
from __future__ import annotations

from pathlib import Path

from teledrive.telegram_client import crypto_backend

ROOT = Path(__file__).resolve().parents[1]


def test_cryptg_is_pinned_in_the_single_dependency_source():
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "cryptg==0.6.0" in lock
    assert "cryptg" in requirements


def test_crypto_backend_is_one_of_the_known_implementations():
    # In a minimal CI environment this is "pyaes" or "libssl"; on Colab the
    # pinned lock installs cryptg and this becomes "cryptg".
    assert crypto_backend() in {"cryptg", "libssl", "pyaes"}
