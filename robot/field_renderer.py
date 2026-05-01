from __future__ import annotations

from dataclasses import dataclass

import tkinter as tk

from .gui_layout import calculate_field_offset
from .model import Cell, RobotEnv


@dataclass
class FieldColors:
    grid_color: str
    wall_color: str
    robot_color: str
    robot_outline: str
    cell_to_paint_color: str
    cell_to_paint_when_painted_color: str
    home_color: str
    pollution_color: str
    print_color: str
    cell_background_color: str


class FieldRenderer:
    """Draws the robot grid field on a tkinter canvas."""

    def __init__(self, canvas: tk.Canvas, cell_size: int, wall_width: int) -> None:
        self.canvas = canvas
        self.cell_size = cell_size
        self.wall_width = wall_width

    def set_dimensions(self, cell_size: int, wall_width: int) -> None:
        self.cell_size = cell_size
        self.wall_width = wall_width

    def draw_field(
        self,
        env: RobotEnv,
        canvas_width: int,
        canvas_height: int,
        colors: FieldColors,
    ) -> None:
        half_wall_width = self.wall_width // 2

        self.canvas.delete("all")

        self._draw_cell_field_background(env, half_wall_width, colors.cell_background_color)
        self._draw_painted_cells(env, half_wall_width, colors.cell_to_paint_color)
        self._draw_cells_to_paint(env, colors)
        self._draw_grid(env, half_wall_width, colors.grid_color)
        self._draw_outline(env, half_wall_width, colors.wall_color)
        self._draw_walls(env, half_wall_width, colors.wall_color)
        self._draw_robot(env, colors.robot_color, colors.robot_outline)
        self._draw_home(env, colors.home_color)
        self._draw_pollution(env, colors.pollution_color)
        self._draw_print_values(env, colors.print_color)

        offset_x, offset_y = calculate_field_offset(
            canvas_width,
            canvas_height,
            env,
            self.cell_size,
            self.wall_width,
        )
        self.canvas.move("all", offset_x, offset_y)

    def _draw_cell_field_background(
        self, env: RobotEnv, half_wall_width: int, fill: str
    ) -> None:
        self.canvas.create_rectangle(
            half_wall_width,
            half_wall_width,
            half_wall_width + env.width * self.cell_size,
            half_wall_width + env.height * self.cell_size,
            fill=fill,
            outline="",
        )

    def _draw_painted_cells(
        self, env: RobotEnv, half_wall_width: int, fill: str
    ) -> None:
        for cell in env.extract_painted_cells():
            x = cell.c * self.cell_size + half_wall_width
            y = cell.r * self.cell_size + half_wall_width
            self.canvas.create_rectangle(
                x,
                y,
                x + self.cell_size,
                y + self.cell_size,
                fill=fill,
                outline="",
            )

    def _draw_cells_to_paint(self, env: RobotEnv, colors: FieldColors) -> None:
        marker_size = self.wall_width * 2
        offset = self.wall_width * 2
        for cell in env.cells_to_paint:
            x = cell.c * self.cell_size + offset
            y = cell.r * self.cell_size + offset
            color = (
                colors.cell_to_paint_when_painted_color
                if env.is_painted(cell)
                else colors.cell_to_paint_color
            )
            self.canvas.create_rectangle(
                x,
                y,
                x + marker_size,
                y + marker_size,
                fill=color,
                outline="",
            )

    def _draw_grid(self, env: RobotEnv, half_wall_width: int, grid_color: str) -> None:
        for row in range(1, env.height):
            y = half_wall_width + row * self.cell_size
            self.canvas.create_line(
                half_wall_width,
                y,
                half_wall_width + env.width * self.cell_size - 1,
                y,
                fill=grid_color,
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
                fill=grid_color,
                width=1,
                dash=(2, 1),
            )

    def _draw_outline(
        self, env: RobotEnv, half_wall_width: int, outline_color: str
    ) -> None:
        self.canvas.create_rectangle(
            half_wall_width,
            half_wall_width,
            half_wall_width + env.width * self.cell_size,
            half_wall_width + env.height * self.cell_size,
            outline=outline_color,
            width=self.wall_width,
        )

    def _draw_walls(self, env: RobotEnv, half_wall_width: int, wall_color: str) -> None:
        for first, second in env.walls:
            if first.r == second.r:
                x = (
                    min(first.c, second.c) + 1
                ) * self.cell_size + half_wall_width
                y1 = first.r * self.cell_size + half_wall_width
                y2 = (first.r + 1) * self.cell_size + half_wall_width
                self.canvas.create_line(
                    x, y1, x, y2, fill=wall_color, width=self.wall_width
                )
            else:
                y = (
                    min(first.r, second.r) + 1
                ) * self.cell_size + half_wall_width
                x1 = first.c * self.cell_size + half_wall_width
                x2 = (first.c + 1) * self.cell_size + half_wall_width
                self.canvas.create_line(
                    x1, y, x2, y, fill=wall_color, width=self.wall_width
                )

    def _draw_robot(
        self, env: RobotEnv, robot_fill: str, robot_outline: str
    ) -> None:
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
            fill=robot_fill,
            outline=robot_outline,
            width=2,
        )

    def _draw_home(self, env: RobotEnv, home_color: str) -> None:
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
            fill=home_color,
            outline=home_color,
        )

    def _draw_pollution(self, env: RobotEnv, pollution_color: str) -> None:
        for cell in env.polluted_cells:
            self._draw_centered_text(
                cell,
                str(cell.value),
                pollution_color,
                font_size=int(self.cell_size * 0.28),
            )

    def _draw_print_values(self, env: RobotEnv, print_color: str) -> None:
        for cell in env.printed_cells:
            self._draw_centered_text(
                cell,
                str(cell.value),
                print_color,
                font_size=int(self.cell_size * 0.28),
            )

    def _draw_centered_text(
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
