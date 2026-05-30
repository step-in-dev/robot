"""Small Tkinter helpers for safe window teardown."""

from __future__ import annotations

import tkinter as tk


def cancel_all_after_callbacks(root: tk.Misc) -> None:
    """Cancel every pending ``after`` / ``after_idle`` callback on *root*."""
    try:
        pending = root.tk.call("after", "info")
    except tk.TclError:
        return
    if not pending:
        return
    for after_id in root.tk.splitlist(pending):
        try:
            root.after_cancel(after_id)
        except tk.TclError:
            pass


def flush_tk_events(root: tk.Misc, *, max_rounds: int = 50) -> None:
    """Process pending Tk events so idle handlers run before teardown."""
    for _ in range(max_rounds):
        try:
            if not root.winfo_exists():
                return
            root.update_idletasks()
            root.update()
        except tk.TclError:
            return


def destroy_tk_root(root: tk.Misc) -> None:
    """Cancel pending work, flush, destroy *root*, and clear the default-root pointer."""
    try:
        cancel_all_after_callbacks(root)
        flush_tk_events(root)
    except tk.TclError:
        pass
    try:
        root.destroy()
    except tk.TclError:
        pass
    # Tk keeps a process-global default root for implicit-master widgets.
    # destroy() does not clear it; without this, GUI tests (one process, many
    # open/close cycles) and RobotWindow.close() can leave a dead interpreter.
    if getattr(tk, "_default_root", None) is root:
        tk._default_root = None  # type: ignore[attr-defined]  # pylint: disable=protected-access
