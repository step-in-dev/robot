import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import robot.runtime as runtime
from robot.loader import load_task
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
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.initial_index = initial_index
        self.debug_mode = debug_mode
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


class LoaderRuntimeTest(unittest.TestCase):
    def tearDown(self):
        runtime._clear_debug_session()
        FakeDebugWindow.instances = []

    def test_loader_reads_web_environment_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "line.json"
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
                envs = load_task("line")

        self.assertEqual(len(envs), 1)
        self.assertEqual(envs[0].width, 2)
        self.assertEqual(envs[0].final_col, 1)

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
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                with patch("robot.runtime.sys.gettrace", return_value=lambda *_: None):
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 2)
                            runtime.move_right()

                        run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertTrue(window.debug_mode)
        self.assertTrue(window.shown)
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
                with patch("robot.runtime.sys.gettrace", return_value=lambda *_: None):
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
                with patch("robot.runtime.sys.gettrace", return_value=lambda *_: None):
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
                with patch("robot.runtime.sys.gettrace", return_value=lambda *_: None):
                    with patch("robot.gui.RobotWindow", FakeDebugWindow):

                        def run_solution():
                            runtime.task("debug", 1)
                            runtime.move_right()

                        with self.assertRaises(RobotPathError):
                            run_solution()

        window = FakeDebugWindow.instances[0]
        self.assertEqual(
            window.robot_error,
            "робот уперся в стену или границу поля",
        )
        self.assertIsNone(window.result)
        self.assertTrue(window.run_until_closed_called)

    def write_task(self, temp_dir, task_id, environments):
        task_file = Path(temp_dir) / f"{task_id}.json"
        task_file.write_text(
            json.dumps({"environments": environments}),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
