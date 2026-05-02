from __future__ import annotations

from typing import Callable

import tkinter as tk

from .gui_theme import (
    STATUS_CANVAS_WIDGET_HEIGHT,
    STATUS_HATCH_SPACING,
    STATUS_HATCH_WIDTH,
    STATUS_TEXT_PAD_X,
    TODO_TEXT_BORDER,
)


class StatusStrip:
    """Status message row with optional hatched success background."""

    def __init__(
        self,
        parent: tk.Misc,
        get_canvas_width: Callable[[], int],
        is_closed: Callable[[], bool],
        initial_text: str,
        initial_bg: str,
    ) -> None:
        self._get_canvas_width = get_canvas_width
        self._is_closed = is_closed

        self.status_var = tk.StringVar(value=initial_text)
        self.status_frame = tk.Frame(parent, bg=initial_bg)
        self._background = initial_bg
        self._hatched = False

        self.status_canvas = tk.Canvas(
            self.status_frame,
            height=STATUS_CANVAS_WIDGET_HEIGHT,
            highlightthickness=1,
            highlightbackground=TODO_TEXT_BORDER,
            highlightcolor=TODO_TEXT_BORDER,
            bd=0,
            relief=tk.FLAT,
        )
        self.status_canvas.pack(side=tk.TOP, fill=tk.X)
        self.status_canvas.bind("<Configure>", self._handle_configure)

        self._draw_status(initial_bg, hatched=False)

    @property
    def background(self) -> str:
        return self._background

    @property
    def hatched(self) -> bool:
        return self._hatched

    def _handle_configure(self, _event: tk.Event) -> None:
        if self._is_closed():
            return
        try:
            self._draw_status(self._background, hatched=self._hatched)
        except tk.TclError:
            pass

    def set_status(self, text: str, background: str, *, hatched: bool = False) -> None:
        if self._is_closed():
            return
        self.status_var.set(text)
        self.status_frame.configure(bg=background)
        self._background = background
        self._hatched = hatched
        self._draw_status(background, hatched=hatched)

    def _draw_status(self, background: str, *, hatched: bool) -> None:
        cw = self.status_canvas.winfo_width()
        ch = self.status_canvas.winfo_height()
        width = max(cw, self._get_canvas_width(), 1)
        height = max(ch, STATUS_CANVAS_WIDGET_HEIGHT, 1)

        self.status_canvas.delete("all")

        fill = "#ffffff" if hatched else background
        self.status_canvas.configure(bg=fill)
        self.status_canvas.create_rectangle(0, 0, width, height, fill=fill, outline="")

        if hatched:
            for x in range(-height, width + height, STATUS_HATCH_SPACING):
                self.status_canvas.create_line(
                    x,
                    height,
                    x + height,
                    0,
                    fill=background,
                    width=STATUS_HATCH_WIDTH,
                )

        self.status_canvas.create_text(
            STATUS_TEXT_PAD_X,
            height // 2,
            text=self.status_var.get(),
            anchor=tk.W,
            fill="#000000",
        )
