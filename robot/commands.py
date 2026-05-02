from __future__ import annotations

import time

from .runtime_state import active_robot, command_delay_seconds


def _delay_before_command() -> None:
    delay = command_delay_seconds()
    if delay > 0:
        time.sleep(delay)


def _robot():
    return active_robot()


def _run_mutating_robot_command(command) -> None:
    _delay_before_command()
    command()


def move_right() -> None:
    _run_mutating_robot_command(lambda: _robot().move_right())


def move_left() -> None:
    _run_mutating_robot_command(lambda: _robot().move_left())


def move_up() -> None:
    _run_mutating_robot_command(lambda: _robot().move_up())


def move_down() -> None:
    _run_mutating_robot_command(lambda: _robot().move_down())


def paint() -> None:
    _run_mutating_robot_command(lambda: _robot().paint())


def is_free_left() -> bool:
    return _robot().is_free_from("left")


def is_free_right() -> bool:
    return _robot().is_free_from("right")


def is_free_up() -> bool:
    return _robot().is_free_from("up")


def is_free_down() -> bool:
    return _robot().is_free_from("down")


def is_wall_left() -> bool:
    return _robot().is_wall_from("left")


def is_wall_right() -> bool:
    return _robot().is_wall_from("right")


def is_wall_up() -> bool:
    return _robot().is_wall_from("up")


def is_wall_down() -> bool:
    return _robot().is_wall_from("down")


def is_cell_painted() -> bool:
    return _robot().is_cell_painted()


def is_cell_not_painted() -> bool:
    return not is_cell_painted()


def pol() -> int:
    return _robot().get_pollution_level()


def printn(value: int) -> None:
    _run_mutating_robot_command(lambda: _robot().print_number(value))
