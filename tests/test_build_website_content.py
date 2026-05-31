"""Tests for static website content generation."""

from __future__ import annotations

import re
import unittest

from robot.task_catalog import TaskCatalog
from tools.build_website_content import build_theme_hub


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


if __name__ == "__main__":
    unittest.main()
