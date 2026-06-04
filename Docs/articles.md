# Robot Articles (`articles/`)

Long-form articles about the Robot simulator for teachers and learners. Markdown sources in this directory are intended for automatic conversion to HTML when the static site is published.

## Directory layout

Each article topic lives in its own subdirectory under [`articles/`](../articles/). The **folder name** is the stable `article_id` (language-neutral, kebab-case). It is not necessarily the same as any URL slug.

Example:

```
articles/
  robot-simulator-intro/
    meta.yaml
    en.md
    ru.md
```

- **`meta.yaml`** — shared metadata, list order, and per-locale URL slugs.
- **`en.md`**, **`ru.md`** — locale body and locale-specific SEO fields in YAML front matter.

There are no topic categories or `series` fields. Articles appear in one flat list ordered by `order` in `meta.yaml`.

## `meta.yaml`

Required fields:

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `order` | integer | Position in the site article index (must be unique across article folders) |
| `date` | string | Publication date, `YYYY-MM-DD` |
| `author` | string | Author name |
| `slug` | object | Map of locale code → URL slug, e.g. `en` and `ru` |

Example:

```yaml
order: 1
date: 2026-06-03
author: StepInDev
slug:
  en: what-is-the-robot-executor
  ru: chto-takoe-ispolnitel-robot
```

Rules:

- **`order`** values must be unique among all article folders.
- **`slug`** values must be unique among all published locales (no two articles may share the same slug for the same language).
- Every key under `slug` must have a matching locale file (`en` → `en.md`, `ru` → `ru.md`). Do not list a slug without a file, or ship a locale file without a `slug` entry.

Optional (for a future site builder; not used yet):

- `draft: true` — exclude the article from the published index and sitemap.

## Locale files (`en.md`, `ru.md`)

Each locale file starts with YAML front matter, then Markdown body.

Required front matter:

| Field | Purpose |
| ----- | ------- |
| `title` | Page title and main heading text |
| `description` | Short summary for SEO and social previews |
| `keywords` | List of search keywords |

Do **not** put `slug`, `lang`, `date`, or `author` in locale front matter; those come from `meta.yaml` (and the filename implies the locale).

Example:

```yaml
---
title: "Robot: what it is, commands, and how to use in class"
description: "The school Robot on a grid field…"
keywords:
  - robot executor school
  - grid robot programming
---

# Robot: what it is, commands, and how to use in class

Body text…
```

Keeping a `#` heading in the body that matches `title` is normal for Markdown editors and for renderers that show the article content below a site chrome title.

### Images

Paths to assets under [`website/`](../website/) are relative to the locale file. From `articles/<article_id>/en.md`, use:

```markdown
![Alt text.](../../website/img/hero/intro19_en.png)
```

## List order

The site index (when implemented) should sort article folders by ascending `order`. If two folders share the same `order`, use the folder name (`article_id`) as a stable tie-breaker (lexicographic).

## Translations and language alternates

All locales of one article live in the **same folder**. Translations are not separate `article_id` values.

A future HTML builder should link language versions the same way task pages do: `alternate_en` / `alternate_ru` and `hreflang` tags derived from `slug` in `meta.yaml` (see `PageLayout` in [`tools/build_website_content.py`](../tools/build_website_content.py)).

Supported site locales today are `en` and `ru`. Locale filenames are fixed: `en.md` and `ru.md` only.

## Adding a new article

1. Pick a new `article_id` (folder name), e.g. `using-the-task-viewer`.
2. Choose the next free `order` integer (one greater than the current maximum).
3. Create `articles/<article_id>/meta.yaml` with `order`, `date`, `author`, and `slug` entries for each locale you ship.
4. Add `en.md` and/or `ru.md` with front matter (`title`, `description`, `keywords`) and body.
5. Use `../../website/...` for images referenced from the new folder.

## What is out of scope here

- HTML generation, `website/articles/` output, and CI wiring (handled separately when a builder is added).
- Automatic validation tests for `meta.yaml` (may be added under `tests/` later).
