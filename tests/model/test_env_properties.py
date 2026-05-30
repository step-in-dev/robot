"""Tests for environment dimensions and cell access."""

import unittest

from robot.model import Cell

from .helpers import make_env, cell_1x1, corridor_with_paint, env_dict


class RobotEnvPropertiesTest(unittest.TestCase):
    def test_width_and_height(self):
        env = make_env(env_dict(5, 3, start_row=1, start_col=2, final_row=2, final_col=4))
        self.assertEqual(env.width, 5)
        self.assertEqual(env.height, 3)

    def test_start_and_final_positions(self):
        env = make_env(env_dict(5, 3, start_row=1, start_col=2, final_row=2, final_col=4))
        self.assertEqual(env.start_row, 1)
        self.assertEqual(env.start_col, 2)
        self.assertEqual(env.final_row, 2)
        self.assertEqual(env.final_col, 4)

    def test_walls_returns_tuple_of_tuples(self):
        env = make_env(env_dict(2, 1, final_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        walls = env.walls
        self.assertIsInstance(walls, tuple)
        self.assertEqual(len(walls), 1)
        first, second = walls[0]
        self.assertIsInstance(first, Cell)
        self.assertIsInstance(second, Cell)
        self.assertEqual((first.r, first.c), (0, 0))
        self.assertEqual((second.r, second.c), (0, 1))

    def test_painted_cells_returns_tuple(self):
        env = make_env(env_dict(2, 1, final_col=1, paintedCells=[{'r': 0, 'c': 0}]))
        painted = env.painted_cells
        self.assertIsInstance(painted, tuple)
        self.assertEqual(len(painted), 1)
        self.assertEqual((painted[0].r, painted[0].c), (0, 0))

    def test_cells_to_paint_returns_tuple(self):
        env = make_env(corridor_with_paint())
        cells = env.cells_to_paint
        self.assertIsInstance(cells, tuple)
        self.assertEqual(len(cells), 1)
        self.assertEqual((cells[0].r, cells[0].c), (0, 1))

    def test_polluted_cells_returns_tuple(self):
        env = make_env(env_dict(2, 1, final_col=1, pollutedCells=[{'r': 0, 'c': 0, 'value': 5}]))
        polluted = env.polluted_cells
        self.assertIsInstance(polluted, tuple)
        self.assertEqual(len(polluted), 1)
        self.assertEqual(
            (polluted[0].r, polluted[0].c, polluted[0].value), (0, 0, 5)
        )

    def test_cells_to_print_returns_tuple(self):
        env = make_env(env_dict(2, 1, final_col=1, cellsToPrint=[{'r': 0, 'c': 0, 'value': 7}]))
        cells = env.cells_to_print
        self.assertIsInstance(cells, tuple)
        self.assertEqual(len(cells), 1)
        self.assertEqual((cells[0].r, cells[0].c, cells[0].value), (0, 0, 7))

    def test_printed_cells_initially_empty(self):
        env = make_env(cell_1x1())
        self.assertEqual(env.printed_cells, ())


if __name__ == "__main__":
    unittest.main()
