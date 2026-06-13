"""Tests for task file serialization used by the environment editor."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.i18n import clear_translation_cache, t
from robot.task_serializer import (
    ConstraintFieldInput,
    EditorDocument,
    TaskSaveError,
    apply_constraint_fields_to_preserved,
    apply_snapshot,
    bundled_tasks_dir,
    constraint_field_display_values,
    create_default_env_dto,
    create_empty_document,
    document_to_payload,
    is_bundled_task_path,
    load_task_file,
    parse_constraint_field_input,
    save_task_file,
    snapshot_from_document,
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

    def test_constraint_field_display_values_reads_preserved_fields(self) -> None:
        preserved = {
            "operatorsLimit": 4,
            "requiredKeywords": "for, while",
        }
        values = constraint_field_display_values(preserved)
        self.assertEqual(values["operators_limit"], "4")
        self.assertEqual(values["required_keywords"], "for, while")
        self.assertEqual(values["if_limit"], "")

    def test_apply_constraint_fields_to_preserved_updates_and_clears(self) -> None:
        preserved = {
            "operatorsLimit": 1,
            "ifLimit": 2,
            "requiredKeywords": "for",
        }
        apply_constraint_fields_to_preserved(
            preserved,
            ConstraintFieldInput(
                operators_limit="5",
                custom_function_call_count="",
                if_limit="",
                while_limit="3",
                required_keywords="def",
                banned_keywords="while",
            ),
        )
        self.assertEqual(preserved["operatorsLimit"], 5)
        self.assertNotIn("ifLimit", preserved)
        self.assertEqual(preserved["whileLimit"], 3)
        self.assertEqual(preserved["requiredKeywords"], "def")
        self.assertEqual(preserved["bannedKeywords"], "while")

    def test_parse_constraint_field_input_parses_values(self) -> None:
        constraints = parse_constraint_field_input(
            ConstraintFieldInput(
                operators_limit="2",
                custom_function_call_count="1",
                if_limit="",
                while_limit="",
                required_keywords="for",
                banned_keywords="",
            )
        )
        self.assertEqual(constraints.operators_limit, 2)
        self.assertEqual(constraints.custom_function_call_count, 1)
        self.assertEqual(constraints.required_keywords, ("for",))

    def test_parse_constraint_field_input_rejects_invalid_operators_limit(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            parse_constraint_field_input(
                ConstraintFieldInput(operators_limit="bad")
            )

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_parse_constraint_field_input_unknown_keyword_uses_field_label(
        self,
    ) -> None:
        clear_translation_cache()
        with self.assertRaises(ValueError) as ctx:
            parse_constraint_field_input(
                ConstraintFieldInput(banned_keywords="BB")
            )
        message = str(ctx.exception)
        self.assertEqual(
            message,
            "Unknown Python keywords in "
            f"{t('editor.constraints.field.banned_keywords')}: BB",
        )
        self.assertNotIn("bannedKeywords", message)
        self.assertNotIn("<editor>", message)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_parse_constraint_field_input_keyword_lists_conflict(
        self,
    ) -> None:
        clear_translation_cache()
        with self.assertRaises(ValueError) as ctx:
            parse_constraint_field_input(
                ConstraintFieldInput(
                    required_keywords="while",
                    banned_keywords="while",
                )
            )
        message = str(ctx.exception)
        self.assertIn(t("editor.constraints.field.required_keywords"), message)
        self.assertIn(t("editor.constraints.field.banned_keywords"), message)
        self.assertNotIn("requiredKeywords", message)
        self.assertNotIn("bannedKeywords", message)
        self.assertNotIn("<editor>", message)

    def test_snapshot_round_trip_preserves_constraints(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            preserved_fields={"operatorsLimit": 9, "bannedKeywords": "while"},
        )
        snapshot = snapshot_from_document(document)
        document.preserved_fields.clear()
        apply_snapshot(document, snapshot)
        self.assertEqual(document.preserved_fields["operatorsLimit"], 9)
        self.assertEqual(document.preserved_fields["bannedKeywords"], "while")


if __name__ == "__main__":
    unittest.main()
