"""Minimal i18n: OS language detection and JSON locale files."""

from __future__ import annotations

import ctypes
import json
import locale
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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


def _normalize_chinese_language(parts: List[str]) -> str:
    """Map Chinese locale parts to ``zh-hans`` or ``zh-hant``."""
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


def normalize_language(value: Optional[str]) -> Optional[str]:
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
        return _normalize_chinese_language(parts)

    if primary in _SUPPORTED_SET:
        return primary
    return None


def _language_from_locale_env() -> Optional[str]:
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        lang = normalize_language(os.environ.get(var))
        if lang is not None:
            return lang
    return None


def _language_from_getlocale_messages() -> Optional[str]:
    try:
        loc = locale.getlocale(locale.LC_MESSAGES)
    except (AttributeError, ValueError, OSError):
        return None
    if not loc or not loc[0]:
        return None
    return normalize_language(loc[0])


def _windows_ui_locale_string() -> Optional[str]:
    """Return a locale-style string for the Windows UI language, or ``None``.

    Uses ``GetUserDefaultUILanguage`` (display language), not regional format
    settings. Only meaningful on Windows; returns ``None`` elsewhere or on
    failure. Relies on :data:`locale.windows_locale` for LANGID → name mapping.
    """
    if sys.platform != "win32":
        return None
    try:
        lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    wl = getattr(locale, "windows_locale", None)
    if not isinstance(wl, dict):
        return None
    name = wl.get(lang_id)
    if name:
        return name
    # Some builds may omit newer LANGIDs; try the low 16 bits.
    return wl.get(lang_id & 0xFFFF)


def detect_language() -> str:
    """Resolve UI language: ``ROBOT_LANGUAGE`` override, then OS locale, else ``en``."""
    override = os.environ.get(LANGUAGE_ENV_VAR)
    if override is not None and override.strip() != "":
        lang = normalize_language(override.strip())
        if lang is not None:
            return lang

    lang = _language_from_locale_env()
    if lang is not None:
        return lang

    if sys.platform == "win32":
        win_loc = _windows_ui_locale_string()
        if win_loc:
            lang = normalize_language(win_loc)
            if lang is not None:
                return lang

    lang = _language_from_getlocale_messages()
    if lang is not None:
        return lang

    return DEFAULT_LANGUAGE


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def _load_catalog(language: str) -> Mapping[str, str]:
    path = _LOCALES_DIR / f"{language}.json"
    with path.open(encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    out: Dict[str, str] = {}
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
