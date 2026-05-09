from __future__ import annotations

import unittest
from unittest.mock import patch

from robot.operator_limits import (
    BANNED_KEYWORDS_MESSAGE_TEMPLATE,
    CUSTOM_FUNCTION_CALL_COUNT_MESSAGE_TEMPLATE,
    IF_LIMIT_MESSAGE_TEMPLATE,
    OPERATORS_LIMIT_MESSAGE_TEMPLATE,
    REQUIRED_KEYWORDS_MESSAGE_TEMPLATE,
    WHILE_LIMIT_MESSAGE_TEMPLATE,
    check_banned_keywords,
    check_custom_function_call_count,
    check_if_limit,
    check_operators_limit,
    check_required_keywords,
    check_while_limit,
    count_custom_function_calls_with_robot_commands,
    count_python_keyword_token_occurrences,
    count_robot_operators,
    extract_python_keywords,
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

    def test_counts_only_move_paint_printn_among_other_calls(self) -> None:
        src = (
            "task('x')\n"
            "field(8, 6)\n"
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


class CountCustomFunctionCallsTest(unittest.TestCase):
    def test_counts_qualifying_module_level_call(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "step()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 1)

    def test_declared_but_not_called_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "move_right()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_called_without_robot_command_not_counted(self) -> None:
        src = (
            "def helper():\n"
            "    x = 1\n"
            "\n"
            "helper()\n"
            "move_right()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_robot_outside_function_does_not_make_call_qualify(self) -> None:
        src = (
            "def helper():\n"
            "    pass\n"
            "\n"
            "helper()\n"
            "move_right()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_two_distinct_qualifying_calls(self) -> None:
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
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 2)

    def test_two_calls_to_same_function_count_twice(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "step()\n"
            "step()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 2)

    def test_builtin_call_not_counted_without_def(self) -> None:
        src = "len([])\nmove_right()\n"
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_nested_def_robot_does_not_satisfy_outer(self) -> None:
        src = (
            "def outer():\n"
            "    def inner():\n"
            "        move_right()\n"
            "    inner()\n"
            "\n"
            "outer()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_robot_only_inside_lambda_does_not_satisfy_outer(self) -> None:
        src = (
            "def outer():\n"
            "    (lambda: move_right())()\n"
            "\n"
            "outer()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_self_recursive_not_called_from_module_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "    step()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

    def test_called_only_from_unused_function_not_counted(self) -> None:
        src = (
            "def step():\n"
            "    move_right()\n"
            "\n"
            "def unused():\n"
            "    step()\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 0)

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
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 1)

    def test_recursive_called_from_module_counts_each_call_site_once(self) -> None:
        src = (
            "def rec(n):\n"
            "    if n:\n"
            "        move_right()\n"
            "    rec(n - 1)\n"
            "\n"
            "rec(1)\n"
        )
        self.assertEqual(count_custom_function_calls_with_robot_commands(src), 2)


class CheckCustomFunctionCallCountTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(
            check_custom_function_call_count("def f():\n    pass\nf()", None)
        )

    def test_zero_always_passes(self) -> None:
        self.assertIsNone(
            check_custom_function_call_count("move_right()", 0)
        )

    def test_violation_message(self) -> None:
        v = check_custom_function_call_count(
            "move_right()",
            1,
        )
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.actual, 0)
        self.assertEqual(v.required, 1)
        self.assertEqual(
            v.message,
            CUSTOM_FUNCTION_CALL_COUNT_MESSAGE_TEMPLATE.format(
                actual=0,
                required=1,
            ),
        )


class ExtractPythonKeywordsTest(unittest.TestCase):
    def test_collects_keywords_from_code_only(self) -> None:
        src = (
            "def run():\n"
            "    for _ in range(2):\n"
            "        if True:\n"
            "            move_right()\n"
        )
        self.assertEqual(
            extract_python_keywords(src),
            frozenset({"True", "def", "for", "if", "in"}),
        )

    def test_ignores_keywords_in_strings_and_comments(self) -> None:
        src = (
            "# for while def\n"
            "text = 'if else match case'\n"
            "move_right()\n"
        )
        self.assertEqual(extract_python_keywords(src), frozenset())

    def test_soft_keywords_do_not_count(self) -> None:
        src = (
            "match value:\n"
            "    case 1:\n"
            "        move_right()\n"
        )
        self.assertEqual(extract_python_keywords(src), frozenset())


class CountPythonKeywordTokenOccurrencesTest(unittest.TestCase):
    def test_counts_if_and_while_tokens(self) -> None:
        src = (
            "if True:\n"
            "    while False:\n"
            "        pass\n"
        )
        self.assertEqual(count_python_keyword_token_occurrences(src, "if"), 1)
        self.assertEqual(count_python_keyword_token_occurrences(src, "while"), 1)

    def test_ignores_keywords_in_strings_and_comments(self) -> None:
        src = (
            "# if while\n"
            "s = 'if while'\n"
            "move_right()\n"
        )
        self.assertEqual(count_python_keyword_token_occurrences(src, "if"), 0)
        self.assertEqual(count_python_keyword_token_occurrences(src, "while"), 0)

    def test_counts_ternary_if_tokens(self) -> None:
        src = "a = 1 if True else 0\n"
        self.assertEqual(count_python_keyword_token_occurrences(src, "if"), 1)

    def test_repeated_if_tokens(self) -> None:
        src = (
            "if True:\n"
            "    pass\n"
            "if False:\n"
            "    pass\n"
        )
        self.assertEqual(count_python_keyword_token_occurrences(src, "if"), 2)


class CheckIfLimitTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(check_if_limit("if True:\n    pass\n", None))

    def test_within_limit(self) -> None:
        self.assertIsNone(
            check_if_limit(
                "if True:\n    pass\n",
                1,
            )
        )

    def test_exceeds_returns_violation_with_message(self) -> None:
        v = check_if_limit(
            "if True:\n    pass\nif False:\n    pass\n",
            1,
        )
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.actual, 2)
        self.assertEqual(v.limit, 1)
        self.assertEqual(
            v.message,
            IF_LIMIT_MESSAGE_TEMPLATE.format(actual=2, limit=1),
        )


class CheckWhileLimitTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(check_while_limit("while False:\n    pass\n", None))

    def test_within_limit(self) -> None:
        self.assertIsNone(
            check_while_limit(
                "while False:\n    pass\n",
                1,
            )
        )

    def test_exceeds_returns_violation_with_message(self) -> None:
        v = check_while_limit(
            "while False:\n    pass\nwhile False:\n    pass\n",
            1,
        )
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.actual, 2)
        self.assertEqual(v.limit, 1)
        self.assertEqual(
            v.message,
            WHILE_LIMIT_MESSAGE_TEMPLATE.format(actual=2, limit=1),
        )


class CheckRequiredKeywordsTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(check_required_keywords("move_right()", None))

    def test_passes_when_all_keywords_are_present(self) -> None:
        src = (
            "def go():\n"
            "    for _ in range(1):\n"
            "        move_right()\n"
        )
        self.assertIsNone(check_required_keywords(src, ("def", "for")))

    def test_violation_lists_missing_keywords(self) -> None:
        v = check_required_keywords("move_right()", ("def", "for"))
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.missing_keywords, ("def", "for"))
        self.assertEqual(
            v.message,
            REQUIRED_KEYWORDS_MESSAGE_TEMPLATE.format(keywords="def, for"),
        )


class CheckBannedKeywordsTest(unittest.TestCase):
    def test_none_skips(self) -> None:
        self.assertIsNone(check_banned_keywords("move_right()", None))

    def test_passes_when_banned_keywords_are_absent(self) -> None:
        src = "move_right()\n"
        self.assertIsNone(check_banned_keywords(src, ("for", "while")))

    def test_violation_lists_used_banned_keywords(self) -> None:
        src = (
            "while True:\n"
            "    break\n"
        )
        v = check_banned_keywords(src, ("for", "while", "True"))
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.used_keywords, ("while", "True"))
        self.assertEqual(
            v.message,
            BANNED_KEYWORDS_MESSAGE_TEMPLATE.format(keywords="while, True"),
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
                "Команд Робота: 3. Можно не больше 2",
            )

    def test_custom_function_call_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.custom_function_calls", actual=3, required=2),
                "Вызовов своих функций: 3. Нужно не меньше 2",
            )

    def test_required_keywords_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.required_keywords", keywords="for, def"),
                "В решении требуются слова: for, def",
            )

    def test_banned_keywords_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.banned_keywords", keywords="while"),
                "В решении запрещены слова: while",
            )

    def test_if_keyword_limit_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.if_keyword", actual=2, limit=1),
                "«if» использовано: 2. Разрешено не более 1",
            )

    def test_while_keyword_limit_message_russian_via_t(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            from robot import i18n

            i18n.clear_translation_cache()
            self.assertEqual(
                i18n.t("limit.while_keyword", actual=3, limit=1),
                "«while» использовано: 3. Разрешено не более 1",
            )


if __name__ == "__main__":
    unittest.main()
