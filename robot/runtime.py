from __future__ import annotations

import sys
from pathlib import Path

from .runtime_state import (
    expected_task_id,
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
from .executor import (
    DEFAULT_COMMAND_DELAY_SECONDS,
    ROBOT_PATH_COLLISION_USER_MESSAGE,
    StepExecutionSession,
    StudentLine,
    run_solution_on_env,
)
from .loader import load_task_definition
from .model import RobotError
from .results import RunResult, RunStatus


def task(task_id: str) -> None:
    if is_executing_solution():
        eid = expected_task_id()
        if eid is not None and task_id != eid:
            raise RobotError(
                f"Expected task '{eid}', got '{task_id}'"
            )
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
        script_path=script_path,
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
    "StepExecutionSession",
    "StudentLine",
]
