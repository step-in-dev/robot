"""Tests for ``StepExecutionSession`` (single exec with trace-based stepping).

``StepExecutionSession`` does not read the task ``.env`` file: ``StepExecutionTarget.task_id``
is only stored for solution-run bookkeeping. Static script constraints
from the task definition are enforced elsewhere (GUI). Tests using
``task_id="noop"`` therefore succeed even when the script would violate limits
on a real constrained task.
"""

from typing import List, Tuple


import queue
import re
import tempfile
import threading
import unittest
from pathlib import Path

from robot.executor import (
    EXECUTION_CANCELLED_MESSAGE,
    StepExecutionCallbacks,
    StepExecutionSession,
    StepExecutionTarget,
)
from robot.i18n import t
from tests.env_fixtures import cell_1x1, corridor, env_dict, make_env

from ._helpers import NOOP_STEP_CALLBACKS, LoaderRuntimeTestBase


class StepExecutionSessionTest(LoaderRuntimeTestBase):
    def test_step_session_second_move_right_hits_wall_then_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "two_moves.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertEqual(result.status, "crashed")
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_noop_task_does_not_block_plain_move_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "plain_move.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_noop_task_does_not_block_for_loop_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "forbidden_for.py"
            script.write_text(
                "from robot import move_right\n"
                "for _ in range(1):\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_noop_task_does_not_block_two_ifs_success(self) -> None:
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
            env = make_env(env_dict(3, 1, final_col=2))
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 2))

    def test_step_session_noop_task_does_not_block_two_whiles_success(self) -> None:
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
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_step_session_noop_task_does_not_block_single_move_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "one_move.py"
            script.write_text(
                "from robot import move_right\n"
                "move_right()\n",
                encoding="utf-8",
            )
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
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
            env = make_env(corridor())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=NOOP_STEP_CALLBACKS,
                command_delay_seconds=0.0,
            )
            result = session.start()

        self.assertEqual(result.status, "error")
        self.assertIn("SyntaxError", result.message)
        head = t("line.with_message", lineno=1, message="")
        self.assertRegex(result.message, "^" + re.escape(head) + r"SyntaxError:")

    def test_step_session_runs_assignments_line_by_line(self) -> None:
        """Each student-file line waits until allow_one_step + handshake release."""
        sync: queue.Queue[object] = queue.Queue()
        captured: List[Tuple[int, str]] = []

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
            env = make_env(cell_1x1())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=show_line,
                    wait_for_next_step=wait_next,
                ),
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
        captured: List[Tuple[int, str]] = []

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
            env = make_env(cell_1x1())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=show_line,
                    wait_for_next_step=wait_next,
                ),
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
            env = make_env(cell_1x1())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=lambda _line: None,
                    wait_for_next_step=wait_next,
                ),
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
            env = make_env(cell_1x1())
            session = StepExecutionSession(
                StepExecutionTarget(script, "noop"),
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=lambda _line: None,
                    wait_for_next_step=wait_next,
                ),
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


if __name__ == "__main__":
    unittest.main()
