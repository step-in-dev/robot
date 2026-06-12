"""Help dialog content and command reference text."""

from __future__ import annotations

from typing import Optional
import webbrowser
import tkinter as tk
import tkinter.font as tkfont

from .command_help import iter_command_help_lines
from .task_help import iter_task_list_lines
from .i18n import t

# Source repository URL (shown as a clickable link in the help dialog).
_HELP_PROJECT_REPOSITORY_URL = "https://github.com/step-in-dev/robot"
_HELP_AUTHOR_NAME = "Виктор Терещук (Viktar Tserashchuk)"
_HELP_BODY_LINK_TAG = "help_repo_link"

_HELP_TEXT_KP_NAV_KEYS = frozenset(
    {
        "KP_Left",
        "KP_Right",
        "KP_Up",
        "KP_Down",
        "KP_Prior",
        "KP_Next",
        "KP_Home",
        "KP_End",
        "KP_Begin",
    }
)
_HELP_TEXT_BLOCK_KEYS = frozenset(
    {
        "BackSpace",
        "Delete",
        "Return",
        "KP_Enter",
        "Linefeed",
        "Tab",
        "ISO_Left_Tab",
        "space",
    }
)


def _help_text_should_block_edit(event: tk.Event) -> bool:
    """Return whether the help ``Text`` should swallow this key (block editing)."""
    if event.keysym == "Escape":
        return False

    state = event.state or 0
    modifier = bool(state & 0x0004) or bool(state & 0x0008)
    ks = event.keysym or ""

    if modifier:
        lower = ks.lower()
        if lower in ("c", "a", "insert"):
            return False
        if lower in ("v", "x"):
            return True

    if ks in _HELP_TEXT_BLOCK_KEYS:
        return True
    if ks.startswith("KP_") and ks not in _HELP_TEXT_KP_NAV_KEYS:
        return True

    ch = event.char
    return bool(ch and ch.isprintable() and not modifier)


def _help_text_readonly_key_action(event: tk.Event) -> Optional[str]:
    """Return ``\"break\"`` to block edits; ``None`` to keep copy, selection, and navigation."""
    return "break" if _help_text_should_block_edit(event) else None


def _help_text_block_paste(_event: tk.Event) -> str:
    return "break"


def _open_help_project_repository() -> None:
    """Open the public project repository in the user's browser."""
    webbrowser.open(_HELP_PROJECT_REPOSITORY_URL)


def _populate_robot_help_text(text: tk.Text) -> None:
    """Fill the help ``Text`` with module info, repo link, and command list (read-only)."""
    text.insert(tk.END, t("help.module_intro") + "\n\n")
    text.insert(tk.END, t("help.author", author=_HELP_AUTHOR_NAME) + "\n")
    text.insert(tk.END, t("help.project_repo_label") + "\n")
    text.insert(tk.END, _HELP_PROJECT_REPOSITORY_URL, (_HELP_BODY_LINK_TAG,))
    text.insert(tk.END, "\n\n")

    cmd_iter = iter(iter_command_help_lines())
    intro_line = next(cmd_iter, "")
    text.insert(tk.END, intro_line, "bold")
    body = "\n" + "\n".join(cmd_iter).rstrip() + "\n"
    text.insert(tk.END, body)

    task_iter = iter(iter_task_list_lines())
    tasks_title = next(task_iter, "")
    text.insert(tk.END, "\n" + tasks_title, "bold")
    task_body = "\n" + "\n".join(task_iter).rstrip() + "\n"
    text.insert(tk.END, task_body)

    text.tag_configure(_HELP_BODY_LINK_TAG, foreground="#0645ad", underline=True)
    _bold_font = tkfont.Font(font=text.cget("font"))
    _bold_font.configure(weight="bold")
    text.tag_configure("bold", font=_bold_font)

    def _on_help_text_button1(event: tk.Event) -> None:
        try:
            idx = text.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        if _HELP_BODY_LINK_TAG in text.tag_names(idx):
            _open_help_project_repository()

    def _link_enter(_event: tk.Event) -> None:
        text.config(cursor="hand2")

    def _link_leave(_event: tk.Event) -> None:
        text.config(cursor="")

    text.bind("<Button-1>", _on_help_text_button1)
    text.tag_bind(_HELP_BODY_LINK_TAG, "<Enter>", _link_enter)
    text.tag_bind(_HELP_BODY_LINK_TAG, "<Leave>", _link_leave)

    text.bind("<Key>", _help_text_readonly_key_action)
    text.bind("<<Paste>>", _help_text_block_paste)
