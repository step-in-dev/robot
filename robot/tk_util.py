"""Small Tkinter helpers for safe window teardown and layout."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk


def fix_win_hidpi() -> None:
    """Enable system DPI awareness on Windows before any Tk widgets are created.

    Without this call Windows bitmap-stretches the whole window on HiDPI displays,
    which makes text and ``PhotoImage`` icons look blurry. Same approach as IDLE
    (``idlelib.util.fix_win_hidpi``) and Thonny.
    """
    if sys.platform != "win32":
        return
    try:
        process_system_dpi_aware = 1
        ctypes.OleDLL("shcore").SetProcessDpiAwareness(process_system_dpi_aware)
    except (AttributeError, OSError):
        pass


def widget_reqheight(widget: tk.Misc) -> int:
    """Return the widget's requested height after idle layout."""
    widget.update_idletasks()
    return widget.winfo_reqheight()


def pack_ipady_for_target_height(widget: tk.Misc, *, target_height: int) -> int:
    """Return ``ipady`` so *widget* matches *target_height* when packed."""
    widget.update_idletasks()
    padding = target_height - widget.winfo_reqheight()
    if padding <= 0:
        return 0
    return padding // 2


def pack_fill_host(host: tk.Frame, widget: tk.Misc) -> None:
    """Fill a fixed-height host with *widget*."""
    widget.pack(in_=host, fill=tk.BOTH, expand=True)


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
