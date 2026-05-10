"""Tests for ``run_solution_on_env`` (batch exec of student script).

``run_solution_on_env`` compiles and ``exec``s the script, then checks final
robot state. It does **not** call ``check_limit_violations``; limit checks run
in the GUI after a successful ``run_env`` / step session (see
``tests/test_gui.py``). Regression: ``test_run_solution_on_env_does_not_call_check_limit_violations``.
"""

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import robot.runtime as runtime
from robot.executor import run_solution_on_env
from robot.i18n import t
from robot.model import RobotEnv, RobotEnvDto

from ._helpers import LoaderRuntimeTestBase


class RunSolutionOnEnvTest(LoaderRuntimeTestBase):
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

    def test_run_solution_on_env_does_not_call_check_limit_violations(self) -> None:
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
            with patch("robot.executor.check_limit_violations") as mock_check:
                result = run_solution_on_env(script, "noop", env)
            mock_check.assert_not_called()

        self.assertTrue(result.success)

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


if __name__ == "__main__":
    unittest.main()
