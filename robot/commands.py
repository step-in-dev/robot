from __future__ import annotations

import sys
import time
from pathlib import Path

from .executor import ROBOT_PATH_COLLISION_USER_MESSAGE
from .model import RobotPathError
from .runtime_state import active_robot, command_delay_seconds, get_debug_session


def _delay_before_command() -> None:
    delay = command_delay_seconds()
    if delay > 0:
        time.sleep(delay)


def _robot():
    return active_robot()


def _run_mutating_robot_command(command) -> None:
    _delay_before_command()
    try:
        command()
    except RobotPathError:
        session = get_debug_session()
        if session is not None:
            lineno = None
            try:
                student_frame = sys._getframe(2)
                student_file = Path(student_frame.f_code.co_filename).resolve()
                script_file = session.script_path.resolve()
                if student_file == script_file:
                    lineno = student_frame.f_lineno
            except (ValueError, OSError):
                lineno = None
            if lineno is not None:
                msg = f"Строка {lineno}: {ROBOT_PATH_COLLISION_USER_MESSAGE}"
            else:
                msg = ROBOT_PATH_COLLISION_USER_MESSAGE
            from .debug_runtime import _mark_debug_robot_error

            _mark_debug_robot_error(msg)
        raise


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
