"""Tests for robot movement and wall handling."""

import unittest

from robot.model import RobotPathError

from .helpers import make_env, corridor, env_dict


class RobotMovementTest(unittest.TestCase):
    def test_initial_position(self):
        env = make_env(env_dict(5, 5, start_row=2, start_col=3, final_row=4, final_col=4))
        self.assertEqual((env.robot.row, env.robot.col), (2, 3))

    def test_move_right_success(self):
        env = make_env(env_dict(3, 1, final_col=2))
        env.robot.move_right()
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_move_left_success(self):
        env = make_env(env_dict(3, 1, start_col=2))
        env.robot.move_left()
        self.assertEqual((env.robot.row, env.robot.col), (0, 1))

    def test_move_up_success(self):
        env = make_env(env_dict(1, 3, start_row=2))
        env.robot.move_up()
        self.assertEqual((env.robot.row, env.robot.col), (1, 0))

    def test_move_down_success(self):
        env = make_env(env_dict(1, 3, final_row=2))
        env.robot.move_down()
        self.assertEqual((env.robot.row, env.robot.col), (1, 0))

    def test_move_right_into_border_raises(self):
        env = make_env(corridor())
        env.robot.move_right()
        with self.assertRaises(RobotPathError):
            env.robot.move_right()

    def test_move_left_into_border_raises(self):
        env = make_env(env_dict(2, 1, start_col=1))
        env.robot.move_left()
        with self.assertRaises(RobotPathError):
            env.robot.move_left()

    def test_move_up_into_border_raises(self):
        env = make_env(env_dict(1, 2, start_row=1))
        env.robot.move_up()
        with self.assertRaises(RobotPathError):
            env.robot.move_up()

    def test_move_down_into_border_raises(self):
        env = make_env(env_dict(1, 2, final_row=1))
        env.robot.move_down()
        with self.assertRaises(RobotPathError):
            env.robot.move_down()

    def test_move_right_into_internal_wall_raises(self):
        env = make_env(env_dict(2, 1, final_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        self.assertTrue(env.robot.is_wall_from("right"))
        with self.assertRaises(RobotPathError):
            env.robot.move_right()

    def test_move_left_into_internal_wall_raises(self):
        env = make_env(env_dict(2, 1, start_col=1, walls=[[{'r': 0, 'c': 0}, {'r': 0, 'c': 1}]]))
        self.assertTrue(env.robot.is_wall_from("left"))
        with self.assertRaises(RobotPathError):
            env.robot.move_left()

    def test_move_up_into_internal_wall_raises(self):
        env = make_env(env_dict(1, 2, start_row=1, walls=[[{'r': 0, 'c': 0}, {'r': 1, 'c': 0}]]))
        self.assertTrue(env.robot.is_wall_from("up"))
        with self.assertRaises(RobotPathError):
            env.robot.move_up()

    def test_move_down_into_internal_wall_raises(self):
        env = make_env(env_dict(1, 2, final_row=1, walls=[[{'r': 0, 'c': 0}, {'r': 1, 'c': 0}]]))
        self.assertTrue(env.robot.is_wall_from("down"))
        with self.assertRaises(RobotPathError):
            env.robot.move_down()


if __name__ == "__main__":
    unittest.main()
