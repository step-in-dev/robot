"""Tests for localized student command help text."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import robot
from robot import command_help, i18n


class CommandHelpTest(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.clear_translation_cache()

    def test_public_keys_match_student_exports(self) -> None:
        self.assertEqual(
            command_help.command_help_public_keys(),
            frozenset(robot.__all__),
        )

    def test_signatures_include_parentheses(self) -> None:
        for signature, _desc in command_help.iter_command_help():
            self.assertIn("(", signature)
            self.assertIn(")", signature)

    def test_descriptions_switch_with_language(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            i18n.clear_translation_cache()
            _, en_desc = next(
                (s, d)
                for s, d in command_help.iter_command_help()
                if s.startswith("move_right")
            )
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            i18n.clear_translation_cache()
            _, ru_desc = next(
                (s, d)
                for s, d in command_help.iter_command_help()
                if s.startswith("move_right")
            )
        self.assertNotEqual(en_desc, ru_desc)


if __name__ == "__main__":
    unittest.main()
