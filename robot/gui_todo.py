"""Shared todo-text banner widgets for solution and editor windows."""

from __future__ import annotations

import tkinter as tk
from typing import Tuple

from .gui_theme import DIALOG_BODY_FONT, TODO_TEXT_BG, TODO_TEXT_BORDER


def create_todo_banner(
    parent: tk.Misc,
    *,
    text: str,
    wraplength: int,
) -> Tuple[tk.Frame, tk.Label]:
    """Create a bordered frame and label for task condition text."""
    frame = tk.Frame(
        parent,
        bg=TODO_TEXT_BORDER,
        bd=0,
        highlightthickness=0,
    )
    label = tk.Label(
        frame,
        text=text,
        anchor=tk.W,
        justify=tk.LEFT,
        wraplength=wraplength,
        font=DIALOG_BODY_FONT,
        bg=TODO_TEXT_BG,
        fg="#000000",
        padx=8,
        pady=6,
        bd=0,
        relief=tk.FLAT,
        highlightthickness=0,
    )
    label.pack(side=tk.TOP, fill=tk.X, padx=1, pady=1)
    return frame, label
