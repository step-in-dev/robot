"""Tests for static website content generation."""

from __future__ import annotations

import re
import unittest

from robot.task_catalog import TaskCatalog
from tools.build_website_content import (
    build_commands_page,
    build_editor_page,
    build_theme_hub,
)


class BuildThemeHubTest(unittest.TestCase):
    def test_theme_hub_renders_task_thumbnail(self) -> None:
        catalog = TaskCatalog.discover()
        html = build_theme_hub(catalog, "intro", "en")

        self.assertIn('class="task-list__thumb"', html)
        self.assertIn('src="../../img/tasks/intro1_env0.png"', html)

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
        self.assertEqual(steps.group(1).count("<li>"), 5)
        self.assertIn("https://stepindev.com/en/py-robot", html)
        self.assertIn('src="img/editor/editor.png"', html)
        self.assertIn('src="img/editor/save_env_en.png"', html)
        self.assertIn("Docs/task-env-format.md#solution-constraints", html)
        self.assertIn('href="editor.html"', html)
        self.assertIn('task("robot")', html)

    def test_editor_page_ru(self) -> None:
        html = build_editor_page("ru")

        self.assertIn("<h1>Редактор обстановок</h1>", html)
        self.assertIn("https://stepindev.com/ru/py-robot", html)
        self.assertIn('src="img/editor/save_env_ru.png"', html)
        self.assertIn('href="editor_ru.html"', html)
        self.assertIn(
            "Docs/task-env-format.ru.md#%D0%BE%D0%B3%D1%80%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BD%D0%B0-%D1%80%D0%B5%D1%88%D0%B5%D0%BD%D0%B8%D0%B5",
            html,
        )


if __name__ == "__main__":
    unittest.main()
