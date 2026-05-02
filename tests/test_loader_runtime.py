import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import call, patch

import robot.runtime as runtime
from robot.loader import TaskLoadError, load_task, load_task_definition
from robot.model import RobotEnv, RobotEnvDto
from robot.runtime import run_solution_on_env


class LoaderRuntimeTest(unittest.TestCase):
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
        self.assertIn("printn() accepts only integers", result.message)
        self.assertRegex(result.message, r"^Строка 3: RobotError:")

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


    def test_task_under_global_trace_uses_standard_gui_path(self) -> None:
        """IDE-style sys.settrace must not switch task() to a separate execution branch."""
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
                todo_text="Note",
            )

            fake_main = types.ModuleType("fake_main")
            fake_main.__file__ = str(script)

            def ide_global(frame, event, arg):
                return ide_global

            old_trace = sys.gettrace()
            sys.settrace(ide_global)
            try:
                with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
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
        self.assertEqual(kw["todo_text"], "Note")
        self.assertIsNotNone(kw["run_env"])
        self.assertTrue(callable(kw["run_env"]))

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
