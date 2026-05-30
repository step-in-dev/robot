"""Shared helpers for GUI unittest modules."""

import contextlib
from collections.abc import Callable, Iterator

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
    "corridor",
    "env_dict",
    "make_env",
    "make_test_window",
    "minimal_env_dict",
    "requires_tk_display",
    "test_window",
]


def _find_first_text_widget(parent: tk.Misc) -> tk.Text | None:
    for child in parent.winfo_children():
        if isinstance(child, tk.Text):
            return child
        nested = _find_first_text_widget(child)
        if nested is not None:
            return nested
    return None


def make_test_window(
    task_id: str,
    envs: list[RobotEnv],
    run_env: Callable[[RobotEnv], RunResult] | None,
    *,
    options: RobotWindowOptions | None = None,
    constraints: ScriptConstraints | None = None,
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
    envs: list[RobotEnv],
    run_env: Callable[[RobotEnv], RunResult] | None,
    *,
    options: RobotWindowOptions | None = None,
    constraints: ScriptConstraints | None = None,
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

