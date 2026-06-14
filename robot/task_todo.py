"""Resolve ``todoText`` from task ``.env`` JSON for display and loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .i18n import DEFAULT_LANGUAGE, detect_language, normalize_language


@dataclass(frozen=True)
class ResolvedTodoText:
    """Task condition text resolved for the current UI language."""

    text: str
    source_lang: Optional[str] = None


def normalized_todo_text_map(raw: dict) -> Dict[str, str]:
    """Return supported language keys from a localized ``todoText`` object."""
    by_lang: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        norm = normalize_language(key)
        if norm is not None:
            by_lang[norm] = value
    return by_lang


def resolve_todo_text_for_ui(raw: Any) -> ResolvedTodoText:
    """Resolve ``todoText`` for display and single-locale editing in the editor.

    Plain strings are returned as-is with no ``source_lang``. For localized
    maps, ``source_lang`` is the key whose value was chosen: current UI
    language, then :data:`DEFAULT_LANGUAGE` (``en``), or ``None`` when no
    suitable entry exists.
    """
    if isinstance(raw, str):
        return ResolvedTodoText(text=raw)
    if not isinstance(raw, dict):
        return ResolvedTodoText(text="")
    by_lang = normalized_todo_text_map(raw)
    if not by_lang:
        return ResolvedTodoText(text="")
    ui = detect_language()
    if ui in by_lang:
        return ResolvedTodoText(text=by_lang[ui], source_lang=ui)
    if DEFAULT_LANGUAGE in by_lang:
        return ResolvedTodoText(
            text=by_lang[DEFAULT_LANGUAGE], source_lang=DEFAULT_LANGUAGE
        )
    return ResolvedTodoText(text="")


def resolve_todo_text(raw: Any) -> str:
    """Return task condition text: plain string, or localized map resolved to UI language.

    If ``raw`` is a string, it is returned as-is (legacy format).
    If ``raw`` is a dict mapping locale keys to strings, pick the value for
    :func:`detect_language`, then fall back to :data:`DEFAULT_LANGUAGE` (``en``),
    then ``""``. Only string keys and string values contribute; keys are
    normalized with :func:`normalize_language` (e.g. ``ru_RU`` → ``ru``).
    Any other type yields ``""``.
    """
    return resolve_todo_text_for_ui(raw).text
