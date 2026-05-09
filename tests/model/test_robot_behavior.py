import unittest

from robot.model import RobotPathError, RobotError

from .helpers import make_env


class RobotMovementTest(unittest.TestCase):
    def test_move_right_and_border_wall(self):
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


class RobotWallTest(unittest.TestCase):
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


class RobotPrintValidationTest(unittest.TestCase):
    def test_print_number_accepts_only_integers(self):
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

        env.robot.print_number(7)
        self.assertTrue(env.is_in_final_state())

        env.reset()
        with self.assertRaises(RobotError):
            env.robot.print_number(1.2)
        self.assertEqual(len(env.printed_cells), 0)

        env.reset()
        with self.assertRaises(RobotError):
            env.robot.print_number("7")
        self.assertEqual(len(env.printed_cells), 0)

        env.reset()
        with self.assertRaises(RobotError):
            env.robot.print_number(True)
        self.assertEqual(len(env.printed_cells), 0)


if __name__ == "__main__":
    unittest.main()
