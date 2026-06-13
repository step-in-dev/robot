"""Tests for centered Tk dialog placement and string prompt."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import tkinter as tk

from robot.gui_dialogs import prompt_string_dialog, reveal_centered_toplevel

from ._helpers import emit_keypad_enter, requires_tk_display

_CENTER_TOLERANCE_PX = 3


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


def _find_first_entry(parent: tk.Misc) -> tk.Entry | None:
    for child in parent.winfo_children():
        if isinstance(child, tk.Entry):
            return child
        nested = _find_first_entry(child)
        if nested is not None:
            return nested
    return None


@requires_tk_display
class CenterToplevelOnParentTest(unittest.TestCase):
    def test_centers_child_on_parent(self) -> None:
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
            self.assertLessEqual(
                abs(parent_center[1] - child_center[1]),
                _CENTER_TOLERANCE_PX,
            )
        finally:
            root.destroy()


@requires_tk_display
class PromptStringDialogTest(unittest.TestCase):
    def test_ok_returns_entered_text(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            def wait_then_click_ok(dialog_self: tk.Toplevel) -> None:
                entry = _find_first_entry(dialog_self)
                self.assertIsNotNone(entry)
                assert entry is not None
                entry.delete(0, tk.END)
                entry.insert(0, "New condition")
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
        finally:
            root.destroy()

    def test_cancel_returns_none(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
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
        finally:
            root.destroy()

    def test_return_commits_value(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            original_wait_window = tk.Toplevel.wait_window

            def wait_then_press_return(dialog_self: tk.Toplevel) -> None:
                entry = _find_first_entry(dialog_self)
                if entry is None:
                    original_wait_window(dialog_self)
                    return
                entry.delete(0, tk.END)
                entry.insert(0, "Committed")
                entry.focus_set()
                dialog_self.update_idletasks()
                emit_keypad_enter(entry, root)

            with patch.object(tk.Toplevel, "wait_window", wait_then_press_return):
                result = prompt_string_dialog(
                    root,
                    title="Title",
                    prompt="Prompt",
                    initialvalue="Old",
                )
            self.assertEqual(result, "Committed")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
