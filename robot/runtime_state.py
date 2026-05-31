"""Mutable execution state shared across executor and robot commands."""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass

from .i18n import t
from .model import Robot, RobotEnv, RobotError


@dataclass
class _SolutionRunState:
    """Mutable globals for the active student solution run."""

    active_env: Optional[RobotEnv] = None
    expected_task_id: Optional[str] = None
    is_executing_solution: bool = False
    command_delay_seconds: float = 0.0


_state = _SolutionRunState()


def begin_solution_run(
    env: RobotEnv, task_id: str, delay_seconds: float
) -> float:
    """Begin a GUI-driven solution run; returns previous command delay for ``end_solution_run``."""
    previous_delay = _state.command_delay_seconds
    _state.active_env = env
    _state.expected_task_id = task_id
    _state.is_executing_solution = True
    _state.command_delay_seconds = delay_seconds
    return previous_delay


def end_solution_run(previous_command_delay_seconds: float) -> None:
    """Restore state after ``exec`` of a student script finishes."""
    _state.active_env = None
    _state.expected_task_id = None
    _state.is_executing_solution = False
    _state.command_delay_seconds = previous_command_delay_seconds


def is_executing_solution() -> bool:
    """Return whether a student script is currently running."""
    return _state.is_executing_solution


def expected_task_id() -> Optional[str]:
    """Task id for the active solution run, or ``None`` outside a run."""
    return _state.expected_task_id


def active_env() -> Optional[RobotEnv]:
    """Environment receiving robot commands during a run, or ``None``."""
    return _state.active_env


def active_robot() -> Robot:
    """Return the robot for the active environment."""
    env = _state.active_env
    if env is None:
        raise RobotError(
            t("runtime_state.error.commands_after_task")
        )
    return env.robot


def command_delay_seconds() -> float:
    """Seconds to sleep before each robot command during the active run."""
    return _state.command_delay_seconds
