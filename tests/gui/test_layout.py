"""Tests for pure layout helpers (cell size, canvas size, field offset)."""

import unittest

from robot.gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from robot.gui_theme import COMPACT_CELL_SIZE, DEFAULT_CELL_SIZE, MIN_CANVAS_WIDTH

from ._helpers import make_env, minimal_env_dict


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
        self.assertEqual(calculate_canvas_size(envs, 80, 4), (530, 244))

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
        # Width 7 so calculated canvas width (7*80+4) exceeds MIN_CANVAS_WIDTH; otherwise
        # the minimum-width canvas adds horizontal centering unrelated to height mismatch.
        max_env = make_env(
            {
                "width": 7,
                "height": 3,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        shorter_same_width = make_env(
            {
                "width": 7,
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

if __name__ == "__main__":
    unittest.main()
