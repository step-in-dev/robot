# Localization Style Guide

This document describes conventions for user-visible strings in locale JSON files under `robot/locales/` (and for other localized copy that follows the same rules).

## Python keywords in prose

When a message mentions Python **language keywords** (for example `for`, `while`, `def`, `if`, `else`, `return`, `import`, `class`, …), wrap those words in **quotation marks appropriate to the target language and locale typography**, not necessarily ASCII straight quotes.

Examples:

- English: e.g. `Use a 'while' loop` using the quotation style normal for instructional English in your region.
- Russian: e.g. Используйте цикл «while» using «ёлочки» (or another established local style) around the keyword.

The important rule: **keywords are quoted** so they read as words of the programming language, not as ordinary prose.

For a **locale-by-locale cheat sheet** (opening and closing characters, code points), see [Quotation marks by locale](#quotation-marks-by-locale) below.

## Quotation marks by locale

The table below is the **canonical pair** (opening, closing) used around **Python keywords** in existing strings (see keys such as `limit.if_keyword`, `limit.while_keyword`, and `help.task_group.*` in each `robot/locales/<locale>.json`). Use the same style for new or edited keyword mentions in that locale, and use it for **other quoted snippets** (technical tokens, product name in running prose, etc.) unless a locale already follows a different established pattern for nested quotes.

| Locale | Language (short) | Opening | Closing | Unicode (opening / closing) | Notes |
|--------|-------------------|---------|---------|-------------------------------|--------|
| `ar` | Arabic | « | » | U+00AB / U+00BB | Wrap embedded LTR in bidi isolates per [RTL section](#unicode-bidirectional-isolation-rtl-locales). |
| `be` | Belarusian | « | » | U+00AB / U+00BB | |
| `bn` | Bengali | ' | ' | U+0027 / U+0027 | ASCII apostrophe, same glyph both sides. |
| `cs` | Czech | „ | “ | U+201E / U+201C | |
| `de` | German | ' | ' | U+0027 / U+0027 | |
| `el` | Greek | « | » | U+00AB / U+00BB | |
| `en` | English | ' | ' | U+0027 / U+0027 | |
| `es` | Spanish | ' | ' | U+0027 / U+0027 | |
| `fr` | French | « | » | U+00AB / U+00BB | Often a space inside the guillemets, e.g. `« if »`. |
| `hi` | Hindi | ' | ' | U+0027 / U+0027 | |
| `hu` | Hungarian | „ | ” | U+201E / U+201D | |
| `it` | Italian | ' | ' | U+0027 / U+0027 | |
| `ja` | Japanese | 「 | 」 | U+300C / U+300D | |
| `ko` | Korean | ' | ' | U+0027 / U+0027 | |
| `nl` | Dutch | ' | ' | U+0027 / U+0027 | |
| `pl` | Polish | „ | ” | U+201E / U+201D | |
| `pt` | Portuguese | ' | ' | U+0027 / U+0027 | |
| `ro` | Romanian | „ | ” | U+201E / U+201D | |
| `ru` | Russian | « | » | U+00AB / U+00BB | |
| `sv` | Swedish | ' | ' | U+0027 / U+0027 | |
| `tr` | Turkish | “ | ” | U+201C / U+201D | |
| `uk` | Ukrainian | « | » | U+00AB / U+00BB | |
| `ur` | Urdu | « | » | U+00AB / U+00BB | Same bidi rules as Arabic. |
| `zh-hans` | Chinese (Simplified) | 「 | 」 | U+300C / U+300D | Some keys use “ ” (U+201C / U+201D) around placeholders; keep consistency within each string. |
| `zh-hant` | Chinese (Traditional) | 「 | 」 | U+300C / U+300D | |

When adding a **new locale file**, pick the pair that matches standard typography for that language; align keyword quoting with this table once the file exists so the reference stays accurate.

## `True`, `False`, and `None`

The literals **`True`**, **`False`**, and **`None`** are **not** treated like generic keywords for this purpose: **do not** put them in quotation marks in localized strings unless you have a rare case where quotes are required for another reason (e.g. nested dialogue). In normal UI and error text, write them as bare identifiers, consistent with Python spelling and casing.

## Proper name: Robot

**Robot** (the application / simulator name) is a **proper noun**. In each locale, spell and capitalize it according to **that language’s rules for proper names** and product naming.

- In Russian, use **Робот** with an initial capital letter when it names the application or исполнитель (e.g. status line, window title), matching strings such as `Робот: Готов` in `robot/locales/ru.json`.
- In English, **Robot** is typically capitalized when it refers to the app or the simulator as a named entity; adjust if editorial guidelines differ.

Do not lowercase the name in running text when it refers to the product or the on-grid robot in the simulator, unless a locale explicitly uses a different convention for product names.

## Dashes

Use the **en dash** (–, U+2013), not the **em dash** (—, U+2014), in localized UI strings, task conditions (`todoText`), marketing copy on the Robot website, and other prose that follows this guide.

- For **parenthetical asides** or a **break in a sentence**, use a spaced en dash: e.g. `The Robot window – buttons and help – is translated`.
- For **ranges** or **title-style separators** (e.g. `Robot – simulator`), use the same en dash; spacing follows normal typography for that language.

When editing existing text, replace em dashes with en dashes rather than introducing a mix.

## Domain terms (consistent within each locale)

These English labels name core simulator concepts. **Within a single locale file**, pick one established wording per concept (translation, compound, or loanword) and **reuse it everywhere** the same idea appears – status line, errors, help, buttons – so the UI reads as one coherent vocabulary.

Canonical terms (align all strings in that locale with your chosen equivalent for each):

- **Robot** – the named application; capitalization follows [Proper name: Robot](#proper-name-robot).
- **simulator** – the educational programming tool in general (the classic school “Robot” simulator), not a generic runtime “executor” in CS jargon or an unrelated game/simulation product. In Russian, use **исполнитель** consistently (e.g. учебный исполнитель); in English, use **simulator** (e.g. Robot simulator). When both the concept and the proper name appear together, follow established phrasing in that locale (e.g. исполнитель «Робот», educational Robot simulator).
- **environment** – a loaded task world (grid, robot placement, goals), not “the natural world” or generic “setting”.
- **cell** – one square of the grid (not a spreadsheet cell, biological cell, etc., unless context forces disambiguation in that locale).
- **field** – the grid as a whole or the `field()` synthetic playground, consistent with other keys about size and drawing.
- **wall** – an impassable edge between cells or at the boundary.
- **painted cell** – a cell the student’s program has painted (filled), as opposed to an empty or merely valued cell.
- **marked cell** – a cell the task requires to be painted (`cellsToPaint`), usually shown with a task marker in the UI until it is painted; distinct from a **painted cell**.

When adding a new key, grep the locale file for existing mentions of the same idea and match that wording instead of introducing a synonym.

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

1. Keep terminology for the simulator, grid, and tasks aligned with existing keys in the same locale file; see [Domain terms (consistent within each locale)](#domain-terms-consistent-within-each-locale).
2. Prefer the same quoting style as other strings in that file for Python keywords, or the pair listed for that locale in [Quotation marks by locale](#quotation-marks-by-locale).
3. Use en dashes, not em dashes; see [Dashes](#dashes).
4. Re-read the string at the minimum window width if it appears in the status strip; see [Status strip length](#status-strip-length) above.
5. For RTL locales, follow [Unicode bidirectional isolation (RTL locales)](#unicode-bidirectional-isolation-rtl-locales) and match isolate usage in that locale file.
