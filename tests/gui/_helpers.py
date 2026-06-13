"""Shared helpers for GUI unittest modules."""

import contextlib
import sys
from typing import Callable, Iterator, List, Optional

import tkinter as tk

from robot.tk_util import flush_tk_events
from robot import i18n
from robot.gui import RobotWindow, RobotWindowOptions
from robot.loader import RobotTask, ScriptConstraints
from robot.model import RobotEnv
from robot.results import RunResult
from tests.env_fixtures import (
    cell_1x1,
    corridor,
    env_dict,
    make_env,
)
from tests.tk_display import GuiTestCase, requires_tk_display

__all__ = [
    "GuiTestCase",
    "cell_1x1",
    "clear_i18n_cache",
    "corridor",
    "emit_action_enter_press",
    "emit_action_enter_press_release",
    "emit_action_enter_release",
    "emit_keypad_enter",
    "emit_return",
    "env_dict",
    "make_env",
    "make_test_window",
    "minimal_env_dict",
    "noop_success_run_env",
    "requires_tk_display",
    "test_window",
    "withdrawn_root",
    "dialog_test_root",
]


def clear_i18n_cache() -> None:
    i18n.clear_translation_cache()


def _prepare_dialog_test_root(root: tk.Tk) -> None:
    """Hide the root without breaking modal dialog focus/keys on Windows CI."""
    if sys.platform == "win32":
        # Withdrawn roots break grab_set, focus_get, and synthetic key events on Windows.
        root.geometry("1x1+-2000+-2000")
        root.update()
        return
    root.withdraw()


@contextlib.contextmanager
def dialog_test_root() -> Iterator[tk.Tk]:
    """Yield a root suitable for modal dialog GUI tests."""
    root = tk.Tk()
    try:
        _prepare_dialog_test_root(root)
        yield root
    finally:
        root.destroy()


@contextlib.contextmanager
def withdrawn_root() -> Iterator[tk.Tk]:
    root = tk.Tk()
    try:
        _prepare_dialog_test_root(root)
        yield root
    finally:
        root.destroy()


def noop_success_run_env(_env: RobotEnv) -> RunResult:
    return RunResult(status="success", message="ok")


def emit_action_enter_press(widget: tk.Misc) -> None:
    """Simulate main Enter key press for action-button bindings."""
    widget.event_generate("<Return>", when="tail")


def emit_action_enter_release(widget: tk.Misc) -> None:
    """Simulate main Enter key release for action-button bindings."""
    widget.event_generate("<KeyRelease-Return>", when="tail")


def emit_action_enter_press_release(widget: tk.Misc, root: tk.Misc) -> None:
    """Simulate main Enter press and release, then flush Tk events."""
    emit_action_enter_press(widget)
    emit_action_enter_release(widget)
    root.update()


def emit_return(widget: tk.Misc, _root: tk.Misc) -> None:
    """Simulate main Enter key in GUI tests."""
    toplevel = widget.winfo_toplevel()
    if sys.platform == "win32":
        # event_generate does not reliably reach Entry bindings on Windows modal dialogs.
        # KeyPress alone is enough; KeyRelease raises TclError after Return destroys the dialog.
        try:
            widget.tk.call("event", "generate", str(widget), "<KeyPress-Return>")
        except tk.TclError:
            pass
        try:
            if toplevel.winfo_exists():
                toplevel.tk.call("event", "generate", str(toplevel), "<KeyPress-Return>")
        except tk.TclError:
            pass
    else:
        widget.event_generate("<KeyPress-Return>", when="tail")
        widget.event_generate("<KeyRelease-Return>", when="tail")
    try:
        if toplevel.winfo_exists():
            flush_tk_events(toplevel, max_rounds=5)
    except tk.TclError:
        pass


def emit_keypad_enter(widget: tk.Misc, root: tk.Misc) -> None:
    """Simulate numpad Enter in GUI tests."""
    # Windows Tcl/Tk ignores synthetic <KP_Enter>; numpad Enter is <Return> there.
    if sys.platform == "win32":
        emit_return(widget, root)
        return
    widget.event_generate("<KP_Enter>", when="tail")
    flush_tk_events(widget.winfo_toplevel(), max_rounds=5)


def _find_first_text_widget(parent: tk.Misc) -> Optional[tk.Text]:
    for child in parent.winfo_children():
        if isinstance(child, tk.Text):
            return child
        nested = _find_first_text_widget(child)
        if nested is not None:
            return nested
    return None


def make_test_window(
    task_id: str,
    envs: List[RobotEnv],
    run_env: Optional[Callable[[RobotEnv], RunResult]],
    *,
    options: Optional[RobotWindowOptions] = None,
    constraints: Optional[ScriptConstraints] = None,
) -> RobotWindow:
    opts = options or RobotWindowOptions()
    c = constraints or ScriptConstraints()
    return RobotWindow(
        task_id,
        RobotTask(envs=envs, todo_text="", script_constraints=c),
        run_env,
        opts,
    )


def minimal_env_dict(width: int, height: int) -> dict:
    return env_dict(width, height, final_col=0)


@contextlib.contextmanager
def test_window(
    task_id: str,
    envs: List[RobotEnv],
    run_env: Optional[Callable[[RobotEnv], RunResult]],
    *,
    options: Optional[RobotWindowOptions] = None,
    constraints: Optional[ScriptConstraints] = None,
) -> Iterator[RobotWindow]:
    window = make_test_window(
        task_id,
        envs,
        run_env,
        options=options,
        constraints=constraints,
    )
    try:
        yield window
    finally:
        window.close()
