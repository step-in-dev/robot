"""Tests for robot position and internal state."""

import unittest
from unittest.mock import MagicMock

from .helpers import make_env, cell_1x1, env_dict


class RobotStateTest(unittest.TestCase):
    def test_reset_restores_position(self):
        env = make_env(env_dict(3, 1, final_col=2))
        env.robot.move_right()
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))
        env.robot.reset()
        self.assertEqual((env.robot.row, env.robot.col), (0, 0))

    def test_reset_notifies_listener(self):
        env = make_env(cell_1x1())
        listener = MagicMock()
        env.add_listener(listener)
        env.robot.reset()
        listener.assert_called_once()

    def test_reset_sensors_still_work(self):
        env = make_env(env_dict(2, 1, final_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        env.robot.reset()
        self.assertTrue(env.robot.is_wall_from("right"))
        self.assertTrue(env.robot.is_wall_from("left"))


if __name__ == "__main__":
    unittest.main()
