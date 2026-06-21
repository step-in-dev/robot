"""Tests for centered Tk dialog placement and string prompt."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

import tkinter as tk

from robot.gui_dialogs import (
    center_toplevel_on_parent,
    create_dialog_string_field,
    prompt_string_dialog,
    reveal_centered_toplevel,
)
from robot.tk_util import flush_tk_events

from ._helpers import (
    dialog_test_root,
    find_first_text_widget,
    press_return_in_dialog_string_field,
    requires_tk_display,
    set_dialog_string_field,
    withdrawn_root,
)

# Windows Tk root vs Toplevel client metrics can differ by one frame border (~8 px).
_CENTER_TOLERANCE_PX = 8 if sys.platform == "win32" else 3
_FRAME_PADDING_TOLERANCE_PX = 12


def _widget_right_edge(widget: tk.Misc) -> int:
    widget.update_idletasks()
    return widget.winfo_rootx() + widget.winfo_width()


def _parse_wm_geometry(geometry: str) -> tuple[int, int, int, int]:
    size_part, x_str, y_str = geometry.split("+", 2)
    width_str, height_str = size_part.split("x", 1)
    return int(width_str), int(height_str), int(x_str), int(y_str)


def _window_center(win: tk.Misc) -> tuple[int, int]:
    win.update_idletasks()
    return (
        win.winfo_rootx() + win.winfo_width() // 2,
        win.winfo_rooty() + win.winfo_height() // 2,
    )


def _find_buttons(parent: tk.Misc) -> list[tk.Button]:
    buttons: list[tk.Button] = []
    for child in parent.winfo_children():
        if isinstance(child, tk.Button):
            buttons.append(child)
            continue
        buttons.extend(_find_buttons(child))
    return buttons


@requires_tk_display
class CreateDialogStringFieldTest(unittest.TestCase):
    def test_tab_focus_chain_follows_widget_order(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            dialog = tk.Toplevel(root)
            first = create_dialog_string_field(dialog, initialvalue="a")
            second = create_dialog_string_field(dialog, initialvalue="b")
            ok_button = tk.Button(dialog, text="OK")
            first.pack()
            second.pack()
            ok_button.pack()
            dialog.update()
            self.assertIs(first.tk_focusNext(), second)
            self.assertIs(second.tk_focusNext(), ok_button)
            self.assertIs(ok_button.tk_focusNext(), first)
        finally:
            root.destroy()

    def test_tab_binding_does_not_insert_tab_character(self) -> None:
        root = tk.Tk()
        try:
            field = create_dialog_string_field(root, initialvalue="abc")
            field.pack()
            field.focus_set()
            root.update()
            field.event_generate("<Tab>")
            root.update()
            self.assertEqual(field.get("1.0", "end-1c"), "abc")
        finally:
            root.destroy()

    def test_control_y_binding_redoes_undone_text(self) -> None:
        root = tk.Tk()
        try:
            field = create_dialog_string_field(root, initialvalue="Old")
            field.pack()
            field.focus_set()
            root.update()
            field.insert(tk.END, " added")
            field.edit_undo()
            self.assertEqual(field.get("1.0", "end-1c"), "Old")
            field.event_generate("<Control-y>")
            root.update()
            self.assertEqual(field.get("1.0", "end-1c"), "Old added")
        finally:
            root.destroy()

    def test_control_shift_z_binding_redoes_undone_text(self) -> None:
        root = tk.Tk()
        try:
            field = create_dialog_string_field(root, initialvalue="Old")
            field.pack()
            field.focus_set()
            root.update()
            field.insert(tk.END, " added")
            field.edit_undo()
            self.assertEqual(field.get("1.0", "end-1c"), "Old")
            field.event_generate("<Control-Shift-z>")
            root.update()
            self.assertEqual(field.get("1.0", "end-1c"), "Old added")
        finally:
            root.destroy()


@requires_tk_display
class CenterToplevelOnParentTest(unittest.TestCase):
    def test_centers_child_horizontally_on_parent(self) -> None:
        """Visual X centering after reveal (Y is checked via wm_geometry below)."""
        root = tk.Tk()
        root.geometry("400x300+100+200")
        try:
            child = tk.Toplevel(root)
            child.withdraw()
            tk.Label(child, text="dialog", width=20, height=5).pack()
            reveal_centered_toplevel(child, root)
            root.update_idletasks()
            child.update_idletasks()

            parent_center = _window_center(root)
            child_center = _window_center(child)
            self.assertLessEqual(
                abs(parent_center[0] - child_center[0]),
                _CENTER_TOLERANCE_PX,
            )
        finally:
            root.destroy()

    def test_center_toplevel_geometry_matches_parent(self) -> None:
        """Algorithm sets wm_geometry centered on parent in both axes."""
        root = tk.Tk()
        root.geometry("400x300+100+200")
        try:
            parent = tk.Frame(root, width=360, height=240)
            parent.place(x=20, y=30)
            parent.update_idletasks()

            child = tk.Toplevel(root)
            child.withdraw()
            tk.Label(child, text="dialog", width=20, height=5).pack()
            child.update_idletasks()

            center_toplevel_on_parent(child, parent)
            parent.update_idletasks()
            child.update_idletasks()

            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            child_width, child_height, child_x, child_y = _parse_wm_geometry(
                child.wm_geometry()
            )
            expected_x = parent_x + (parent_width - child_width) // 2
            expected_y = parent_y + (parent_height - child_height) // 2
            self.assertEqual(child_x, expected_x)
            self.assertEqual(child_y, expected_y)
            self.assertGreater(child_width, 0)
            self.assertGreater(child_height, 0)
        finally:
            root.destroy()


@requires_tk_display
class PromptStringDialogTest(unittest.TestCase):
    def test_ok_returns_entered_text(self) -> None:
        with dialog_test_root() as root:
            def wait_then_click_ok(dialog_self: tk.Toplevel) -> None:
                text_field = find_first_text_widget(dialog_self)
                self.assertIsNotNone(text_field)
                assert text_field is not None
                set_dialog_string_field(text_field, "New condition")
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 1)
                buttons[0].invoke()

            with patch.object(tk.Toplevel, "wait_window", wait_then_click_ok):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertEqual(result, "New condition")

    def test_cancel_returns_none(self) -> None:
        with withdrawn_root() as root:
            def wait_then_click_cancel(dialog_self: tk.Toplevel) -> None:
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 2)
                buttons[1].invoke()

            with patch.object(tk.Toplevel, "wait_window", wait_then_click_cancel):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertIsNone(result)

    def test_return_commits_value(self) -> None:
        with withdrawn_root() as root:
            def wait_then_press_return(dialog_self: tk.Toplevel) -> None:
                field = press_return_in_dialog_string_field(
                    dialog_self,
                    text="Committed",
                    use_keypad=True,
                )
                self.assertIsNotNone(field)

            with patch.object(tk.Toplevel, "wait_window", wait_then_press_return):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertEqual(result, "Committed")

    def test_text_field_receives_focus_on_open(self) -> None:
        with dialog_test_root() as root:
            def wait_then_check_focus(dialog_self: tk.Toplevel) -> None:
                flush_tk_events(dialog_self, max_rounds=10)
                text_field = find_first_text_widget(dialog_self)
                self.assertIsNotNone(text_field)
                assert text_field is not None
                self.assertIs(text_field, dialog_self.focus_get())
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 1)
                buttons[0].invoke()

            with patch.object(
                tk.Toplevel, "wait_window", wait_then_check_focus
            ):
                prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )

    def test_edit_undo_restores_previous_text(self) -> None:
        with dialog_test_root() as root:
            def wait_then_undo(dialog_self: tk.Toplevel) -> None:
                flush_tk_events(dialog_self, max_rounds=10)
                text_field = find_first_text_widget(dialog_self)
                self.assertIsNotNone(text_field)
                assert text_field is not None
                self.assertEqual(text_field.get("1.0", "end-1c"), "Old")
                text_field.insert(tk.END, " added")
                self.assertEqual(text_field.get("1.0", "end-1c"), "Old added")
                text_field.edit_undo()
                self.assertEqual(text_field.get("1.0", "end-1c"), "Old")
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 1)
                buttons[0].invoke()

            with patch.object(tk.Toplevel, "wait_window", wait_then_undo):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertEqual(result, "Old")

    def test_edit_redo_restores_undone_text(self) -> None:
        with dialog_test_root() as root:
            def wait_then_redo(dialog_self: tk.Toplevel) -> None:
                flush_tk_events(dialog_self, max_rounds=10)
                text_field = find_first_text_widget(dialog_self)
                self.assertIsNotNone(text_field)
                assert text_field is not None
                text_field.insert(tk.END, " added")
                text_field.edit_undo()
                self.assertEqual(text_field.get("1.0", "end-1c"), "Old")
                text_field.edit_redo()
                self.assertEqual(text_field.get("1.0", "end-1c"), "Old added")
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 1)
                buttons[0].invoke()

            with patch.object(tk.Toplevel, "wait_window", wait_then_redo):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertEqual(result, "Old added")

    def test_cancel_button_aligned_right(self) -> None:
        with dialog_test_root() as root:
            def wait_then_check_alignment(dialog_self: tk.Toplevel) -> None:
                dialog_self.update_idletasks()
                buttons = _find_buttons(dialog_self)
                self.assertGreaterEqual(len(buttons), 2)
                cancel_button = buttons[-1]
                dialog_right = _widget_right_edge(dialog_self)
                cancel_right = _widget_right_edge(cancel_button)
                self.assertLessEqual(
                    abs(dialog_right - cancel_right),
                    _FRAME_PADDING_TOLERANCE_PX,
                )
                buttons[0].invoke()

            with patch.object(
                tk.Toplevel, "wait_window", wait_then_check_alignment
            ):
                prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )


if __name__ == "__main__":
    unittest.main()
