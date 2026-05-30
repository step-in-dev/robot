"""Shared helpers for GUI unittest modules."""

import unittest
from collections.abc import Callable

import tkinter as tk

from robot.gui import RobotWindow, RobotWindowOptions
from robot.loader import RobotTask, ScriptConstraints
from robot.model import RobotEnv, RobotEnvDto
from robot.results import RunResult


def _tkinter_display_works() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


def _find_first_text_widget(parent: tk.Misc) -> tk.Text | None:
    for child in parent.winfo_children():
        if isinstance(child, tk.Text):
            return child
        nested = _find_first_text_widget(child)
        if nested is not None:
            return nested
    return None


def make_env(data: dict) -> RobotEnv:
    return RobotEnv(RobotEnvDto.from_dict(data))


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
    return {
        "width": width,
        "height": height,
        "startRow": 0,
        "startCol": 0,
        "finalRow": 0,
        "finalCol": 0,
    }


requires_tk_display = unittest.skipUnless(
    _tkinter_display_works(),
    "tkinter display not available (headless / no DISPLAY)",
)
