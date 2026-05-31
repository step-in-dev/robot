"""Tk display availability checks for GUI-related tests."""

from __future__ import annotations

from typing import Optional
import gc
import unittest

import tkinter as tk

from robot.tk_util import destroy_tk_root

_TK_DISPLAY_WORKS: Optional[bool] = None


def tkinter_display_works() -> bool:
    global _TK_DISPLAY_WORKS  # pylint: disable=global-statement
    if _TK_DISPLAY_WORKS is not None:
        return _TK_DISPLAY_WORKS
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        destroy_tk_root(root)
        _TK_DISPLAY_WORKS = True
    except tk.TclError:
        _TK_DISPLAY_WORKS = False
    return _TK_DISPLAY_WORKS


def destroy_stray_tk_root() -> None:
    """Destroy a leftover default root (e.g. leaked by a GUI test)."""
    root = getattr(tk, "_default_root", None)
    if root is not None:
        destroy_tk_root(root)


class GuiTestCase(unittest.TestCase):
    """Base for tests that create Tk windows; tears down stray roots after each test."""

    def tearDown(self) -> None:
        destroy_stray_tk_root()
        # Tkinter/Tcl objects must be collected on the main thread (Python 3.7 is strict).
        gc.collect()
        super().tearDown()


requires_tk_display = unittest.skipUnless(
    tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
