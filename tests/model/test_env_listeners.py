"""Tests for environment change listeners."""

import unittest

from .helpers import attach_mock_listener, cell_1x1, corridor, make_env


class RobotEnvListenerTest(unittest.TestCase):
    def test_listener_notified_on_robot_move(self):
        env = make_env(corridor())
        listener = attach_mock_listener(env)
        env.robot.move_right()
        listener.assert_called_once()

    def test_listener_notified_on_robot_paint(self):
        env = make_env(cell_1x1())
        listener = attach_mock_listener(env)
        env.robot.paint()
        listener.assert_called_once()

    def test_listener_notified_on_robot_print_number(self):
        env = make_env(cell_1x1())
        listener = attach_mock_listener(env)
        env.robot.print_number(5)
        listener.assert_called_once()

    def test_multiple_listeners_all_notified(self):
        env = make_env(corridor())
        listener1 = attach_mock_listener(env)
        listener2 = attach_mock_listener(env)
        env.robot.move_right()
        listener1.assert_called_once()
        listener2.assert_called_once()

    def test_removed_listener_is_not_notified(self):
        env = make_env(corridor())
        listener = attach_mock_listener(env)
        env.remove_listener(listener)
        env.robot.move_right()
        listener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
