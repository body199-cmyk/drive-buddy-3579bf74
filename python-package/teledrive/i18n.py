"""Locale loader with runtime language toggle."""
from __future__ import annotations

import json
from pathlib import Path

from .config import CONFIG, SUPPORTED_LANGUAGES


_LOCALE_DIR = Path(__file__).parent / "locale"
_CACHE: dict[str, dict[str, str]] = {}


def load(lang: str) -> dict[str, str]:
    if lang in _CACHE:
        return _CACHE[lang]
    path = _LOCALE_DIR / f"{lang}.json"
    if not path.exists():
        path = _LOCALE_DIR / "en.json"
    _CACHE[lang] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[lang]


def t(key: str, lang: str | None = None) -> str:
    lang = lang or CONFIG.language
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    return load(lang).get(key, key)


def set_language(lang: str) -> None:
    if lang in SUPPORTED_LANGUAGES:
        CONFIG.language = lang


def toggle() -> str:
    CONFIG.language = "ar" if CONFIG.language == "en" else "en"
    return CONFIG.language


def keyset(lang: str) -> set[str]:
    return set(load(lang).keys())
