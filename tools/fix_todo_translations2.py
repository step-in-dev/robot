#!/usr/bin/env python3
"""Apply remaining fixes to todoText translations in .env files."""
import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parents[1] / "robot" / "tasks"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

REPLACEMENTS = {
    "forfun3.env": {
        "cs": ('„pro“', '„for"'),
    },
    "forfun4.env": {
        "cs": ('„pro“', '„for"'),
    },
    "forfun8.env": {
        "cs": ('„pro“', '„for"'),
    },
    "forfun9.env": {
        "cs": ('„pro“', '„for"'),
    },
}

def main():
    updated = 0
    for fname, langs in REPLACEMENTS.items():
        path = TASKS_DIR / fname
        if not path.exists():
            print(f"SKIP: {fname} not found")
            continue
        data = load(path)
        todo = data.get("todoText", {})
        changed = False
        for lang, (old, new) in langs.items():
            text = todo.get(lang, "")
            if old in text:
                todo[lang] = text.replace(old, new)
                changed = True
            else:
                print(f"WARN: {fname} [{lang}] substring not found: {old!r}")
        if changed:
            data["todoText"] = todo
            save(path, data)
            updated += 1
            print(f"UPDATED: {fname}")
    print(f"\nTotal files updated: {updated}")

if __name__ == "__main__":
    main()
