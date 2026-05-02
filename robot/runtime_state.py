"""Mutable execution state shared across executor and robot commands."""

from __future__ import annotations

from .model import Robot, RobotEnv, RobotError

_active_env: RobotEnv | None = None
_expected_task_id: str | None = None
_is_executing_solution = False
_active_command_delay_seconds = 0.0


def begin_solution_run(
    env: RobotEnv, task_id: str, command_delay_seconds: float
) -> float:
    """Begin a GUI-driven solution run; returns previous command delay for ``end_solution_run``."""
    global _active_env, _expected_task_id, _is_executing_solution, _active_command_delay_seconds
    previous_delay = _active_command_delay_seconds
    _active_env = env
    _expected_task_id = task_id
    _is_executing_solution = True
    _active_command_delay_seconds = command_delay_seconds
    return previous_delay


def end_solution_run(previous_command_delay_seconds: float) -> None:
    """Restore state after ``exec`` of a student script finishes."""
    global _active_env, _expected_task_id, _is_executing_solution, _active_command_delay_seconds
    _active_env = None
    _expected_task_id = None
    _is_executing_solution = False
    _active_command_delay_seconds = previous_command_delay_seconds


def is_executing_solution() -> bool:
    return _is_executing_solution


def expected_task_id() -> str | None:
    return _expected_task_id


def active_env() -> RobotEnv | None:
    return _active_env


def active_robot() -> Robot:
    env = _active_env
    if env is None:
        raise RobotError(
            "Robot commands can be used only after task() starts a solution run"
        )
    return env.robot


def command_delay_seconds() -> float:
    return _active_command_delay_seconds
