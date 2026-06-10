"""Tests for RobotWindow Step button and step execution."""

import tempfile
import unittest
from pathlib import Path

import tkinter as tk

from robot.executor import StudentLine
from robot.gui import RobotWindowOptions
from robot.model import RobotEnv
from robot.gui_theme import (
    ACTION_BUTTON_HELP,
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_STOP,
    ACTION_BUTTON_STEP,
    STATUS_BG_SUCCESS,
)
from robot.i18n import t
from robot.results import RunResult

from ._helpers import (
    GuiTestCase,
    cell_1x1,
    corridor,
    make_env,
    make_test_window,
    requires_tk_display,
    test_window,
)

@requires_tk_display
class RobotWindowStepButtonTest(GuiTestCase):
    def test_step_button_is_right_of_run_with_script_path(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "sol.py"
            script.write_text("#\n", encoding="utf-8")
            with test_window(
                "step_layout",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            ) as window:
                left_slaves = list(window.controls_left.pack_slaves())
                self.assertEqual(left_slaves[0], window.action_button)
                self.assertEqual(left_slaves[1], window.step_button)
                self.assertIs(window.help_button.master, window.controls_right)
                self.assertIn(window.help_button, window.controls_right.pack_slaves())
                self.assertEqual(window.step_button.cget("text"), ACTION_BUTTON_STEP)
                self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
                self.assertEqual(window.help_button.cget("text"), ACTION_BUTTON_HELP)
                self.assertEqual(window.help_button.cget("state"), tk.NORMAL)

    def test_step_button_disabled_without_script_path(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("no_script", envs, run_env) as window:
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
            self.assertEqual(window.help_button.cget("state"), tk.NORMAL)

    def test_enter_does_not_invoke_step_button(self) -> None:
        envs = [make_env(corridor())]
        step_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s2.py"
            script.write_text("#\n", encoding="utf-8")
            window = make_test_window(
                "enter_no_step",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:

                def count_step() -> None:
                    nonlocal step_calls
                    step_calls += 1

                window.step_button.configure(command=count_step)
                window.canvas.focus_set()
                window.canvas.event_generate("<Return>", when="tail")
                window.root.update()
                self.assertEqual(step_calls, 0)
            finally:
                window.close()

    def test_run_all_shows_stop_button_while_running(self) -> None:
        envs = [make_env(cell_1x1())]

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s3.py"
            script.write_text("#\n", encoding="utf-8")
            with test_window(
                "run_disables_step",
                envs,
                None,
                options=RobotWindowOptions(script_path=script),
            ) as window:

                def run_env(_env: RobotEnv) -> RunResult:
                    self.assertNotIn(window.step_button, window.controls_left.pack_slaves())
                    self.assertIn(window.stop_button, window.controls_left.pack_slaves())
                    self.assertEqual(window.stop_button.cget("text"), ACTION_BUTTON_STOP)
                    self.assertEqual(window.stop_button.cget("state"), tk.NORMAL)
                    self.assertEqual(
                        window.action_button.cget("text"), ACTION_BUTTON_RESTORE
                    )
                    self.assertEqual(
                        window.action_button.cget("state"), tk.DISABLED
                    )
                    return RunResult(status="success", message="ok")

                window.run_env = run_env
                window.run_all()
                self.assertNotIn(
                    window.step_button,
                    window.controls_left.pack_slaves(),
                    "Step button must be hidden after run_all completes",
                )
                self.assertNotIn(window.stop_button, window.controls_left.pack_slaves())
                self.assertIn(window.help_button, window.controls_right.pack_slaves())
                self.assertEqual(window.help_button.cget("state"), tk.NORMAL)

    def test_restore_re_enables_step_with_script_path(self) -> None:
        envs = [make_env(corridor())]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s4.py"
            script.write_text("#\n", encoding="utf-8")
            window = make_test_window(
                "restore_step",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:
                window.run_all()
                self.assertNotIn(window.step_button, window.controls_left.pack_slaves())
                window.step_button.configure(state=tk.DISABLED)
                window.restore()
                self.assertIn(window.step_button, window.controls_left.pack_slaves())
                self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
                self.assertEqual(
                    list(window.controls_left.pack_slaves()),
                    [window.action_button, window.step_button],
                )
                self.assertIs(window.help_button.master, window.controls_right)
                self.assertIn(window.help_button, window.controls_right.pack_slaves())
                self.assertEqual(
                    set(window.controls.pack_slaves()),
                    {window.controls_left, window.controls_right},
                )
            finally:
                window.close()

    def test_run_all_hides_step_without_script_restore_shows_disabled(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("hide_step_no_script", envs, run_env) as window:
            window.run_all()
            self.assertNotIn(window.step_button, window.controls_left.pack_slaves())
            window.restore()
            self.assertIn(window.step_button, window.controls_left.pack_slaves())
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)

    def test_show_step_line_status_format(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s5.py"
            script.write_text("#\n", encoding="utf-8")
            window = make_test_window(
                "step_status_fmt",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:
                window._show_step_line(StudentLine(2, "move_right()"))
                self.assertEqual(
                    window.status_var.get(),
                    t("step.line", lineno=2, text="move_right()"),
                )
            finally:
                window.close()

    def test_successful_step_shows_hatched_status(self) -> None:
        """Step-by-step success uses hatched green status (unlike run_all)."""
        base = corridor()
        envs = [make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "step_ok.py"
            script.write_text(
                "from robot import move_right; move_right()\n",
                encoding="utf-8",
            )
            window = make_test_window(
                "step_hatch",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:
                window.step_once()
                self.assertEqual(
                    window.status_var.get(),
                    t("step.success_for_env", env_label=1),
                )
                self.assertEqual(window._status_background, STATUS_BG_SUCCESS)
                self.assertTrue(window._status_hatched)
                self.assertNotIn(
                    window.step_button,
                    window.controls_left.pack_slaves(),
                )
            finally:
                window.close()

    def test_first_step_shows_restore_enabled_and_keeps_step_visible(self) -> None:
        """After starting step debug, Restore is active while waiting for the next line."""
        base = corridor()
        envs = [make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "two_lines.py"
            script.write_text(
                "from robot import move_right\nmove_right()\n",
                encoding="utf-8",
            )
            window = make_test_window(
                "step_restore_visible",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:

                def wait_assert_then_unblock() -> None:
                    btn = window.action_button
                    self.assertIsNotNone(btn)
                    self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
                    self.assertEqual(btn.cget("state"), tk.NORMAL)
                    self.assertIn(window.step_button, window.controls_left.pack_slaves())
                    self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
                    self.assertIsNotNone(window._step_session)
                    window._step_session.allow_one_step()
                    window._step_release_token += 1

                window._wait_for_next_step_impl = wait_assert_then_unblock
                window.step_once()
            finally:
                window.close()

    def test_restore_during_step_wait_resets_field(self) -> None:
        """Restore while paused between steps cancels stepping and resets the grid."""
        base = corridor()
        envs = [make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "step_then_move.py"
            script.write_text(
                "from robot import move_right\nmove_right()\n",
                encoding="utf-8",
            )
            window = make_test_window(
                "restore_mid_step",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
            )
            try:
                saved_wait = window._wait_for_next_step_impl

                def wait_schedule_restore() -> None:
                    window.root.after(0, window.restore)
                    saved_wait()

                window._wait_for_next_step_impl = wait_schedule_restore
                window.step_once()
                self.assertIsNone(window._step_session)
                self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RUN)
                self.assertIn(window.step_button, window.controls_left.pack_slaves())
                self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
                self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 0))
            finally:
                window.close()

    def test_close_during_step_wait_does_not_raise_tcl_error(self) -> None:
        """Closing while waiting for the next step must not configure destroyed widgets."""
        base = cell_1x1()
        envs = [make_env(dict(base)), make_env(dict(base))]

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "multi_line.py"
            script.write_text("a = 1\nb = 2\n", encoding="utf-8")
            window = make_test_window(
                "close_during_step",
                envs,
                None,
                options=RobotWindowOptions(script_path=script),
            )
            try:

                def close_window() -> None:
                    window.close()

                window._wait_for_next_step_impl = close_window
                window.step_once()
                self.assertTrue(window.is_closed)
                self.assertIsNone(window._step_session)
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
