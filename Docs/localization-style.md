# Localization Style Guide

This document describes conventions for user-visible strings in locale JSON files under `robot/locales/` (and for other localized copy that follows the same rules).

## Python keywords in prose

When a message mentions Python **language keywords** (for example `for`, `while`, `def`, `if`, `else`, `return`, `import`, `class`, …), wrap those words in **quotation marks appropriate to the target language and locale typography**, not necessarily ASCII straight quotes.

Examples:

- English: e.g. `Use a 'while' loop` using the quotation style normal for instructional English in your region.
- Russian: e.g. Используйте цикл «while» using «ёлочки» (or another established local style) around the keyword.

The important rule: **keywords are quoted** so they read as words of the programming language, not as ordinary prose.

## `True`, `False`, and `None`

The literals **`True`**, **`False`**, and **`None`** are **not** treated like generic keywords for this purpose: **do not** put them in quotation marks in localized strings unless you have a rare case where quotes are required for another reason (e.g. nested dialogue). In normal UI and error text, write them as bare identifiers, consistent with Python spelling and casing.

## Proper name: Robot

**Robot** (the application / executor name) is a **proper noun**. In each locale, spell and capitalize it according to **that language’s rules for proper names** and product naming.

- In Russian, use **Робот** with an initial capital letter when it denotes the named environment (e.g. status line, window title), matching strings such as `Робот: Готов` in `robot/locales/ru.json`.
- In English, **Robot** is typically capitalized when it refers to the app or the executor as a named entity; adjust if editorial guidelines differ.

Do not lowercase the name in running text when it refers to the product or the in-world executor, unless a locale explicitly uses a different convention for product names.

## Consistency

When adding or editing keys:

1. Keep terminology for the executor, grid, and tasks aligned with existing keys in the same locale file.
2. Prefer the same quoting style as other strings in that file for Python keywords.
3. Re-read the string at the minimum window width if it appears in the status strip; see `AGENTS.md` for the character limit there.
