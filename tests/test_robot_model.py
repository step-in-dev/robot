import unittest
from unittest.mock import MagicMock

from robot.model import (
    RobotEnv,
    RobotEnvDto,
    RobotError,
    RobotPathError,
    Cell,
    ValuedCell,
)


def make_env(data):
    return RobotEnv(RobotEnvDto.from_dict(data))


class RobotEnvPropertiesTest(unittest.TestCase):
    def test_width_and_height(self):
        env = make_env(
            {
                "width": 5,
                "height": 3,
                "startRow": 1,
                "startCol": 2,
                "finalRow": 2,
                "finalCol": 4,
            }
        )
        self.assertEqual(env.width, 5)
        self.assertEqual(env.height, 3)

    def test_start_and_final_positions(self):
        env = make_env(
            {
                "width": 5,
                "height": 3,
                "startRow": 1,
                "startCol": 2,
                "finalRow": 2,
                "finalCol": 4,
            }
        )
        self.assertEqual(env.start_row, 1)
        self.assertEqual(env.start_col, 2)
        self.assertEqual(env.final_row, 2)
        self.assertEqual(env.final_col, 4)

    def test_walls_returns_tuple_of_tuples(self):
        env = make_env(
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
        walls = env.walls
        self.assertIsInstance(walls, tuple)
        self.assertEqual(len(walls), 1)
        first, second = walls[0]
        self.assertIsInstance(first, Cell)
        self.assertIsInstance(second, Cell)
        self.assertEqual((first.r, first.c), (0, 0))
        self.assertEqual((second.r, second.c), (0, 1))

    def test_painted_cells_returns_tuple(self):
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
        painted = env.painted_cells
        self.assertIsInstance(painted, tuple)
        self.assertEqual(len(painted), 1)
        self.assertEqual((painted[0].r, painted[0].c), (0, 0))

    def test_cells_to_paint_returns_tuple(self):
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
        cells = env.cells_to_paint
        self.assertIsInstance(cells, tuple)
        self.assertEqual(len(cells), 1)
        self.assertEqual((cells[0].r, cells[0].c), (0, 1))

    def test_polluted_cells_returns_tuple(self):
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
        polluted = env.polluted_cells
        self.assertIsInstance(polluted, tuple)
        self.assertEqual(len(polluted), 1)
        self.assertEqual(
            (polluted[0].r, polluted[0].c, polluted[0].value), (0, 0, 5)
        )

    def test_cells_to_print_returns_tuple(self):
        env = make_env(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "cellsToPrint": [{"r": 0, "c": 0, "value": 7}],
            }
        )
        cells = env.cells_to_print
        self.assertIsInstance(cells, tuple)
        self.assertEqual(len(cells), 1)
        self.assertEqual((cells[0].r, cells[0].c, cells[0].value), (0, 0, 7))

    def test_printed_cells_initially_empty(self):
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
        self.assertEqual(env.printed_cells, ())


class RobotEnvListenerTest(unittest.TestCase):
    def test_listener_notified_on_robot_move(self):
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
        listener = MagicMock()
        env.add_listener(listener)
        env.robot.move_right()
        listener.assert_called_once()

    def test_listener_notified_on_robot_paint(self):
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

    def test_listener_notified_on_robot_print_number(self):
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
        env.robot.print_number(5)
        listener.assert_called_once()

    def test_multiple_listeners_all_notified(self):
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
        listener1 = MagicMock()
        listener2 = MagicMock()
        env.add_listener(listener1)
        env.add_listener(listener2)
        env.robot.move_right()
        listener1.assert_called_once()
        listener2.assert_called_once()

    def test_removed_listener_is_not_notified(self):
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
        listener = MagicMock()
        env.add_listener(listener)
        env.remove_listener(listener)
        env.robot.move_right()
        listener.assert_not_called()


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


class RobotEnvDtoNormalizationTest(unittest.TestCase):
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
