from __future__ import annotations

import tkinter as tk
from typing import Callable

from .model import Cell, RobotEnv
from .runtime import RunResult


STATUS_RUNNING = "Выполнение..."
STATUS_READY = "Робот: Готов"
STATUS_WRONG = "Задание не выполнено"
STATUS_ALL_CORRECT = "Все верно"
ACTION_BUTTON_RUN = "Выполнить"
ACTION_BUTTON_RESTORE = "Восстановить"

DEFAULT_CELL_SIZE = 80
COMPACT_CELL_SIZE = 60
COMPACT_CELL_MAX_WIDTH = 7
COMPACT_CELL_MAX_HEIGHT = 5
MIN_CANVAS_WIDTH = 450


def calculate_cell_size(envs: list[RobotEnv]) -> int:
    """Pixel side length for cells; compact when any env exceeds width/height thresholds."""
    max_width = max(env.width for env in envs)
    max_height = max(env.height for env in envs)
    if (
        max_width > COMPACT_CELL_MAX_WIDTH
        or max_height > COMPACT_CELL_MAX_HEIGHT
    ):
        return COMPACT_CELL_SIZE
    return DEFAULT_CELL_SIZE


def calculate_canvas_size(
    envs: list[RobotEnv], cell_size: int, wall_width: int
) -> tuple[int, int]:
    """Pixel size of the canvas needed to show the largest environment in envs."""
    max_width = max(env.width for env in envs)
    max_height = max(env.height for env in envs)
    calculated_width = max_width * cell_size + wall_width
    return (
        max(calculated_width, MIN_CANVAS_WIDTH),
        max_height * cell_size + wall_width,
    )


def calculate_field_offset(
    canvas_width: int,
    canvas_height: int,
    env: RobotEnv,
    cell_size: int,
    wall_width: int,
) -> tuple[int, int]:
    """Pixel offset to center env's field inside a canvas for the largest env."""
    field_width = env.width * cell_size + wall_width
    field_height = env.height * cell_size + wall_width
    return (
        (canvas_width - field_width) // 2,
        (canvas_height - field_height) // 2,
    )


class RobotWindow:
    def __init__(
        self,
        task_id: str,
        envs: list[RobotEnv],
        run_env: Callable[[RobotEnv], RunResult] | None,
        initial_index: int = 0,
        debug_mode: bool = False,
        todo_text: str = "",
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.selected_index = initial_index
        self.debug_mode = debug_mode
        self.todo_text = todo_text.strip()
        self.current_listener: Callable[[], None] | None = None
        self.is_closed = False

        self.grid_color = "#428bca"
        self.wall_color = "#428bca"
        self.robot_color = "#428bca"
        self.robot_outline = "#ffffff"
        self.cell_to_paint_color = "#f0ad4e"
        self.cell_to_paint_when_painted_color = "#ffffff"
        self.home_color = "#a93b20"
        self.pollution_color = "#404C51"
        self.print_color = "#712903"
        self.cell_background_color = "#ffffff"
        self.wall_width = 4
        self.cell_size = calculate_cell_size(self.envs)

        self.root = tk.Tk()
        self.root.title(f"Robot: {task_id}")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.lift()
        self.root.attributes("-topmost", True)

        self.canvas_width, self.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )

        self.todo_label: tk.Label | None = None
        if self.todo_text:
            self.todo_label = tk.Label(
                self.root,
                text=f"{self.todo_text}",
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=max(self.canvas_width, 320),
                bg="#fdf9d3",
                fg="#000000",
                padx=8,
                pady=6,
                bd=0,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground="#999999",
                highlightcolor="#999999",
            )
            self.todo_label.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

        self.tab_frame: tk.Frame | None = None
        self.tab_buttons: list[tk.Button] = []
        if len(envs) > 1:
            tab_top_pady = (2, 2) if self.todo_label is not None else (6, 2)
            self.tab_frame = tk.Frame(self.root)
            self.tab_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady)
            for index in range(len(envs)):
                button = tk.Button(
                    self.tab_frame,
                    text=str(index + 1),
                    command=lambda index=index: self.select_env(index),
                    width=4,
                )
                button.pack(side=tk.LEFT)
                self.tab_buttons.append(button)
        self.canvas = tk.Canvas(
            self.root,
            bg=self.root.cget("bg"),
            highlightthickness=0,
            width=self.canvas_width,
            height=self.canvas_height,
        )
        self.canvas.pack(padx=6, pady=6)

        self.controls = tk.Frame(self.root)
        self.controls.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 6))

        self.action_button: tk.Button | None = None
        self._pending_restore_enable_after_id: str | None = None
        if not debug_mode:
            self.action_button = tk.Button(
                self.controls,
                text=ACTION_BUTTON_RUN,
                command=self.run_all,
            )
            self.action_button.pack(side=tk.LEFT)

        initial_status = STATUS_RUNNING if debug_mode else STATUS_READY
        self.status_var = tk.StringVar(value=initial_status)
        self.status_label = tk.Label(
            self.controls, textvariable=self.status_var, anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

        self.select_env(initial_index)
        self.lock_window_size()

    def lock_window_size(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self.root.minsize(width, height)
        self.root.maxsize(width, height)

    def run(self) -> None:
        self.root.mainloop()

    def run_until_closed(self) -> None:
        if self.is_closed:
            return
        try:
            self.root.mainloop()
        except tk.TclError:
            self.is_closed = True

    def close(self) -> None:
        if self.is_closed:
            return
        self._cancel_pending_restore_enable_after()
        self.is_closed = True
        self.root.destroy()

    def show_debug_started(self) -> None:
        if self.is_closed:
            return
        self.status_var.set(STATUS_RUNNING)
        self.root.update()

    def select_env(self, index: int) -> None:
        if self.current_listener is not None:
            self.envs[self.selected_index].remove_listener(self.current_listener)

        self.selected_index = index
        self.current_listener = self.on_env_change
        self.envs[self.selected_index].add_listener(self.current_listener)

        self.configure_tab_buttons()

        self.draw_field()

    def configure_tab_buttons(self) -> None:
        for tab_index, button in enumerate(self.tab_buttons):
            state = (
                tk.DISABLED
                if self.debug_mode or tab_index == self.selected_index
                else tk.NORMAL
            )
            button.configure(
                relief=tk.SUNKEN
                if tab_index == self.selected_index
                else tk.RAISED,
                state=state,
            )

    def _set_action_to_run(self) -> None:
        self._cancel_pending_restore_enable_after()
        if self.action_button is None:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
            state=tk.NORMAL,
        )

    def _cancel_pending_restore_enable_after(self) -> None:
        if self._pending_restore_enable_after_id is None:
            return
        pending = self._pending_restore_enable_after_id
        self._pending_restore_enable_after_id = None
        try:
            self.root.after_cancel(pending)
        except tk.TclError:
            pass

    def _enable_action_button_if_current(self) -> None:
        self._pending_restore_enable_after_id = None
        if self.action_button is None or self.is_closed:
            return
        if self.action_button.cget("text") != ACTION_BUTTON_RESTORE:
            return
        if self.action_button.cget("state") != tk.DISABLED:
            return
        self.action_button.configure(state=tk.NORMAL)

    def _set_action_to_restore_after_idle(self) -> None:
        """Show Restore while disabled so queued clicks drain before the button is clickable."""
        self._cancel_pending_restore_enable_after()
        if self.action_button is None:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RESTORE,
            command=self.restore,
            state=tk.DISABLED,
        )
        self._pending_restore_enable_after_id = self.root.after_idle(
            self._enable_action_button_if_current
        )

    def _disable_action_button(self) -> None:
        if self.action_button is None:
            return
        self.action_button.configure(state=tk.DISABLED)

    def restore(self) -> None:
        for env in self.envs:
            env.reset()
        self.status_var.set(STATUS_READY)
        self.select_env(0)
        self._set_action_to_run()

    def run_all(self) -> None:
        if self.run_env is None:
            raise RuntimeError("run_env is required outside debug mode")

        try:
            self._disable_action_button()
            self.status_var.set(STATUS_RUNNING)
            self.root.update_idletasks()

            for index, env in enumerate(self.envs):
                self.select_env(index)
                result = self.run_env(env)
                self.draw_field()
                if not result.success:
                    if result.status == "wrong":
                        self.status_var.set(STATUS_WRONG)
                    else:
                        self.status_var.set(result.message)
                    return

            self.status_var.set(STATUS_ALL_CORRECT)
        finally:
            self._set_action_to_restore_after_idle()

    def on_env_change(self) -> None:
        if self.is_closed:
            return
        try:
            self.draw_field()
            if self.debug_mode:
                self.root.update()
            else:
                self.root.update_idletasks()
        except tk.TclError:
            self.is_closed = True

    def show_debug_result(self, env_number: int, result: RunResult) -> None:
        if self.is_closed:
            return
        self.draw_field()
        if result.success:
            self.status_var.set(f"Обстановка {env_number}: {result.message}")
        elif result.status == "wrong":
            self.status_var.set(STATUS_WRONG)
        else:
            self.status_var.set(result.message)
        self.root.update_idletasks()

    def show_robot_error(self, message: str) -> None:
        if self.is_closed:
            return
        self.status_var.set(message)
        self.root.update_idletasks()

    def draw_field(self) -> None:
        if self.is_closed:
            return

        env = self.envs[self.selected_index]
        half_wall_width = self.wall_width // 2

        self.canvas.delete("all")

        self.draw_cell_field_background(env, half_wall_width)
        self.draw_painted_cells(env, half_wall_width)
        self.draw_cells_to_paint(env)
        self.draw_grid(env, half_wall_width)
        self.draw_outline(env, half_wall_width)
        self.draw_walls(env, half_wall_width)
        self.draw_robot(env)
        self.draw_home(env)
        self.draw_pollution(env)
        self.draw_print_values(env)

        offset_x, offset_y = calculate_field_offset(
            self.canvas_width,
            self.canvas_height,
            env,
            self.cell_size,
            self.wall_width,
        )
        self.canvas.move("all", offset_x, offset_y)

    def draw_cell_field_background(self, env: RobotEnv, half_wall_width: int) -> None:
        self.canvas.create_rectangle(
            half_wall_width,
            half_wall_width,
            half_wall_width + env.width * self.cell_size,
            half_wall_width + env.height * self.cell_size,
            fill=self.cell_background_color,
            outline="",
        )

    def draw_painted_cells(self, env: RobotEnv, half_wall_width: int) -> None:
        for cell in env.extract_painted_cells():
            x = cell.c * self.cell_size + half_wall_width
            y = cell.r * self.cell_size + half_wall_width
            self.canvas.create_rectangle(
                x,
                y,
                x + self.cell_size,
                y + self.cell_size,
                fill=self.cell_to_paint_color,
                outline="",
            )

    def draw_cells_to_paint(self, env: RobotEnv) -> None:
        marker_size = self.wall_width * 2
        offset = self.wall_width * 2
        for cell in env.cells_to_paint:
            x = cell.c * self.cell_size + offset
            y = cell.r * self.cell_size + offset
            color = (
                self.cell_to_paint_when_painted_color
                if env.is_painted(cell)
                else self.cell_to_paint_color
            )
            self.canvas.create_rectangle(
                x,
                y,
                x + marker_size,
                y + marker_size,
                fill=color,
                outline="",
            )

    def draw_grid(self, env: RobotEnv, half_wall_width: int) -> None:
        for row in range(1, env.height):
            y = half_wall_width + row * self.cell_size
            self.canvas.create_line(
                half_wall_width,
                y,
                half_wall_width + env.width * self.cell_size - 1,
                y,
                fill=self.grid_color,
                width=1,
                dash=(2, 1),
            )

        for col in range(1, env.width):
            x = half_wall_width + col * self.cell_size
            self.canvas.create_line(
                x,
                half_wall_width,
                x,
                half_wall_width + env.height * self.cell_size - 1,
                fill=self.grid_color,
                width=1,
                dash=(2, 1),
            )

    def draw_outline(self, env: RobotEnv, half_wall_width: int) -> None:
        self.canvas.create_rectangle(
            half_wall_width,
            half_wall_width,
            half_wall_width + env.width * self.cell_size,
            half_wall_width + env.height * self.cell_size,
            outline=self.wall_color,
            width=self.wall_width,
        )

    def draw_walls(self, env: RobotEnv, half_wall_width: int) -> None:
        for first, second in env.walls:
            if first.r == second.r:
                x = (
                    min(first.c, second.c) + 1
                ) * self.cell_size + half_wall_width
                y1 = first.r * self.cell_size + half_wall_width
                y2 = (first.r + 1) * self.cell_size + half_wall_width
                self.canvas.create_line(
                    x, y1, x, y2, fill=self.wall_color, width=self.wall_width
                )
            else:
                y = (
                    min(first.r, second.r) + 1
                ) * self.cell_size + half_wall_width
                x1 = first.c * self.cell_size + half_wall_width
                x2 = (first.c + 1) * self.cell_size + half_wall_width
                self.canvas.create_line(
                    x1, y, x2, y, fill=self.wall_color, width=self.wall_width
                )

    def draw_robot(self, env: RobotEnv) -> None:
        row = env.robot.row
        col = env.robot.col
        half_wall_width = self.wall_width // 2
        padding = self.cell_size * 0.27
        x1 = half_wall_width + col * self.cell_size + padding
        y1 = half_wall_width + row * self.cell_size + padding
        x2 = half_wall_width + (col + 1) * self.cell_size - padding
        y2 = half_wall_width + (row + 1) * self.cell_size - padding
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=self.robot_color,
            outline=self.robot_outline,
            width=2,
        )

    def draw_home(self, env: RobotEnv) -> None:
        row = env.final_row
        col = env.final_col
        half_wall_width = self.wall_width // 2
        half_cell_size = self.cell_size // 2
        x = col * self.cell_size + half_cell_size + half_wall_width
        y = row * self.cell_size + half_cell_size + half_wall_width
        size = half_cell_size - half_wall_width - 1
        scale = size / 24

        def point(svg_x: float, svg_y: float) -> tuple[float, float]:
            return x + svg_x * scale, y + svg_y * scale

        points = [
            point(12, 2),
            point(1, 12),
            point(4, 12),
            point(4, 20),
            point(5, 21),
            point(9, 21),
            point(10, 20),
            point(10, 14),
            point(14, 14),
            point(14, 20),
            point(15, 21),
            point(19, 21),
            point(20, 20),
            point(20, 12),
            point(23, 12),
        ]
        self.canvas.create_polygon(
            points,
            fill=self.home_color,
            outline=self.home_color,
        )

    def draw_pollution(self, env: RobotEnv) -> None:
        for cell in env.polluted_cells:
            self.draw_centered_text(
                cell,
                str(cell.value),
                self.pollution_color,
                font_size=int(self.cell_size * 0.28),
            )

    def draw_print_values(self, env: RobotEnv) -> None:
        for cell in env.printed_cells:
            self.draw_centered_text(
                cell,
                str(cell.value),
                self.print_color,
                font_size=int(self.cell_size * 0.28),
            )

    def draw_centered_text(
        self, cell: Cell, text: str, color: str, font_size: int
    ) -> None:
        half_wall_width = self.wall_width // 2
        self.canvas.create_text(
            half_wall_width + cell.c * self.cell_size + self.cell_size / 2,
            half_wall_width + cell.r * self.cell_size + self.cell_size / 2,
            text=text,
            fill=color,
            font=("Arial", font_size, "bold"),
        )
