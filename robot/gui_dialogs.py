"""Modal dialogs (constraints, help, and related UI)."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Callable, List, Optional

from .gui_constraints import constraints_body_lines
from .gui_help import _populate_robot_help_text
from .gui_theme import DIALOG_BODY_FONT
from .i18n import t
from .loader import ScriptConstraints
from .tk_util import flush_tk_events

HELP_TEXT_WIDTH = 65
HELP_TEXT_HEIGHT = 32

CONSTRAINTS_TEXT_WIDTH = 65


_ESCAPE_BINDING = "<Escape>"
# Windows tests synthesize KeyPress-Return; include it so modal Entry dialogs commit on Enter.
_RETURN_BINDINGS = ("<Return>", "<KP_Enter>", "<KeyPress-Return>")


def _widget_size(widget: tk.Misc) -> tuple[int, int]:
    widget.update_idletasks()
    width = widget.winfo_width()
    height = widget.winfo_height()
    if width <= 1:
        width = widget.winfo_reqwidth()
    if height <= 1:
        height = widget.winfo_reqheight()
    return width, height


def center_toplevel_on_parent(child: tk.Toplevel, parent: tk.Misc) -> None:
    """Place *child* at the visual center of *parent*."""
    child_width, child_height = _widget_size(child)
    parent_width, parent_height = _widget_size(parent)
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    x = parent_x + (parent_width - child_width) // 2
    y = parent_y + (parent_height - child_height) // 2
    screen_width = child.winfo_screenwidth()
    screen_height = child.winfo_screenheight()
    x = max(0, min(x, screen_width - child_width))
    y = max(0, min(y, screen_height - child_height))
    child.wm_geometry(f"{child_width}x{child_height}+{x}+{y}")


def _nudge_toplevel_visual_center(child: tk.Toplevel, parent: tk.Misc) -> None:
    """Align mapped *child* to the visual center of *parent*.

    On Windows, ``wm_geometry`` size/position and ``winfo_*`` client metrics can
    disagree by a few pixels after the WM adds the toplevel border; nudge X so
    the mapped window looks centered (see ``test_centers_child_horizontally_on_parent``).
    """
    try:
        parent.update_idletasks()
        child.update_idletasks()
        parent.update()
        child.update()
    except tk.TclError:
        pass
    for _ in range(4):
        parent_width, _ = _widget_size(parent)
        child_width, _ = _widget_size(child)
        parent_center_x = parent.winfo_rootx() + parent_width // 2
        child_center_x = child.winfo_rootx() + child_width // 2
        dx = parent_center_x - child_center_x
        if abs(dx) <= 1:
            break
        child.wm_geometry(f"+{child.winfo_rootx() + dx}+{child.winfo_rooty()}")
        try:
            child.update_idletasks()
        except tk.TclError:
            break


def _focus_toplevel_widget(child: tk.Toplevel, focus_widget: Optional[tk.Misc]) -> None:
    """Raise focus to *focus_widget* after the toplevel is mapped, or to *child*."""
    if focus_widget is None:
        child.focus_set()
        return

    def _apply_focus() -> None:
        child.focus_set()
        focus_widget.focus_set()
        if sys.platform == "win32":
            # focus_set alone often leaves focus_get() as None on Windows CI.
            focus_widget.focus_force()
        if isinstance(focus_widget, tk.Entry):
            focus_widget.select_range(0, tk.END)

    # Windows WM may steal focus after grab_set/deiconify; retry on idle as well.
    _apply_focus()
    child.after_idle(_apply_focus)


def _ensure_mapped_before_grab(child: tk.Toplevel, parent: tk.Misc) -> None:
    """Prepare *child* for grab_set on Windows without blocking on a hidden parent."""
    if sys.platform != "win32":
        return
    try:
        child.update_idletasks()
        child.update()
        if child.winfo_viewable():
            return
        # wait_visibility() blocks forever when the parent root is withdrawn.
        if parent.winfo_toplevel().winfo_viewable():
            child.wait_visibility()
    except tk.TclError:
        pass


def reveal_centered_toplevel(
    child: tk.Toplevel,
    parent: tk.Misc,
    *,
    modal: bool = False,
    focus_widget: Optional[tk.Misc] = None,
) -> None:
    """Map a withdrawn toplevel centered over *parent*."""
    child.transient(parent)
    center_toplevel_on_parent(child, parent)
    child.deiconify()
    child.update_idletasks()
    # Windows needs a full update after deiconify before winfo sizes are reliable.
    try:
        child.update()
    except tk.TclError:
        pass
    center_toplevel_on_parent(child, parent)
    _nudge_toplevel_visual_center(child, parent)
    child.lift()
    _ensure_mapped_before_grab(child, parent)
    if modal:
        child.grab_set()
    _focus_toplevel_widget(child, focus_widget)
    # Process after_idle focus handlers before wait_window (Windows CI runs them late).
    flush_rounds = 10 if sys.platform == "win32" else 3
    flush_tk_events(child, max_rounds=flush_rounds)
    _nudge_toplevel_visual_center(child, parent)
    if modal:
        child.wait_window()


def _bind_return(widget: tk.Misc, handler: Callable[[tk.Event], str]) -> None:
    for sequence in _RETURN_BINDINGS:
        widget.bind(sequence, handler)


def pack_ok_cancel_buttons(
    button_row: tk.Misc,
    *,
    on_ok: Callable[[], None],
    on_cancel: Callable[[], None],
) -> None:
    """Pack localized OK and Cancel buttons into *button_row*."""
    tk.Button(
        button_row,
        text=t("editor.constraints.ok"),
        width=10,
        command=on_ok,
    ).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(
        button_row,
        text=t("editor.constraints.cancel"),
        width=10,
        command=on_cancel,
    ).pack(side=tk.LEFT)


def bind_dialog_cancel(dialog: tk.Toplevel, on_cancel: Callable[[], None]) -> None:
    """Wire WM close and Escape on *dialog* to *on_cancel*."""
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    def _handle_escape(_event: tk.Event) -> str:
        on_cancel()
        return "break"

    dialog.bind(_ESCAPE_BINDING, _handle_escape)


def _pack_string_prompt_form(
    dialog: tk.Toplevel,
    *,
    prompt: str,
    initialvalue: str,
    on_ok: Callable[[], None],
    on_cancel: Callable[[], None],
) -> tuple[tk.StringVar, tk.Entry]:
    frame = tk.Frame(dialog, padx=12, pady=12)
    frame.pack(fill=tk.BOTH, expand=True)

    label = tk.Label(
        frame,
        text=prompt,
        font=DIALOG_BODY_FONT,
        anchor=tk.W,
        justify=tk.LEFT,
    )
    label.pack(fill=tk.X, pady=(0, 8))

    variable = tk.StringVar(dialog, value=initialvalue)
    entry = tk.Entry(frame, textvariable=variable, width=40, font=DIALOG_BODY_FONT)
    entry.pack(fill=tk.X)

    button_row = tk.Frame(frame)
    button_row.pack(pady=(12, 0), anchor=tk.E)
    pack_ok_cancel_buttons(button_row, on_ok=on_ok, on_cancel=on_cancel)

    def _handle_return(_event: tk.Event) -> str:
        on_ok()
        return "break"

    _bind_return(dialog, _handle_return)
    _bind_return(entry, _handle_return)
    return variable, entry


def prompt_string_dialog(
    parent: tk.Misc,
    *,
    title: str,
    prompt: str,
    initialvalue: str = "",
) -> Optional[str]:
    """Open a centered modal string-entry dialog and return the entered value."""
    result: dict[str, Optional[str]] = {"value": None}

    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title(title)
    dialog.resizable(False, False)

    def _close_dialog() -> None:
        try:
            dialog.destroy()
        except tk.TclError:
            pass

    def _on_ok() -> None:
        result["value"] = variable.get()
        _close_dialog()

    def _on_cancel() -> None:
        _close_dialog()

    bind_dialog_cancel(dialog, _on_cancel)

    variable, entry = _pack_string_prompt_form(
        dialog,
        prompt=prompt,
        initialvalue=initialvalue,
        on_ok=_on_ok,
        on_cancel=_on_cancel,
    )

    reveal_centered_toplevel(
        dialog, parent, modal=True, focus_widget=entry
    )
    return result["value"]


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
        reveal_centered_toplevel(win, self.root)

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
