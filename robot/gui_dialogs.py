"""Modal dialogs (constraints, help, and related UI)."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, List, Optional

from .gui_constraints import constraints_body_lines
from .gui_help import _populate_robot_help_text
from .gui_theme import DIALOG_BODY_FONT
from .i18n import t
from .loader import ScriptConstraints

HELP_TEXT_WIDTH = 65
HELP_TEXT_HEIGHT = 32

CONSTRAINTS_TEXT_WIDTH = 65


_ESCAPE_BINDING = "<Escape>"


def _try_focus_existing_toplevel(win: Optional[tk.Toplevel]) -> bool:
    """If ``win`` still exists, raise and focus it and return True; else return False."""
    if win is None:
        return False
    try:
        if win.winfo_exists():
            win.lift()
            win.focus_set()
            return True
    except tk.TclError:
        pass
    return False


class DialogManagerMixin:
    """Help and constraints secondary windows (open-or-focus, Escape / WM close)."""

    root: tk.Tk
    is_closed: bool
    _help_window: Optional[tk.Toplevel]
    _help_window_close_handler: Optional[Callable[[], None]]
    _constraints_window: Optional[tk.Toplevel]
    _constraints_window_close_handler: Optional[Callable[[], None]]
    _script_constraints: ScriptConstraints

    def _init_dialog_manager(self) -> None:
        self._help_window = None
        self._help_window_close_handler = None
        self._constraints_window = None
        self._constraints_window_close_handler = None

    def _focus_toplevel_dialog(self, win: tk.Toplevel) -> None:
        """Map a dialog built while withdrawn, then raise and focus it.

        Secondary windows are created with ``withdraw()`` so the WM does not
        briefly show an empty default-sized frame before widgets are packed.
        """
        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_set()

    def close_dialogs(self) -> None:
        """Destroy help and constraints dialogs if they are open."""
        if self._help_window is not None:
            try:
                self._help_window.destroy()
            except tk.TclError:
                pass
            self._help_window = None
            self._help_window_close_handler = None
        if self._constraints_window is not None:
            try:
                self._constraints_window.destroy()
            except tk.TclError:
                pass
            self._constraints_window = None
            self._constraints_window_close_handler = None

    def show_help(self) -> None:
        """Open or focus a window with module info, project link, and Robot command help."""
        if self.is_closed:
            return
        if self._help_window is not None:
            if _try_focus_existing_toplevel(self._help_window):
                return
            self._help_window = None

        help_win = tk.Toplevel(self.root)
        help_win.withdraw()
        self._help_window = help_win
        help_win.title(t("help.title"))
        help_win.transient(self.root)

        def _clear_help_ref() -> None:
            try:
                help_win.destroy()
            except tk.TclError:
                pass
            self._help_window = None
            self._help_window_close_handler = None

        self._help_window_close_handler = _clear_help_ref
        help_win.protocol("WM_DELETE_WINDOW", self._help_window_close_handler)

        def _handle_help_escape(_event: tk.Event) -> Optional[str]:
            _clear_help_ref()
            return "break"

        help_win.bind(_ESCAPE_BINDING, _handle_help_escape)

        frame = tk.Frame(help_win, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(
            frame,
            wrap=tk.WORD,
            width=HELP_TEXT_WIDTH,
            height=HELP_TEXT_HEIGHT,
            font=DIALOG_BODY_FONT,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        scroll = tk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        _populate_robot_help_text(text)
        self._focus_toplevel_dialog(help_win)

    def _constraints_body_lines(self) -> List[str]:
        return constraints_body_lines(self._script_constraints)

    def show_constraints(self) -> None:
        """Open or focus a window listing task limits that apply to this task."""
        if self.is_closed:
            return
        if self._constraints_window is not None:
            if _try_focus_existing_toplevel(self._constraints_window):
                return
            self._constraints_window = None

        body_lines = self._constraints_body_lines()
        if not body_lines:
            return

        c_win = tk.Toplevel(self.root)
        c_win.withdraw()
        self._constraints_window = c_win
        c_win.title(t("constraints.title"))
        c_win.transient(self.root)

        def _clear_constraints_ref() -> None:
            try:
                c_win.destroy()
            except tk.TclError:
                pass
            self._constraints_window = None
            self._constraints_window_close_handler = None

        self._constraints_window_close_handler = _clear_constraints_ref
        c_win.protocol("WM_DELETE_WINDOW", self._constraints_window_close_handler)

        def _handle_constraints_escape(_event: tk.Event) -> Optional[str]:
            _clear_constraints_ref()
            return "break"

        c_win.bind(_ESCAPE_BINDING, _handle_constraints_escape)

        frame = tk.Frame(c_win, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(
            frame,
            wrap=tk.WORD,
            width=CONSTRAINTS_TEXT_WIDTH,
            height=min(24, max(6, len(body_lines) + 2)),
            font=DIALOG_BODY_FONT,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        scroll = tk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = "\n".join(body_lines).rstrip() + "\n"
        text.insert(tk.END, body)
        text.configure(state=tk.DISABLED)
        self._focus_toplevel_dialog(c_win)
