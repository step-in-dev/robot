"""Tests for task file serialization used by the environment editor."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.i18n import clear_translation_cache
from robot.task_serializer import (
    EditorDocument,
    TaskSaveError,
    bundled_tasks_dir,
    create_default_env_dto,
    create_empty_document,
    document_to_payload,
    is_bundled_task_path,
    load_task_file,
    save_task_file,
    update_todo_text,
)


class TaskSerializerTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_translation_cache()

    def test_create_empty_document_has_default_env(self) -> None:
        document = create_empty_document()
        self.assertEqual(len(document.env_dtos), 1)
        self.assertEqual(document.env_dtos[0], create_default_env_dto())
        self.assertEqual(document.todo_text, "")
        self.assertIsNone(document.file_path)

    def test_round_trip_preserves_constraints_and_localized_todo(self) -> None:
        payload = {
            "envDtos": [
                {
                    "width": 3,
                    "height": 2,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 1,
                    "finalCol": 2,
                }
            ],
            "todoText": {"en": "Reach goal", "ru": "Дойди до цели"},
            "operatorsLimit": 5,
            "requiredKeywords": "for",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.env"
            path.write_text(json.dumps(payload), encoding="utf-8")
            document = load_task_file(path)
            self.assertEqual(document.preserved_fields["operatorsLimit"], 5)
            self.assertEqual(document.preserved_fields["requiredKeywords"], "for")
            self.assertEqual(
                document.todo_text,
                {"en": "Reach goal", "ru": "Дойди до цели"},
            )
            save_path = Path(temp_dir) / "saved.env"
            save_task_file(save_path, document)
            saved = json.loads(save_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["operatorsLimit"], 5)
        self.assertEqual(saved["requiredKeywords"], "for")
        self.assertEqual(saved["todoText"]["ru"], "Дойди до цели")
        self.assertEqual(saved["envDtos"][0]["width"], 3)

    def test_save_task_file_raises_task_save_error_on_write_failure(self) -> None:
        document = create_empty_document()
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            with self.assertRaises(TaskSaveError):
                save_task_file(Path("blocked.env"), document)

    def test_is_bundled_task_path_detects_packaged_tasks(self) -> None:
        bundled = bundled_tasks_dir() / "intro1.env"
        self.assertTrue(is_bundled_task_path(bundled))
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertFalse(is_bundled_task_path(Path(temp_dir) / "custom.env"))

    def test_update_todo_text_updates_localized_map(self) -> None:
        with patch("robot.task_serializer.detect_language", return_value="ru"):
            updated = update_todo_text({"en": "Old", "ru": "Старое"}, "Новое")
        self.assertEqual(updated["en"], "Old")
        self.assertEqual(updated["ru"], "Новое")

    def test_document_to_payload_omits_empty_todo(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text="",
            preserved_fields={"operatorsLimit": 1},
        )
        payload = document_to_payload(document)
        self.assertNotIn("todoText", payload)
        self.assertEqual(payload["operatorsLimit"], 1)


if __name__ == "__main__":
    unittest.main()
