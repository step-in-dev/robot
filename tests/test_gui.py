import unittest

from robot.gui import calculate_canvas_size, calculate_field_offset
from robot.model import RobotEnv, RobotEnvDto


def make_env(data: dict) -> RobotEnv:
    return RobotEnv(RobotEnvDto.from_dict(data))


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
        self.assertEqual(calculate_canvas_size(envs, 80, 4), (404, 244))

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
        self.assertEqual(calculate_canvas_size(envs, 80, 4), (164, 84))


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


if __name__ == "__main__":
    unittest.main()
