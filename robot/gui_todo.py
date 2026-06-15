"""Shared todo-text banner widgets for solution and editor windows."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from functools import lru_cache
from typing import Tuple

from .gui_theme import (
    DIALOG_BODY_FONT,
    TODO_TEXT_BG,
    TODO_TEXT_BORDER,
    TODO_TEXT_HEIGHT,
    TODO_TEXT_PAD_X,
    TODO_TEXT_PAD_Y,
    TODO_TEXT_SCROLLBAR_WIDTH,
)


@lru_cache(maxsize=1)
def _avg_char_width() -> int:
    font = tkfont.Font(font=DIALOG_BODY_FONT)
    return max(1, font.measure("n" * 10) // 10)


def _wrap_pixels_to_text_width(wraplength_px: int) -> int:
    usable = wraplength_px - TODO_TEXT_SCROLLBAR_WIDTH - TODO_TEXT_PAD_X * 2
    return max(1, usable // _avg_char_width())


def set_todo_banner_text(widget: tk.Text, text: str) -> None:
    """Replace read-only todo banner text."""
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    if text:
        widget.insert("1.0", text)
    widget.configure(state=tk.DISABLED)


def set_todo_banner_wrap_pixels(widget: tk.Text, wraplength_px: int) -> None:
    """Update todo banner wrapping width from a pixel wrap length."""
    widget.configure(width=_wrap_pixels_to_text_width(wraplength_px))


def get_todo_banner_text(widget: tk.Text) -> str:
    """Return the current todo banner text."""
    return widget.get("1.0", "end-1c")


def create_todo_banner(
    parent: tk.Misc,
    *,
    text: str,
    wraplength: int,
) -> Tuple[tk.Frame, tk.Text]:
    """Create a bordered frame and read-only text widget for task condition text."""
    frame = tk.Frame(
        parent,
        bg=TODO_TEXT_BORDER,
        bd=0,
        highlightthickness=0,
    )
    inner = tk.Frame(frame, bg=TODO_TEXT_BG, bd=0, highlightthickness=0)
    inner.pack(side=tk.TOP, fill=tk.X, padx=1, pady=1)

    text_widget = tk.Text(
        inner,
        height=TODO_TEXT_HEIGHT,
        width=_wrap_pixels_to_text_width(wraplength),
        wrap=tk.WORD,
        font=DIALOG_BODY_FONT,
        bg=TODO_TEXT_BG,
        fg="#000000",
        padx=TODO_TEXT_PAD_X,
        pady=TODO_TEXT_PAD_Y,
        bd=0,
        relief=tk.FLAT,
        highlightthickness=0,
        state=tk.DISABLED,
    )
    scroll = tk.Scrollbar(inner, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    set_todo_banner_text(text_widget, text)

    return frame, text_widget
