"""Tests for is_free / is_wall style probes."""

import unittest

from robot.model import RobotError

from .helpers import make_env, cell_1x1, corridor, env_dict


class RobotSensorsTest(unittest.TestCase):
    def test_is_free_from_all_directions_on_open_field(self):
        env = make_env(env_dict(3, 3, start_row=1, start_col=1, final_row=2, final_col=2))
        self.assertTrue(env.robot.is_free_from("right"))
        self.assertTrue(env.robot.is_free_from("left"))
        self.assertTrue(env.robot.is_free_from("up"))
        self.assertTrue(env.robot.is_free_from("down"))

    def test_is_wall_from_all_directions_on_open_field_at_edge(self):
        env = make_env(env_dict(2, 2, final_row=1, final_col=1))
        self.assertTrue(env.robot.is_wall_from("left"))
        self.assertTrue(env.robot.is_wall_from("up"))
        self.assertFalse(env.robot.is_wall_from("right"))
        self.assertFalse(env.robot.is_wall_from("down"))

    def test_is_wall_from_internal_wall_right(self):
        env = make_env(env_dict(2, 1, final_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        self.assertTrue(env.robot.is_wall_from("right"))

    def test_is_wall_from_internal_wall_left(self):
        env = make_env(env_dict(2, 1, start_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        self.assertTrue(env.robot.is_wall_from("left"))

    def test_is_wall_from_internal_wall_up(self):
        env = make_env(env_dict(1, 2, start_row=1, walls=[[{'r': 0, 'c': 0}, {'r': 1, 'c': 0}]]))
        self.assertTrue(env.robot.is_wall_from("up"))

    def test_is_wall_from_internal_wall_down(self):
        env = make_env(env_dict(1, 2, final_row=1, walls=[[{'r': 0, 'c': 0}, {'r': 1, 'c': 0}]]))
        self.assertTrue(env.robot.is_wall_from("down"))

    def test_is_free_from_internal_wall(self):
        env = make_env(env_dict(2, 1, final_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        self.assertFalse(env.robot.is_free_from("right"))

    def test_is_wall_from_unknown_direction_raises(self):
        env = make_env(cell_1x1())
        with self.assertRaises(RobotError):
            env.robot.is_wall_from("forward")

    def test_is_cell_painted_unpainted(self):
        env = make_env(corridor())
        self.assertFalse(env.robot.is_cell_painted())

    def test_is_cell_painted_pre_painted(self):
        env = make_env(env_dict(2, 1, final_col=1, paintedCells=[{'r': 0, 'c': 0}]))
        self.assertTrue(env.robot.is_cell_painted())

    def test_is_cell_painted_after_paint(self):
        env = make_env(corridor())
        self.assertFalse(env.robot.is_cell_painted())
        env.robot.paint()
        self.assertTrue(env.robot.is_cell_painted())

    def test_get_pollution_level_clean(self):
        env = make_env(corridor())
        self.assertEqual(env.robot.get_pollution_level(), 0)

    def test_get_pollution_level_polluted(self):
        env = make_env(env_dict(2, 1, final_col=1, pollutedCells=[{'r': 0, 'c': 0, 'value': 5}]))
        self.assertEqual(env.robot.get_pollution_level(), 5)


if __name__ == "__main__":
    unittest.main()
