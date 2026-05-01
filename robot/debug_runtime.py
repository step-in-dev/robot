from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

from .executor import _message_with_line
from .loader import load_task_definition
from .model import RobotEnv, RobotError, RobotPathError
from .results import check_final_state
from .runtime_state import (
    assign_debug_session,
    clear_debug_session_state,
    get_debug_session,
)


@dataclass
class DebugSession:
    task_id: str
    env_number: int
    env: RobotEnv
    window: Any
    caller_frame: FrameType
    script_path: Path
    previous_profile: Any = None
    previous_trace: Any = None
    caller_f_trace_before_robot: Any = None
    caller_local_trace: Any = None
    debug_global_trace_installed: bool = False
    debug_trace_installed: bool = False
    has_robot_error: bool = False
    is_finalized: bool = False


def _exception_message(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


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

        get_dbg = getattr(pydevd, "GetGlobalDebugger", None) or getattr(
            pydevd, "get_global_debugger", None
        )
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
    script_path = Path(caller_frame.f_code.co_filename).resolve()

    assign_debug_session(
        DebugSession(
            task_id=task_id,
            env_number=env_number,
            env=env,
            window=window,
            caller_frame=caller_frame,
            script_path=script_path,
        )
    )
    _install_debug_finalizer()
    window.show_debug_started()


def _debug_exception_status_message(exc: BaseException) -> str | None:
    """Status text for uncaught exception in debug caller frame; None if skip."""
    if isinstance(exc, RobotPathError):
        return None
    if isinstance(exc, SystemExit):
        code = exc.code if exc.code is not None else 0
        if code == 0:
            return None
        return f"программа завершилась с кодом {code}"
    if isinstance(exc, KeyboardInterrupt):
        return None
    if isinstance(exc, Exception):
        return _exception_message(exc)
    return None


def _debug_global_trace_enabler(frame, event, arg):
    """Enable tracing machinery when no debugger trace was present; caller_frame uses _debug_caller_frame_trace."""
    return _debug_global_trace_enabler


def _debug_caller_frame_trace(frame, event, arg):
    """Local trace on session.caller_frame: chains IDE/Thonny local trace, then Robot status."""
    session = get_debug_session()
    if session is None:
        return _debug_caller_frame_trace

    nxt = session.caller_local_trace
    if nxt is not None:
        try:
            chain_result = nxt(frame, event, arg)
            if chain_result is not None:
                session.caller_local_trace = chain_result
        except Exception:
            pass

    if event == "exception":
        _, exc, tb = arg
        msg = _debug_exception_status_message(exc)
        if msg is not None:
            _mark_debug_robot_error(_message_with_line(session.script_path, tb, msg))

    return _debug_caller_frame_trace


def _install_debug_finalizer() -> None:
    session = get_debug_session()
    if session is None:
        return

    session.previous_profile = sys.getprofile()
    sys.setprofile(_debug_profile)
    session.previous_trace = sys.gettrace()
    session.caller_f_trace_before_robot = session.caller_frame.f_trace
    session.caller_local_trace = session.caller_frame.f_trace

    if session.previous_trace is None:
        sys.settrace(_debug_global_trace_enabler)
        session.debug_global_trace_installed = True
    else:
        session.debug_global_trace_installed = False

    # sys.settrace() does not hook frames already on the stack; caller must be wired explicitly.
    session.caller_frame.f_trace = _debug_caller_frame_trace
    session.debug_trace_installed = True


def _debug_profile(frame, event, arg) -> None:
    session = get_debug_session()
    if session is None:
        return

    previous_profile = session.previous_profile
    if previous_profile is not None:
        previous_profile(frame, event, arg)

    if frame is session.caller_frame and event == "return":
        _finalize_debug_session()


def _finalize_debug_session() -> None:
    session = get_debug_session()
    if session is None or session.is_finalized:
        return

    session.is_finalized = True
    _restore_debug_hooks(session)
    try:
        if not session.has_robot_error:
            result = check_final_state(session.env)
            session.window.show_debug_result(session.env_number, result)
        session.window.run_until_closed()
    finally:
        _clear_debug_session()


def _mark_debug_robot_error(message: str) -> None:
    session = get_debug_session()
    if session is None:
        return

    session.has_robot_error = True
    session.window.show_robot_error(message)


def _clear_debug_session() -> None:
    session = get_debug_session()
    if session is not None:
        _restore_debug_hooks(session)

    clear_debug_session_state()


def _restore_debug_hooks(session: DebugSession) -> None:
    if sys.getprofile() is _debug_profile:
        sys.setprofile(session.previous_profile)
    session.previous_profile = None
    if session.debug_trace_installed:
        try:
            session.caller_frame.f_trace = session.caller_f_trace_before_robot
        except (RuntimeError, AttributeError):
            pass
        session.caller_f_trace_before_robot = None
        session.caller_local_trace = None
        if session.debug_global_trace_installed:
            sys.settrace(session.previous_trace)
            session.debug_global_trace_installed = False
        session.previous_trace = None
        session.debug_trace_installed = False
