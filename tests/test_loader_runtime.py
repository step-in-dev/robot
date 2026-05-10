import contextlib
import json
import queue
import re
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import call, patch

import robot.runtime as runtime
from robot.executor import (
    EXECUTION_CANCELLED_MESSAGE,
    StepExecutionSession,
    run_solution_on_env,
)
from robot.i18n import clear_translation_cache, t
from robot.loader import TaskLoadError, load_task, load_task_definition
from robot.model import RobotEnv, RobotEnvDto, RobotError
from robot.operator_limits import (
    BANNED_KEYWORDS_MESSAGE_TEMPLATE,
    CUSTOM_FUNCTION_CALL_COUNT_MESSAGE_TEMPLATE,
    IF_LIMIT_MESSAGE_TEMPLATE,
    OPERATORS_LIMIT_MESSAGE_TEMPLATE,
    REQUIRED_KEYWORDS_MESSAGE_TEMPLATE,
    WHILE_LIMIT_MESSAGE_TEMPLATE,
)


class LoaderRuntimeTest(unittest.TestCase):
    @staticmethod
    def _minimal_env_dto() -> dict[str, int]:
        """Single-cell environment used by several loader tests."""
        return {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }

    @staticmethod
    def _make_capture_robot_window_cls(captured: list) -> type:
        class CaptureRobotWindow:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            def run(self) -> None:
                pass  # Skip Tk mainloop in unit tests

        return CaptureRobotWindow

    @staticmethod
    @contextlib.contextmanager
    def _patched_main_as_script(script: Path):
        fake_main = types.ModuleType("fake_main")
        fake_main.__file__ = str(script)
        with patch.dict(sys.modules, {"__main__": fake_main}):
            yield

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

    def test_runtime_executes_student_file_in_clean_robot_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('while1')\n"
                "while is_free_right():\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 4,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 3,
                    }
                )
            )

            result = run_solution_on_env(script, "while1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 3))

    def test_runtime_delays_only_mutating_commands_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('delay')\n"
                "is_free_right()\n"
                "pol()\n"
                "move_right()\n"
                "paint()\n"
                "printn(7)\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                        "cellsToPaint": [{"r": 0, "c": 1}],
                        "cellsToPrint": [{"r": 0, "c": 1, "value": 7}],
                    }
                )
            )

            with patch("robot.commands.time.sleep") as sleep:
                result = run_solution_on_env(
                    script,
                    "delay",
                    env,
                    command_delay_seconds=0.05,
                )

        self.assertTrue(result.success)
        self.assertEqual(
            sleep.call_args_list,
            [call(0.05), call(0.05), call(0.05)],
        )

    def test_runtime_reports_wrong_solution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('while1')\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "while1", env)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "wrong")

    def test_runtime_operators_limit_exceeded_runs_then_returns_wrong_by_final_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('lim')\n"
                "move_right()\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 4,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 3,
                    }
                )
            )

            result = run_solution_on_env(script, "lim", env)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "wrong")
        self.assertEqual(result.message, "")
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_runtime_operators_limit_allows_single_written_operator_in_loop(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('looplim')\n"
                "for _ in range(3):\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 4,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 3,
                    }
                )
            )

            result = run_solution_on_env(script, "looplim", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 3))

    def test_runtime_custom_function_call_count_exceeded_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "uf1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_custom_function_call_count_empty_function_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "def helper():\n"
                "    x = 1\n"
                "\n"
                "helper()\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "uf1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_custom_function_call_count_allows_defined_and_called_function(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n\n"
                "def step():\n"
                "    move_right()\n"
                "\n"
                "step()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "uf1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_custom_function_call_count_requires_two_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n\n"
                "def step():\n"
                "    move_right()\n"
                "\n"
                "step()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "uf2", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_custom_function_call_count_allows_two_calls_to_same_function(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n\n"
                "def step():\n"
                "    move_right()\n"
                "\n"
                "step()\n"
                "step()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 2,
                    }
                )
            )

            result = run_solution_on_env(script, "uf2", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_runtime_custom_function_call_count_none_allows_plain_solution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\nmove_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "uf1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_required_keywords_missing_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "kw_required", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_banned_keywords_used_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "for _ in range(1):\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "kw_banned", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_if_limit_exceeded_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "if True:\n"
                "    move_right()\n"
                "if True:\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 2,
                    }
                )
            )

            result = run_solution_on_env(script, "iflim", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_runtime_if_limit_counts_ternary_expression_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "a = 1 if True else 0\n"
                "b = 2 if False else 3\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "iftern", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_runtime_if_limit_allows_single_if(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "if True:\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "ifok", env)

        self.assertTrue(result.success)

    def test_runtime_while_limit_exceeded_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\n"
                "n = 2\n"
                "while n:\n"
                "    move_right()\n"
                "    n -= 1\n"
                "while False:\n"
                "    pass\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 2,
                    }
                )
            )

            result = run_solution_on_env(script, "wlim", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_step_session_operators_limit_exceeded_runs_then_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "two_moves.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertEqual(result.status, "crashed")
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_required_keywords_missing_runs_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "plain_move.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_banned_keywords_used_runs_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "forbidden_for.py"
            script.write_text(
                "from robot import move_right\n"
                "for _ in range(1):\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_if_limit_exceeded_runs_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "two_ifs.py"
            script.write_text(
                "from robot import move_right\n"
                "if True:\n"
                "    move_right()\n"
                "if True:\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 2,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_step_session_while_limit_exceeded_runs_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "two_whiles.py"
            script.write_text(
                "from robot import move_right\n"
                "n = 1\n"
                "while n:\n"
                "    move_right()\n"
                "    n -= 1\n"
                "while False:\n"
                "    pass\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_custom_function_call_count_exceeded_runs_then_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "one_move.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_syntax_error_maps_to_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "bad_syntax.py"
            script.write_text(
                "if True\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=lambda: None,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertEqual(result.status, "error")
        self.assertIn("SyntaxError", result.message)
        head = t("line.with_message", lineno=1, message="")
        self.assertRegex(result.message, "^" + re.escape(head) + r"SyntaxError:")

    def test_runtime_error_message_includes_student_line_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('divtask')\n"
                "1/0\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "divtask", env)

        self.assertEqual(result.status, "error")
        self.assertIn("ZeroDivisionError", result.message)
        head = t("line.with_message", lineno=3, message="")
        self.assertRegex(result.message, "^" + re.escape(head) + r"ZeroDivisionError:")

    def test_runtime_printn_rejects_non_integer_with_line_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('printntest')\n"
                "printn(1.2)\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )

            result = run_solution_on_env(script, "printntest", env)

        self.assertEqual(result.status, "error")
        self.assertIn("RobotError", result.message)
        self.assertIn(t("model.error.printn_integers"), result.message)
        head = t("line.with_message", lineno=3, message="")
        self.assertRegex(result.message, "^" + re.escape(head) + r"RobotError:")

    def test_runtime_robot_path_collision_message_includes_student_line_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('walltask')\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )

            result = run_solution_on_env(script, "walltask", env)

        self.assertEqual(result.status, "crashed")
        expected = t(
            "line.with_message",
            lineno=3,
            message=str(runtime.ROBOT_PATH_COLLISION_USER_MESSAGE),
        )
        self.assertEqual(result.message, expected)

    def test_step_session_runs_assignments_line_by_line(self) -> None:
        """Each student-file line waits until allow_one_step + handshake release."""
        sync: queue.Queue[object] = queue.Queue()
        captured: list[tuple[int, str]] = []

        def show_line(line) -> None:
            captured.append((line.lineno, line.text))

        def wait_next() -> None:
            sync.put("wait")
            sync.get(timeout=5)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "step_assign.py"
            script.write_text(
                "a = 0\n"
                "a = 1\n"
                "a = 2\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=show_line,
                wait_for_next_step=wait_next,
                command_delay_seconds=0.0,
            )
            result_holder: list = []

            def runner() -> None:
                result_holder.append(session.start())

            session.allow_one_step()
            thread = threading.Thread(target=runner)
            thread.start()
            while thread.is_alive():
                try:
                    sync.get(timeout=0.5)
                except queue.Empty:
                    continue
                session.allow_one_step()
                sync.put(1)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(result_holder), 1)
            result = result_holder[0]
            self.assertTrue(result.success)
            self.assertEqual(session.namespace.get("a"), 2)
            self.assertEqual(
                captured,
                [
                    (1, "a = 0"),
                    (2, "a = 1"),
                    (3, "a = 2"),
                ],
            )

    def test_step_session_enters_student_function_body(self) -> None:
        sync: queue.Queue[object] = queue.Queue()
        captured: list[tuple[int, str]] = []

        def show_line(line) -> None:
            captured.append((line.lineno, line.text))

        def wait_next() -> None:
            sync.put("wait")
            sync.get(timeout=5)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "step_fn.py"
            script.write_text(
                "def go():\n"
                "    return 7\n"
                "y = go()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=show_line,
                wait_for_next_step=wait_next,
                command_delay_seconds=0.0,
            )
            result_holder: list = []

            def runner() -> None:
                result_holder.append(session.start())

            session.allow_one_step()
            thread = threading.Thread(target=runner)
            thread.start()
            while thread.is_alive():
                try:
                    sync.get(timeout=0.5)
                except queue.Empty:
                    continue
                session.allow_one_step()
                sync.put(1)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertTrue(result_holder[0].success)
            self.assertEqual(session.namespace.get("y"), 7)
            self.assertIn((1, "def go():"), captured)
            self.assertIn((2, "return 7"), captured)
            self.assertIn((3, "y = go()"), captured)

    def test_step_session_cancel_during_wait(self) -> None:
        sync: queue.Queue[object] = queue.Queue()
        blocked = threading.Event()

        def wait_next() -> None:
            blocked.set()
            sync.get(timeout=5)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "step_slow.py"
            script.write_text(
                "a = 1\n"
                "a = 2\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=wait_next,
                command_delay_seconds=0.0,
            )
            result_holder: list = []

            def runner() -> None:
                result_holder.append(session.start())

            session.allow_one_step()
            thread = threading.Thread(target=runner)
            thread.start()
            self.assertTrue(blocked.wait(timeout=5))
            session.cancel()
            sync.put(1)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(result_holder), 1)
            result = result_holder[0]
            self.assertEqual(result.status, "error")
            self.assertEqual(result.message, EXECUTION_CANCELLED_MESSAGE)

    def test_step_session_runtime_error_includes_line(self) -> None:
        sync: queue.Queue[object] = queue.Queue()

        def wait_next() -> None:
            sync.put("wait")
            sync.get(timeout=5)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "step_err.py"
            script.write_text(
                "a = 1\n"
                "1 / 0\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                )
            )
            session = StepExecutionSession(
                script,
                "noop",
                env,
                show_line=lambda _line: None,
                wait_for_next_step=wait_next,
                command_delay_seconds=0.0,
            )
            result_holder: list = []

            def runner() -> None:
                result_holder.append(session.start())

            session.allow_one_step()
            thread = threading.Thread(target=runner)
            thread.start()
            while thread.is_alive():
                try:
                    sync.get(timeout=0.5)
                except queue.Empty:
                    continue
                session.allow_one_step()
                sync.put(1)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            result = result_holder[0]
            self.assertEqual(result.status, "error")
            head = t("line.with_message", lineno=2, message="")
            self.assertRegex(
                result.message, "^" + re.escape(head) + r"ZeroDivisionError:"
            )

    def test_task_under_global_trace_uses_standard_gui_path(self) -> None:
        """IDE trace must not switch task(); localized todoText resolves before RobotWindow."""
        captured: list[dict[str, object]] = []

        class CaptureRobotWindow:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            def run(self) -> None:
                """Skip Tk mainloop while exercising task() wiring."""
                pass

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "student.py"
            script.write_text("# student\n", encoding="utf-8")
            self.write_task(
                temp_dir,
                "trace_task",
                [self._minimal_env_dto()],
                todo_text={"en": "Note", "ru": "Записка"},
                operators_limit=42,
                custom_function_call_count=7,
                if_limit=3,
                while_limit=0,
                required_keywords="for,def",
                banned_keywords="while",
            )

            fake_main = types.ModuleType("fake_main")
            fake_main.__file__ = str(script)

            def ide_global(frame, event, arg):
                return ide_global

            old_trace = sys.gettrace()
            sys.settrace(ide_global)
            try:
                with patch.dict(
                    "os.environ",
                    {"ROBOT_TASKS_DIR": temp_dir, "ROBOT_LANGUAGE": "ru"},
                    clear=False,
                ):
                    with patch.dict(sys.modules, {"__main__": fake_main}):
                        with patch("robot.gui.RobotWindow", CaptureRobotWindow):
                            with self.assertRaises(SystemExit) as ctx:
                                runtime.task("trace_task")
            finally:
                sys.settrace(old_trace)

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(captured), 1)
        kw = captured[0]
        self.assertEqual(kw["task_id"], "trace_task")
        self.assertEqual(kw["todo_text"], "Записка")
        self.assertEqual(kw["operators_limit"], 42)
        self.assertEqual(kw["custom_function_call_count"], 7)
        self.assertEqual(kw["if_limit"], 3)
        self.assertEqual(kw["while_limit"], 0)
        self.assertEqual(kw["required_keywords"], ("def", "for"))
        self.assertEqual(kw["banned_keywords"], ("while",))
        self.assertIsNotNone(kw["run_env"])
        self.assertTrue(callable(kw["run_env"]))
        self.assertEqual(kw["script_path"], Path(script).resolve())

    def test_field_wires_robot_window_and_sys_exit(self) -> None:
        captured: list[dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "student_field.py"
            script.write_text("# student field\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit) as ctx:
                    runtime.field(7, 5)

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(captured), 1)
        kw = captured[0]
        self.assertEqual(kw["task_id"], "field(7, 5)")
        self.assertEqual(kw["todo_text"], "")
        self.assertIsNone(kw["operators_limit"])
        self.assertIsNone(kw["custom_function_call_count"])
        self.assertIsNone(kw["if_limit"])
        self.assertIsNone(kw["while_limit"])
        self.assertIsNone(kw["required_keywords"])
        self.assertIsNone(kw["banned_keywords"])
        envs = kw["envs"]
        self.assertEqual(len(envs), 1)
        env = envs[0]
        self.assertEqual(env.width, 7)
        self.assertEqual(env.height, 5)
        self.assertEqual(env.start_row, 0)
        self.assertEqual(env.start_col, 0)
        self.assertEqual(env.final_row, 4)
        self.assertEqual(env.final_col, 6)
        self.assertEqual(kw["script_path"], Path(script).resolve())

    def test_field_defaults_eight_by_six(self) -> None:
        captured: list[dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "def_field.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field()

        env = captured[0]["envs"][0]
        self.assertEqual(env.width, 8)
        self.assertEqual(env.height, 6)

    def test_field_positional_width_only(self) -> None:
        captured: list[dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "w10.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field(10)

        env = captured[0]["envs"][0]
        self.assertEqual(env.width, 10)
        self.assertEqual(env.height, 6)

    def test_field_keyword_height_only(self) -> None:
        captured: list[dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "h7.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field(height=7)

        env = captured[0]["envs"][0]
        self.assertEqual(env.width, 8)
        self.assertEqual(env.height, 7)

    def test_field_rejects_non_integers(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "bad.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        getattr(runtime, "field")(1.5, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_integers"))

    def test_field_rejects_width_out_of_range(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badw.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(0, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_width_range"))
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badw2.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(21, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_width_range"))

    def test_field_rejects_height_out_of_range(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badh.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(8, 0)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_height_range"))
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badh2.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(8, 16)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_height_range"))

    def test_field_noop_during_solution_run(self) -> None:
        one = RobotEnv(
            RobotEnvDto.from_dict(
                {
                    "width": 1,
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 0,
                }
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "sol.py"
            script.write_text(
                "from robot import field\n"
                "field(9, 9)\n",
                encoding="utf-8",
            )
            result = run_solution_on_env(
                script,
                "dummy_task",
                one,
                command_delay_seconds=0.0,
            )
        self.assertEqual(result.status, "success")

    def test_field_validates_before_noop_in_solution_run(self) -> None:
        one = RobotEnv(
            RobotEnvDto.from_dict(
                {
                    "width": 1,
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 0,
                }
            )
        )
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "bad_sol.py"
                script.write_text(
                    "from robot import field\n"
                    "field(2.0, 3)\n",
                    encoding="utf-8",
                )
                result = run_solution_on_env(
                    script,
                    "dummy_task",
                    one,
                    command_delay_seconds=0.0,
                )
        self.assertEqual(result.status, "error")
        self.assertIn(t("runtime.error.field_integers"), result.message)

    def write_task(
        self,
        temp_dir,
        task_id,
        env_dtos,
        todo_text=None,
        operators_limit=None,
        custom_function_call_count=None,
        if_limit=None,
        while_limit=None,
        required_keywords=None,
        banned_keywords=None,
    ):
        task_file = Path(temp_dir) / f"{task_id}.env"
        payload = {"envDtos": env_dtos}
        if todo_text is not None:
            payload["todoText"] = todo_text
        if operators_limit is not None:
            payload["operatorsLimit"] = operators_limit
        if custom_function_call_count is not None:
            payload["customFunctionCallCount"] = custom_function_call_count
        if if_limit is not None:
            payload["ifLimit"] = if_limit
        if while_limit is not None:
            payload["whileLimit"] = while_limit
        if required_keywords is not None:
            payload["requiredKeywords"] = required_keywords
        if banned_keywords is not None:
            payload["bannedKeywords"] = banned_keywords
        task_file.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
