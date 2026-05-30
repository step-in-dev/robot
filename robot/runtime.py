"""Facade: task(), field(), and wiring loader, GUI, and executor."""

from __future__ import annotations

import sys
from pathlib import Path

from .i18n import t
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
    StepExecutionTarget,
    StudentLine,
    check_limit_violations,
    run_solution_on_env,
)
from .loader import RobotTask, load_task_definition
from .model import RobotEnv, RobotEnvDto, RobotError, _is_plain_int
from .results import RunResult, RunStatus


def _detect_student_script() -> Path:
    main_module = sys.modules.get("__main__")
    script = getattr(main_module, "__file__", None)
    if not script:
        raise RobotError(t("runtime.error.task_from_file"))
    return Path(script).resolve()


def _launch_student_robot_window(
    *,
    task_id: str,
    task_definition: RobotTask,
    initial_index: int = 0,
    open_constraints_on_startup: bool = False,
) -> None:
    """Open the GUI for a loaded or synthetic task; never returns normally."""
    script_path = _detect_student_script()
    from .gui import RobotWindow, RobotWindowOptions

    window = RobotWindow(
        task_id,
        task_definition,
        lambda env: run_solution_on_env(
            script_path,
            task_id,
            env,
            command_delay_seconds=DEFAULT_COMMAND_DELAY_SECONDS,
        ),
        RobotWindowOptions(
            initial_index=initial_index,
            script_path=script_path,
            open_constraints_on_startup=open_constraints_on_startup,
        ),
    )
    window.run()
    raise SystemExit(0)


def task(task_id: str) -> None:
    """Open the Robot window for a bundled or external task id."""
    if is_executing_solution():
        eid = expected_task_id()
        if eid is not None and task_id != eid:
            raise RobotError(
                t("runtime.error.expected_task", expected=eid, got=task_id)
            )
        return

    task_definition = load_task_definition(task_id)
    _launch_student_robot_window(
        task_id=task_id,
        task_definition=task_definition,
    )


def _field_task_label(width: int, height: int) -> str:
    return f"field({width}, {height})"


def _validate_field_dimensions(width: object, height: object) -> tuple[int, int]:
    if not _is_plain_int(width) or not _is_plain_int(height):
        raise RobotError(t("runtime.error.field_integers"))
    if not (1 <= width <= 20):
        raise RobotError(t("runtime.error.field_width_range"))
    if not (1 <= height <= 15):
        raise RobotError(t("runtime.error.field_height_range"))
    return width, height


def _synthetic_field_envs(width: int, height: int) -> list[RobotEnv]:
    dto = RobotEnvDto(
        width=width,
        height=height,
        start_row=0,
        start_col=0,
        final_row=height - 1,
        final_col=width - 1,
    )
    return [RobotEnv(dto)]


def field(width: int = 8, height: int = 6) -> None:
    """Open the Robot window on a blank synthetic field of the given size."""
    width_i, height_i = _validate_field_dimensions(width, height)
    if is_executing_solution():
        return

    task_id = _field_task_label(width_i, height_i)
    _launch_student_robot_window(
        task_id=task_id,
        task_definition=RobotTask(
            envs=_synthetic_field_envs(width_i, height_i),
            todo_text="",
        ),
    )


__all__ = [
    "task",
    "field",
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
    "check_limit_violations",
    "DEFAULT_COMMAND_DELAY_SECONDS",
    "ROBOT_PATH_COLLISION_USER_MESSAGE",
    "StepExecutionSession",
    "StepExecutionTarget",
    "StudentLine",
]
