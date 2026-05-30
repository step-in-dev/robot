"""Tests for RobotWindow Run/Restore action button behavior."""

import unittest
from unittest.mock import call, patch

import tkinter as tk

from robot.gui import INTER_ENV_PAUSE_SECONDS, RobotWindowOptions
from robot.model import RobotEnv
from robot.gui_theme import (
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
)
from robot.results import RunResult

from ._helpers import (
    GuiTestCase,
    cell_1x1,
    corridor,
    make_env,
    make_test_window,
    minimal_env_dict,
    requires_tk_display,
    test_window,
)

@requires_tk_display
class RobotWindowActionButtonTest(GuiTestCase):
    def test_run_then_restore_button_and_first_env(self) -> None:
        base = corridor()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = make_test_window(
            "test_task",
            envs,
            run_env,
            options=RobotWindowOptions(initial_index=1),
        )
        try:
            self.assertIsNotNone(window.action_button)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RUN)

            window.run_all()
            self.assertEqual(window.selected_index, 1)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertNotIn(window.step_button, window.controls_left.pack_slaves())
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            self.assertEqual((envs[1].robot.row, envs[1].robot.col), (0, 1))

            window.restore()
            self.assertEqual(window.selected_index, 0)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RUN)
            self.assertIn(window.step_button, window.controls_left.pack_slaves())
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
            for env in envs:
                self.assertEqual((env.robot.row, env.robot.col), (0, 0))
        finally:
            window.close()

    def test_run_all_pauses_before_second_env_when_first_succeeds(self) -> None:
        base = corridor()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("pause_between_envs", envs, run_env) as window:
            with patch("robot.gui.time.sleep") as sleep_mock:
                window.run_all()
            self.assertEqual(
                sleep_mock.call_args_list,
                [call(INTER_ENV_PAUSE_SECONDS)],
            )

    def test_run_all_no_inter_env_sleep_for_single_env(self) -> None:
        envs = [make_env(corridor())]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("single_env_no_pause", envs, run_env) as window:
            with patch("robot.gui.time.sleep") as sleep_mock:
                window.run_all()
            sleep_mock.assert_not_called()

    def test_run_all_no_pause_after_failed_first_env(self) -> None:
        base = corridor()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message="wrong")

        with test_window("fail_first_no_pause", envs, run_env) as window:
            with patch("robot.gui.time.sleep") as sleep_mock:
                window.run_all()
            sleep_mock.assert_not_called()

    def test_failed_run_still_shows_restore(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message="wrong")

        with test_window("test_task2", envs, run_env) as window:
            self.assertIsNotNone(window.action_button)
            window.run_all()
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertNotIn(window.step_button, window.controls_left.pack_slaves())

    def test_run_all_shows_restore_disabled_while_running(self) -> None:
        """Restore label appears immediately; disabled Restore ignores invokes during run."""
        envs = [make_env(corridor())]

        window = make_test_window("restore_while_run", envs, None)
        try:
            btn = window.action_button
            self.assertIsNotNone(btn)

            def run_env(env: RobotEnv) -> RunResult:
                self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
                self.assertEqual(btn.cget("state"), tk.DISABLED)
                idx_before = window.selected_index
                btn.invoke()
                window.root.update()
                self.assertEqual(
                    window.selected_index,
                    idx_before,
                    "Disabled Restore must not reset env selection mid-run",
                )
                env.robot.move_right()
                return RunResult(status="success", message="ok")

            window.run_env = run_env
            window.run_all()
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            window.root.update()
            self.assertEqual(btn.cget("state"), tk.NORMAL)
        finally:
            window.close()

    def test_queued_invokes_during_run_do_not_restore_then_rerun(self) -> None:
        """Queued button invokes while disabled must not restore then start run_all."""
        envs = [make_env(cell_1x1())]
        run_count = 0

        window = make_test_window("test_queued_invoke", envs, None)
        try:
            self.assertIsNotNone(window.action_button)
            btn = window.action_button

            def run_env(_env: RobotEnv) -> RunResult:
                nonlocal run_count
                run_count += 1
                window.root.after(0, btn.invoke)
                window.root.after(0, btn.invoke)
                return RunResult(status="success", message="ok")

            window.run_env = run_env
            window.run_all()
            self.assertEqual(run_count, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            window.root.update()
            self.assertEqual(run_count, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertEqual(btn.cget("state"), tk.NORMAL)
        finally:
            window.close()

    def test_enter_from_canvas_runs_then_restores(self) -> None:
        base = corridor()
        envs = [make_env(dict(base))]
        run_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("enter_canvas", envs, run_env) as window:
            btn = window.action_button
            self.assertIsNotNone(btn)
            window.canvas.focus_set()
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(run_calls, 1)
            self.assertEqual(window.selected_index, 0)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            window.root.update()
            self.assertEqual(btn.cget("state"), tk.NORMAL)
            window.canvas.event_generate("<KeyRelease-Return>", when="tail")
            window.root.update()
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(window.selected_index, 0)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RUN)
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 0))

    def test_enter_from_canvas_when_action_button_in_active_state(self) -> None:
        """Hover makes tk.Button state 'active'; Enter must still run like normal."""
        envs = [make_env(corridor())]
        run_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("enter_when_button_active", envs, run_env) as window:
            btn = window.action_button
            self.assertIsNotNone(btn)
            btn.configure(state=tk.ACTIVE)
            self.assertEqual(btn.cget("state"), tk.ACTIVE)
            window.canvas.focus_set()
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(run_calls, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)

    def test_start_run_via_enter_with_two_queued_enters_during_run(self) -> None:
        """Start run with Enter; two Enter pairs queued during run must not restore+rerun."""
        envs = [make_env(corridor())]
        run_count = 0

        with test_window("enter_start_two_queued", envs, None) as window:
            btn = window.action_button
            self.assertIsNotNone(btn)
            window.canvas.focus_set()

            def run_env(env: RobotEnv) -> RunResult:
                nonlocal run_count
                run_count += 1
                env.robot.move_right()

                def enqueue_two_enters() -> None:
                    for _ in range(2):
                        window.canvas.event_generate("<Return>", when="tail")
                        window.canvas.event_generate(
                            "<KeyRelease-Return>", when="tail"
                        )

                window.root.after(0, enqueue_two_enters)
                return RunResult(status="success", message="ok")

            window.run_env = run_env
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(run_count, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            window.root.update()
            self.assertEqual(run_count, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            self.assertEqual(btn.cget("state"), tk.NORMAL)
            window.canvas.event_generate("<KeyRelease-Return>", when="tail")
            window.root.update()
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RUN)
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 0))

    def test_enter_does_not_invoke_when_restore_button_disabled(self) -> None:
        envs = [make_env(corridor())]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("enter_while_disabled", envs, run_env) as window:
            btn = window.action_button
            self.assertIsNotNone(btn)
            window.canvas.focus_set()
            window.run_all()
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertEqual(btn.cget("state"), tk.DISABLED)
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(
                (envs[0].robot.row, envs[0].robot.col),
                (0, 1),
                "Enter must not restore while button is still disabled",
            )
            self.assertEqual(btn.cget("state"), tk.NORMAL)

    def test_kp_enter_from_canvas_runs(self) -> None:
        envs = [make_env(cell_1x1())]
        run_calls = 0

        def run_env(_env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            return RunResult(status="success", message="ok")

        with test_window("kp_enter_canvas", envs, run_env) as window:
            btn = window.action_button
            self.assertIsNotNone(btn)
            window.canvas.focus_set()
            window.canvas.event_generate("<KP_Enter>", when="tail")
            window.root.update()
            self.assertEqual(run_calls, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)

    def test_escape_from_canvas_closes_window(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("escape_canvas", envs, run_env) as window:
            window.canvas.focus_set()
            window.canvas.event_generate("<Escape>", when="tail")
            window.root.update()
            self.assertTrue(window.is_closed)



if __name__ == "__main__":
    unittest.main()
