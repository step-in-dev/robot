"""Tests for ``run_solution_on_env`` (batch exec of student script).

``run_solution_on_env`` compiles and ``exec``s the script, then checks final
robot state. It does **not** call ``check_limit_violations``; limit checks run
in the GUI after a successful ``run_env`` / step session (see
``tests/gui/``). Regression: ``test_run_solution_on_env_does_not_call_check_limit_violations``.
"""


import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from robot import runtime
from robot.executor import (
    EXECUTION_CANCELLED_MESSAGE,
    RunExecutionCallbacks,
    StudentSolution,
    run_solution_on_env,
)
from robot.i18n import t
from tests.env_fixtures import cell_1x1, corridor, make_env

from ._helpers import INFINITE_LOOP_SCRIPT, LoaderRuntimeTestBase


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
            env = make_env(corridor(width=4))

            result = run_solution_on_env(StudentSolution(script, "while1"), env)

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
            env = make_env(
                corridor(
                    cellsToPaint=[{"r": 0, "c": 1}],
                    cellsToPrint=[{"r": 0, "c": 1, "value": 7}],
                )
            )

            with patch("robot.commands.time.sleep") as sleep:
                result = run_solution_on_env(
                    StudentSolution(script, "delay"),
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
            env = make_env(corridor())

            result = run_solution_on_env(StudentSolution(script, "while1"), env)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "wrong")

    def test_run_solution_on_env_does_not_call_check_limit_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import move_right\nmove_right()\n",
                encoding="utf-8",
            )
            env = make_env(corridor())
            with patch("robot.executor.check_limit_violations") as mock_check:
                result = run_solution_on_env(StudentSolution(script, "noop"), env)
            mock_check.assert_not_called()

        self.assertTrue(result.success)

    def test_run_solution_on_env_can_cancel_infinite_loop_via_callback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(INFINITE_LOOP_SCRIPT, encoding="utf-8")
            env = make_env(cell_1x1())
            poll_calls = 0

            def poll_events() -> None:
                nonlocal poll_calls
                poll_calls += 1

            with patch("robot.executor.RUN_EVENT_POLL_INTERVAL_SECONDS", 0.0):
                result = run_solution_on_env(
                    StudentSolution(script, "cancelled"),
                    env,
                    callbacks=RunExecutionCallbacks(
                        should_cancel=lambda: poll_calls >= 3,
                        poll_events=poll_events,
                    ),
                )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.message, EXECUTION_CANCELLED_MESSAGE)
        self.assertGreaterEqual(poll_calls, 3)
        self.assertTrue(env.robot.is_cell_painted())

    def test_runtime_error_message_includes_student_line_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('divtask')\n"
                "1/0\n",
                encoding="utf-8",
            )
            env = make_env(corridor())

            result = run_solution_on_env(StudentSolution(script, "divtask"), env)

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
            env = make_env(cell_1x1())

            result = run_solution_on_env(StudentSolution(script, "printntest"), env)

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
            env = make_env(cell_1x1())

            result = run_solution_on_env(StudentSolution(script, "walltask"), env)

        self.assertEqual(result.status, "crashed")
        expected = t(
            "line.with_message",
            lineno=3,
            message=str(runtime.ROBOT_PATH_COLLISION_USER_MESSAGE),
        )
        self.assertEqual(result.message, expected)


if __name__ == "__main__":
    unittest.main()
