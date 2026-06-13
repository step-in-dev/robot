"""Hover tooltips for Tkinter widgets."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

_DEFAULT_DELAY_MS = 1000


def bind_tooltip(widget: tk.Widget, text: str, *, delay_ms: int = _DEFAULT_DELAY_MS) -> None:
    """Show *text* in a small popup after the pointer rests on *widget*."""
    tip_window: Optional[tk.Toplevel] = None
    after_id: Optional[str] = None

    def cancel_scheduled_show() -> None:
        nonlocal after_id
        if after_id is not None:
            widget.after_cancel(after_id)
            after_id = None

    def destroy_tip_window() -> None:
        nonlocal tip_window
        if tip_window is not None:
            tip_window.destroy()
            tip_window = None

    def hide(_event: object = None) -> None:
        cancel_scheduled_show()
        destroy_tip_window()

    def handle_destroy(_event: object = None) -> None:
        hide()

    def show(_event: object = None) -> None:
        nonlocal tip_window
        if tip_window is not None:
            return
        tip_window = tk.Toplevel(widget)
        tip_window.withdraw()
        tip_window.wm_overrideredirect(True)
        tip_window.wm_attributes("-topmost", True)
        label = tk.Label(
            tip_window,
            text=text,
            justify=tk.LEFT,
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=3,
        )
        label.pack()
        tip_window.update_idletasks()
        tip_width = tip_window.winfo_reqwidth()
        x = widget.winfo_rootx() + max(0, (widget.winfo_width() - tip_width) // 2)
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        tip_window.wm_geometry(f"+{x}+{y}")
        tip_window.deiconify()

    def schedule_show(_event: object) -> None:
        nonlocal after_id
        hide()
        # after(0, …) is not always processed in one update() on Windows.
        if delay_ms <= 0:
            show()
            return
        after_id = widget.after(delay_ms, show)

    widget.bind("<Enter>", schedule_show, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<ButtonPress>", hide, add="+")
    widget.bind("<Destroy>", handle_destroy, add="+")
