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

## Unicode bidirectional isolation (RTL locales)

Locales written **right-to-left** (for example **Arabic**, **Hebrew**, **Urdu**) must wrap embedded **left-to-right** fragments in **Unicode bidirectional isolates** so the UI shows numbers, Latin identifiers, file paths, brackets, and mixed `{placeholders}` in the correct order. Without isolates, the Unicode Bidirectional Algorithm can reorder punctuation and digits relative to the surrounding script in confusing ways.

Use the **isolate** characters from [Unicode Standard Annex #9](https://www.unicode.org/reports/tr9/) (Bidi Algorithm), not the older embedding controls (U+202A–U+202E) for new strings:

| Role | Code point | Name (abbrev.) | Typical use |
|------|------------|----------------|-------------|
| Start LTR isolate | U+2066 | LRI | Wrap Latin text, digits, `v{version}`, `(row, col)`, `[Enter]`, `JSON`, `envDtos`, `printn()`, `task()`, etc. |
| Start first-strong isolate | U+2068 | FSI | Wrap segments where direction should follow the **first strong** character (e.g. a `{message}` or path that may start with Latin or digits). |
| End isolate | U+2069 | PDI | **Always** close every LRI or FSI with a matching PDI. |

**Rules of thumb:**

1. Isolate any **interpolation** or **technical snippet** that is not pure RTL prose: `{lineno}`, `{task_path}`, `{code}`, English error fragments, version strings, and keyboard hints.
2. Prefer **LRI … PDI** when the isolated content is **known to be LTR** (identifiers, numbers, paths, markup-like tokens).
3. Use **FSI … PDI** when the isolated unit’s direction should follow its **first strong** character (mixed or unknown content inside placeholders).
4. Keep pairs **balanced**; do not leave an isolate open across unrelated phrasing.

Reference implementation for Arabic lives in `robot/locales/ar.json` (and similarly for other RTL locale files): copy the same isolate placement when adding keys or editing strings.

## Status strip length

Strings shown in the Robot window **status strip** must not exceed **50 characters**, so they remain visible when the window is at its minimum size.

## Consistency

When adding or editing keys:

1. Keep terminology for the executor, grid, and tasks aligned with existing keys in the same locale file.
2. Prefer the same quoting style as other strings in that file for Python keywords.
3. Re-read the string at the minimum window width if it appears in the status strip; see [Status strip length](#status-strip-length) above.
4. For RTL locales, follow [Unicode bidirectional isolation (RTL locales)](#unicode-bidirectional-isolation-rtl-locales) and match isolate usage in that locale file.
