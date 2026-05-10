"""Minimal i18n: OS language detection and JSON locale files."""

from __future__ import annotations

import json
import locale
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

SUPPORTED_LANGUAGES = (
    "en",
    "ru",
    "zh-hans",
    "zh-hant",
    "hi",
    "es",
    "fr",
    "ar",
    "bn",
    "pt",
    "ur",
    "uk",
    "pl",
    "be",
    "ja",
    "ko",
    "de",
    "it",
    "nl",
    "tr",
    "el",
    "cs",
    "sv",
    "ro",
    "hu",
)
_SUPPORTED_SET = frozenset(SUPPORTED_LANGUAGES)
DEFAULT_LANGUAGE = "en"
LANGUAGE_ENV_VAR = "ROBOT_LANGUAGE"

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


def normalize_language(value: str | None) -> str | None:
    """Map locale strings to a supported language code; unsupported returns ``None``."""
    if value is None:
        return None
    raw = value.strip()
    if not raw or raw == "C":
        return None
    # LANGUAGE can be "de:fr:en" — take first segment
    first = raw.split(":")[0].strip()
    # Strip encoding suffix: ru_RU.UTF-8 -> ru_RU
    base = first.split(".")[0].strip()
    # Normalize separators to underscore
    norm = base.replace("-", "_")
    parts = norm.split("_")
    primary = (parts[0] or "").lower()

    if primary == "zh":
        rest = "_".join(parts[1:]).lower()
        if "hans" in rest:
            return "zh-hans"
        if "hant" in rest:
            return "zh-hant"
        if any(r in rest for r in ("cn", "sg")):
            return "zh-hans"
        if any(r in rest for r in ("tw", "hk", "mo")):
            return "zh-hant"
        return "zh-hans"

    if primary in _SUPPORTED_SET:
        return primary
    return None


def detect_language() -> str:
    """Resolve UI language: ``ROBOT_LANGUAGE`` override, then OS locale, else ``en``."""
    override = os.environ.get(LANGUAGE_ENV_VAR)
    if override is not None and override.strip() != "":
        lang = normalize_language(override.strip())
        if lang is not None:
            return lang

    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        lang = normalize_language(os.environ.get(var))
        if lang is not None:
            return lang

    try:
        loc = locale.getlocale(locale.LC_MESSAGES)
    except (AttributeError, ValueError, OSError):
        loc = (None, None)
    if loc and loc[0]:
        lang = normalize_language(loc[0])
        if lang is not None:
            return lang

    return DEFAULT_LANGUAGE


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def _load_catalog(language: str) -> Mapping[str, str]:
    path = _LOCALES_DIR / f"{language}.json"
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    out: dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise TypeError(f"Invalid locale entry in {path}: {k!r}")
        out[k] = v
    return out


def t(key: str, **kwargs: object) -> str:
    """Translate ``key`` for the current language; format with ``kwargs`` if placeholders exist."""
    lang = detect_language()
    catalog = _load_catalog(lang)
    template = catalog.get(key)
    if template is None:
        if lang != DEFAULT_LANGUAGE:
            template = _load_catalog(DEFAULT_LANGUAGE).get(key)
        if template is None:
            raise KeyError(f"Missing i18n key {key!r} in {lang} and {DEFAULT_LANGUAGE}")
    return template.format(**kwargs) if kwargs else template


def clear_translation_cache() -> None:
    """Clear loaded locale JSON (for tests)."""
    _load_catalog.cache_clear()
