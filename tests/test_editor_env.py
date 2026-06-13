"""Tests for environment editing helpers."""

from __future__ import annotations

import unittest

from robot.editor_env import (
    MAX_ENV_COUNT,
    MAX_FIELD_WIDTH,
    CanvasHitContext,
    EnvEditTool,
    add_environment,
    apply_tool_to_env,
    can_add_environment,
    can_remove_environment,
    canvas_to_cell,
    remove_environment,
    reset_env_dto,
    resize_env_dto,
    toggle_wall,
)
from robot.model import Cell
from robot.task_serializer import create_default_env_dto


class EditorEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env = create_default_env_dto()

    def test_apply_painted_removes_to_paint_on_same_cell(self) -> None:
        env = apply_tool_to_env(self.env, EnvEditTool.TO_PAINT, Cell(1, 1))
        env = apply_tool_to_env(env, EnvEditTool.PAINTED, Cell(1, 1))
        self.assertIn({"r": 1, "c": 1}, env["paintedCells"])
        self.assertNotIn("cellsToPaint", env)

    def test_toggle_wall_adds_and_removes(self) -> None:
        env = toggle_wall(self.env, Cell(0, 0), Cell(0, 1))
        self.assertEqual(len(env["walls"]), 1)
        env = toggle_wall(env, Cell(0, 0), Cell(0, 1))
        self.assertNotIn("walls", env)

    def test_reset_env_clears_collections(self) -> None:
        env = apply_tool_to_env(self.env, EnvEditTool.PAINTED, Cell(0, 0))
        env = toggle_wall(env, Cell(0, 0), Cell(0, 1))
        reset = reset_env_dto(env)
        self.assertNotIn("walls", reset)
        self.assertNotIn("paintedCells", reset)
        self.assertEqual(reset["startRow"], 0)
        self.assertEqual(reset["finalRow"], reset["height"] - 1)

    def test_resize_drops_out_of_bounds_data(self) -> None:
        env = apply_tool_to_env(self.env, EnvEditTool.PAINTED, Cell(4, 4))
        resized = resize_env_dto(env, width=3, height=3)
        self.assertEqual(resized["width"], 3)
        self.assertEqual(resized["height"], 3)
        self.assertNotIn("paintedCells", resized)

    def test_resize_filters_in_bounds_cells(self) -> None:
        env = {
            "width": 3,
            "height": 3,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 2,
            "finalCol": 2,
            "paintedCells": [{"r": 0, "c": 0}, {"r": 1, "c": 1}],
        }
        resized = resize_env_dto(env, width=2, height=2)
        self.assertEqual(
            resized["paintedCells"], [{"r": 0, "c": 0}, {"r": 1, "c": 1}]
        )

    def test_resize_accepts_max_dimensions(self) -> None:
        resized = resize_env_dto(self.env, width=20, height=15)
        self.assertEqual(resized["width"], 20)
        self.assertEqual(resized["height"], 15)

    def test_resize_out_of_range_error_message_is_localized(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            resize_env_dto(self.env, width=99, height=5)
        message = str(ctx.exception)
        self.assertIn(str(MAX_FIELD_WIDTH), message)

    def test_add_and_remove_environment(self) -> None:
        envs = [self.env]
        envs = add_environment(envs)
        self.assertEqual(len(envs), 2)
        envs = remove_environment(envs, 1)
        self.assertEqual(len(envs), 1)

    def test_can_add_environment(self) -> None:
        self.assertTrue(can_add_environment([self.env]))
        self.assertTrue(can_add_environment([self.env] * (MAX_ENV_COUNT - 1)))
        self.assertFalse(can_add_environment([self.env] * MAX_ENV_COUNT))

    def test_can_remove_environment(self) -> None:
        self.assertFalse(can_remove_environment([self.env]))
        self.assertTrue(can_remove_environment([self.env, self.env]))

    def test_add_environment_rejects_limit(self) -> None:
        envs = [self.env] * MAX_ENV_COUNT
        with self.assertRaises(ValueError):
            add_environment(envs)

    def test_remove_environment_rejects_last_env(self) -> None:
        with self.assertRaises(ValueError):
            remove_environment([self.env], 0)

    def test_canvas_to_cell_maps_click_to_cell(self) -> None:
        cell, wall = canvas_to_cell(
            50,
            50,
            context=CanvasHitContext(
                offset_x=0,
                offset_y=0,
                half_wall_width=2,
                cell_size=80,
                width=5,
                height=5,
            ),
        )
        self.assertEqual(cell, Cell(0, 0))
        self.assertIsNotNone(wall)


if __name__ == "__main__":
    unittest.main()
