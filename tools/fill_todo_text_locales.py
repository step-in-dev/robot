#!/usr/bin/env python3
"""One-off: fill todoText in task .env files for all SUPPORTED_LANGUAGES (except en/ru).

Requires: pip install deep-translator

Run from repo root:
  python tools/fill_todo_text_locales.py           # add any missing locale keys
  python tools/fill_todo_text_locales.py --fix-rtl  # rebuild ar/ur from en (bidi-safe)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound

# Must match robot/i18n.py
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

# Google Translate target codes (deep_translator)
_GOOGLE = {
    "zh-hans": "zh-CN",
    "zh-hant": "zh-TW",
}


def _google_target(code: str) -> str:
    return _GOOGLE.get(code, code.replace("-", "-"))


def _cache_path() -> Path:
    return Path(__file__).resolve().parent / "_todo_translate_cache.json"


def _load_cache() -> dict[str, str]:
    p = _cache_path()
    if not p.is_file():
        return {}
    with p.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {str(k): str(v) for k, v in raw.items()}


def _save_cache(cache: dict[str, str]) -> None:
    p = _cache_path()
    with p.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def _cache_key(lang: str, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
    return f"{lang}:{h}"


def translate_line(lang: str, english: str, cache: dict[str, str]) -> str:
    key = _cache_key(lang, english)
    if key in cache:
        return cache[key]
    tgt = _google_target(lang)
    last_err: Exception | None = None
    for attempt in range(6):
        try:
            tr = GoogleTranslator(source="en", target=tgt)
            out = tr.translate(english)
            if not out or not str(out).strip():
                raise TranslationNotFound(english)
            cache[key] = str(out)
            time.sleep(0.15)
            return cache[key]
        except (TranslationNotFound, OSError, TimeoutError) as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))
    assert last_err is not None
    raise last_err


_LRI = "\u2066"
_PDI = "\u2069"

# Match longer tokens first (alternation is left-to-first-match).
_PROTECT_PAT = re.compile(
    r'paint\(\)|printn\(\)|task\(\)|"for"|"while"|"if"|"else"|"def"|Robot'
)


def protect_en_for_rtl(en: str) -> tuple[str, list[str]]:
    """Replace LTR technical snippets with placeholders before MT to ar/ur."""
    store: list[str] = []

    def repl(m: re.Match[str]) -> str:
        store.append(m.group(0))
        return f"[[[{len(store) - 1}]]]"

    return _PROTECT_PAT.sub(repl, en), store


def restore_rtl_markers(translated: str, store: list[str]) -> str:
    """Swap placeholders back to originals wrapped in bidi isolates."""
    out = translated
    for i, orig in enumerate(store):
        marker = f"[[[{i}]]]"
        wrapped = f"{_LRI}{orig}{_PDI}"
        out = out.replace(marker, wrapped)
    return out


def wrap_digits_outside_isolates(text: str) -> str:
    """Isolate Western digit runs not already prefixed with LRI."""

    def repl(m: re.Match[str]) -> str:
        i = m.start()
        if i > 0 and text[i - 1] == _LRI:
            return m.group(0)
        return f"{_LRI}{m.group(0)}{_PDI}"

    return re.sub(r"[0-9]+", repl, text)


def translate_ar_ur(lang: str, en: str, cache: dict[str, str]) -> str:
    """Translate to Arabic/Urdu with preserved Python tokens and bidi isolates."""
    protected, store = protect_en_for_rtl(en)
    raw = translate_line(lang, protected, cache)
    out = restore_rtl_markers(raw, store)
    return wrap_digits_outside_isolates(out)


def merge_todo_text(existing: dict, cache: dict[str, str]) -> dict[str, str]:
    en = existing.get("en")
    if not isinstance(en, str) or not en.strip():
        raise ValueError("todoText must have non-empty en string")
    out: dict[str, str] = {}
    for lang in SUPPORTED_LANGUAGES:
        if lang in existing and isinstance(existing[lang], str):
            out[lang] = existing[lang]
        elif lang in ("en", "ru"):
            raise ValueError("todoText must include string keys 'en' and 'ru'")
        else:
            if lang in ("ar", "ur"):
                translated = translate_ar_ur(lang, en, cache)
            else:
                translated = translate_line(lang, en, cache)
            out[lang] = translated
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tasks_dir = root / "robot" / "tasks"
    cache = _load_cache()
    paths = sorted(tasks_dir.glob("*.env"))
    updated = 0
    fix_rtl = "--fix-rtl" in sys.argv
    for path in paths:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        todo = data.get("todoText")
        if not isinstance(todo, dict) or "en" not in todo:
            continue
        if fix_rtl:
            en = todo.get("en")
            if not isinstance(en, str) or not en.strip():
                continue
            ar = translate_ar_ur("ar", en, cache)
            ur = translate_ar_ur("ur", en, cache)
            todo2 = {**todo, "ar": ar, "ur": ur}
            new_todo = {lang: todo2[lang] for lang in SUPPORTED_LANGUAGES}
            for k, v in todo2.items():
                if k not in new_todo and isinstance(v, str):
                    new_todo[k] = v
            data["todoText"] = new_todo
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            updated += 1
            print(path.name, flush=True)
            continue
        missing = [
            lang
            for lang in SUPPORTED_LANGUAGES
            if lang not in todo or not isinstance(todo.get(lang), str)
        ]
        if not missing:
            continue
        merged = merge_todo_text(todo, cache)
        new_todo = {lang: merged[lang] for lang in SUPPORTED_LANGUAGES}
        for k, v in todo.items():
            if k not in new_todo and isinstance(v, str):
                new_todo[k] = v
        data["todoText"] = new_todo
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated += 1
        print(path.name, flush=True)
    _save_cache(cache)
    print(f"Updated {updated} files.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
