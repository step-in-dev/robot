import tempfile
import unittest
from pathlib import Path

import tkinter as tk

from robot.executor import StudentLine

from robot.gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from robot.gui_theme import (
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_STEP,
    COMPACT_CELL_SIZE,
    DEFAULT_CELL_SIZE,
    MIN_CANVAS_WIDTH,
    STATUS_ALL_CORRECT,
    STATUS_READY,
    STATUS_WRONG,
    STATUS_BG_ERROR,
    STATUS_BG_NEUTRAL,
    STATUS_BG_SUCCESS,
    TODO_TEXT_BORDER,
)
from robot.gui import RobotWindow
from robot.model import RobotEnv, RobotEnvDto
from robot.results import RunResult


def _tkinter_display_works() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


def make_env(data: dict) -> RobotEnv:
    return RobotEnv(RobotEnvDto.from_dict(data))


def minimal_env_dict(width: int, height: int) -> dict:
    return {
        "width": width,
        "height": height,
        "startRow": 0,
        "startCol": 0,
        "finalRow": 0,
        "finalCol": 0,
    }


class CalculateCellSizeTest(unittest.TestCase):
    def test_default_when_width_8_and_height_6(self) -> None:
        envs = [make_env(minimal_env_dict(7, 5))]
        self.assertEqual(calculate_cell_size(envs), DEFAULT_CELL_SIZE)

    def test_compact_when_width_greater_than_8(self) -> None:
        envs = [make_env(minimal_env_dict(9, 1))]
        self.assertEqual(calculate_cell_size(envs), COMPACT_CELL_SIZE)

    def test_compact_when_height_greater_than_6(self) -> None:
        envs = [make_env(minimal_env_dict(1, 7))]
        self.assertEqual(calculate_cell_size(envs), COMPACT_CELL_SIZE)

    def test_maxima_across_multiple_envs_use_compact(self) -> None:
        envs = [
            make_env(minimal_env_dict(9, 1)),
            make_env(minimal_env_dict(1, 7)),
        ]
        self.assertEqual(calculate_cell_size(envs), COMPACT_CELL_SIZE)


class CalculateCanvasSizeTest(unittest.TestCase):
    def test_uses_max_width_and_max_height_across_envs(self) -> None:
        envs = [
            make_env(
                {
                    "width": 2,
                    "height": 3,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 0,
                }
            ),
            make_env(
                {
                    "width": 5,
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 0,
                }
            ),
        ]
        self.assertEqual(calculate_canvas_size(envs, 80, 4), (450, 244))

    def test_small_environment_uses_minimum_canvas_width(self) -> None:
        envs = [
            make_env(
                {
                    "width": 1,
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 0,
                }
            )
        ]
        self.assertEqual(
            calculate_canvas_size(envs, 80, 4),
            (MIN_CANVAS_WIDTH, 84),
        )

    def test_single_environment(self) -> None:
        envs = [
            make_env(
                {
                    "width": 2,
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 1,
                }
            )
        ]
        self.assertEqual(calculate_canvas_size(envs, 80, 4), (MIN_CANVAS_WIDTH, 84))


class CalculateFieldOffsetTest(unittest.TestCase):
    def test_zero_offset_when_environment_matches_canvas(self) -> None:
        env = make_env(
            {
                "width": 6,
                "height": 3,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        canvas_w, canvas_h = 6 * 80 + 4, 3 * 80 + 4
        self.assertEqual(
            calculate_field_offset(canvas_w, canvas_h, env, 80, 4),
            (0, 0),
        )

    def test_horizontal_offset_only_when_height_matches_max(self) -> None:
        max_env = make_env(
            {
                "width": 6,
                "height": 3,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        narrower_same_height = make_env(
            {
                "width": 5,
                "height": 3,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        canvas_w, canvas_h = calculate_canvas_size([max_env], 80, 4)
        offset_x, offset_y = calculate_field_offset(
            canvas_w, canvas_h, narrower_same_height, 80, 4
        )
        self.assertEqual(offset_y, 0)
        self.assertGreater(offset_x, 0)
        self.assertEqual(offset_x, (canvas_w - (5 * 80 + 4)) // 2)

    def test_vertical_offset_only_when_width_matches_max(self) -> None:
        max_env = make_env(
            {
                "width": 6,
                "height": 3,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        shorter_same_width = make_env(
            {
                "width": 6,
                "height": 2,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        canvas_w, canvas_h = calculate_canvas_size([max_env], 80, 4)
        offset_x, offset_y = calculate_field_offset(
            canvas_w, canvas_h, shorter_same_width, 80, 4
        )
        self.assertEqual(offset_x, 0)
        self.assertGreater(offset_y, 0)
        self.assertEqual(offset_y, (canvas_h - (2 * 80 + 4)) // 2)

    def test_example_smaller_field_in_larger_canvas(self) -> None:
        """while1-style: 5x1 field centered in canvas sized for 6x3."""
        env = make_env(
            {
                "width": 5,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 4,
            }
        )
        canvas_w, canvas_h = 6 * 80 + 4, 3 * 80 + 4
        self.assertEqual(
            calculate_field_offset(canvas_w, canvas_h, env, 80, 4),
            (40, 80),
        )


@unittest.skipUnless(
    _tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
class RobotWindowActionButtonTest(unittest.TestCase):
    def test_run_then_restore_button_and_first_env(self) -> None:
        base = {**minimal_env_dict(2, 1), "finalCol": 1}
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("test_task", envs, run_env, initial_index=1)
        try:
            self.assertIsNotNone(window.action_button)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RUN)

            window.run_all()
            self.assertEqual(window.selected_index, 1)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertNotIn(window.step_button, window.controls.pack_slaves())
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            self.assertEqual((envs[1].robot.row, envs[1].robot.col), (0, 1))

            window.restore()
            self.assertEqual(window.selected_index, 0)
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RUN)
            self.assertIn(window.step_button, window.controls.pack_slaves())
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
            for env in envs:
                self.assertEqual((env.robot.row, env.robot.col), (0, 0))
        finally:
            window.close()

    def test_failed_run_still_shows_restore(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message="неверно")

        window = RobotWindow("test_task2", envs, run_env, initial_index=0)
        try:
            self.assertIsNotNone(window.action_button)
            window.run_all()
            self.assertEqual(window.action_button.cget("text"), ACTION_BUTTON_RESTORE)
            self.assertNotIn(window.step_button, window.controls.pack_slaves())
        finally:
            window.close()

    def test_queued_invokes_during_run_do_not_restore_then_rerun(self) -> None:
        """Queued button invokes while disabled must not restore then start run_all."""
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]
        run_count = 0

        window = RobotWindow("test_queued_invoke", envs, None, initial_index=0)
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
        base = {**minimal_env_dict(2, 1), "finalCol": 1}
        envs = [make_env(dict(base))]
        run_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("enter_canvas", envs, run_env, initial_index=0)
        try:
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
        finally:
            window.close()

    def test_enter_from_canvas_when_action_button_in_active_state(self) -> None:
        """Hover makes tk.Button state 'active'; Enter must still run like normal."""
        envs = [make_env({**minimal_env_dict(2, 1), "finalCol": 1})]
        run_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("enter_when_button_active", envs, run_env, initial_index=0)
        try:
            btn = window.action_button
            self.assertIsNotNone(btn)
            btn.configure(state=tk.ACTIVE)
            self.assertEqual(btn.cget("state"), tk.ACTIVE)
            window.canvas.focus_set()
            window.canvas.event_generate("<Return>", when="tail")
            window.root.update()
            self.assertEqual(run_calls, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
        finally:
            window.close()

    def test_start_run_via_enter_with_two_queued_enters_during_run(self) -> None:
        """Start run with Enter; two Enter pairs queued during run must not restore+rerun."""
        envs = [make_env({**minimal_env_dict(2, 1), "finalCol": 1})]
        run_count = 0

        window = RobotWindow("enter_start_two_queued", envs, None, initial_index=0)
        try:
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
        finally:
            window.close()

    def test_enter_does_not_invoke_when_restore_button_disabled(self) -> None:
        envs = [make_env({**minimal_env_dict(2, 1), "finalCol": 1})]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("enter_while_disabled", envs, run_env, initial_index=0)
        try:
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
        finally:
            window.close()

    def test_kp_enter_from_canvas_runs(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]
        run_calls = 0

        def run_env(_env: RobotEnv) -> RunResult:
            nonlocal run_calls
            run_calls += 1
            return RunResult(status="success", message="ok")

        window = RobotWindow("kp_enter_canvas", envs, run_env, initial_index=0)
        try:
            btn = window.action_button
            self.assertIsNotNone(btn)
            window.canvas.focus_set()
            window.canvas.event_generate("<KP_Enter>", when="tail")
            window.root.update()
            self.assertEqual(run_calls, 1)
            self.assertEqual(btn.cget("text"), ACTION_BUTTON_RESTORE)
        finally:
            window.close()


@unittest.skipUnless(
    _tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
class RobotWindowStatusCanvasTest(unittest.TestCase):
    def test_status_row_has_border_like_todo_panel(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_border", envs, run_env, initial_index=0)
        try:
            self.assertEqual(int(window.status_canvas.cget("highlightthickness")), 1)
            self.assertEqual(
                window.status_canvas.cget("highlightbackground"), TODO_TEXT_BORDER
            )
            self.assertEqual(
                window.status_canvas.cget("highlightcolor"), TODO_TEXT_BORDER
            )
        finally:
            window.close()

    def test_initial_status_background_is_neutral(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_bg_init", envs, run_env, initial_index=0)
        try:
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()

    def test_status_row_is_below_controls_and_full_width(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_layout", envs, run_env, initial_index=0)
        try:
            self.assertNotEqual(window.status_canvas.master, window.controls)
            self.assertEqual(window.status_canvas.master, window.status_frame)
            slaves = window.root.pack_slaves()
            self.assertGreater(
                slaves.index(window.status_frame),
                slaves.index(window.controls),
            )
            self.assertEqual(window.status_frame.pack_info().get("fill"), "x")
            self.assertEqual(window.status_canvas.pack_info().get("fill"), "x")
        finally:
            window.close()

    def test_initial_status_is_robot_ready(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_init", envs, run_env, initial_index=0)
        try:
            self.assertEqual(window.status_var.get(), STATUS_READY)
        finally:
            window.close()

    def test_restore_sets_robot_ready(self) -> None:
        base = {**minimal_env_dict(2, 1), "finalCol": 1}
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_restore", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_ALL_CORRECT)
            window.restore()
            self.assertEqual(window.status_var.get(), STATUS_READY)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()

    def test_successful_run_all_shows_all_correct(self) -> None:
        base = {**minimal_env_dict(2, 1), "finalCol": 1}
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        window = RobotWindow("status_success", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_ALL_CORRECT)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_SUCCESS)
            self.assertEqual(window._status_background, STATUS_BG_SUCCESS)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()

    def test_wrong_solution_shows_task_not_done(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message="неверно")

        window = RobotWindow("status_wrong", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_WRONG)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()

    def test_error_shows_run_result_message_text(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]
        err_msg = "текст ошибки"

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="error", message=err_msg)

        window = RobotWindow("status_error", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), err_msg)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_ERROR)
            self.assertEqual(window._status_background, STATUS_BG_ERROR)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()

    def test_crashed_uses_error_background(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]
        msg = "Робот уперся в стену"

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="crashed", message=msg)

        window = RobotWindow("status_crashed", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), msg)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_ERROR)
            self.assertEqual(window._status_background, STATUS_BG_ERROR)
            self.assertFalse(window._status_hatched)
        finally:
            window.close()


@unittest.skipUnless(
    _tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
class RobotWindowStepButtonTest(unittest.TestCase):
    def test_step_button_is_right_of_run_with_script_path(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "sol.py"
            script.write_text("#\n", encoding="utf-8")
            window = RobotWindow(
                "step_layout",
                envs,
                run_env,
                initial_index=0,
                script_path=script,
            )
            try:
                slaves = list(window.controls.pack_slaves())
                self.assertEqual(slaves[0], window.action_button)
                self.assertEqual(slaves[1], window.step_button)
                self.assertEqual(window.step_button.cget("text"), ACTION_BUTTON_STEP)
                self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
            finally:
                window.close()

    def test_step_button_disabled_without_script_path(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("no_script", envs, run_env, initial_index=0)
        try:
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
        finally:
            window.close()

    def test_enter_does_not_invoke_step_button(self) -> None:
        envs = [make_env({**minimal_env_dict(2, 1), "finalCol": 1})]
        step_calls = 0

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s2.py"
            script.write_text("#\n", encoding="utf-8")
            window = RobotWindow(
                "enter_no_step",
                envs,
                run_env,
                initial_index=0,
                script_path=script,
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

    def test_run_all_disables_step_button_while_running(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s3.py"
            script.write_text("#\n", encoding="utf-8")
            window = RobotWindow("run_disables_step", envs, None, script_path=script)
            try:

                def run_env(_env: RobotEnv) -> RunResult:
                    self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
                    return RunResult(status="success", message="ok")

                window.run_env = run_env
                window.run_all()
                self.assertNotIn(
                    window.step_button,
                    window.controls.pack_slaves(),
                    "Шаг must be hidden after run_all completes",
                )
            finally:
                window.close()

    def test_restore_re_enables_step_with_script_path(self) -> None:
        envs = [make_env({**minimal_env_dict(2, 1), "finalCol": 1})]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s4.py"
            script.write_text("#\n", encoding="utf-8")
            window = RobotWindow(
                "restore_step",
                envs,
                run_env,
                script_path=script,
            )
            try:
                window.run_all()
                self.assertNotIn(window.step_button, window.controls.pack_slaves())
                window.step_button.configure(state=tk.DISABLED)
                window.restore()
                self.assertIn(window.step_button, window.controls.pack_slaves())
                self.assertEqual(window.step_button.cget("state"), tk.NORMAL)
            finally:
                window.close()

    def test_run_all_hides_step_without_script_restore_shows_disabled(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow("hide_step_no_script", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertNotIn(window.step_button, window.controls.pack_slaves())
            window.restore()
            self.assertIn(window.step_button, window.controls.pack_slaves())
            self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
        finally:
            window.close()

    def test_show_step_line_status_format(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "s5.py"
            script.write_text("#\n", encoding="utf-8")
            window = RobotWindow(
                "step_status_fmt",
                envs,
                run_env,
                script_path=script,
            )
            try:
                window._show_step_line(StudentLine(2, "move_right()"))
                self.assertEqual(
                    window.status_var.get(),
                    "Строка 2: move_right()",
                )
            finally:
                window.close()

    def test_successful_step_shows_hatched_status(self) -> None:
        """Step-by-step success uses hatched green status (unlike run_all)."""
        base = {**minimal_env_dict(2, 1), "finalCol": 1}
        envs = [make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "step_ok.py"
            script.write_text(
                "from robot import move_right; move_right()\n",
                encoding="utf-8",
            )
            window = RobotWindow(
                "step_hatch",
                envs,
                run_env,
                initial_index=0,
                script_path=script,
            )
            try:
                window.step_once()
                self.assertEqual(window.status_var.get(), STATUS_ALL_CORRECT)
                self.assertEqual(window._status_background, STATUS_BG_SUCCESS)
                self.assertTrue(window._status_hatched)
                self.assertNotIn(
                    window.step_button,
                    window.controls.pack_slaves(),
                )
            finally:
                window.close()

    def test_close_during_step_wait_does_not_raise_tcl_error(self) -> None:
        """Closing while waiting for the next step must not configure destroyed widgets."""
        base = {**minimal_env_dict(1, 1), "finalCol": 0}
        envs = [make_env(dict(base)), make_env(dict(base))]

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "multi_line.py"
            script.write_text("a = 1\nb = 2\n", encoding="utf-8")
            window = RobotWindow(
                "close_during_step",
                envs,
                None,
                script_path=script,
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
