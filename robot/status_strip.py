from __future__ import annotations

from typing import Callable

import tkinter as tk

from .gui_theme import STATUS_TEXT_PAD_X, STATUS_TEXT_PAD_Y, TODO_TEXT_BORDER


class StatusStrip:
    """Status message row with colored background and border like todoText."""

    def __init__(
        self,
        parent: tk.Misc,
        is_closed: Callable[[], bool],
        initial_text: str,
        initial_bg: str,
    ) -> None:
        self._is_closed = is_closed

        self.status_var = tk.StringVar(value=initial_text)
        self.status_frame = tk.Frame(parent, bg=initial_bg)
        self._background = initial_bg

        self.status_label = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            anchor=tk.W,
            justify=tk.LEFT,
            bg=initial_bg,
            fg="#000000",
            padx=STATUS_TEXT_PAD_X,
            pady=STATUS_TEXT_PAD_Y,
            bd=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=TODO_TEXT_BORDER,
            highlightcolor=TODO_TEXT_BORDER,
        )
        self.status_label.pack(side=tk.TOP, fill=tk.X)

    @property
    def background(self) -> str:
        return self._background

    def set_status(self, text: str, background: str) -> None:
        if self._is_closed():
            return
        self.status_var.set(text)
        self.status_frame.configure(bg=background)
        self.status_label.configure(bg=background)
        self._background = background
