import json
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import call, patch

import robot.runtime as runtime
from robot.loader import TaskLoadError, load_task, load_task_definition
from robot.model import RobotEnv, RobotEnvDto, RobotError, RobotPathError
from robot.runtime import run_solution_on_env


class FakeDebugWindow:
    instances = []

    def __init__(
        self,
        task_id,
        envs,
        run_env,
        initial_index=0,
        debug_mode=False,
        todo_text="",
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.initial_index = initial_index
        self.debug_mode = debug_mode
        self.todo_text = todo_text
        self.shown = False
        self.result = None
        self.robot_error = None
        self.run_until_closed_called = False
        FakeDebugWindow.instances.append(self)

    def show_debug_started(self):
        self.shown = True

    def show_debug_result(self, env_number, result):
        self.result = (env_number, result)

    def show_robot_error(self, message):
        self.robot_error = message

    def run_until_closed(self):
        self.run_until_closed_called = True


@contextmanager
def _installed_debugger_global_trace():
    """Simulate an IDE: tracing only runs if sys.settrace is non-None (local f_trace alone is not enough)."""
    def ide_global(frame, event, arg):
        return ide_global

    old = sys.gettrace()
    sys.settrace(ide_global)
    try:
        yield
    finally:
        sys.settrace(old)


class LoaderRuntimeTest(unittest.TestCase):
    def tearDown(self):
        runtime._clear_debug_session()
        FakeDebugWindow.instances = []

    def test_loader_reads_env_dtos_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "line.json"
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

    def test_load_task_definition_without_todo_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "minimal.json"
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

    def test_load_task_definition_empty_or_invalid_todo_text_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            (base_path / "empty.json").write_text(
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
            (base_path / "bad_type.json").write_text(
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

    def test_loader_rejects_legacy_environments_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "legacy.json"
            task_file.write_text(
                json.dumps(
                    {
                        "environments": [
                            {
                                "width": 2,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with self.assertRaises(TaskLoadError):
                    load_task("legacy")

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

            with patch("robot.runtime.time.sleep") as sleep:
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
        self.assertRegex(result.message, r"^Строка 3: ZeroDivisionError:")

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
        self.assertRegex(
            result.message,
            r"^Строка 3: "
            + re.escape(runtime.ROBOT_PATH_COLLISION_USER_MESSAGE)
            + r"$",
        )

    def test_task_with_environment_number_continues_in_selected_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    },
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    },
                ],
                todo_text="Reach the end",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 2)
                            runtime.move_right()

                        run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertTrue(window.debug_mode)
        self.assertTrue(window.shown)
        self.assertEqual(window.todo_text, "Reach the end")
        self.assertEqual(window.initial_index, 1)
        self.assertEqual(window.envs[0].robot.col, 0)
        self.assertEqual(window.envs[1].robot.col, 1)
        self.assertEqual(window.result[0], 2)
        self.assertTrue(window.result[1].success)
        self.assertTrue(window.run_until_closed_called)

    def test_task_without_environment_number_uses_first_env_under_debugger(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    },
                    {
                        "width": 3,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    },
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug")
                            runtime.move_right()

                        run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertTrue(window.debug_mode)
        self.assertTrue(window.shown)
        self.assertEqual(window.initial_index, 0)
        self.assertEqual(window.envs[0].robot.col, 1)
        self.assertEqual(window.envs[1].robot.col, 0)
        self.assertEqual(window.result[0], 1)
        self.assertTrue(window.result[1].success)
        self.assertTrue(window.run_until_closed_called)

    def test_task_environment_number_must_be_valid_int(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    },
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    },
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    for env_number in ("2", True, 0, 3):
                        with self.subTest(env_number=env_number):
                            with self.assertRaises(RobotError):
                                runtime.task("debug", env_number)

        self.assertEqual(FakeDebugWindow.instances, [])

    def test_robot_path_error_updates_debug_window_and_propagates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 1)
                            runtime.move_right()

                        expected_line = run_solution.__code__.co_firstlineno + 2

                        with self.assertRaises(RobotPathError):
                            run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertEqual(
            window.robot_error,
            f"Строка {expected_line}: {runtime.ROBOT_PATH_COLLISION_USER_MESSAGE}",
        )
        self.assertIsNone(window.result)
        self.assertTrue(window.run_until_closed_called)

    def test_debug_python_runtime_error_shows_message_without_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 1)
                            1 / 0

                        with self.assertRaises(ZeroDivisionError):
                            run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertEqual(window.robot_error, "ZeroDivisionError: division by zero")
        self.assertIsNone(window.result)
        self.assertTrue(window.run_until_closed_called)

    def test_debug_thonny_style_local_tracer_is_chained_for_runtime_errors(self):
        """Simulate Thonny (local f_trace); Robot status must still see ZeroDivisionError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):
                        local_calls = []

                        def fake_thonny_local_trace(frame, event, arg):
                            local_calls.append((event, arg))
                            return fake_thonny_local_trace

                        def run_solution():
                            sys._getframe(0).f_trace = fake_thonny_local_trace
                            runtime.task("debug", 1)
                            1 / 0

                        with self.assertRaises(ZeroDivisionError):
                            run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertEqual(window.robot_error, "ZeroDivisionError: division by zero")
        exception_events = [e for e, _ in local_calls if e == "exception"]
        self.assertGreater(len(exception_events), 0)

    def test_debug_system_exit_shows_code_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_task(
                temp_dir,
                "debug",
                [
                    {
                        "width": 1,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 0,
                    }
                ],
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with _installed_debugger_global_trace():
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 1)
                            raise SystemExit(7)

                        with self.assertRaises(SystemExit) as ctx:
                            run_solution()

        self.assertEqual(ctx.exception.code, 7)
        window = FakeDebugWindow.instances[0]
        self.assertEqual(window.robot_error, "программа завершилась с кодом 7")
        self.assertIsNone(window.result)
        self.assertTrue(window.run_until_closed_called)

    def write_task(self, temp_dir, task_id, env_dtos, todo_text=None):
        task_file = Path(temp_dir) / f"{task_id}.json"
        payload = {"envDtos": env_dtos}
        if todo_text is not None:
            payload["todoText"] = todo_text
        task_file.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
