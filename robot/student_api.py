"""Student-facing command names and export lists (no heavy imports)."""

from typing import FrozenSet, Tuple

ACTION_COMMAND_NAMES: Tuple[str, ...] = (
    "move_right",
    "move_left",
    "move_up",
    "move_down",
    "paint",
    "printn",
)

STUDENT_COMMAND_NAMES: Tuple[str, ...] = (
    *ACTION_COMMAND_NAMES[:-1],
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
    ACTION_COMMAND_NAMES[-1],
)

COUNTED_OPERATOR_NAMES: FrozenSet[str] = frozenset(ACTION_COMMAND_NAMES)

INIT_EXPORT_NAMES: Tuple[str, ...] = ("field", *STUDENT_COMMAND_NAMES, "task")

RUNTIME_STUDENT_EXPORT_NAMES: Tuple[str, ...] = (
    "task",
    "field",
    *STUDENT_COMMAND_NAMES,
)

RUNTIME_EXTRA_EXPORT_NAMES: Tuple[str, ...] = (
    "RunResult",
    "RunStatus",
    "run_solution_on_env",
    "check_limit_violations",
    "DEFAULT_COMMAND_DELAY_SECONDS",
    "ROBOT_PATH_COLLISION_USER_MESSAGE",
    "StepExecutionSession",
    "StudentSolution",
    "StudentLine",
)
