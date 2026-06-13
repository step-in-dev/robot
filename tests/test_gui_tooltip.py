"""Tests for Tkinter tooltip lifecycle handling."""

from __future__ import annotations

import tkinter as tk

from robot.gui_tooltip import bind_tooltip
from robot.tk_util import destroy_tk_root
from tests.tk_display import GuiTestCase, requires_tk_display


def _find_toplevels(widget: tk.Misc) -> list[tk.Toplevel]:
    found: list[tk.Toplevel] = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Toplevel):
            found.append(child)
        found.extend(_find_toplevels(child))
    return found


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

    @requires_tk_display
    def test_show_positions_tooltip_below_widget(self) -> None:
        root = tk.Tk()
        try:
            button = tk.Button(root, text="hover")
            button.place(x=80, y=60)
            root.update_idletasks()

            bind_tooltip(button, "Tooltip", delay_ms=0)
            button.event_generate("<Enter>")
            root.update()

            toplevels = _find_toplevels(root)
            self.assertEqual(len(toplevels), 1)
            tip = toplevels[0]

            expected_x = button.winfo_rootx() + max(
                0, (button.winfo_width() - tip.winfo_reqwidth()) // 2
            )
            expected_y = button.winfo_rooty() + button.winfo_height() + 4

            self.assertGreater(button.winfo_rootx(), 0)
            self.assertGreater(button.winfo_rooty(), 0)
            self.assertAlmostEqual(tip.winfo_rootx(), expected_x, delta=2)
            self.assertAlmostEqual(tip.winfo_rooty(), expected_y, delta=2)
        finally:
            destroy_tk_root(root)
