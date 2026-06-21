"""Tests for explicit-path site task loading helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from robot.loader import TaskLoadError
from tests.loader_runtime._helpers import write_minimal_task_env
from tools.site_catalog import COMMUNITY_DIR, discover_site_catalog
from tools.site_task_load import load_raw_todo_from_path, load_task_from_path


class LoadTaskFromPathTest(unittest.TestCase):
    def test_loads_minimal_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_path = Path(temp_dir) / "custom1.env"
            write_minimal_task_env(task_path, "custom1", todo_text="hello")

            task = load_task_from_path(task_path)

        self.assertEqual(len(task.envs), 1)
        self.assertEqual(task.todo_text, "hello")

    def test_reads_raw_todo_without_language_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_path = Path(temp_dir) / "custom1.env"
            payload = {
                "envDtos": [{"width": 1, "height": 1, "startRow": 0, "startCol": 0}],
                "todoText": {"ru": "Привет", "en": "Hello"},
            }
            task_path.write_text(json.dumps(payload), encoding="utf-8")

            raw_todo = load_raw_todo_from_path(task_path)

        self.assertEqual(raw_todo, {"ru": "Привет", "en": "Hello"})

    def test_invalid_json_raises_task_load_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_path = Path(temp_dir) / "broken.env"
            task_path.write_text("{", encoding="utf-8")

            with self.assertRaises(TaskLoadError):
                load_task_from_path(task_path)

    def test_loads_real_pack1_task(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        location = site_catalog.locate_community_task("rintro1")
        assert location is not None

        task = load_task_from_path(location.path)
        raw_todo = load_raw_todo_from_path(location.path)

        self.assertGreater(len(task.envs), 0)
        self.assertIsInstance(task.todo_text, str)
        self.assertIsInstance(raw_todo, (str, dict))


if __name__ == "__main__":
    unittest.main()
