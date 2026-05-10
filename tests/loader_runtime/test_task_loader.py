import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.loader import TaskLoadError, load_task, load_task_definition

from ._helpers import LoaderRuntimeTestBase


class TaskLoaderTest(LoaderRuntimeTestBase):
    def test_loader_reads_env_dtos_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "line.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 2,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 1,
                            }
                        ],
                        "todoText": "Reach the end",
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                envs = load_task("line")
                task = load_task_definition("line")

        self.assertEqual(len(envs), 1)
        self.assertEqual(envs[0].width, 2)
        self.assertEqual(envs[0].final_col, 1)
        self.assertEqual(task.todo_text, "Reach the end")
        self.assertIsNone(task.operators_limit)
        self.assertIsNone(task.custom_function_call_count)
        self.assertIsNone(task.if_limit)
        self.assertIsNone(task.while_limit)
        self.assertIsNone(task.required_keywords)
        self.assertIsNone(task.banned_keywords)

    def test_load_task_definition_reads_operators_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "lim.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 1,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 0,
                            }
                        ],
                        "operatorsLimit": 5,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                task = load_task_definition("lim")

        self.assertEqual(task.operators_limit, 5)

    def test_load_task_definition_reads_custom_function_call_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "uf.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 1,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 0,
                            }
                        ],
                        "customFunctionCallCount": 2,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                task = load_task_definition("uf")

        self.assertEqual(task.custom_function_call_count, 2)

    def test_load_task_definition_reads_if_limit_and_while_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "kwlim.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [self._minimal_env_dto()],
                        "ifLimit": 2,
                        "whileLimit": 1,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                task = load_task_definition("kwlim")

        self.assertEqual(task.if_limit, 2)
        self.assertEqual(task.while_limit, 1)

    def test_load_task_definition_reads_keyword_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "kw.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [self._minimal_env_dto()],
                        "requiredKeywords": "for, def, for",
                        "bannedKeywords": "while, if",
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                task = load_task_definition("kw")

        self.assertEqual(task.required_keywords, ("def", "for"))
        self.assertEqual(task.banned_keywords, ("if", "while"))

    def test_load_task_definition_rejects_invalid_operators_limit(self) -> None:
        base_env = {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }
        invalid_cases = {
            "neg": -1,
            "string": "3",
            "bool": True,
            "float": 1.5,
            "object": {},
            "array": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            for name, limit_value in invalid_cases.items():
                (base_path / f"{name}.env").write_text(
                    json.dumps(
                        {"envDtos": [base_env], "operatorsLimit": limit_value}
                    ),
                    encoding="utf-8",
                )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                for name in invalid_cases:
                    with self.assertRaises(TaskLoadError):
                        load_task_definition(name)

    def test_load_task_definition_rejects_invalid_custom_function_call_count(
        self,
    ) -> None:
        base_env = {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }
        invalid_cases = {
            "neg": -1,
            "string": "3",
            "bool": True,
            "float": 1.5,
            "object": {},
            "array": [],
            "null": None,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            for name, value in invalid_cases.items():
                (base_path / f"uf_{name}.env").write_text(
                    json.dumps(
                        {
                            "envDtos": [base_env],
                            "customFunctionCallCount": value,
                        }
                    ),
                    encoding="utf-8",
                )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                for name in invalid_cases:
                    with self.assertRaises(TaskLoadError):
                        load_task_definition(f"uf_{name}")

    def test_load_task_definition_rejects_invalid_if_limit(self) -> None:
        base_env = {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }
        invalid_cases = {
            "neg": -1,
            "string": "3",
            "bool": True,
            "float": 1.5,
            "object": {},
            "array": [],
            "null": None,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            for name, value in invalid_cases.items():
                (base_path / f"if_{name}.env").write_text(
                    json.dumps({"envDtos": [base_env], "ifLimit": value}),
                    encoding="utf-8",
                )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                for name in invalid_cases:
                    with self.assertRaises(TaskLoadError):
                        load_task_definition(f"if_{name}")

    def test_load_task_definition_rejects_invalid_while_limit(self) -> None:
        base_env = {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }
        invalid_cases = {
            "neg": -1,
            "string": "3",
            "bool": True,
            "float": 1.5,
            "object": {},
            "array": [],
            "null": None,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            for name, value in invalid_cases.items():
                (base_path / f"while_{name}.env").write_text(
                    json.dumps({"envDtos": [base_env], "whileLimit": value}),
                    encoding="utf-8",
                )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                for name in invalid_cases:
                    with self.assertRaises(TaskLoadError):
                        load_task_definition(f"while_{name}")

    def test_load_task_definition_rejects_invalid_keyword_lists(self) -> None:
        invalid_cases = {
            "required_not_string": {"requiredKeywords": ["for"]},
            "banned_not_string": {"bannedKeywords": ["while"]},
            "required_unknown": {"requiredKeywords": "for,not_a_keyword"},
            "banned_unknown": {"bannedKeywords": "while,helper"},
            "required_soft_keyword": {"requiredKeywords": "match"},
            "banned_soft_keyword": {"bannedKeywords": "case"},
            "overlap": {
                "requiredKeywords": "for,def",
                "bannedKeywords": "def,while",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            for name, extra_fields in invalid_cases.items():
                payload = {"envDtos": [self._minimal_env_dto()]}
                payload.update(extra_fields)
                (base_path / f"{name}.env").write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                for name in invalid_cases:
                    with self.assertRaises(TaskLoadError):
                        load_task_definition(name)

    def test_load_task_definition_without_todo_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "minimal.env"
            task_file.write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 1,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 0,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                task = load_task_definition("minimal")

        self.assertEqual(task.todo_text, "")
        self.assertEqual(len(task.envs), 1)
        self.assertIsNone(task.operators_limit)
        self.assertIsNone(task.custom_function_call_count)
        self.assertIsNone(task.if_limit)
        self.assertIsNone(task.while_limit)
        self.assertIsNone(task.required_keywords)
        self.assertIsNone(task.banned_keywords)

    def test_load_task_definition_empty_or_invalid_todo_text_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            (base_path / "empty.env").write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 1,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 0,
                            }
                        ],
                        "todoText": "",
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "bad_type.env").write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 1,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 0,
                            }
                        ],
                        "todoText": 123,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                self.assertEqual(load_task_definition("empty").todo_text, "")
                self.assertEqual(load_task_definition("bad_type").todo_text, "")

    def test_load_task_definition_localized_todo_text_resolves_by_language(self) -> None:
        base_env = self._minimal_env_dto()
        cases: list[tuple[str, str, dict[str, str], str]] = [
            (
                "loc_ru",
                "ru",
                {"en": "Reach the end", "ru": "Дойди до конца"},
                "Дойди до конца",
            ),
            (
                "loc_fallback",
                "ru",
                {"en": "English line", "de": "Deutsch"},
                "English line",
            ),
            (
                "loc_no_en",
                "en",
                {"ru": "Только русский"},
                "",
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            for task_id, _lang, todo, _expected in cases:
                (Path(temp_dir) / f"{task_id}.env").write_text(
                    json.dumps({"envDtos": [base_env], "todoText": todo}),
                    encoding="utf-8",
                )
            for task_id, lang, _todo, expected in cases:
                with self.subTest(task_id=task_id, lang=lang):
                    with patch.dict(
                        "os.environ",
                        {
                            "ROBOT_TASKS_DIR": temp_dir,
                            "ROBOT_LANGUAGE": lang,
                        },
                        clear=False,
                    ):
                        task = load_task_definition(task_id)
                    self.assertEqual(task.todo_text, expected)

    def test_load_task_definition_localized_todo_text_regional_keys(self) -> None:
        base_env = self._minimal_env_dto()
        todo = {"ru_RU.UTF-8": "Из ru_RU", "en-GB": "From en-GB"}
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "loc_reg.env").write_text(
                json.dumps({"envDtos": [base_env], "todoText": todo}),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"ROBOT_TASKS_DIR": temp_dir, "ROBOT_LANGUAGE": "ru"},
                clear=False,
            ):
                task_ru = load_task_definition("loc_reg")
            with patch.dict(
                "os.environ",
                {"ROBOT_TASKS_DIR": temp_dir, "ROBOT_LANGUAGE": "en"},
                clear=False,
            ):
                task_en = load_task_definition("loc_reg")
        self.assertEqual(task_ru.todo_text, "Из ru_RU")
        self.assertEqual(task_en.todo_text, "From en-GB")

    def test_load_task_definition_localized_todo_text_empty_or_invalid_map(self) -> None:
        base_env = self._minimal_env_dto()
        cases = [
            ("loc_empty", {}),
            ("loc_unsup", {"eo": "not supported"}),
            ("loc_bad_vals", {"en": 1, "ru": None}),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            for name, todo in cases:
                (Path(temp_dir) / f"{name}.env").write_text(
                    json.dumps({"envDtos": [base_env], "todoText": todo}),
                    encoding="utf-8",
                )
            with patch.dict(
                "os.environ",
                {"ROBOT_TASKS_DIR": temp_dir, "ROBOT_LANGUAGE": "en"},
                clear=False,
            ):
                for name, _ in cases:
                    with self.subTest(name=name):
                        self.assertEqual(load_task_definition(name).todo_text, "")


if __name__ == "__main__":
    unittest.main()
