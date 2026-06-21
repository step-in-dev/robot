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
# <KeyPress-Return> is for Windows GUI tests that synthesize Enter via tk.call.
# Real keyboards use <Return>.
_RETURN_BINDINGS = ("<Return>", "<KP_Enter>", "<KeyPress-Return>")
# On X11, <<Paste>> maps Ctrl+Y (emacs yank); bind paste keys explicitly instead.
_PASTE_BINDINGS = (
    "<Control-v>",
    "<Control-V>",
    "<Control-Lock-v>",
    "<Control-Lock-V>",
    "<Shift-Insert>",
    "<Key-F18>",
)
# On Linux/X11, Tk maps Ctrl+Y to <<Paste>> (emacs yank), not edit_redo.
# Bind redo shortcuts explicitly so Ctrl+Y restores undone text in dialog fields.
_REDO_BINDINGS = (
    "<Control-y>",
    "<Control-Y>",
    "<Control-Shift-z>",
    "<Control-Shift-Z>",
)
_TAB_BINDINGS = ("<Tab>", "<KeyPress-Tab>")
_SHIFT_TAB_BINDINGS = ("<Shift-Tab>", "<ISO_Left_Tab>", "<KeyPress-ISO_Left_Tab>")


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


def create_dialog_string_field(
    parent: tk.Misc,
    *,
    initialvalue: str = "",
    width: int = 40,
) -> tk.Text:
    """Create a single-line editable text field with undo support."""
    text_widget = tk.Text(
        parent,
        height=1,
        width=width,
        font=DIALOG_BODY_FONT,
        wrap=tk.NONE,
        undo=True,
        relief=tk.SUNKEN,
        bd=1,
    )
    if initialvalue:
        text_widget.insert("1.0", initialvalue)
    text_widget.edit_reset()
    _bind_single_line_paste(text_widget)
    _bind_dialog_text_redo(text_widget)
    _bind_dialog_text_tab_navigation(text_widget)
    return text_widget


def read_dialog_string_field(widget: tk.Text) -> str:
    """Return the current value of a dialog string field."""
    return widget.get("1.0", "end-1c")


def focus_dialog_string_field(widget: tk.Text) -> None:
    """Focus a dialog string field and select its contents."""
    widget.focus_set()
    if widget.get("1.0", "end-1c"):
        widget.tag_add(tk.SEL, "1.0", "end-1c")
        widget.mark_set(tk.INSERT, "end-1c")
    else:
        widget.mark_set(tk.INSERT, "1.0")


def _bind_single_line_paste(text_widget: tk.Text) -> None:
    """Replace multiline clipboard paste with a single-line value."""

    def _handle_paste(_event: tk.Event) -> str:
        try:
            clipboard = text_widget.clipboard_get()
        except tk.TclError:
            return "break"
        normalized = clipboard.replace("\r", "").replace("\n", "")
        if text_widget.tag_ranges(tk.SEL):
            text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        text_widget.insert(tk.INSERT, normalized)
        return "break"

    for sequence in _PASTE_BINDINGS:
        text_widget.bind(sequence, _handle_paste)


def _bind_dialog_text_redo(text_widget: tk.Text) -> None:
    """Override X11 Ctrl+Y paste binding so redo shortcuts call edit_redo."""

    def _handle_redo(_event: tk.Event) -> str:
        try:
            text_widget.edit_redo()
        except tk.TclError:
            pass
        return "break"

    for sequence in _REDO_BINDINGS:
        text_widget.bind(sequence, _handle_redo)


def _bind_dialog_text_tab_navigation(text_widget: tk.Text) -> None:
    """Move focus on Tab instead of inserting a tab character."""

    def _focus_next(_event: tk.Event) -> str:
        next_widget = text_widget.tk_focusNext()
        if next_widget:
            next_widget.focus_set()
        return "break"

    def _focus_prev(_event: tk.Event) -> str:
        prev_widget = text_widget.tk_focusPrev()
        if prev_widget:
            prev_widget.focus_set()
        return "break"

    for sequence in _TAB_BINDINGS:
        text_widget.bind(sequence, _focus_next)
    for sequence in _SHIFT_TAB_BINDINGS:
        text_widget.bind(sequence, _focus_prev)


def _focus_toplevel_widget(child: tk.Toplevel, focus_widget: Optional[tk.Misc]) -> None:
    """Raise focus to *focus_widget* after the toplevel is mapped, or to *child*."""
    if focus_widget is None:
        child.focus_set()
        return

    def _apply_focus() -> None:
        if isinstance(focus_widget, tk.Text):
            focus_dialog_string_field(focus_widget)
            return
        focus_widget.focus_set()
        if isinstance(focus_widget, tk.Entry):
            focus_widget.select_range(0, tk.END)

    # Defer until after deiconify/grab_set so the WM does not steal focus back.
    child.after_idle(_apply_focus)


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
    child.lift()
    if modal:
        child.grab_set()
    _focus_toplevel_widget(child, focus_widget)
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
) -> tk.Text:
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

    text_widget = create_dialog_string_field(
        frame,
        initialvalue=initialvalue,
        width=40,
    )
    text_widget.pack(fill=tk.X)

    button_row = tk.Frame(frame)
    button_row.pack(pady=(12, 0), anchor=tk.E)
    pack_ok_cancel_buttons(button_row, on_ok=on_ok, on_cancel=on_cancel)

    def _handle_return(_event: tk.Event) -> str:
        on_ok()
        return "break"

    _bind_return(dialog, _handle_return)
    _bind_return(text_widget, _handle_return)
    return text_widget


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
        result["value"] = read_dialog_string_field(text_widget)
        _close_dialog()

    def _on_cancel() -> None:
        _close_dialog()

    bind_dialog_cancel(dialog, _on_cancel)

    text_widget = _pack_string_prompt_form(
        dialog,
        prompt=prompt,
        initialvalue=initialvalue,
        on_ok=_on_ok,
        on_cancel=_on_cancel,
    )

    reveal_centered_toplevel(
        dialog, parent, modal=True, focus_widget=text_widget
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
