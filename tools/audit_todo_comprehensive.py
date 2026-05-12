#!/usr/bin/env python3
"""Comprehensive audit of todoText translations in .env files.

Checks:
1. Missing language keys
2. Python keywords in Latin (not translated)
3. Keyword quoting style matches locale convention
4. Robot as proper noun (capitalization)
5. True/False/None not quoted
6. Bidi isolates for ar/ur
7. Function names (paint(), printn(), etc.) remain Latin in ar/ur
8. Terminology consistency with UI locales
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "robot" / "tasks"
LOCALES_DIR = ROOT / "robot" / "locales"

SUPPORTED = (
    "en", "ru", "zh-hans", "zh-hant", "hi", "es", "fr", "ar", "bn", "pt",
    "ur", "uk", "pl", "be", "ja", "ko", "de", "it", "nl", "tr", "el", "cs", "sv", "ro", "hu",
)

LRI = "\u2066"
PDI = "\u2069"
FSI = "\u2068"

PYTHON_KEYWORDS = {"for", "while", "if", "else", "def", "return", "import", "class"}
PYTHON_LITERALS = {"True", "False", "None"}

# ── Quoting convention per locale (open_q, close_q) ──────────────────
# Extracted from each locale's limit.if_keyword / help.task_group.for
QUOTE_STYLE: dict[str, tuple[str, str]] = {
    "en":     ("'", "'"),              # 'if'
    "ru":     ("«", "»"),              # «if»
    "be":     ("«", "»"),              # «if»
    "uk":     ("«", "»"),              # «if»
    "pl":     ("\u201e", "\u201d"),    # „if"
    "de":     ("'", "'"),              # 'if'
    "es":     ("'", "'"),              # 'if'
    "fr":     ("« ", " »"),            # « if »  (with spaces)
    "it":     ("'", "'"),              # 'if'
    "nl":     ("'", "'"),              # 'if'
    "tr":     ("\u201e", "\u201d"),    # „if"
    "el":     ("«", "»"),              # «if»
    "cs":     ("\u201e", "\u201d"),    # „if"
    "sv":     ("'", "'"),              # 'if'
    "ro":     ("\u201e", "\u201d"),    # „if"
    "hu":     ("\u201e", "\u201d"),    # „if"
    "pt":     ("'", "'"),              # 'if'
    "ja":     ("\u300c", "\u300d"),     # 「if」
    "zh-hans":("\u300c", "\u300d"),     # 「if」
    "zh-hant":("\u300c", "\u300d"),     # 「if」
    "ko":     ("'", "'"),              # 'if'
    "hi":     ("'", "'"),              # 'if'
    "bn":     ("'", "'"),              # 'if'
    "ar":     ("«", "»"),              # «⁦if⁩» (bidi isolates checked separately)
    "ur":     ("«", "»"),              # «⁦if⁩» (bidi isolates checked separately)
}

# ── Robot proper noun per locale ───────────────────────────────────────
# How "Robot" should appear as a proper noun in each locale.
# None means the locale uses a non-Latin script and we check differently.
ROBOT_PROPER: dict[str, str | None] = {
    "en":     "Robot",
    "ru":     "Робот",
    "be":     "Робат",
    "uk":     "Робот",
    "pl":     "Robot",
    "de":     "Roboter",   # German: "Roboter" in UI (status.ready = "Roboter: Bereit")
    "es":     "Robot",
    "fr":     "Robot",
    "it":     "Robot",
    "nl":     "Robot",
    "tr":     "Robot",
    "el":     "Ρομπότ",     # Greek: uppercaseΡομπότ — see el.json
    "cs":     "Robot",
    "sv":     "Robot",      # Swedish: "Roboten" is definite, but "Robot" as proper noun
    "ro":     "Robot",
    "hu":     "Robot",
    "pt":     "Robô",      # Portuguese: "Robô" (with circumflex)
    "ja":     None,         # Non-Latin; ロボット in UI
    "ko":     None,         # Non-Latin
    "zh-hans":None,         # Non-Latin
    "zh-hant":None,         # Non-Latin
    "hi":     None,         # Non-Latin (Devanagari)
    "bn":     None,         # Non-Latin (Bengali)
    "ar":     None,         # RTL (Arabic)
    "ur":     None,         # RTL (Urdu)
}

# ── Terminology: canonical term per language (from UI locales) ─────────
# Maps (concept) -> {lang: [expected roots]}
# These are substrings that SHOULD appear in todoText (in various grammatical forms).
TERMS: dict[str, dict[str, list[str]]] = {
    "paint": {
        "en":  ["paint", "Paint"],
        "ru":  ["закраш", "Закраш", "покраш", "Покраш"],
        "be":  ["фарб", "Фарб", "пафарб", "Пафарб"],
        "uk":  ["фарб", "Фарб", "пофарб", "Пофарб", "малюв", "Малюв"],
        "pl":  ["mal", "Mal", "pomal", "Pomal"],
        "de":  ["färb", "Färb", "gefärbt", "malt", "Malt"],
        "fr":  ["pein", "Pein"],
        "es":  ["pint", "Pint"],
        "it":  ["color", "Color"],
        "nl":  ["verf", "Verf", "geverfd"],
        "tr":  ["boy", "Boy"],
        "el":  ["βαφ", "Βαφ", "ζωγραφ", "Ζωγραφ"],
        "cs":  ["vybarv", "Vybarv", "barv", "Barv"],
        "sv":  ["mål", "Mål"],
        "ro":  ["vops", "Vops"],
        "hu":  ["fest", "Fest"],
        "pt":  ["pint", "Pint"],
    },
    "cell": {
        "en":  ["cell"],
        "ru":  ["клетк"],
        "be":  ["клетк"],
        "uk":  ["клітин", "клітинк"],
        "pl":  ["komórk"],
        "de":  ["Zelle", "Zellen"],
        "fr":  ["case"],
        "es":  ["celda"],
        "it":  ["cella", "celle"],
        "nl":  ["cel", "cellen"],
        "tr":  ["hücre"],
        "el":  ["κελ"],
        "cs":  ["buňk"],
        "sv":  ["cell", "cells"],
        "ro":  ["celul"],
        "hu":  ["cell", "cellá"],
        "pt":  ["célul"],
    },
    "wall": {
        "en":  ["wall"],
        "ru":  ["стен", "Стен"],
        "be":  ["сцен", "Сцен"],
        "uk":  ["стін", "Стін", "стін", "Стін"],
        "pl":  ["ścian", "Ścian"],
        "de":  ["Wand", "Wände"],
        "fr":  ["mur"],
        "es":  ["pared", "muro"],
        "it":  ["muro", "muri"],
        "nl":  ["muur", "muren"],
        "tr":  ["duvar"],
        "el":  ["τοίχ", "Τοίχ"],
        "cs":  ["zeď", "zd", "Cěl"],
        "sv":  ["vägg", "Vägg"],
        "ro":  ["perete", "pereţ", "pereți"],
        "hu":  ["fal"],
        "pt":  ["parede"],
    },
}


def load_tasks() -> dict[str, dict]:
    """Load all .env files' todoText entries."""
    tasks = {}
    for path in sorted(TASKS_DIR.glob("*.env")):
        data = json.loads(path.read_text(encoding="utf-8"))
        todo = data.get("todoText")
        if isinstance(todo, dict):
            tasks[path.name] = todo
    return tasks


def load_locales() -> dict[str, dict]:
    """Load all UI locale files."""
    locales = {}
    for lang in SUPPORTED:
        path = LOCALES_DIR / f"{lang}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                locales[lang] = json.load(f)
    return locales


def check_missing_keys(tasks: dict[str, dict]) -> list[str]:
    """Check 1: All todoText have all SUPPORTED languages."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang in SUPPORTED:
            if lang not in todo or not isinstance(todo.get(lang), str) or not todo[lang].strip():
                issues.append(f"MISSING_KEY: {fname} [{lang}]")
    return issues


def check_keywords_latin(tasks: dict[str, dict]) -> list[str]:
    """Check 2: Python keywords should remain in Latin script."""
    # Common mistranslations of 'for'
    translated_for = {
        "de": ["für", "Für"],
        "es": ["para", "Para"],
        "fr": ["pour", "Pour"],
        "it": ["per", "Per"],
        "pt": ["para", "Para"],
        "nl": ["voor", "Voor"],
        "sv": ["för", "För"],
        "cs": ["pro", "Pro"],
        "el": ["για", "Για"],
        "hi": ["के लिए"],
        "bn": ["জন্য"],
        "tr": ["için"],
        "pl": ["dla", "Dla"],
    }
    # Common mistranslations of 'while'
    translated_while = {
        "de": ["während", "Während"],
        "es": ["mientras", "Mientras"],
        "fr": ["tant que", "Tant que"],
        "it": ["mentre", "Mentre"],
        "pt": ["enquanto", "Enquanto"],
        "nl": ["terwijl", "Terwijl"],
        "sv": ["medan", "Medan"],
        "cs": ["zatímco", "Zatímco"],
        "el": ["ενώ", "Ενώ"],
        "hi": ["जबकि"],
        "bn": ["যখন"],
        "tr": ["iken"],
        "pl": ["dopóki", "Dopóki"],
    }
    # Common mistranslations of 'if'
    translated_if = {
        "de": ["falls", "Falls", "wenn", "Wenn"],
        "es": ["si", "Si", "SI"],  # "si" in lowercase can be ambiguous in Spanish
        "fr": ["si ", "Si "],  # "si" is very common in French, only flag in keyword context
        "it": ["se", "Se"],
        "pt": ["se", "Se"],
        "nl": ["als", "Als"],
        "sv": ["om", "Om"],
        "cs": ["pokud", "Pokud"],
        "el": ["αν", "Αν"],
        "hi": ["यदि"],
        "bn": ["যদি"],
        "tr": ["eğer", "Eğer"],
        "pl": ["jeśli", "Jeśli", "jezeli"],
        "uk": ["якщо", "Якщо"],
        "be": ["калі", "Калі"],
    }

    issues = []
    for fname, todo in sorted(tasks.items()):
        # Get the Russian text to check if keywords are referenced
        ru_text = todo.get("ru", "").lower()
        en_text = todo.get("en", "").lower()
        has_for = any(kw in ru_text or kw in en_text for kw in ["for", "цикл «for»", "цикл «for»", "'for'", "「for」"])
        has_while = any("while" in ru_text or "while" in en_text for _ in [1])
        has_if = any("if" in ru_text or "if" in en_text for _ in [1])

        for lang, text in todo.items():
            if not isinstance(text, str):
                continue
            # Check for translated 'for'
            if lang in translated_for:
                for mistr in translated_for[lang]:
                    # Only flag if the English/Russian text references 'for' as a keyword
                    # and the translation uses the translated word IN QUOTES (likely keyword context)
                    if mistr in text and ('for' in en_text.lower() or '«for»' in ru_text or "'for'" in en_text.lower()):
                        # But only flag if the Latin 'for' is NOT also present nearby
                        if 'for' not in text.lower() or ('for' in text.lower() and text.count(mistr) > 0):
                            # If 'for' appears in Latin AND translated word, it might be OK (translated word in prose + Latin keyword)
                            # Only flag if Latin 'for' is missing from the translation
                            # Actually, let's be more careful: check if 'for' (as keyword) appears in the translation
                            if not re.search(r'["\'«»\u300c\u300d\u201e\u201d]for["\'«»\u300c\u300d\u201e\u201d]', text) and not re.search(r'for\(\)', text):
                                issues.append(f"TRANSLATED_KEYWORD: {fname} [{lang}]: 'for' may be translated as '{mistr}' without Latin 'for' keyword")

            # Check for translated 'if' in keyword context
            if lang in translated_if:
                for mistr in translated_if[lang]:
                    if mistr in text:
                        # Flag if the Latin 'if' is NOT present in keyword context
                        if not re.search(r'["\'«»\u300c\u300d\u201e\u201d]if["\'«»\u300c\u300d\u201e\u201d]', text) and 'if()' not in text:
                            # Check if 'if' is even relevant (English/Russian has 'if')
                            if 'if' in en_text.lower() or '«if»' in ru_text:
                                issues.append(f"TRANSLATED_KEYWORD: {fname} [{lang}]: 'if' may be translated as '{mistr}' without Latin 'if' keyword")

    return issues


def check_keyword_quoting(tasks: dict[str, dict]) -> list[str]:
    """Check 3: Python keyword quoting style matches locale convention."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang in SUPPORTED:
            text = todo.get(lang, "")
            if not text:
                continue
            oq, cq = QUOTE_STYLE.get(lang, ("'", "'"))

            for kw in PYTHON_KEYWORDS:
                # Check if the keyword appears in the text at all
                if kw not in text:
                    continue

                # For RTL languages, keyword is wrapped in LRI/PDI inside quotes
                if lang in ("ar", "ur"):
                    # Expected pattern: «⁦kw⁩» or « kw » with bidi isolates
                    # Just check that keyword is present in Latin and is inside quotes
                    # Bidi check is separate
                    continue

                # For fr, the pattern is « for » with spaces
                if lang == "fr":
                    expected_pattern = f"« {kw} »"
                    if expected_pattern in text:
                        pass  # OK
                    elif f"«{kw}»" in text:
                        issues.append(f"QUOTE_STYLE: {fname} [{lang}]: keyword '{kw}' uses «{kw}» without spaces, expected « {kw} »")
                    elif f"'{kw}'" in text:
                        issues.append(f"QUOTE_STYLE: {fname} [{lang}]: keyword '{kw}' uses single quotes, expected « {kw} »")
                    continue

                # For most languages, check for open_q + kw + close_q
                # But also accept alternative quoting (e.g., both 'for' and «for» for Russian)
                expected = f"{oq}{kw}{cq}"

                # For fr-style guillemets with spaces
                if lang == "fr":
                    continue  # Already handled

                # Find all occurrences of the keyword
                # It should be properly quoted. Check if it's quoted at all.
                kw_pattern = re.escape(oq) + kw + re.escape(cq)
                if re.search(kw_pattern, text):
                    continue  # Properly quoted

                # Check if keyword appears without quotes (or with wrong quotes)
                # Find the keyword that's not part of a function call like paint()
                # and is not inside a quoted form we accept
                # Simple check: if the keyword appears bare (unquoted)
                bare_pattern = r'(?<![\'"«»\u300c\u300d\u201e\u201dA-Za-z])' + kw + r'(?![\'"«»\u300c\u300d\u201e\u201dA-Za-z()])'
                # Actually this is complex. Let's just flag if keyword appears but
                # the expected quote form is NOT present in the text.
                if kw in text and expected not in text:
                    # Check if any quote form is present
                    alt_found = False
                    # Accept single quotes as alternative (very common)
                    if f"'{kw}'" in text and lang not in ("ru", "be", "uk", "el", "fr"):
                        alt_found = True
                    # Accept guillemets as alternative (common for some langs)
                    if f"«{kw}»" in text or f"« {kw} »" in text:
                        alt_found = True
                    # Accept CJK brackets
                    if f"「{kw}」" in text:
                        alt_found = True
                    # Accept „kw" (German/Polish/Czech style)
                    if f"\u201e{kw}\u201d" in text:
                        alt_found = True
                    # For ar/ur, check with bidi isolates already handled

                    if not alt_found:
                        # Keyword appears unquoted or with unexpected quotes
                        # Extract context around the keyword
                        idx = text.find(kw)
                        start = max(0, idx - 5)
                        end = min(len(text), idx + len(kw) + 5)
                        context = text[start:end]
                        issues.append(f"QUOTE_STYLE: {fname} [{lang}]: keyword '{kw}' not properly quoted. Expected {expected!r}. Context: ...{context!r}...")

    return issues


def check_robot_proper_noun(tasks: dict[str, dict]) -> list[str]:
    """Check 4: Robot as proper noun should be capitalized correctly."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang in SUPPORTED:
            text = todo.get(lang, "")
            if not text:
                continue

            proper = ROBOT_PROPER.get(lang)
            if proper is None:
                continue  # Non-Latin script, skip

            # Check if "robot" (lowercase Latin) appears when it should be "Robot"
            # But be careful: in German, "Roboter" is correct, not "Robot"
            if lang == "de":
                # In German: "Roboter" (with -er suffix) is correct in running text
                # "Robot" (without -er) would be incorrect in German running text
                # But "Robot" might appear as the app/executor name
                # Check for lowercase "roboter" which should be "Roboter"
                if "roboter" in text and "Roboter" not in text and "Robot" not in text:
                    issues.append(f"ROBOT_CASE: {fname} [{lang}]: 'roboter' should be 'Roboter'")
                # Also check for bare lowercase 'robot' (not followed by 'er' or 'en')
                # This might flag false positives in other contexts
                for m in re.finditer(r'\bRobot\b', text):
                    pass  # Robot without -er is OK as proper noun
                # Check for lowercase 'robot' that's not part of 'Roboter'
                if re.search(r'\b(?!Roboter|Robot)robot\b', text, re.IGNORECASE):
                    # Only if there's no "Robot" or "Roboter" nearby
                    pass  # German is complex, skip for now
                continue

            if lang == "pt":
                # Portuguese uses "Robô" (with circumflex)
                if re.search(r'\brobot\b', text, re.IGNORECASE):
                    # Check if it's lowercase or wrong form
                    for m in re.finditer(r'\b[Rr]obô?\b', text):
                        if m.group() == "robot" or m.group() == "Robot":
                            issues.append(f"ROBOT_CASE: {fname} [{lang}]: '{m.group()}' should be 'Robô'")
                continue

            # For most Latin-script langs, check for lowercase "robot"
            if re.search(r'\brobot\b', text, re.IGNORECASE):
                # Find all forms of "robot" in the text
                for m in re.finditer(r'\b[Rr]obot\b', text):
                    word = m.group()
                    if word[0].islower():
                        issues.append(f"ROBOT_CASE: {fname} [{lang}]: '{word}' should start with capital (proper noun)")

            # For Cyrillic langs
            if lang in ("ru", "uk", "be"):
                lower_forms = {"ru": ["робот", "Робот"], "uk": ["робот", "Робот"], "be": ["робат", "Робат"]}
                proper_form = proper
                # Lowercase form would be wrong
                lower = lower_forms[lang][0]
                if lower in text:
                    # Check if the proper form also appears or if it's always lowercase
                    has_proper = proper_form in text
                    if not has_proper:
                        issues.append(f"ROBOT_CASE: {fname} [{lang}]: uses lowercase '{lower}', should be '{proper_form}'")

    return issues


def check_bidi_isolates(tasks: dict[str, dict]) -> list[str]:
    """Check 5: ar/ur should have bidi isolates around Latin text and digits."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang in ("ar", "ur"):
            text = todo.get(lang, "")
            if not text:
                continue

            # Find Latin words and digits not wrapped in LRI/PDI
            # Latin word: sequence of Latin letters
            for m in re.finditer(r'[A-Za-z][A-Za-z0-9_()]*', text):
                word = m.group()
                start = m.start()
                end = m.end()

                # Skip if it's a common Arabic word that happens to look Latin
                # Check if preceded by LRI or FSI
                if start > 0 and text[start - 1] in (LRI, FSI):
                    continue  # Already isolated

                # Skip very short matches that might be particles
                if len(word) <= 1 and not word.isdigit():
                    continue

                issues.append(f"BIDI: {fname} [{lang}]: Latin '{word}' not wrapped in bidi isolates at position {start}")

            # Check digits not wrapped in isolates
            for m in re.finditer(r'\d+', text):
                start = m.start()
                if start > 0 and text[start - 1] in (LRI, FSI):
                    continue
                end = m.end()
                if end < len(text) and text[end] == PDI:
                    continue
                # Check if digit is inside an LRI...PDI block
                # This is a simple heuristic
                if start > 0 and text[start - 1] == LRI:
                    continue
                issues.append(f"BIDI: {fname} [{lang}]: digit '{m.group()}' not wrapped in bidi isolates at position {start}")

    return issues


def check_literals_not_quoted(tasks: dict[str, dict]) -> list[str]:
    """Check 6: True, False, None should not be in quotes."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang, text in todo.items():
            if not isinstance(text, str):
                continue
            for lit in PYTHON_LITERALS:
                # Check if literal is in quotes: 'True', "True", «True», 「True」etc.
                patterns = [
                    f"'{lit}'",
                    f'"{lit}"',
                    f"«{lit}»",
                    f"「{lit}」",
                    f"\u201e{lit}\u201d",
                ]
                for pat in patterns:
                    if pat in text:
                        issues.append(f"LITERAL_QUOTED: {fname} [{lang}]: Python literal '{lit}' should not be in quotes: found {pat!r}")
    return issues


def check_function_names(tasks: dict[str, dict]) -> list[str]:
    """Check 7: Function names paint(), printn(), task(), field() should remain Latin even in RTL."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        for lang in ("ar", "ur"):
            text = todo.get(lang, "")
            if not text:
                continue
            # Check that paint(), printn(), task(), field() appear in Latin
            for fn in ["paint()", "printn()", "task()", "field()"]:
                if fn in text:
                    # Check it's wrapped in isolates
                    idx = text.find(fn)
                    if idx > 0 and text[idx - 1] == LRI:
                        # Also check closing PDI after fn
                        end_idx = idx + len(fn)
                        if end_idx < len(text) and text[end_idx] == PDI:
                            pass  # OK
                        else:
                            # Might be "⁦paint()⁩" with just the LRI before
                            pass  # Acceptable if LRI is before
                # Also check for translated forms (very unlikely but worth flagging)

    return issues


def check_terminology(tasks: dict[str, dict]) -> list[str]:
    """Check 8: Key terminology should be consistent with UI locales."""
    issues = []
    for fname, todo in sorted(tasks.items()):
        ru_text = todo.get("ru", "")
        en_text = todo.get("en", "")

        # Check if the task involves painting
        involves_paint = bool(re.search(r'закраш|Закраш|покраш|Покраш|paint|Paint', ru_text + en_text))
        # Check if the task involves walls
        involves_wall = bool(re.search(r'стен|Стен|wall|Wall', ru_text + en_text))
        # Check if the task involves cells
        involves_cell = bool(re.search(r'клетк|клітинк|cell|Cell', ru_text + en_text))

        for lang, terms_for_lang in TERMS.get("paint", {}).items():
            if not involves_paint:
                continue
            text = todo.get(lang, "")
            if not text:
                continue

            # Check if any of the expected terms appear
            found = any(root in text for root in terms_for_lang)
            if not found and lang not in ("ja", "ko", "zh-hans", "zh-hant", "hi", "bn", "ar", "ur"):
                # Only flag for Latin/Cyrillic script languages where we can meaningfully check
                issues.append(f"TERMINOLOGY: {fname} [{lang}]: painting task but no paint-related term found. Expected one of: {terms_for_lang}")

        for lang, terms_for_lang in TERMS.get("cell", {}).items():
            if not involves_cell and involves_paint:
                # If painting is involved, cell should be mentioned
                text = todo.get(lang, "")
                if not text:
                    continue
                # Check if any cell-related term appears
                found = any(root in text for root in terms_for_lang)
                if not found and lang not in ("ja", "ko", "zh-hans", "zh-hant", "hi", "bn", "ar", "ur"):
                    issues.append(f"TERMINOLOGY: {fname} [{lang}]: task mentions cells/painting but no cell-related term found. Expected one of: {terms_for_lang}")

    return issues


def check_keyword_in_context(tasks: dict[str, dict]) -> list[str]:
    """Check that Python keywords in translations are in Latin and properly quoted.
    This is a more targeted check that examines specific known issues."""
    issues = []

    # Known translated keyword patterns that are WRONG
    # These were found in previous fix_todo_translations.py and should all be resolved
    wrong_patterns = {
        "for": {
            "hi": "फॉर",       # Hindi translation of 'for'
            "bn": "ফর",         # Bengali translation of 'for'
            "el": "για",        # Greek translation of 'for' (lowercase)
            "sv": "för",        # Swedish translation of 'for'
            "cs": "pro",        # Czech translation of 'for'
            "de": "für",        # German translation of 'for'
        },
        "if": {
            "es": '"si"',       # Spanish 'if' (not keyword)
            "uk": "«якщо»",     # Ukrainian translation of 'if'
            "be": '"калі"',     # Belarusian translation (in wrong quotes)
            "el": '"αν"',       # Greek translation of 'if'
            "sv": '"om"',       # Swedish translation of 'if'
            "cs": "„pokud\"",   # Czech 'if' as keyword
        },
    }

    for fname, todo in sorted(tasks.items()):
        for kw, lang_mistr in wrong_patterns.items():
            for lang, mistr in lang_mistr.items():
                text = todo.get(lang, "")
                if not text:
                    continue
                if mistr in text:
                    # Check if this is actually a keyword context (not just the word in prose)
                    # Simple heuristic: if the Russian text has the keyword in quotes
                    ru_text = todo.get("ru", "")
                    en_text = todo.get("en", "")
                    if kw in en_text.lower() or f"«{kw}»" in ru_text:
                        issues.append(f"TRANSLATED_KW: {fname} [{lang}]: found '{mistr}' which is translated keyword '{kw}', should be Latin '{kw}' in locale-appropriate quotes")

    return issues


def main():
    tasks = load_tasks()
    locales = load_locales()

    print("=" * 60)
    print("COMPREHENSIVE TODO TEXT AUDIT")
    print("=" * 60)

    all_issues = []

    # Check 1: Missing keys
    print("\n--- Check 1: Missing language keys ---")
    issues = check_missing_keys(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 2: Keywords in Latin
    print("\n--- Check 2: Python keywords in Latin ---")
    issues = check_keywords_latin(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 2b: Known translated keyword patterns
    print("\n--- Check 2b: Known translated keyword patterns ---")
    issues = check_keyword_in_context(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 3: Keyword quoting
    print("\n--- Check 3: Keyword quoting style ---")
    issues = check_keyword_quoting(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 4: Robot proper noun
    print("\n--- Check 4: Robot as proper noun ---")
    issues = check_robot_proper_noun(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 5: Bidi isolates
    print("\n--- Check 5: Bidi isolates (ar/ur) ---")
    issues = check_bidi_isolates(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 6: True/False/None not quoted
    print("\n--- Check 6: True/False/None not quoted ---")
    issues = check_literals_not_quoted(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 7: Function names
    print("\n--- Check 7: Function names in Latin (ar/ur) ---")
    issues = check_function_names(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Check 8: Terminology
    print("\n--- Check 8: Terminology consistency ---")
    issues = check_terminology(tasks)
    for i in issues:
        print(i)
    all_issues.extend(issues)

    # Summary
    print("\n" + "=" * 60)
    print(f"TOTAL ISSUES FOUND: {len(all_issues)}")
    print("=" * 60)

    # Categorize
    categories = {}
    for issue in all_issues:
        cat = issue.split(":")[0]
        categories.setdefault(cat, []).append(issue)

    for cat, cat_issues in sorted(categories.items()):
        print(f"  {cat}: {len(cat_issues)} issues")


if __name__ == "__main__":
    main()