from __future__ import annotations

import tkinter as tk
from typing import Callable

from .model import Cell, RobotEnv
from .runtime import RunResult


class RobotWindow:
    def __init__(
        self,
        task_id: str,
        envs: list[RobotEnv],
        run_env: Callable[[RobotEnv], RunResult],
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.selected_index = 0
        self.current_listener: Callable[[], None] | None = None

        self.root = tk.Tk()
        self.root.title(f"Robot: {task_id}")

        self.tab_frame = tk.Frame(self.root)
        self.tab_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

        self.tab_buttons: list[tk.Button] = []
        for index in range(len(envs)):
            button = tk.Button(
                self.tab_frame,
                text=str(index + 1),
                command=lambda index=index: self.select_env(index),
                width=4,
            )
            button.pack(side=tk.LEFT)
            self.tab_buttons.append(button)

        self.canvas = tk.Canvas(self.root, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)

        self.controls = tk.Frame(self.root)
        self.controls.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 6))

        self.run_button = tk.Button(
            self.controls, text="Запустить", command=self.run_all
        )
        self.run_button.pack(side=tk.LEFT)

        self.reset_button = tk.Button(self.controls, text="Сброс", command=self.reset)
        self.reset_button.pack(side=tk.LEFT, padx=(6, 0))

        self.status_var = tk.StringVar(value="Готово")
        self.status_label = tk.Label(
            self.controls, textvariable=self.status_var, anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

        self.grid_color = "#428bca"
        self.wall_color = "#428bca"
        self.robot_color = "#428bca"
        self.robot_outline = "#ffffff"
        self.cell_to_paint_color = "#f0ad4e"
        self.cell_to_paint_when_painted_color = "#ffffff"
        self.home_color = "#a93b20"
        self.pollution_color = "#404C51"
        self.print_color = "#712903"
        self.wall_width = 4
        self.cell_size = 80

        self.select_env(0)

    def run(self) -> None:
        self.root.mainloop()

    def select_env(self, index: int) -> None:
        if self.current_listener is not None:
            self.envs[self.selected_index].remove_listener(self.current_listener)

        self.selected_index = index
        self.current_listener = self.on_env_change
        self.envs[self.selected_index].add_listener(self.current_listener)

        for tab_index, button in enumerate(self.tab_buttons):
            button.configure(
                relief=tk.SUNKEN if tab_index == index else tk.RAISED,
                state=tk.DISABLED if tab_index == index else tk.NORMAL,
            )

        self.draw_field()

    def reset(self) -> None:
        for env in self.envs:
            env.reset()
        self.status_var.set("Готово")
        self.select_env(self.selected_index)

    def run_all(self) -> None:
        self.run_button.configure(state=tk.DISABLED)
        self.reset_button.configure(state=tk.DISABLED)
        self.status_var.set("Выполнение...")
        self.root.update()

        try:
            for index, env in enumerate(self.envs):
                self.select_env(index)
                result = self.run_env(env)
                self.draw_field()
                if not result.success:
                    self.status_var.set(
                        f"Ошибка на обстановке {index + 1}: {result.message}"
                    )
                    return

            self.status_var.set("Решение верное для всех обстановок")
        finally:
            self.run_button.configure(state=tk.NORMAL)
            self.reset_button.configure(state=tk.NORMAL)

    def on_env_change(self) -> None:
        self.draw_field()
        self.root.update_idletasks()

    def draw_field(self) -> None:
        env = self.envs[self.selected_index]
        half_wall_width = self.wall_width // 2
        width = env.width * self.cell_size + self.wall_width
        height = env.height * self.cell_size + self.wall_width

        self.canvas.configure(width=width, height=height)
        self.canvas.delete("all")

        self.draw_painted_cells(env, half_wall_width)
        self.draw_cells_to_paint(env)
        self.draw_grid(env, half_wall_width)
        self.draw_outline(env, half_wall_width)
        self.draw_walls(env, half_wall_width)
        self.draw_robot(env)
        self.draw_home(env)
        self.draw_pollution(env)
        self.draw_print_values(env)

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
        padding = self.cell_size * 0.27
        x1 = col * self.cell_size + padding
        y1 = row * self.cell_size + padding
        x2 = (col + 1) * self.cell_size - padding
        y2 = (row + 1) * self.cell_size - padding
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
        self.canvas.create_text(
            cell.c * self.cell_size + self.cell_size / 2,
            cell.r * self.cell_size + self.cell_size / 2,
            text=text,
            fill=color,
            font=("Arial", font_size, "bold"),
        )
