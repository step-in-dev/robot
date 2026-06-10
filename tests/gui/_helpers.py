"""Shared helpers for GUI unittest modules."""

import contextlib
import sys
from typing import Callable, Iterator, List, Optional

import tkinter as tk

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
    "env_dict",
    "make_env",
    "make_test_window",
    "minimal_env_dict",
    "noop_success_run_env",
    "requires_tk_display",
    "test_window",
]


def clear_i18n_cache() -> None:
    from robot import i18n

    i18n.clear_translation_cache()


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


def emit_keypad_enter(widget: tk.Misc, root: tk.Misc) -> None:
    """Simulate numpad Enter in GUI tests."""
    # Windows Tcl/Tk ignores synthetic <KP_Enter>; numpad Enter is <Return> there.
    if sys.platform == "win32":
        widget.event_generate("<Return>", when="tail")
    else:
        widget.event_generate("<KP_Enter>", when="tail")
    root.update()


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
