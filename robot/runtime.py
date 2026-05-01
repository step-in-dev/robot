from __future__ import annotations

import sys
from pathlib import Path

from .runtime_state import (
    expected_task_id,
    get_debug_session,
    is_executing_solution,
)
from .commands import (
    is_cell_not_painted,
    is_cell_painted,
    is_free_down,
    is_free_left,
    is_free_right,
    is_free_up,
    is_wall_down,
    is_wall_left,
    is_wall_right,
    is_wall_up,
    move_down,
    move_left,
    move_right,
    move_up,
    paint,
    pol,
    printn,
)
from .debug_runtime import (
    DebugSession,
    _clear_debug_session,
    _is_under_debugger,
    _start_debug_task,
)
from .executor import (
    DEFAULT_COMMAND_DELAY_SECONDS,
    ROBOT_PATH_COLLISION_USER_MESSAGE,
    run_solution_on_env,
)
from .loader import load_task_definition
from .model import RobotError
from .results import RunResult, RunStatus


def task(task_id: str, env_number: int | None = None) -> None:
    if is_executing_solution():
        eid = expected_task_id()
        if eid is not None and task_id != eid:
            raise RobotError(
                f"Expected task '{eid}', got '{task_id}'"
            )
        return

    if get_debug_session() is not None:
        raise RobotError("Only one task() call is supported in debug mode")

    if _is_under_debugger():
        effective_env_number = 1 if env_number is None else env_number
        _start_debug_task(task_id, effective_env_number, sys._getframe(1))
        return

    script_path = _detect_student_script()
    task_definition = load_task_definition(task_id)
    envs = task_definition.envs

    from .gui import RobotWindow

    window = RobotWindow(
        task_id=task_id,
        envs=envs,
        run_env=lambda env: run_solution_on_env(
            script_path,
            task_id,
            env,
            command_delay_seconds=DEFAULT_COMMAND_DELAY_SECONDS,
        ),
        todo_text=task_definition.todo_text,
    )
    window.run()
    raise SystemExit(0)


def _detect_student_script() -> Path:
    main_module = sys.modules.get("__main__")
    script = getattr(main_module, "__file__", None)
    if not script:
        raise RobotError("task() must be called from a Python file")
    return Path(script).resolve()


__all__ = [
    "task",
    "move_right",
    "move_left",
    "move_up",
    "move_down",
    "paint",
    "is_free_left",
    "is_free_right",
    "is_free_up",
    "is_free_down",
    "is_wall_left",
    "is_wall_right",
    "is_wall_up",
    "is_wall_down",
    "is_cell_painted",
    "is_cell_not_painted",
    "pol",
    "printn",
    "RunResult",
    "RunStatus",
    "run_solution_on_env",
    "DEFAULT_COMMAND_DELAY_SECONDS",
    "ROBOT_PATH_COLLISION_USER_MESSAGE",
    "DebugSession",
    "_clear_debug_session",
]
