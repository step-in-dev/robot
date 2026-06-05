"""Tests for help window and read-only key filter."""

import unittest
from typing import List, Optional, cast
from unittest.mock import MagicMock, patch

import tkinter as tk

from robot.gui_help import _HELP_AUTHOR_NAME, _help_text_readonly_key_action
from robot.i18n import t

from ._helpers import (
    GuiTestCase,
    _find_first_text_widget,
    cell_1x1,
    clear_i18n_cache,
    make_env,
    noop_success_run_env,
    requires_tk_display,
    test_window,
)

_EXPECTED_HELP_PROJECT_REPO_URL = "https://github.com/step-in-dev/robot"


def _help_toplevel_children(root: tk.Misc) -> List[tk.Toplevel]:
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


def _help_window_body_text(help_top: tk.Toplevel) -> str:
    widget = _find_first_text_widget(help_top)
    if widget is None:
        return ""
    return widget.get("1.0", tk.END)


class HelpReadonlyKeyFilterTest(unittest.TestCase):
    """Regression: help ``Text`` stays read-only.

    Copy must work (``<Key>`` handler must not use bare ``break``).
    """

    @staticmethod
    def _help_key(
        keysym: str,
        *,
        state: int = 0,
        char: str = "",
    ) -> Optional[str]:
        from types import SimpleNamespace

        return _help_text_readonly_key_action(
            cast(
                tk.Event,
                SimpleNamespace(keysym=keysym, state=state, char=char),
            )
        )

    def test_help_readonly_allows_copy_and_select_all(self) -> None:
        for modifier_state in (0x0004, 0x0008):  # Ctrl, Meta
            with self.subTest(modifier_state=modifier_state):
                self.assertIsNone(self._help_key("c", state=modifier_state))
                self.assertIsNone(self._help_key("a", state=modifier_state))

    def test_help_readonly_allows_escape_and_keypad_navigation(self) -> None:
        self.assertIsNone(self._help_key("Escape"))
        self.assertIsNone(self._help_key("KP_Left"))

    def test_help_readonly_blocks_paste_cut_and_editing_keys(self) -> None:
        self.assertEqual(self._help_key("v", state=0x0004), "break")
        self.assertEqual(self._help_key("x", state=0x0004), "break")
        self.assertIsNone(self._help_key("Insert", state=0x0004))
        self.assertEqual(self._help_key("KP_Enter"), "break")

    def test_help_readonly_blocks_plain_printable_keys(self) -> None:
        self.assertEqual(self._help_key("x", char="x"), "break")


@requires_tk_display
class RobotWindowHelpTest(GuiTestCase):
    def tearDown(self) -> None:
        clear_i18n_cache()
        super().tearDown()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_help_opens_toplevel_with_expected_title_and_body(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("help_win", envs, noop_success_run_env) as window:
            window.show_help()
            window.root.update()
            tops = _help_toplevel_children(window.root)
            self.assertEqual(len(tops), 1)
            self.assertEqual(tops[0].title(), t("help.title"))
            body = _help_window_body_text(tops[0])
            self.assertIn(t("help.module_intro"), body)
            self.assertIn(t("help.author", author=_HELP_AUTHOR_NAME), body)
            self.assertIn(_EXPECTED_HELP_PROJECT_REPO_URL, body)
            self.assertIn("move_right()", body)
            self.assertIn(t("help.command.move_right"), body)
            self.assertIn("field(width=8, height=6)", body)
            self.assertIn(t("help.command.field"), body)
            self.assertIn("20", body)
            self.assertIn("15", body)

    @patch("robot.gui_help.webbrowser.open")
    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_help_repo_link_click_opens_browser(self, open_mock: MagicMock) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("help_link", envs, noop_success_run_env) as window:
            window.show_help()
            window.root.update_idletasks()
            tops = _help_toplevel_children(window.root)
            self.assertEqual(len(tops), 1)
            text = _find_first_text_widget(tops[0])
            self.assertIsNotNone(text)
            assert text is not None
            ranges = text.tag_ranges("help_repo_link")
            self.assertEqual(len(ranges), 2)
            self.assertEqual(
                text.get(ranges[0], ranges[1]), _EXPECTED_HELP_PROJECT_REPO_URL
            )
            # bbox() is None for off-screen indices (Windows help layout).
            text.see(ranges[0])
            text.update_idletasks()
            window.root.update_idletasks()
            bbox = text.bbox(ranges[0])
            self.assertIsNotNone(bbox)
            x = int(bbox[0] + max(bbox[2], 1) / 2)
            y = int(bbox[1] + max(bbox[3], 1) / 2)
            text.focus_set()
            text.event_generate("<Button-1>", x=x, y=y)
            window.root.update()
            open_mock.assert_called_once_with(_EXPECTED_HELP_PROJECT_REPO_URL)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_help_escape_dismisses_help_but_not_main(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("help_escape", envs, noop_success_run_env) as window:
            window.show_help()
            window.root.update()
            tops = _help_toplevel_children(window.root)
            self.assertEqual(len(tops), 1)
            help_top = tops[0]
            text = _find_first_text_widget(help_top)
            self.assertIsNotNone(text)
            text.focus_set()
            text.event_generate("<Escape>", when="tail")
            window.root.update()
            self.assertIsNone(window._help_window)
            self.assertIsNone(window._help_window_close_handler)
            self.assertFalse(window.is_closed)
            self.assertEqual(window.root.winfo_exists(), 1)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_help_second_open_lifts_same_window(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("help_reuse", envs, noop_success_run_env) as window:
            window.show_help()
            window.root.update()
            first = _help_toplevel_children(window.root)[0]
            window.show_help()
            window.root.update()
            tops = _help_toplevel_children(window.root)
            self.assertEqual(len(tops), 1)
            self.assertIs(tops[0], first)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_help_reopens_after_wm_delete_window_handler(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("help_reopen", envs, noop_success_run_env) as window:
            window.show_help()
            window.root.update()
            first = window._help_window
            self.assertIsNotNone(first)
            self.assertIsNotNone(window._help_window_close_handler)
            window._help_window_close_handler()
            window.root.update()
            self.assertIsNone(window._help_window)
            self.assertIsNone(window._help_window_close_handler)

            window.show_help()
            window.root.update()
            second = window._help_window
            self.assertIsNotNone(second)
            self.assertIsNot(first, second)
            self.assertEqual(len(_help_toplevel_children(window.root)), 1)


if __name__ == "__main__":
    unittest.main()
