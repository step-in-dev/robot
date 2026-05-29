"""Tests for environment change listeners."""

import unittest
from unittest.mock import MagicMock

from .helpers import make_env


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


if __name__ == "__main__":
    unittest.main()
