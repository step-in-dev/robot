import unittest

from robot.model import RobotEnv, RobotEnvDto, RobotPathError


def make_env(data):
    return RobotEnv(RobotEnvDto.from_dict(data))


class RobotModelTest(unittest.TestCase):
    def test_robot_moves_and_treats_border_as_wall(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
            }
        )

        self.assertTrue(env.robot.is_free_from("right"))
        self.assertTrue(env.robot.is_wall_from("left"))

        env.robot.move_right()
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

        with self.assertRaises(RobotPathError):
            env.robot.move_right()

    def test_internal_wall_blocks_both_sides(self):
        left_env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "walls": [[{"r": 0, "c": 0}, {"r": 0, "c": 1}]],
            }
        )

        self.assertTrue(left_env.robot.is_wall_from("right"))
        with self.assertRaises(RobotPathError):
            left_env.robot.move_right()

        right_env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 1,
                "finalRow": 0,
                "finalCol": 0,
                "walls": [[{"r": 0, "c": 0}, {"r": 0, "c": 1}]],
            }
        )
        self.assertTrue(right_env.robot.is_wall_from("left"))

    def test_final_state_requires_position_and_exact_new_painting(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "cellsToPaint": [{"r": 0, "c": 1}],
            }
        )

        env.robot.paint()
        env.robot.move_right()
        env.robot.paint()

        self.assertFalse(env.is_in_final_state())

        env.reset()
        env.robot.move_right()
        env.robot.paint()

        self.assertTrue(env.is_in_final_state())

    def test_final_state_checks_printed_numbers_by_cell_and_value(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
                "cellsToPrint": [{"r": 0, "c": 0, "value": 7}],
            }
        )

        env.robot.print_number(6)
        self.assertFalse(env.is_in_final_state())

        env.robot.print_number(7)
        self.assertTrue(env.is_in_final_state())

    def test_normalization_matches_sidwebui_rules(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "walls": [
                    [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
                    [{"r": 0, "c": 0}, {"r": 0, "c": 0}],
                ],
                "paintedCells": [{"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
            }
        )

        self.assertEqual(len(dto.walls), 1)
        self.assertEqual(len(dto.cells_to_paint), 1)
        self.assertEqual((dto.cells_to_paint[0].r, dto.cells_to_paint[0].c), (0, 1))


if __name__ == "__main__":
    unittest.main()
