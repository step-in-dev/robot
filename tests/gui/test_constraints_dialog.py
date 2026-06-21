"""Tests for RobotWindow constraints dialog and top toolbar."""

from typing import List

import unittest
from unittest.mock import patch

import tkinter as tk

from robot.loader import ScriptConstraints
from robot.i18n import t

from ._helpers import (
    GuiTestCase,
    find_first_text_widget,
    cell_1x1,
    clear_i18n_cache,
    make_env,
    make_test_window,
    noop_success_run_env,
    requires_tk_display,
    test_window,
)


def _toplevels_with_title(root: tk.Misc, title: str) -> List[tk.Toplevel]:
    return [
        w
        for w in root.winfo_children()
        if isinstance(w, tk.Toplevel) and w.title() == title
    ]


@requires_tk_display
class RobotWindowConstraintsTest(GuiTestCase):
    def tearDown(self) -> None:
        clear_i18n_cache()
        super().tearDown()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_no_constraints_no_top_toolbar_single_env(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window("no_lim", envs, noop_success_run_env) as window:
            self.assertIsNone(window.top_toolbar)
            self.assertIsNone(window.constraints_button)
            self.assertEqual(window.tab_buttons, [])

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_multi_env_without_constraints_has_top_bar_only_tabs(self) -> None:
        clear_i18n_cache()
        base = cell_1x1()
        envs = [make_env(dict(base)), make_env(dict(base))]

        with test_window("two_env", envs, noop_success_run_env) as window:
            self.assertIsNotNone(window.top_toolbar)
            self.assertIsNotNone(window.tab_frame)
            self.assertIsNone(window.constraints_button)
            self.assertEqual(len(window.tab_buttons), 2)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_button_top_right_single_env(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        with test_window(
            "one_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(operators_limit=5),
        ) as window:
            self.assertIsNotNone(window.top_toolbar)
            self.assertIsNotNone(window.constraints_button)
            self.assertIs(window.tab_frame.master, window.top_toolbar)
            self.assertIs(window.constraints_button.master, window.top_toolbar)
            slaves = list(window.top_toolbar.pack_slaves())
            self.assertEqual(slaves, [window.tab_frame, window.constraints_button])

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_with_multi_env_tabs_left_button_right(self) -> None:
        clear_i18n_cache()
        base = cell_1x1()
        envs = [make_env(dict(base)), make_env(dict(base))]

        window = make_test_window(
            "two_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(while_limit=0),
        )
        try:
            self.assertEqual(len(window.tab_buttons), 2)
            self.assertIsNotNone(window.constraints_button)
            slaves = list(window.top_toolbar.pack_slaves())
            self.assertEqual(slaves, [window.tab_frame, window.constraints_button])
        finally:
            window.close()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_dialog_lists_only_active_limits(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        window = make_test_window(
            "dlg_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(
                operators_limit=3,
                required_keywords=("for", "def"),
            ),
        )
        try:
            window.show_constraints()
            window.root.update()
            tops = _toplevels_with_title(window.root, t("constraints.title"))
            self.assertEqual(len(tops), 1)
            text_w = find_first_text_widget(tops[0])
            self.assertIsNotNone(text_w)
            body = text_w.get("1.0", tk.END)
            self.assertIn(
                t("constraints.operators_max", limit=3),
                body,
            )
            self.assertIn(
                t("constraints.required_keywords", keywords="for, def"),
                body,
            )
            self.assertNotIn(
                t("constraints.while_max", limit=0),
                body,
            )
        finally:
            window.close()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_escape_dismisses_dialog_but_not_main(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        window = make_test_window(
            "esc_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(if_limit=1),
        )
        try:
            window.show_constraints()
            window.root.update()
            tops = _toplevels_with_title(window.root, t("constraints.title"))
            self.assertEqual(len(tops), 1)
            text = find_first_text_widget(tops[0])
            self.assertIsNotNone(text)
            text.focus_set()
            text.event_generate("<Escape>", when="tail")
            window.root.update()
            self.assertIsNone(window._constraints_window)
            self.assertIsNone(window._constraints_window_close_handler)
            self.assertFalse(window.is_closed)
            self.assertEqual(window.root.winfo_exists(), 1)
        finally:
            window.close()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_second_open_lifts_same_window(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        window = make_test_window(
            "reuse_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(banned_keywords=("while",)),
        )
        try:
            window.show_constraints()
            window.root.update()
            first = _toplevels_with_title(window.root, t("constraints.title"))[0]
            window.show_constraints()
            window.root.update()
            tops = _toplevels_with_title(window.root, t("constraints.title"))
            self.assertEqual(len(tops), 1)
            self.assertIs(tops[0], first)
        finally:
            window.close()

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False)
    def test_constraints_reopens_after_wm_delete_window(self) -> None:
        clear_i18n_cache()
        envs = [make_env(cell_1x1())]

        window = make_test_window(
            "reopen_lim",
            envs,
            noop_success_run_env,
            constraints=ScriptConstraints(custom_function_call_count=2),
        )
        try:
            window.show_constraints()
            window.root.update()
            first = window._constraints_window
            self.assertIsNotNone(first)
            self.assertIsNotNone(window._constraints_window_close_handler)
            window._constraints_window_close_handler()
            window.root.update()
            self.assertIsNone(window._constraints_window)
            self.assertIsNone(window._constraints_window_close_handler)

            window.show_constraints()
            window.root.update()
            second = window._constraints_window
            self.assertIsNotNone(second)
            self.assertIsNot(first, second)
            self.assertEqual(
                len(_toplevels_with_title(window.root, t("constraints.title"))),
                1,
            )
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
