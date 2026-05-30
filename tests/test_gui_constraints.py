"""Tests for task constraint detection helpers."""

import unittest

from robot.gui_constraints import task_has_any_constraints
from robot.loader import ScriptConstraints


class TaskHasAnyConstraintsTest(unittest.TestCase):
    def test_empty_constraints_returns_false(self) -> None:
        self.assertFalse(task_has_any_constraints())
        self.assertFalse(task_has_any_constraints(ScriptConstraints()))

    def test_single_constraint_returns_true(self) -> None:
        cases = (
            ScriptConstraints(operators_limit=5),
            ScriptConstraints(custom_function_call_count=2),
            ScriptConstraints(if_limit=1),
            ScriptConstraints(while_limit=2),
            ScriptConstraints(required_keywords=("while",)),
            ScriptConstraints(banned_keywords=("for",)),
        )
        for constraints in cases:
            with self.subTest(constraints=constraints):
                self.assertTrue(task_has_any_constraints(constraints))

    def test_empty_keyword_tuples_return_false(self) -> None:
        self.assertFalse(
            task_has_any_constraints(
                ScriptConstraints(
                    required_keywords=(),
                    banned_keywords=(),
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
