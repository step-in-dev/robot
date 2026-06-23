"""Tests for static website content generation."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.task_catalog import TaskCatalog
from tools import article_builder
from tools.build_website_content import (
    build_catalog,
    build_community_theme_hub,
    build_commands_page,
    build_editor_page,
    build_task_page,
    build_theme_hub,
    collect_sitemap_urls,
    write_sitemap,
)
from tools.site_catalog import COMMUNITY_DIR, discover_site_catalog


class BuildThemeHubTest(unittest.TestCase):
    def test_theme_hub_en_meta(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_theme_hub(catalog, "intro", "en")

        self.assertIn("<title>First steps | Robot</title>", html)
        self.assertIn(
            'meta name="description" content="24 Robot tasks on First steps: '
            "intro1\u2013intro24. Browse task conditions, field layouts, and limits.\"",
            html,
        )
        self.assertIn(
            'meta name="keywords" content="First steps, robot tasks, '
            "python programming, grid robot simulator, educational programming\"",
            html,
        )
        self.assertIn(
            'meta property="og:site_name" content="Robot"',
            html,
        )
        self.assertIn(
            'meta property="og:image" '
            'content="https://robot.stepindev.com/img/tasks/intro1_env0.webp"',
            html,
        )
        self.assertIn(
            'meta property="og:image:alt" content="Robot tasks on First steps '
            "(intro1\u2013intro24): grid field previews from the task catalog.\"",
            html,
        )
        self.assertIn(
            '"description": "24 Robot tasks on First steps: '
            'intro1\u2013intro24. Browse task conditions, field layouts, and limits."',
            html,
        )
        self.assertIn(
            '<p class="hub-page__intro">First steps with the Robot: move across a '
            "field, paint cells, and reach the goal cell.",
            html,
        )

    def test_theme_hub_ru_meta(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_theme_hub(catalog, "intro", "ru")

        self.assertIn("<title>Первые шаги | Robot</title>", html)
        self.assertNotIn("Robot tasks", html)
        self.assertIn(
            'meta name="description" content="24 задач исполнителя Робот по теме '
            '«Первые шаги»: '
            "intro1\u2013intro24. Условия, поля обстановок и ограничения.\"",
            html,
        )
        self.assertIn(
            'meta name="keywords" content="Первые шаги, задачи робот, '
            "python программирование, исполнитель робот, учебное программирование\"",
            html,
        )
        self.assertIn(
            'meta property="og:site_name" content="Робот"',
            html,
        )
        self.assertIn(
            'meta property="og:image" '
            'content="https://robot.stepindev.com/img/tasks/intro1_env0.webp"',
            html,
        )
        self.assertIn(
            'meta property="og:image:alt" content="Задачи исполнителя Робот по теме '
            '«Первые шаги» '
            "(intro1\u2013intro24): превью полей из каталога задач.\"",
            html,
        )

    def test_theme_hub_renders_task_thumbnail(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_theme_hub(catalog, "intro", "en")

        self.assertIn('class="task-list__thumb"', html)
        self.assertIn('src="../../img/tasks/intro1_env0.webp"', html)

        title_link = re.search(
            r'<h2 class="task-list__title"><a href="([^"]*intro1\.html)">'
            r"<code>intro1</code></a></h2>",
            html,
        )
        self.assertIsNotNone(title_link)

        intro1_item = re.search(
            r'<li class="task-list__item">.*?intro1.*?</li>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(intro1_item)
        item_html = intro1_item.group(0)
        self.assertIn('class="task-list__thumb"', item_html)
        self.assertRegex(
            item_html,
            r'<a class="task-list__thumb-link" href="[^"]*intro1\.html">\s*'
            r'<img class="task-list__thumb"',
        )


class BuildCatalogTest(unittest.TestCase):
    def test_catalog_theme_cards_show_range_without_per_theme_count(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_catalog(catalog, "ru")

        intro_card = re.search(
            r'<li class="theme-card">\s*'
            r'<h2><a href="[^"]*intro/index_ru\.html">Первые шаги</a>'
            r'<span class="theme-card__range">(.*?)</span></h2>\s*'
            r'<p class="theme-card__intro">(.*?)</p>\s*'
            r"</li>",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(intro_card)
        intro_range = intro_card.group(1)
        intro_description = intro_card.group(2)
        self.assertIn("<code>intro1</code> … <code>intro24</code>", intro_range)
        self.assertNotIn("Задач:", intro_range)
        self.assertNotIn("·", intro_range)
        self.assertIn("Первые шаги с исполнителем Робот", intro_description)
        self.assertIn("Всего задач:", html)

    def test_catalog_includes_community_sections(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        html = build_catalog(site_catalog, "ru")

        self.assertIn("Задачи от сообщества", html)
        self.assertIn("Набор задач 1. Подготовил: Александр Родюшкин", html)
        self.assertIn('id="community-pack-r"', html)
        self.assertIn('href="../tasks/community/r/intro/index_ru.html"', html)
        self.assertIn('class="community-pack__download"', html)
        self.assertIn(
            "не включены в архив с модулем и скачиваются отдельно", html
        )
        self.assertIn("Скачать задачи:", html)
        self.assertIn("Распаковать в robot/tasks", html)
        self.assertIn("rtasks.zip", html)
        self.assertIn(
            "https://github.com/step-in-dev/robot/releases/latest/download/rtasks.zip",
            html,
        )
        community_intro_link = re.search(
            r'<section class="community-pack">.*?'
            r'<li class="theme-card community-pack-card">.*?'
            r'<ul class="community-pack__themes">.*?'
            r'<a href="[^"]*community/r/intro/index_ru\.html">Первые шаги</a>'
            r'.*?<span class="theme-card__range">(.*?)</span>.*?</ul>.*?</section>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(community_intro_link)
        intro_range = community_intro_link.group(1)
        self.assertIn("<code>rintro1</code> … <code>rintro6</code>", intro_range)
        community_pack_section = re.search(
            r'<section class="community-pack">(.*?)</section>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(community_pack_section)
        self.assertEqual(
            len(re.findall(r'<li class="theme-card', community_pack_section.group(1))),
            1,
        )


class BuildCommunityThemeHubTest(unittest.TestCase):
    def test_community_theme_hub_uses_pack_breadcrumbs(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        pack = site_catalog.community_packs[0]
        html = build_community_theme_hub(site_catalog, pack, "intro", "ru")

        self.assertIn(
            '<p class="community-pack__eyebrow">Набор задач 1. Подготовил: '
            "Александр Родюшкин</p>",
            html,
        )
        self.assertIn('class="community-pack__download"', html)
        self.assertIn(
            "не включены в архив с модулем и скачиваются отдельно", html
        )
        self.assertIn("Скачать задачи:", html)
        self.assertIn("Распаковать в robot/tasks", html)
        self.assertIn("rtasks.zip", html)
        self.assertIn(
            "https://github.com/step-in-dev/robot/releases/latest/download/rtasks.zip",
            html,
        )
        self.assertIn("tasks/community/r/intro/index_ru.html", html)
        self.assertIn("rintro1_ru.html", html)
        self.assertNotIn('class="hub-page__intro"', html)
        self.assertNotIn("Первые шаги с исполнителем Робот", html)


class BuildCommunityTaskPageTest(unittest.TestCase):
    def test_community_task_page_has_pack_breadcrumb_and_nav(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        html = build_task_page(site_catalog, "rintro2", "ru")

        self.assertIn("Набор задач 1. Подготовил: Александр Родюшкин", html)
        self.assertIn('href="../tasks/index_ru.html#community-pack-r"', html)
        self.assertIn('href="../tasks/community/r/intro/index_ru.html"', html)
        self.assertIn("Предыдущая задача", html)
        self.assertIn("<code>rintro1</code>", html)


class BuildCommandsPageTest(unittest.TestCase):
    def test_commands_page_en_meta_and_intro(self) -> None:
        html = build_commands_page("en")

        self.assertIn(
            "<title>Robot command reference (Python) | Robot</title>",
            html,
        )
        self.assertIn(
            'meta name="description" content="Robot Python command reference: '
            "movement, painting, walls, cell values, task(), field(), pol(), "
            'and printn(), each with a short description."',
            html,
        )
        self.assertIn('meta name="keywords" content="robot simulator commands', html)
        self.assertIn(
            'meta property="og:image:alt" content="Robot command reference page '
            "listing move, paint, task(), and other student commands.",
            html,
        )
        self.assertIn("<h1>Command reference</h1>", html)
        self.assertIn(
            "<p class=\"section__intro\">Below are all commands available to "
            "students in the Robot simulator. Use "
            "<code>from robot import *</code> in your program, or import only "
            "the names you need.</p>",
            html,
        )
        self.assertIn('"name": "Robot Python command reference"', html)

    def test_commands_page_ru_meta_and_intro(self) -> None:
        html = build_commands_page("ru")

        self.assertIn(
            "<title>Справочник команд Робота на Python | Robot</title>",
            html,
        )
        self.assertIn(
            'meta name="description" content="Справочник команд исполнителя Робот '
            "на Python: движение, закраска, проверка стен и клеток, task(), "
            'field(), pol() и printn()."',
            html,
        )
        self.assertIn(
            'meta name="keywords" content="исполнитель робот команды',
            html,
        )
        self.assertIn(
            "<p class=\"section__intro\">Ниже — все команды, доступные учащимся "
            "в исполнителе Робот. В программе подключите модуль: "
            "<code>from robot import *</code> или импортируйте только нужные "
            "имена.</p>",
            html,
        )
        self.assertIn('"name": "Справочник команд Робота на Python"', html)

    def test_commands_page_en_field_legend(self) -> None:
        html = build_commands_page("en")
        legend_html = re.search(
            r'<figure class="field-legend">(.*?)</figure>',
            html,
            re.DOTALL,
        ).group(1)
        leader_points = re.findall(
            r'<polyline points="([^"]+)" data-field-legend-item="([^"]+)"'
            r' class="field-legend__leader"/>',
            legend_html,
        )
        leader_by_item = {item_id: points for points, item_id in leader_points}

        self.assertIn('<figure class="field-legend">', html)
        self.assertIn('img/commands/field.webp', html)
        self.assertIn('viewBox="0 0 774 541"', html)
        self.assertIn("Task environment field elements", html)
        self.assertIn(">Robot</text>", legend_html)
        self.assertIn(">Painted cell</text>", legend_html)
        self.assertIn(">Expected number (printn)</text>", legend_html)
        self.assertIn(">Pollution level</text>", legend_html)
        self.assertIn(">Marked cell</text>", legend_html)
        self.assertIn(">Walls</text>", legend_html)
        self.assertIn(">Expected final</tspan><tspan", legend_html)
        self.assertIn("position of Robot</tspan>", legend_html)
        self.assertIn('dominant-baseline="middle"', legend_html)
        self.assertIn('font-size="13"', legend_html)
        self.assertEqual(len(leader_by_item), 7)
        self.assertNotIn("<line ", legend_html)
        self.assertEqual(leader_by_item["robot"], "122.0,101.0 185.0,101.0 185.0,101.0")
        self.assertEqual(leader_by_item["print"], "572.0,181.0 345.0,181.0 345.0,181.0")
        self.assertEqual(
            leader_by_item["pollution"],
            "572.0,261.0 345.0,261.0 345.0,261.0",
        )
        self.assertEqual(leader_by_item["walls"], "122.0,243.0 150.0,243.0 345.0,221.0")
        self.assertEqual(leader_by_item["home"], "572.0,421.0 505.0,421.0 505.0,421.0")
        self.assertEqual(leader_by_item["painted"], "312.2,32.0 345.0,32.0 345.0,101.0")
        self.assertEqual(leader_by_item["to_paint"], "393.4,487.0 345.0,487.0 345.0,421.0")
        intro_pos = html.find('class="section__intro"')
        legend_pos = html.find("field-legend")
        grid_pos = html.find('class="command-grid"')
        self.assertLess(intro_pos, legend_pos)
        self.assertLess(legend_pos, grid_pos)

    def test_commands_page_ru_field_legend(self) -> None:
        html = build_commands_page("ru")
        legend_html = re.search(
            r'<figure class="field-legend">(.*?)</figure>',
            html,
            re.DOTALL,
        ).group(1)
        leader_points = re.findall(
            r'<polyline points="([^"]+)" data-field-legend-item="([^"]+)"'
            r' class="field-legend__leader"/>',
            legend_html,
        )
        leader_by_item = {item_id: points for points, item_id in leader_points}

        self.assertIn('<figure class="field-legend">', html)
        self.assertIn("Элементы обстановки на поле", html)
        self.assertIn(">Робот</text>", legend_html)
        self.assertIn(">Закрашенная клетка</text>", legend_html)
        self.assertIn(">Ожидаемое число (printn)</text>", legend_html)
        self.assertIn(">Уровень загрязнения</text>", legend_html)
        self.assertIn(">Стены</text>", legend_html)
        self.assertIn("Клетка, помеченная", legend_html)
        self.assertIn("для закраски</tspan>", legend_html)
        self.assertIn(">Ожидаемое</tspan><tspan", legend_html)
        self.assertIn("конечное положение Робота</tspan>", legend_html)
        self.assertIn('dominant-baseline="middle"', legend_html)
        self.assertEqual(len(leader_by_item), 7)
        self.assertNotIn("<line ", legend_html)
        self.assertEqual(leader_by_item["painted"], "333.5,32.0 345.0,32.0 345.0,101.0")
        self.assertEqual(leader_by_item["to_paint"], "369.8,495.0 345.0,495.0 345.0,421.0")
        self.assertEqual(leader_by_item["walls"], "122.0,243.0 150.0,243.0 345.0,221.0")

    def test_commands_page_en_command_groups(self) -> None:
        html = build_commands_page("en")

        self.assertIn("<h2>Choosing a task or creating a field</h2>", html)
        self.assertIn("<h2>Action commands</h2>", html)
        self.assertIn("<h2>Environment analysis</h2>", html)
        self.assertNotIn("<h2>Values &amp; output</h2>", html)
        self.assertEqual(html.count('<article class="command-group">'), 3)

        action_group = re.search(
            r'<article class="command-group">\s*<h2>Action commands</h2>(.*?)</article>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(action_group)
        action_html = action_group.group(1)
        self.assertIn("<code>paint()</code>", action_html)
        self.assertIn("<code>printn(value)</code>", action_html)

        env_group = re.search(
            r'<article class="command-group">\s*<h2>Environment analysis</h2>(.*?)</article>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(env_group)
        env_html = env_group.group(1)
        self.assertIn("<code>pol()</code>", env_html)
        self.assertNotIn("<code>paint()</code>", env_html)
        self.assertNotIn("<code>printn(value)</code>", env_html)

    def test_commands_page_ru_command_groups(self) -> None:
        html = build_commands_page("ru")

        self.assertIn("<h2>Выбор задачи или создание поля</h2>", html)
        self.assertIn("<h2>Команды-действия</h2>", html)
        self.assertIn("<h2>Анализ обстановки</h2>", html)
        self.assertNotIn("<h2>Значения и вывод</h2>", html)
        self.assertEqual(html.count('<article class="command-group">'), 3)

        action_group = re.search(
            r'<article class="command-group">\s*<h2>Команды-действия</h2>(.*?)</article>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(action_group)
        action_html = action_group.group(1)
        self.assertIn("<code>paint()</code>", action_html)
        self.assertIn("<code>printn(value)</code>", action_html)

        env_group = re.search(
            r'<article class="command-group">\s*<h2>Анализ обстановки</h2>(.*?)</article>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(env_group)
        env_html = env_group.group(1)
        self.assertIn("<code>pol()</code>", env_html)
        self.assertNotIn("<code>paint()</code>", env_html)
        self.assertNotIn("<code>printn(value)</code>", env_html)


class BuildEditorPageTest(unittest.TestCase):
    def test_editor_page_en(self) -> None:
        html = build_editor_page("en")

        self.assertIn("<h1>Environment editor</h1>", html)
        steps = re.search(
            r'<ol class="editor-steps">(.*?)</ol>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(steps)
        self.assertEqual(steps.group(1).count("<li>"), 4)
        self.assertIn("python editor/editor.py", html)
        self.assertIn("github.com/step-in-dev/robot/releases", html)
        self.assertIn("GitHub Releases</a>", html)
        self.assertNotIn("repository root", html)
        self.assertIn("robot/tasks", html)
        self.assertIn('src="img/editor/editor.webp"', html)
        self.assertIn("width=\"846\" height=\"554\"", html)
        self.assertNotIn("save_env_en.png", html)
        self.assertIn("stepindev.com/en/py-robot", html)
        self.assertIn("editor-online-card", html)
        self.assertIn("<h3>Online environment editor</h3>", html)
        self.assertIn(
            "Create and edit task environments in the browser without installing "
            "the module.",
            html,
        )
        self.assertIn(">Open online editor</a>", html)
        online_card = re.search(
            r'<div class="callout editor-online-card">(.*?)</div>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(online_card)
        card_html = online_card.group(1)
        self.assertIn('<ul class="track-list">', card_html)
        self.assertIn("8 rows by 10 columns", card_html)
        self.assertIn("Does not support setting solution constraints.", card_html)
        self.assertRegex(
            html,
            r"</div>\s*<div class=\"callout editor-online-card\">",
        )
        self.assertIn("todoText", html)
        self.assertIn("Max Robot commands and function calls", html)
        self.assertIn(
            'Docs/task-env-format.md#operatorslimit" rel="noopener noreferrer" '
            'target="_blank"><code>operatorsLimit</code></a>',
            html,
        )
        self.assertNotIn(">description</a>", html)
        self.assertIn("Docs/task-env-format.md#operatorslimit", html)
        self.assertIn("Docs/task-env-format.md#customfunctioncallcount", html)
        self.assertIn("Docs/task-env-format.md#iflimit-and-whilelimit", html)
        self.assertIn("Docs/task-env-format.md#requiredkeywords-and-bannedkeywords", html)
        self.assertIn('href="editor.html"', html)
        self.assertIn('task("robot")', html)

    def test_editor_page_ru(self) -> None:
        html = build_editor_page("ru")

        self.assertIn("<h1>Редактор обстановок</h1>", html)
        self.assertIn("python editor/editor.py", html)
        self.assertIn("github.com/step-in-dev/robot/releases", html)
        self.assertNotIn("корня репозитория", html)
        self.assertIn("robot/tasks", html)
        self.assertNotIn("save_env_ru.png", html)
        self.assertIn("stepindev.com/ru/py-robot", html)
        self.assertIn("editor-online-card", html)
        self.assertIn("<h3>Онлайн-редактор обстановок</h3>", html)
        self.assertIn(
            "Создавайте и редактируйте обстановки в браузере, без установки модуля.",
            html,
        )
        self.assertIn(">Открыть онлайн-редактор</a>", html)
        online_card = re.search(
            r'<div class="callout editor-online-card">(.*?)</div>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(online_card)
        card_html = online_card.group(1)
        self.assertIn('<ul class="track-list">', card_html)
        self.assertIn("8 строк на 10 колонок", card_html)
        self.assertIn("Не поддерживается задание ограничений на решение.", card_html)
        self.assertRegex(
            html,
            r"</div>\s*<div class=\"callout editor-online-card\">",
        )
        self.assertIn("todoText", html)
        self.assertIn("Макс. команд Робота и вызовов функций", html)
        self.assertIn(
            'Docs/task-env-format.ru.md#operatorslimit" rel="noopener noreferrer" '
            'target="_blank"><code>operatorsLimit</code></a>',
            html,
        )
        self.assertNotIn(">описание</a>", html)
        self.assertIn('href="editor_ru.html"', html)
        self.assertIn("Docs/task-env-format.ru.md#operatorslimit", html)
        self.assertIn("Docs/task-env-format.ru.md#customfunctioncallcount", html)
        self.assertIn("Docs/task-env-format.ru.md#iflimit-%D0%B8-whilelimit", html)
        self.assertIn(
            "Docs/task-env-format.ru.md#requiredkeywords-%D0%B8-bannedkeywords",
            html,
        )


class TaskPageSeoTest(unittest.TestCase):
    def test_task_page_has_noindex(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_task_page(catalog, "intro1", "en")

        self.assertIn(
            'meta name="robots" content="noindex, follow"',
            html,
        )

    def test_theme_hub_has_no_noindex(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_theme_hub(catalog, "intro", "en")

        self.assertNotIn("noindex", html)


class WriteSitemapTest(unittest.TestCase):
    def test_sitemap_omits_lastmod(self) -> None:
        catalog = TaskCatalog.discover()
        articles = article_builder.discover_articles()
        article_groups = article_builder.collect_article_sitemap_groups(articles)

        with tempfile.TemporaryDirectory() as tmp:
            website_dir = Path(tmp) / "website"
            website_dir.mkdir()
            with patch("tools.build_website_content.WEBSITE_DIR", website_dir):
                write_sitemap(catalog, article_groups=article_groups)
                sitemap = (website_dir / "sitemap.xml").read_text(encoding="utf-8")

        self.assertNotIn("<lastmod>", sitemap)
        self.assertIn("<loc>", sitemap)
        self.assertIn('hreflang="en"', sitemap)
        self.assertIn('hreflang="ru"', sitemap)

    def test_sitemap_includes_catalog_and_theme_hubs_not_task_pages(self) -> None:
        catalog = TaskCatalog.discover()
        articles = article_builder.discover_articles()
        article_groups = article_builder.collect_article_sitemap_groups(articles)
        groups = collect_sitemap_urls(catalog, article_groups=article_groups)
        flat_paths = {path for pair in groups for path in pair}

        self.assertIn("tasks/index.html", flat_paths)
        self.assertIn("tasks/intro/index.html", flat_paths)
        self.assertNotIn("tasks/intro1.html", flat_paths)

        with tempfile.TemporaryDirectory() as tmp:
            website_dir = Path(tmp) / "website"
            website_dir.mkdir()
            with patch("tools.build_website_content.WEBSITE_DIR", website_dir):
                write_sitemap(catalog, article_groups=article_groups)
                sitemap = (website_dir / "sitemap.xml").read_text(encoding="utf-8")

        self.assertIn("tasks/index.html", sitemap)
        self.assertIn("tasks/intro/index.html", sitemap)
        self.assertNotIn("tasks/intro1.html", sitemap)

    def test_sitemap_includes_community_theme_hubs(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        groups = collect_sitemap_urls(site_catalog)
        flat_paths = {path for pair in groups for path in pair}

        self.assertIn("tasks/community/r/intro/index.html", flat_paths)
        self.assertIn("tasks/community/r/intro/index_ru.html", flat_paths)


if __name__ == "__main__":
    unittest.main()
