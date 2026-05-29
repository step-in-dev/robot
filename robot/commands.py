"""Student-facing robot command functions (move, paint, probes)."""

from __future__ import annotations

import time

from .runtime_state import active_robot, command_delay_seconds


def _delay_before_command() -> None:
    """Sleep when a positive command delay is configured for the active run."""
    delay = command_delay_seconds()
    if delay > 0:
        time.sleep(delay)


def _robot():
    """Return the robot for the environment in the current solution run."""
    return active_robot()


def _run_mutating_robot_command(command) -> None:
    """Apply optional delay, then run a command that mutates robot state."""
    _delay_before_command()
    command()


def move_right() -> None:
    """Move the robot one cell to the right."""
    _run_mutating_robot_command(lambda: _robot().move_right())


def move_left() -> None:
    """Move the robot one cell to the left."""
    _run_mutating_robot_command(lambda: _robot().move_left())


def move_up() -> None:
    """Move the robot one cell up."""
    _run_mutating_robot_command(lambda: _robot().move_up())


def move_down() -> None:
    """Move the robot one cell down."""
    _run_mutating_robot_command(lambda: _robot().move_down())


def paint() -> None:
    """Paint the cell under the robot."""
    _run_mutating_robot_command(lambda: _robot().paint())


def is_free_left() -> bool:
    """Return whether the robot can move left without hitting a wall or border."""
    return _robot().is_free_from("left")


def is_free_right() -> bool:
    """Return whether the robot can move right without hitting a wall or border."""
    return _robot().is_free_from("right")


def is_free_up() -> bool:
    """Return whether the robot can move up without hitting a wall or border."""
    return _robot().is_free_from("up")


def is_free_down() -> bool:
    """Return whether the robot can move down without hitting a wall or border."""
    return _robot().is_free_from("down")


def is_wall_left() -> bool:
    """Return whether a wall or border blocks movement to the left."""
    return _robot().is_wall_from("left")


def is_wall_right() -> bool:
    """Return whether a wall or border blocks movement to the right."""
    return _robot().is_wall_from("right")


def is_wall_up() -> bool:
    """Return whether a wall or border blocks movement upward."""
    return _robot().is_wall_from("up")


def is_wall_down() -> bool:
    """Return whether a wall or border blocks movement downward."""
    return _robot().is_wall_from("down")


def is_cell_painted() -> bool:
    """Return whether the cell under the robot is painted."""
    return _robot().is_cell_painted()


def is_cell_not_painted() -> bool:
    """Return whether the cell under the robot is not painted."""
    return not is_cell_painted()


def pol() -> int:
    """Return pollution level at the cell under the robot."""
    return _robot().get_pollution_level()


def printn(value: int) -> None:
    """Print ``value`` at the robot's current cell."""
    _run_mutating_robot_command(lambda: _robot().print_number(value))
