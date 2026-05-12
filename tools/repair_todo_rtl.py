#!/usr/bin/env python3
"""Offline repair for ar/ur todoText: flatten nested bidi around keywords, fix known MT glitches."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_LRI = "\u2066"
_PDI = "\u2069"

# ⁦"⁦for⁩"⁩  ->  ⁦"for"⁩  (and while/if/else/def)
_NESTED_QUOTED_KW = re.compile(
    re.escape(_LRI)
    + r'"'
    + re.escape(_LRI)
    + r"(for|while|if|else|def)"
    + re.escape(_PDI)
    + r'"'
    + re.escape(_PDI)
)


def repair_rtl_todo_string(s: str) -> str:
    s = _NESTED_QUOTED_KW.sub(lambda m: f'{_LRI}"{m.group(1)}"{_PDI}', s)
    # Optional: "⁦paint()⁩" -> ⁦paint()⁩ (drop redundant ASCII quotes around isolated call)
    s = s.replace(f'"{_LRI}paint(){_PDI}"', f"{_LRI}paint(){_PDI}")
    s = s.replace(f'"{_LRI}printn(){_PDI}"', f"{_LRI}printn(){_PDI}")
    return s


def fix_ar_for_loop_mistranslation(s: str) -> str:
    """Google sometimes renders English 'for' as Arabic 'من أجل' inside quotes."""
    return s.replace('"من أجل"', f'{_LRI}"for"{_PDI}')


def fix_wif9_if_keywords(ar: str, ur: str) -> tuple[str, str]:
    """Preserve ASCII ``if`` in quotes for wif9 (MT often uses Arabic/Urdu glosses)."""
    ar = ar.replace('"إذا"', f'{_LRI}"if"{_PDI}')
    ur = ur.replace('"اگر"', f'{_LRI}"if"{_PDI}')
    return ar, ur


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tasks_dir = root / "robot" / "tasks"
    n = 0
    for path in sorted(tasks_dir.glob("*.env")):
        data = json.loads(path.read_text(encoding="utf-8"))
        todo = data.get("todoText")
        if not isinstance(todo, dict):
            continue
        changed = False
        for key in ("ar", "ur"):
            if key not in todo or not isinstance(todo[key], str):
                continue
            old = todo[key]
            new = repair_rtl_todo_string(old)
            if key == "ar":
                new = fix_ar_for_loop_mistranslation(new)
            if new != old:
                todo[key] = new
                changed = True
        if "ar" in todo and "ur" in todo and isinstance(todo["ar"], str) and isinstance(todo["ur"], str):
            ar2, ur2 = fix_wif9_if_keywords(todo["ar"], todo["ur"])
            if ar2 != todo["ar"] or ur2 != todo["ur"]:
                todo["ar"] = ar2
                todo["ur"] = ur2
                changed = True
        if changed:
            data["todoText"] = todo
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            n += 1
            print(path.name, flush=True)
    print(f"Repaired {n} files.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
