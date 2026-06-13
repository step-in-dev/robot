"""Tests for article Markdown → HTML site generation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.article_builder import (
    Article,
    LocaleContent,
    build_article_page,
    discover_articles,
    markdown_to_html,
    parse_locale_md,
    rewrite_article_html,
    validate_articles,
)
from tools.build_website_content import PageLayout

INTRO_META = """\
order: 1
date: 2026-06-03
author: StepInDev
slug:
  en: what-is-the-robot-simulator
  ru: chto-takoe-ispolnitel-robot
"""

INTRO_EN_BODY = """\
---
title: "Test title"
description: "Test description for SEO."
keywords:
  - keyword one
---

# Test title

![Hero.](../../website/img/hero/intro19_en.png)

| A | B |
| - | - |
| 1 | 2 |

```python
from robot import *
```
"""


class ParseLocaleMdTest(unittest.TestCase):
    def test_parses_front_matter_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "en.md"
            path.write_text(INTRO_EN_BODY, encoding="utf-8")
            locale = parse_locale_md(path)
        self.assertEqual(locale.title, "Test title")
        self.assertEqual(locale.description, "Test description for SEO.")
        self.assertEqual(locale.keywords, ("keyword one",))
        self.assertIn("# Test title", locale.body)


class DiscoverArticlesTest(unittest.TestCase):
    def test_sorts_by_descending_order(self) -> None:
        articles = discover_articles()
        ids = [article.article_id for article in articles]
        self.assertEqual(ids, ["quick-task-selection", "robot-simulator-intro"])


class ValidateArticlesTest(unittest.TestCase):
    def test_rejects_duplicate_order(self) -> None:
        articles = [
            Article(
                "a", 1, "2026-01-01", "Author",
                {"en": "slug-a"},
                {"en": LocaleContent("t", "d", (), "")},
            ),
            Article(
                "b", 1, "2026-01-02", "Author",
                {"en": "slug-b"},
                {"en": LocaleContent("t", "d", (), "")},
            ),
        ]
        with self.assertRaises(SystemExit):
            validate_articles(articles)

    def test_rejects_duplicate_slug_per_language(self) -> None:
        articles = [
            Article(
                "a", 1, "2026-01-01", "Author",
                {"en": "same-slug"},
                {"en": LocaleContent("t", "d", (), "")},
            ),
            Article(
                "b", 2, "2026-01-02", "Author",
                {"en": "same-slug"},
                {"en": LocaleContent("t", "d", (), "")},
            ),
        ]
        with self.assertRaises(SystemExit):
            validate_articles(articles)


class RewriteArticleHtmlTest(unittest.TestCase):
    def test_rewrites_website_asset_paths(self) -> None:
        layout = PageLayout(
            lang="en",
            depth=2,
            page_kind="article",
            title="T",
            description="D",
            canonical_path="articles/foo/index.html",
            alternate_en="articles/foo/index.html",
            alternate_ru="articles/bar/index_ru.html",
        )
        raw = '<img src="../../website/img/hero/intro19_en.png" alt="">'
        out = rewrite_article_html(raw, layout, "en")
        self.assertIn('src="../../img/hero/intro19_en.png"', out)

    def test_rewrites_absolute_site_links(self) -> None:
        layout = PageLayout(
            lang="ru",
            depth=2,
            page_kind="article",
            title="T",
            description="D",
            canonical_path="articles/bar/index_ru.html",
            alternate_en="articles/foo/index.html",
            alternate_ru="articles/bar/index_ru.html",
        )
        raw = '<a href="https://robot.stepindev.com/commands.html">ref</a>'
        out = rewrite_article_html(raw, layout, "ru")
        self.assertIn('href="../../commands_ru.html"', out)


class MarkdownToHtmlTest(unittest.TestCase):
    def test_renders_table_and_fence(self) -> None:
        html = markdown_to_html("| A | B |\n| - | - |\n| 1 | 2 |\n\n```python\nx = 1\n```")
        self.assertIn("<table>", html)
        self.assertIn("<pre>", html)


class BuildArticlePageSmokeTest(unittest.TestCase):
    def test_intro_article_html(self) -> None:
        articles = discover_articles()
        intro = next(a for a in articles if a.article_id == "robot-simulator-intro")
        html = build_article_page(intro, "en")
        self.assertIn("<table>", html)
        self.assertIn("<pre>", html)
        self.assertIn('src="../../img/hero/intro19_en.png"', html)
        self.assertIn("<meta name=\"keywords\"", html)
        self.assertIn('property="og:type" content="article"', html)


if __name__ == "__main__":
    unittest.main()
