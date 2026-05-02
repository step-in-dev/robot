from __future__ import annotations

import unittest
from unittest.mock import patch

from robot.operator_limits import (
    MIN_USED_USER_FUNCTIONS_MESSAGE_TEMPLATE,
    OPERATORS_LIMIT_MESSAGE_TEMPLATE,
    check_min_used_user_functions,
    check_operators_limit,
    count_robot_operators,
    count_used_user_functions_with_robot_commands,
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


class CountUsedUserFunctionsTest(unittest.TestCase):
    def test_counts_function_with_call_and_robot_command(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "step()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 1)

    def test_declared_but_not_called_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "move_right()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_called_without_robot_command_not_counted(self) -> None:
        src = (
            "def helper():\n"
            "    x = 1\n"
            "\n"
            "helper()\n"
            "move_right()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_robot_outside_function_does_not_count_function(self) -> None:
        src = (
            "def helper():\n"
            "    pass\n"
            "\n"
            "helper()\n"
            "move_right()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_two_distinct_functions(self) -> None:
        src = (
            "def a():\n"
            "    move_right()\n"
            "\n"
            "def b():\n"
            "    move_left()\n"
            "\n"
            "a()\n"
            "b()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 2)

    def test_builtin_call_not_counted_without_def(self) -> None:
        src = "len([])\nmove_right()\n"
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_nested_def_robot_does_not_satisfy_outer(self) -> None:
        src = (
            "def outer():\n"
            "    def inner():\n"
            "        move_right()\n"
            "    inner()\n"
            "\n"
            "outer()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_robot_only_inside_lambda_does_not_satisfy_outer(self) -> None:
        src = (
            "def outer():\n"
            "    (lambda: move_right())()\n"
            "\n"
            "outer()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_self_recursive_not_called_from_module_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "    step()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_called_only_from_unused_function_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "def unused():\n"
            "    step()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 0)

    def test_transitive_call_from_reachable_function_counts_inner(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "def go():\n"
            "    step()\n"
            "\n"
            "go()\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 1)

    def test_recursive_called_from_module_does_not_loop(self) -> None:
        src = (
            "def rec(n):\n"
            "    if n:\n"
            "        move_right()\n"
            "    rec(n - 1)\n"
            "\n"
            "rec(1)\n"
        )
        self.assertEqual(count_used_user_functions_with_robot_commands(src), 1)


class CheckMinUsedUserFunctionsTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(
            check_min_used_user_functions("def f():\n    pass\nf()", None)
        )

    def test_zero_always_passes(self) -> None:
        self.assertIsNone(
            check_min_used_user_functions("move_right()", 0)
        )

    def test_violation_message(self) -> None:
        v = check_min_used_user_functions(
            "move_right()",
            1,
        )
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.actual, 0)
        self.assertEqual(v.required, 1)
        self.assertEqual(
            v.message,
            MIN_USED_USER_FUNCTIONS_MESSAGE_TEMPLATE.format(
                actual=0,
                required=1,
            ),
        )


class OperatorLimitsRussianLocaleTest(unittest.TestCase):
    """Russian strings via ``t()`` when ``ROBOT_LANGUAGE`` is set."""

    def tearDown(self) -> None:
        from robot import i18n

        i18n.clear_translation_cache()

    def test_operator_limit_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.operators", actual=3, limit=2),
                "Использовано команд Робота: 3. Разрешено не более 2",
            )


if __name__ == "__main__":
    unittest.main()
