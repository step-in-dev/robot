#!/usr/bin/env python3
"""Fix confirmed issues in todoText translations across .env files.

Fixes applied:
1. Bengali transliterated keyword 'ফর' → 'for' (proper Latin keyword)
2. Robot capitalization: lowercase 'robot'/'робот'/'робат' → 'Robot'/'Робот'/'Робат'
3. English quoting: "for" → 'for', "if" → 'if', "while" → 'while'
4. Japanese: unquoted 'for' → 「for」
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parents[1] / "robot" / "tasks"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fix_bn_transliterated_keywords(data: dict) -> bool:
    """Fix Bengali transliterated 'for' keyword."""
    todo = data.get("todoText", {})
    if not isinstance(todo, dict):
        return False
    bn = todo.get("bn", "")
    if not bn:
        return False
    changed = False
    if '"ফর"' in bn:
        todo["bn"] = bn.replace('"ফর"', "'for'")
        changed = True
    return changed


def fix_robot_case(data: dict) -> bool:
    """Fix Robot proper noun capitalization."""
    import re
    todo = data.get("todoText", {})
    if not isinstance(todo, dict):
        return False
    changed = False

    # French: robot → Robot
    fr = todo.get("fr", "")
    if fr and re.search(r'\brobot\b', fr):
        todo["fr"] = re.sub(r'\brobot\b', 'Robot', fr)
        changed = True

    # Italian: robot → Robot
    it = todo.get("it", "")
    if it and re.search(r'\brobot\b', it):
        todo["it"] = re.sub(r'\brobot\b', 'Robot', it)
        changed = True

    # Dutch: robot → Robot
    nl = todo.get("nl", "")
    if nl and re.search(r'\brobot\b', nl):
        todo["nl"] = re.sub(r'\brobot\b', 'Robot', nl)
        changed = True

    # Romanian: robot → Robot (in context like "sub robot" → "sub Robot")
    ro = todo.get("ro", "")
    if ro and re.search(r'\brobot\b', ro):
        todo["ro"] = re.sub(r'\brobot\b', 'Robot', ro)
        changed = True

    # Hungarian: robot → Robot
    hu = todo.get("hu", "")
    if hu and re.search(r'\brobot\b', hu):
        todo["hu"] = re.sub(r'\brobot\b', 'Robot', hu)
        changed = True

    # Ukrainian: робот → Робот (but not if Робот already present)
    uk = todo.get("uk", "")
    if uk:
        new_uk = uk
        # Replace lowercase робот/робота/роботом/роботу with capitalized
        # But only if the text doesn't already have the capital form (to avoid double-replacing)
        new_uk = re.sub(r'\bробота\b', 'Робота', new_uk)
        new_uk = re.sub(r'\bроботом\b', 'Роботом', new_uk)
        new_uk = re.sub(r'\bроботу\b', 'Роботу', new_uk)
        new_uk = re.sub(r'\bроботі\b', 'Роботі', new_uk)
        new_uk = re.sub(r'\bробот\b(?!а|ом|у|і)', 'Робот', new_uk)
        if new_uk != uk:
            todo["uk"] = new_uk
            changed = True

    # Belarusian: робат → Робат (various case forms)
    be = todo.get("be", "")
    if be:
        new_be = be
        new_be = re.sub(r'\bробата\b', 'Робата', new_be)
        new_be = re.sub(r'\bробатам\b', 'Робатам', new_be)
        new_be = re.sub(r'\bробату\b', 'Робату', new_be)
        new_be = re.sub(r'\bробате\b', 'Робате', new_be)
        new_be = re.sub(r'\bробат\b(?!а|ам|у|е)', 'Робат', new_be)
        if new_be != be:
            todo["be"] = new_be
            changed = True

    # German: lowercase 'roboter' in running text should be 'Roboter'
    de = todo.get("de", "")
    if de:
        new_de = de
        new_de = re.sub(r'\broboter\b', 'Roboter', new_de, flags=re.IGNORECASE)
        # But don't replace "Roboter" which is already correct
        if new_de != de:
            todo["de"] = new_de
            changed = True

    # Greek: ρομπότ → Ρομπότ
    el = todo.get("el", "")
    if el:
        new_el = el
        new_el = re.sub(r'\bρομπότ\b', 'Ρομπότ', new_el)
        if new_el != el:
            todo["el"] = new_el
            changed = True

    # Czech: robota → Robota, robot → Robot
    cs = todo.get("cs", "")
    if cs:
        new_cs = cs
        new_cs = re.sub(r'\brobota\b', 'Robota', new_cs)
        new_cs = re.sub(r'\brobot\b', 'Robot', new_cs)
        if new_cs != cs:
            todo["cs"] = cs
            changed = True

    # Swedish: roboten → Roboten (definite), robot → Robot
    sv = todo.get("sv", "")
    if sv:
        new_sv = sv
        new_sv = re.sub(r'\broboten\b', 'Roboten', new_sv)
        new_sv = re.sub(r'\brobot\b', 'Robot', new_sv)
        if new_sv != sv:
            todo["sv"] = sv
            changed = True

    return changed


def fix_en_quoting(data: dict) -> bool:
    """Fix English keyword quoting: \"for\" → 'for', \"if\" → 'if', \"while\" → 'while'."""
    todo = data.get("todoText", {})
    if not isinstance(todo, dict):
        return False
    en = todo.get("en", "")
    if not en:
        return False
    changed = False
    new_en = en
    # Replace \"for\" with 'for' (but not already 'for')
    # Also handle "for" when it appears as a keyword reference
    import re
    # Replace "keyword" pattern: 'the "for" loop' → 'the 'for' loop'
    # We need to be careful not to replace "for" when it's part of a larger word
    for kw in ['for', 'while', 'if', 'else']:
        # Pattern: "keyword" (with straight double quotes)
        pattern = f'"{kw}"'
        replacement = f"'{kw}'"
        if pattern in new_en and replacement not in new_en:
            new_en = new_en.replace(pattern, replacement)
            changed = True
    if changed:
        todo["en"] = new_en
    return changed


def fix_ja_quoting(data: dict) -> bool:
    """Fix Japanese keyword quoting: unquoted for → 「for」."""
    import re
    todo = data.get("todoText", {})
    if not isinstance(todo, dict):
        return False
    ja = todo.get("ja", "")
    if not ja:
        return False
    changed = False
    new_ja = ja
    # Fix: forループ → 「for」ループ etc.
    # But don't double-quote if already in 「for」
    for kw in ['for', 'while', 'if', 'else']:
        # Pattern: keyword immediately before katakana/hiragana (no brackets)
        pattern = f'(?<!「)({kw})(?!」)(?=ループ|文|式|内)'
        if re.search(pattern, new_ja):
            new_ja = re.sub(pattern, f'「{kw}」', new_ja)
            changed = True
    if changed:
        todo["ja"] = new_ja
    return changed


def main() -> int:
    updated = 0
    for path in sorted(TASKS_DIR.glob("*.env")):
        data = load(path)
        todo = data.get("todoText", {})
        if not isinstance(todo, dict):
            continue

        changed = False
        changed |= fix_bn_transliterated_keywords(data)
        changed |= fix_robot_case(data)
        changed |= fix_en_quoting(data)
        changed |= fix_ja_quoting(data)

        if changed:
            save(path, data)
            updated += 1
            print(path.name)

    print(f"\nTotal files updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())