from __future__ import annotations

import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, Literal

from .loader import load_task_definition
from .model import RobotEnv, RobotError, RobotPathError


RunStatus = Literal["success", "wrong", "crashed", "error"]
DEFAULT_COMMAND_DELAY_SECONDS = 0.2

ROBOT_PATH_COLLISION_USER_MESSAGE = "робот уперся в стену или границу поля"

_active_env: RobotEnv | None = None
_expected_task_id: str | None = None
_is_executing_solution = False
_active_command_delay_seconds = 0.0
_debug_session: DebugSession | None = None


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    details: str = ""

    @property
    def success(self) -> bool:
        return self.status == "success"


@dataclass
class DebugSession:
    task_id: str
    env_number: int
    env: RobotEnv
    window: Any
    caller_frame: FrameType
    previous_profile: Any = None
    has_robot_error: bool = False
    is_finalized: bool = False


def task(task_id: str, env_number: int | None = None) -> None:
    if _is_executing_solution:
        if _expected_task_id is not None and task_id != _expected_task_id:
            raise RobotError(
                f"Expected task '{_expected_task_id}', got '{task_id}'"
            )
        return

    if _debug_session is not None:
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

def _is_under_debugger() -> bool:
    # pdb, ipdb, many trace-based debuggers
    if sys.gettrace() is not None:
        return True

    # VS Code / debugpy
    try:
        import debugpy
        if debugpy.is_client_connected():
            return True
    except Exception:
        pass

    # PyCharm / pydevd
    try:
        import pydevd
        get_dbg = getattr(pydevd, "GetGlobalDebugger", None) or getattr(pydevd, "get_global_debugger", None)
        if callable(get_dbg) and get_dbg() is not None:
            return True
    except Exception:
        pass

    return False

def _start_debug_task(
    task_id: str,
    env_number: int,
    caller_frame: FrameType,
) -> None:
    global _active_env, _debug_session

    if type(env_number) is not int:
        raise RobotError("Environment number must be an integer")

    task_definition = load_task_definition(task_id)
    envs = task_definition.envs
    if env_number < 1 or env_number > len(envs):
        raise RobotError(
            f"Environment number must be between 1 and {len(envs)}"
        )

    selected_index = env_number - 1
    env = envs[selected_index]
    env.reset()

    from .gui import RobotWindow

    window = RobotWindow(
        task_id=task_id,
        envs=envs,
        run_env=None,
        initial_index=selected_index,
        debug_mode=True,
        todo_text=task_definition.todo_text,
    )
    _debug_session = DebugSession(
        task_id=task_id,
        env_number=env_number,
        env=env,
        window=window,
        caller_frame=caller_frame,
    )
    _active_env = env
    _install_debug_finalizer()
    window.show_debug_started()


def run_solution_on_env(
    script_path: Path,
    task_id: str,
    env: RobotEnv,
    command_delay_seconds: float = 0.0,
) -> RunResult:
    global _active_command_delay_seconds
    global _active_env, _expected_task_id, _is_executing_solution

    previous_command_delay_seconds = _active_command_delay_seconds
    env.reset()
    _active_env = env
    _expected_task_id = task_id
    _is_executing_solution = True
    _active_command_delay_seconds = command_delay_seconds

    namespace = {
        "__name__": "__main__",
        "__file__": str(script_path),
    }

    try:
        source = script_path.read_text(encoding="utf-8")
        code = compile(source, str(script_path), "exec")
        exec(code, namespace)
    except RobotPathError:
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="crashed",
            message=ROBOT_PATH_COLLISION_USER_MESSAGE,
            details=details,
        )
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        if code == 0:
            return _check_final_state(env)
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="error",
            message=f"программа завершилась с кодом {code}",
            details=details,
        )
    except Exception as exc:
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="error",
            message=f"ошибка Python: {type(exc).__name__}: {exc}",
            details=details,
        )
    finally:
        _active_env = None
        _expected_task_id = None
        _is_executing_solution = False
        _active_command_delay_seconds = previous_command_delay_seconds

    return _check_final_state(env)


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


def _run_mutating_robot_command(command) -> None:
    _delay_before_command()
    try:
        command()
    except RobotPathError:
        _mark_debug_robot_error(ROBOT_PATH_COLLISION_USER_MESSAGE)
        raise


def _delay_before_command() -> None:
    if _active_command_delay_seconds > 0:
        time.sleep(_active_command_delay_seconds)


def _robot():
    if _active_env is None:
        raise RobotError(
            "Robot commands can be used only after task() starts a solution run"
        )
    return _active_env.robot


def _check_final_state(env: RobotEnv) -> RunResult:
    if env.is_in_final_state():
        return RunResult(status="success", message="решение верное")
    return RunResult(status="wrong", message="обстановка решена неверно")


def _install_debug_finalizer() -> None:
    session = _debug_session
    if session is None:
        return

    session.previous_profile = sys.getprofile()
    sys.setprofile(_debug_profile)


def _debug_profile(frame, event, arg) -> None:
    session = _debug_session
    if session is None:
        return

    previous_profile = session.previous_profile
    if previous_profile is not None:
        previous_profile(frame, event, arg)

    if frame is session.caller_frame and event == "return":
        _finalize_debug_session()


def _finalize_debug_session() -> None:
    session = _debug_session
    if session is None or session.is_finalized:
        return

    session.is_finalized = True
    _restore_debug_profile(session)
    try:
        if not session.has_robot_error:
            result = _check_final_state(session.env)
            session.window.show_debug_result(session.env_number, result)
        session.window.run_until_closed()
    finally:
        _clear_debug_session()


def _mark_debug_robot_error(message: str) -> None:
    session = _debug_session
    if session is None:
        return

    session.has_robot_error = True
    session.window.show_robot_error(message)


def _clear_debug_session() -> None:
    global _active_command_delay_seconds
    global _active_env, _debug_session

    if _debug_session is not None:
        _restore_debug_profile(_debug_session)

    _active_env = None
    _debug_session = None
    _active_command_delay_seconds = 0.0


def _restore_debug_profile(session: DebugSession) -> None:
    if sys.getprofile() is _debug_profile:
        sys.setprofile(session.previous_profile)
    session.previous_profile = None


def _detect_student_script() -> Path:
    main_module = sys.modules.get("__main__")
    script = getattr(main_module, "__file__", None)
    if not script:
        raise RobotError("task() must be called from a Python file")
    return Path(script).resolve()
