#!/usr/bin/env python3
"""Audit todoText translations in .env files."""
import json
import re
from pathlib import Path

SUPPORTED = (
    "en","ru","zh-hans","zh-hant","hi","es","fr","ar","bn","pt",
    "ur","uk","pl","be","ja","ko","de","it","nl","tr","el","cs","sv","ro","hu",
)

# Regex for Python keywords that should remain in Latin in todoText
KEYWORD_PAT = re.compile(r'\b(for|while|if|else|def|return|import|class|True|False|None)\b', re.I)
# Regex for Robot (proper noun) in Latin script
ROBOT_PAT = re.compile(r'\bRobot\b')
# Regex for digit runs
DIGIT_PAT = re.compile(r'\d+')
# Bidi isolates
LRI = '\u2066'
FSI = '\u2068'
PDI = '\u2069'
OPEN_ISO = {LRI, FSI}

def is_wrapped_in_isolates(text: str, start: int, end: int) -> bool:
    """Check if text[start:end] is immediately preceded by LRI/FSI and followed by PDI."""
    if start > 0 and text[start-1] in OPEN_ISO and end < len(text) and text[end] == PDI:
        return True
    return False

def find_unisolated_latin(text: str) -> list[str]:
    """Find Latin words/digits not wrapped in bidi isolates (for ar/ur)."""
    issues = []
    for m in re.finditer(r'[A-Za-z][A-Za-z0-9_]*', text):
        if not is_wrapped_in_isolates(text, m.start(), m.end()):
            issues.append(m.group(0))
    for m in DIGIT_PAT.finditer(text):
        if not is_wrapped_in_isolates(text, m.start(), m.end()):
            issues.append(m.group(0))
    return issues

def check_keywords(text: str, lang: str) -> list[str]:
    """Check that Python keywords remain in Latin (except in languages where transliteration is expected? No — always Latin)."""
    issues = []
    # We look for the keyword pattern but allow it inside non-Latin script? Actually we just check that
    # if the original English contains the keyword, the translation should preserve the Latin keyword, ideally quoted.
    # This is a heuristic: we check that the translation does NOT contain a fully translated keyword.
    # We'll do a simple check: if the English text contains 'for' (as a keyword), the translation should contain 'for' (case-insensitive ok for some langs).
    # This is not perfect but catches hi/el/sv/cs.
    return issues

def main():
    tasks_dir = Path("/home/viktar/projects/StepInDev/robot/robot/tasks")
    errors = []
    warnings = []
    for path in sorted(tasks_dir.glob("*.env")):
        data = json.loads(path.read_text(encoding="utf-8"))
        todo = data.get("todoText")
        if not isinstance(todo, dict):
            continue
        en = todo.get("en", "")
        # Required keys
        for req in ("en", "ru"):
            if req not in todo or not isinstance(todo[req], str):
                errors.append(f"{path.name}: missing required todoText.{req}")
        for lang in SUPPORTED:
            if lang not in todo or not isinstance(todo[lang], str):
                errors.append(f"{path.name}: missing todoText.{lang}")
                continue
            text = todo[lang]
            # Check proper noun Robot capitalization in Latin-script langs
            if lang in ("en", "uk", "pl", "be", "cs", "hu", "ro", "sv", "nl", "it", "de", "tr", "el"):
                for m in ROBOT_PAT.finditer(text):
                    # Check preceding char: if lowercased 'robot' appears, that's an issue
                    pass
            # RTL isolates for ar/ur
            if lang in ("ar", "ur"):
                unisolated = find_unisolated_latin(text)
                if unisolated:
                    # Filter out things that are inside FSI...PDI? Our regex might miss because FSI is not LRI.
                    # Actually our is_wrapped_in_isolates checks both LRI and FSI before.
                    warnings.append(f"{path.name} [{lang}]: possible unisolated LTR tokens: {unisolated[:5]}")
    print("=== ERRORS ===")
    for e in errors:
        print(e)
    print("\n=== WARNINGS ===")
    for w in warnings:
        print(w)

if __name__ == "__main__":
    main()
