"""Tests for localized task catalog help text."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import robot
from robot import i18n
from robot.loader import TASKS_DIR_ENV
from robot.task_catalog import KNOWN_TASK_GROUP_PREFIXES, TaskCatalog
from robot.task_help import iter_task_list_lines

from tests.loader_runtime._helpers import write_minimal_task_env


class TaskHelpTest(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.clear_translation_cache()

    def test_starts_with_tasks_title_and_theme_blocks(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            i18n.clear_translation_cache()
            lines = list(iter_task_list_lines())

        self.assertEqual(lines[0], "Available tasks for task()")
        self.assertEqual(lines[1], "")

        bundled = Path(robot.__file__).resolve().parent / "tasks"
        catalog = TaskCatalog.discover(bundled)
        expected_prefixes = [
            prefix
            for prefix in KNOWN_TASK_GROUP_PREFIXES
            if catalog.task_ids_for(prefix)
        ]
        idx = 2
        for prefix in expected_prefixes:
            self.assertEqual(lines[idx], i18n.t(f"help.task_group.{prefix}"))
            idx += 1
            task_ids = catalog.task_ids_for(prefix)
            if len(task_ids) > 2:
                expected_ids = f"{task_ids[0]}, ..., {task_ids[-1]}"
            else:
                expected_ids = ", ".join(task_ids)
            self.assertEqual(lines[idx], expected_ids)
            idx += 1
            self.assertEqual(lines[idx], "")
            idx += 1

    def test_compresses_long_id_lists(self) -> None:
        bundled = Path(robot.__file__).resolve().parent / "tasks"
        catalog = TaskCatalog.discover(bundled)
        intro_ids = catalog.task_ids_for("intro")
        self.assertGreater(len(intro_ids), 2)

        lines = list(iter_task_list_lines())
        intro_title = i18n.t("help.task_group.intro")
        title_idx = lines.index(intro_title)
        self.assertEqual(
            lines[title_idx + 1],
            f"{intro_ids[0]}, ..., {intro_ids[-1]}",
        )

    def test_short_lists_are_not_compressed(self) -> None:
        catalog = TaskCatalog(
            themes=("for", "if"),
            groups={
                "for": ("for1", "for2"),
                "if": ("if1",),
            },
        )
        with patch("robot.task_help.TaskCatalog.discover", return_value=catalog):
            lines = list(iter_task_list_lines())

        for_title = i18n.t("help.task_group.for")
        self.assertIn(for_title, lines)
        self.assertIn("for1, for2", lines)
        if_title = i18n.t("help.task_group.if")
        self.assertIn(if_title, lines)
        self.assertIn("if1", lines)

    def test_omits_empty_known_themes(self) -> None:
        catalog = TaskCatalog(
            themes=("for",),
            groups={"for": ("for1", "for2", "for3")},
        )
        with patch("robot.task_help.TaskCatalog.discover", return_value=catalog):
            lines = list(iter_task_list_lines())

        self.assertIn(i18n.t("help.task_group.for"), lines)
        self.assertNotIn(i18n.t("help.task_group.intro"), lines)

    def test_uses_bundled_catalog_not_robot_tasks_dir(self) -> None:
        bundled = Path(robot.__file__).resolve().parent / "tasks"
        bundled_intro = TaskCatalog.discover(bundled).task_ids_for("intro")
        self.assertTrue(bundled_intro)

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "customonly1.env", "customonly1", width=1)
            with patch.dict("os.environ", {TASKS_DIR_ENV: temp_dir}, clear=False):
                lines = list(iter_task_list_lines())

        intro_title = i18n.t("help.task_group.intro")
        self.assertIn(intro_title, lines)
        intro_idx = lines.index(intro_title)
        self.assertIn(bundled_intro[0], lines[intro_idx + 1])
        self.assertNotIn("customonly1", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
