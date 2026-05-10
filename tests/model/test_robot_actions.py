import unittest
from unittest.mock import MagicMock

from robot.model import RobotError, Cell

from .helpers import make_env


class RobotActionsTest(unittest.TestCase):
    def test_paint_notifies_listener(self):
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
        env.robot.paint()
        listener.assert_called_once()

    def test_paint_adds_cell_to_env(self):
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
        self.assertFalse(env.is_painted(Cell(0, 0)))
        env.robot.paint()
        self.assertTrue(env.is_painted(Cell(0, 0)))

    def test_print_number_int_success(self):
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
        listener = MagicMock()
        env.add_listener(listener)
        env.robot.print_number(7)
        self.assertTrue(env.is_in_final_state())
        listener.assert_called_once()

    def test_print_number_replaces_value(self):
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
        env.robot.print_number(3)
        env.robot.print_number(5)
        self.assertEqual(len(env.printed_cells), 1)
        self.assertEqual(env.printed_cells[0].value, 5)

    def test_print_number_float_raises(self):
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
        with self.assertRaises(RobotError):
            env.robot.print_number(1.2)
        self.assertEqual(len(env.printed_cells), 0)

    def test_print_number_string_raises(self):
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
        with self.assertRaises(RobotError):
            env.robot.print_number("7")
        self.assertEqual(len(env.printed_cells), 0)

    def test_print_number_bool_raises(self):
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
        with self.assertRaises(RobotError):
            env.robot.print_number(True)
        self.assertEqual(len(env.printed_cells), 0)


if __name__ == "__main__":
    unittest.main()
