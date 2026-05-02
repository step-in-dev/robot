from __future__ import annotations

import unittest

from robot.operator_limits import (
    OPERATORS_LIMIT_MESSAGE_TEMPLATE,
    check_operators_limit,
    count_robot_operators,
)


class CountRobotOperatorsTest(unittest.TestCase):
    def test_counts_six_commands(self) -> None:
        src = (
            "move_right()\n"
            "move_left()\n"
            "move_up()\n"
            "move_down()\n"
            "paint()\n"
            "printn(1)\n"
        )
        self.assertEqual(count_robot_operators(src), 6)

    def test_loop_body_counts_once(self) -> None:
        src = "for _ in range(10):\n    move_right()\n"
        self.assertEqual(count_robot_operators(src), 1)

    def test_ignores_probes_pol_task(self) -> None:
        src = (
            "task('x')\n"
            "if is_free_right():\n"
            "    move_right()\n"
            "pol()\n"
            "is_wall_left()\n"
        )
        self.assertEqual(count_robot_operators(src), 1)


class CheckOperatorsLimitTest(unittest.TestCase):
    def test_none_limit_skips(self) -> None:
        self.assertIsNone(check_operators_limit("move_right()", None))

    def test_within_limit(self) -> None:
        self.assertIsNone(
            check_operators_limit("move_right()\nmove_right()", 2)
        )

    def test_exceeds_returns_violation_with_message(self) -> None:
        v = check_operators_limit(
            "move_right()\nmove_right()\nmove_right()", 2
        )
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.actual, 3)
        self.assertEqual(v.limit, 2)
        self.assertEqual(
            v.message,
            OPERATORS_LIMIT_MESSAGE_TEMPLATE.format(actual=3, limit=2),
        )


if __name__ == "__main__":
    unittest.main()
