"""Tests for task file discovery and ordering."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.loader import TASKS_DIR_ENV
from robot.task_catalog import (
    TaskCatalog,
    discover_task_groups,
    natural_sort_key,
    ordered_theme_prefixes,
    resolve_tasks_dir,
    task_id_for_theme,
    task_number_from_id,
    theme_from_task_id,
)

from tests.loader_runtime._helpers import patched_tasks_dir, write_minimal_task_env


class NaturalSortKeyTest(unittest.TestCase):
    def test_orders_numbers_numerically(self) -> None:
        ids = ["intro2", "intro10", "intro1"]
        self.assertEqual(
            sorted(ids, key=natural_sort_key),
            ["intro1", "intro2", "intro10"],
        )


class OrderedThemePrefixesTest(unittest.TestCase):
    def test_known_order_then_unknown_alphabetically(self) -> None:
        groups = {
            "wfun": ["wfun1"],
            "intro": ["intro1"],
            "zebra": ["zebra1"],
            "fun": ["fun1"],
            "alpha": ["alpha1"],
        }
        self.assertEqual(
            ordered_theme_prefixes(groups),
            ["intro", "fun", "wfun", "alpha", "zebra"],
        )

    def test_omits_empty_known_themes(self) -> None:
        groups = {"for": ["for1"], "intro": []}
        self.assertEqual(ordered_theme_prefixes(groups), ["for"])


class DiscoverTaskGroupsTest(unittest.TestCase):
    def test_respects_robot_tasks_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1", width=1)
            write_minimal_task_env(base / "custom9.env", "custom9", width=1)
            with patched_tasks_dir(temp_dir):
                groups = discover_task_groups()
                self.assertEqual(groups["intro"], ["intro1"])
                self.assertEqual(groups["custom"], ["custom9"])
                catalog = TaskCatalog.discover()
                self.assertEqual(catalog.themes, ("intro", "custom"))
                self.assertEqual(catalog.task_ids_for("intro"), ("intro1",))

    def test_task_number_helpers(self) -> None:
        self.assertEqual(task_number_from_id("intro8"), 8)
        self.assertEqual(task_id_for_theme("for", 3), "for3")

    def test_suffix_grouping_unicode_and_punctuation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "введение 1.env", "введение 1", width=1)
            write_minimal_task_env(base / "введение 2.env", "введение 2", width=1)
            write_minimal_task_env(base / "my_task-1.env", "my_task-1", width=1)
            write_minimal_task_env(base / "readme.env", "readme", width=1)
            write_minimal_task_env(base / "custom9.env", "custom9", width=1)
            groups = discover_task_groups(base)
            self.assertEqual(
                sorted(groups["введение "]),
                ["введение 1", "введение 2"],
            )
            self.assertEqual(groups["my_task-"], ["my_task-1"])
            self.assertNotIn("readme", groups)
            self.assertEqual(groups["custom"], ["custom9"])

    def test_theme_from_task_id(self) -> None:
        self.assertEqual(theme_from_task_id("введение 8"), "введение ")
        self.assertEqual(theme_from_task_id("урок!!!12"), "урок!!!")
        self.assertIsNone(theme_from_task_id("задача"))
        self.assertIsNone(theme_from_task_id("task5!"))

    def test_current_theme_for_spaced_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "введение 1.env", "введение 1", width=1)
            write_minimal_task_env(base / "введение 2.env", "введение 2", width=1)
            catalog = TaskCatalog.discover(base)
            self.assertEqual(
                catalog.current_theme_for_task("введение 2"),
                "введение ",
            )


class TaskCatalogDiscoverTest(unittest.TestCase):
    def test_bundled_catalog_has_intro_first(self) -> None:
        catalog = TaskCatalog.discover()
        self.assertGreater(len(catalog.themes), 0)
        self.assertEqual(catalog.themes[0], "intro")
        self.assertIn("intro1", catalog.task_ids_for("intro"))


class ResolveTasksDirTest(unittest.TestCase):
    def test_external_dir_when_env_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {TASKS_DIR_ENV: temp_dir}, clear=False):
                self.assertEqual(resolve_tasks_dir(), Path(temp_dir))


if __name__ == "__main__":
    unittest.main()
