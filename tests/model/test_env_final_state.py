import unittest

from robot.model import Cell, ValuedCell

from .helpers import make_env


class RobotEnvFinalStateTest(unittest.TestCase):
    def test_requires_robot_at_final_position(self):
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
        # Robot still at (0, 0)
        self.assertFalse(env.is_in_final_state())

    def test_requires_all_cells_to_paint_painted(self):
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
        env.robot.move_right()
        # Did not paint
        self.assertFalse(env.is_in_final_state())

    def test_rejects_extra_painted_cells(self):
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
        env.robot.paint()  # paints (0,0) which is not required
        env.robot.move_right()
        env.robot.paint()
        self.assertFalse(env.is_in_final_state())

    def test_allows_pre_painted_cells(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 1}],
            }
        )
        env.robot.move_right()
        env.robot.paint()
        self.assertTrue(env.is_in_final_state())

    def test_requires_correct_printed_numbers(self):
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

    def test_rejects_wrong_printed_value(self):
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
        env.robot.print_number(5)
        self.assertFalse(env.is_in_final_state())

    def test_rejects_missing_printed_cell(self):
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
        # Nothing printed
        self.assertFalse(env.is_in_final_state())

    def test_rejects_extra_printed_cell(self):
        env2 = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "cellsToPrint": [{"r": 0, "c": 1, "value": 7}],
            }
        )
        env2.robot.move_right()
        env2.robot.print_number(7)
        env2.robot.move_left()
        env2.robot.print_number(8)  # extra at (0,0)
        self.assertFalse(env2.is_in_final_state())

    def test_true_when_all_conditions_met(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "cellsToPaint": [{"r": 0, "c": 1}],
                "cellsToPrint": [{"r": 0, "c": 1, "value": 3}],
            }
        )
        env.robot.move_right()
        env.robot.paint()
        env.robot.print_number(3)
        self.assertTrue(env.is_in_final_state())

    def test_double_paint_of_required_cell_counts_correctly(self):
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
        env.robot.move_right()
        env.robot.paint()
        env.robot.paint()  # duplicate
        self.assertTrue(env.is_in_final_state())


if __name__ == "__main__":
    unittest.main()
