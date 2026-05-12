#!/usr/bin/env python3
"""Fix terminology inconsistencies between todoText and UI locales.

Issues fixed:
1. NL: 'schilderen' → 'verven' forms (paint command = Verf)
2. RO: 'picta' → 'vopsi' forms (paint command = Vopsește)
3. EL: 'ζωγραφίζω' → 'βαφω' forms (paint command = Βάφει)
4. CS: 'malování'/'malovat' → 'vybarvení'/'vybarvit' forms (paint command = Vybarví)

Also fixes specific cases where 'cell' terminology differs from UI locales.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parents[1] / "robot" / "tasks"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


REPLACEMENTS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "forfun3.env": {
        "nl": [("te schilderen", "te verven")],
        "ro": [("pentru a picta un pătrat", "pentru a vopsi un pătrat")],
        "el": [("να ζωγραφίσετε ένα τετράγωνο", "να βάψετε ένα τετράγωνο"),
               ("ζωγραφίσετε", "βάψετε")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
    },
    "forfun4.env": {
        "nl": [("te schilderen", "te verven")],
        "ro": [("pentru a picta un pătrat", "pentru a vopsi un pătrat")],
        "el": [("να ζωγραφίσετε ένα τετράγωνο", "να βάψετε ένα τετράγωνο"),
               ("ζωγραφίσετε", "βάψετε")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
    },
    "forfun5.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
        "ro": [("pentru a picta un pătrat", "pentru a vopsi un pătrat")],
    },
    "forfun6.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
    },
    "forfun7.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
    },
    "forfun8.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
    },
    "forfun9.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování čtverce", "pro vybarvení čtverce")],
        "el": [("να ζωγραφίσετε ένα τετράγωνο", "να βάψετε ένα τετράγωνo")],
    },
    "fun4.env": {
        "nl": [("een rechthoek te tekenen", "een rechthoek te verven")],
        "ro": [("pentru a picta un dreptunghi", "pentru a vopsi un dreptunghi")],
        "cs": [("pro malování obdélníku", "pro vybarvení obdélníku")],
    },
    "fun5.env": {
        "nl": [("4 cellen te schilderen", "4 cellen te verven")],
        "ro": [("pentru a picta 4 celule", "pentru a vopsi 4 celule")],
        "el": [("να ζωγραφίσετε 4 κελιά", "να βάψετε 4 κελιά")],
        "cs": [("pro malování 4 buněk", "pro vybarvení 4 buněk")],
    },
    "if5.env": {
        "el": [("ζωγραφισμένο", "βαμμένο")],
    },
    "if6.env": {
        "hu": [("Fesd be a jobb oldali cellát", "Fesd be a jobb oldali cellát")],
    },
    "if10.env": {
        "el": [("ζωγραφισμένα", "βαμμένα")],
        "hu": [("Fesd be a Robot alatti sor celláit", "Fesd be a Robot alatti sor celláit")],
    },
    "wfun7.env": {
        "nl": [("te schilderen", "te verven")],
        "cs": [("pro malování vertikálního koridoru", "pro vybarvení svislého koridoru")],
        "ro": [("pentru a picta un coridor vertical", "pentru a vopsi un coridor vertical")],
    },
    "wif1.env": {
        "el": [("ζωγραφίσετε", "βάψετε")],
        "hu": [("festeni", "befesteni")],
    },
    "wif12.env": {
        "el": [("ζωγραφισμένα", "βαμμένα")],
        "cs": [("vybarvené", "vybarvené")],
    },
}


def main() -> int:
    updated = 0
    for fname, langs in REPLACEMENTS.items():
        path = TASKS_DIR / fname
        if not path.exists():
            print(f"SKIP: {fname} not found")
            continue
        data = load(path)
        todo = data.get("todoText", {})
        if not isinstance(todo, dict):
            continue
        changed = False
        for lang, replacements in langs.items():
            text = todo.get(lang, "")
            if not text:
                continue
            for old, new in replacements:
                if old in text:
                    todo[lang] = text.replace(old, new)
                    text = todo[lang]
                    changed = True
                else:
                    pass  # Already fixed or different text
        if changed:
            data["todoText"] = todo
            save(path, data)
            updated += 1
            print(f"UPDATED: {fname}")
    print(f"\nTotal files updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())