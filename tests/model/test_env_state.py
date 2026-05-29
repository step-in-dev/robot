
import unittest
from unittest.mock import MagicMock

from robot.model import Cell, ValuedCell

from .helpers import make_env


class RobotEnvPaintTest(unittest.TestCase):
    def test_is_painted_true_for_pre_painted(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}],
            }
        )
        self.assertTrue(env.is_painted(Cell(0, 0)))
        self.assertFalse(env.is_painted(Cell(0, 1)))

    def test_is_painted_true_for_newly_painted(self):
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
        env.paint(Cell(0, 1))
        self.assertTrue(env.is_painted(Cell(0, 1)))

    def test_is_painted_false_for_unpainted(self):
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
        self.assertFalse(env.is_painted(Cell(0, 1)))

    def test_extract_painted_cells_includes_pre_and_new(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}],
            }
        )
        env.paint(Cell(0, 1))
        painted = env.extract_painted_cells()
        self.assertEqual(len(painted), 2)
        self.assertIn(Cell(0, 0), painted)
        self.assertIn(Cell(0, 1), painted)

    def test_double_paint_tracked_twice(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        env.paint(Cell(0, 0))
        env.paint(Cell(0, 0))
        painted = env.extract_painted_cells()
        self.assertEqual(len(painted), 2)


class RobotEnvPollutionTest(unittest.TestCase):
    def test_get_pollution_level_for_polluted_cell(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "pollutedCells": [{"r": 0, "c": 0, "value": 5}],
            }
        )
        self.assertEqual(env.get_pollution_level(Cell(0, 0)), 5)

    def test_get_pollution_level_for_clean_cell(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "pollutedCells": [{"r": 0, "c": 0, "value": 5}],
            }
        )
        self.assertEqual(env.get_pollution_level(Cell(0, 1)), 0)

    def test_get_pollution_level_for_unknown_cell(self):
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
        self.assertEqual(env.get_pollution_level(Cell(0, 0)), 0)


class RobotEnvPrintTest(unittest.TestCase):
    def test_print_number_adds_valued_cell(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        env.print_number(ValuedCell(0, 0, 7))
        self.assertEqual(len(env.printed_cells), 1)
        self.assertEqual(env.printed_cells[0].value, 7)

    def test_print_number_replaces_same_position(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        env.print_number(ValuedCell(0, 0, 3))
        env.print_number(ValuedCell(0, 0, 5))
        self.assertEqual(len(env.printed_cells), 1)
        self.assertEqual(env.printed_cells[0].value, 5)

    def test_printed_cells_returns_tuple(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        env.print_number(ValuedCell(0, 0, 1))
        printed = env.printed_cells
        self.assertIsInstance(printed, tuple)


class RobotEnvResetTest(unittest.TestCase):
    def test_reset_clears_newly_painted(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}],
            }
        )
        env.paint(Cell(0, 1))
        env.reset()
        self.assertEqual(env.extract_painted_cells(), (Cell(0, 0),))

    def test_reset_clears_printed_cells(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        env.print_number(ValuedCell(0, 0, 5))
        env.reset()
        self.assertEqual(env.printed_cells, ())

    def test_reset_resets_robot_position(self):
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
        env.robot.move_right()
        env.reset()
        self.assertEqual((env.robot.row, env.robot.col), (0, 0))

    def test_reset_notifies_listeners(self):
        env = make_env(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        listener = MagicMock()
        env.add_listener(listener)
        env.reset()
        listener.assert_called_once()


if __name__ == "__main__":
    unittest.main()
