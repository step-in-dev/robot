"""Tests for Tkinter tooltip lifecycle handling."""

from __future__ import annotations

import tkinter as tk

from robot.gui_tooltip import bind_tooltip
from robot.tk_util import destroy_tk_root
from tests.tk_display import GuiTestCase, requires_tk_display


class TooltipLifecycleTest(GuiTestCase):
    @requires_tk_display
    def test_destroy_clears_pending_callback_and_open_tooltip(self) -> None:
        errors = []
        root = tk.Tk()

        def capture_callback_exception(exc_type, exc_value, _traceback) -> None:
            errors.append((exc_type, exc_value))

        root.report_callback_exception = capture_callback_exception
        try:
            button = tk.Button(root, text="hover")
            button.pack()
            bind_tooltip(button, "Tooltip", delay_ms=10)

            button.event_generate("<Enter>")
            root.update()
            button.destroy()
            root.after(30, root.quit)
            root.mainloop()

            self.assertEqual(errors, [])
            self.assertEqual(root.winfo_children(), [])

            second_button = tk.Button(root, text="hover again")
            second_button.pack()
            bind_tooltip(second_button, "Tooltip", delay_ms=0)

            second_button.event_generate("<Enter>")
            root.update()

            second_button.destroy()
            root.update()
            self.assertEqual(errors, [])
            self.assertEqual(root.winfo_children(), [])
        finally:
            destroy_tk_root(root)
