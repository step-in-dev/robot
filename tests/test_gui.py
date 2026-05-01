import unittest

import tkinter as tk

from robot.gui import (
    COMPACT_CELL_SIZE,
    DEFAULT_CELL_SIZE,
    MIN_CANVAS_WIDTH,
    RobotWindow,
    STATUS_ALL_CORRECT,
    STATUS_READY,
    STATUS_WRONG,
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from robot.model import RobotEnv, RobotEnvDto
from robot.runtime import RunResult


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
            self.assertEqual(window.action_button.cget("text"), "Выполнить")

            window.run_all()
            self.assertEqual(window.selected_index, 1)
            self.assertEqual(window.action_button.cget("text"), "Восстановить")
            self.assertEqual((envs[0].robot.row, envs[0].robot.col), (0, 1))
            self.assertEqual((envs[1].robot.row, envs[1].robot.col), (0, 1))

            window.restore()
            self.assertEqual(window.selected_index, 0)
            self.assertEqual(window.action_button.cget("text"), "Выполнить")
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
            self.assertEqual(window.action_button.cget("text"), "Восстановить")
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
            self.assertEqual(btn.cget("text"), "Восстановить")
            window.root.update()
            self.assertEqual(run_count, 1)
            self.assertEqual(btn.cget("text"), "Восстановить")
            self.assertEqual(btn.cget("state"), tk.NORMAL)
        finally:
            window.close()


@unittest.skipUnless(
    _tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
class RobotWindowStatusLabelTest(unittest.TestCase):
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
        finally:
            window.close()

    def test_error_shows_only_message_text(self) -> None:
        envs = [make_env({**minimal_env_dict(1, 1), "finalCol": 0})]
        err_msg = "текст ошибки"

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="error", message=err_msg)

        window = RobotWindow("status_error", envs, run_env, initial_index=0)
        try:
            window.run_all()
            self.assertEqual(window.status_var.get(), err_msg)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
