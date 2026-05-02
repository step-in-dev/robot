from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import TracebackType

from .model import RobotEnv, RobotPathError
from .results import RunResult, check_final_state
from .runtime_state import begin_solution_run, end_solution_run

DEFAULT_COMMAND_DELAY_SECONDS = 0.1

ROBOT_PATH_COLLISION_USER_MESSAGE = "Робот уперся в стену"


def _student_frame_lineno(script_path: Path, tb: TracebackType | None) -> int | None:
    """Innermost lineno in *student* script (closest to the exception in that file)."""
    if tb is None:
        return None
    try:
        resolved_script = script_path.resolve()
    except OSError:
        return None
    for frame_summary in reversed(traceback.extract_tb(tb)):
        try:
            frame_path = Path(frame_summary.filename).resolve()
        except OSError:
            continue
        if frame_path == resolved_script:
            return frame_summary.lineno
    return None


def _message_with_line(
    script_path: Path,
    tb: TracebackType | None,
    message: str,
) -> str:
    lineno = _student_frame_lineno(script_path, tb)
    if lineno is None:
        return message
    return f"Строка {lineno}: {message}"


def _handle_student_system_exit(
    exc: SystemExit, env: RobotEnv, script_path: Path
) -> RunResult:
    """Map student ``SystemExit`` to a ``RunResult`` (do not propagate to the host process)."""
    code = exc.code if exc.code is not None else 0
    if code == 0:
        return check_final_state(env)
    details = traceback.format_exc()
    print(details, file=sys.stderr)
    base_message = f"программа завершилась с кодом {code}"
    return RunResult(
        status="error",
        message=_message_with_line(script_path, exc.__traceback__, base_message),
        details=details,
    )


def run_solution_on_env(
    script_path: Path,
    task_id: str,
    env: RobotEnv,
    command_delay_seconds: float = 0.0,
) -> RunResult:
    env.reset()
    previous_delay = begin_solution_run(env, task_id, command_delay_seconds)

    namespace = {
        "__name__": "__main__",
        "__file__": str(script_path),
    }

    try:
        source = script_path.read_text(encoding="utf-8")
        code = compile(source, str(script_path), "exec")
        exec(code, namespace)
    except RobotPathError as exc:
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="crashed",
            message=_message_with_line(
                script_path, exc.__traceback__, ROBOT_PATH_COLLISION_USER_MESSAGE
            ),
            details=details,
        )
    except SystemExit as exc:  # NOSONAR — student code may call sys.exit; mapped to RunResult
        return _handle_student_system_exit(exc, env, script_path)
    except Exception as exc:
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        base_message = f"{type(exc).__name__}: {exc}"
        return RunResult(
            status="error",
            message=_message_with_line(script_path, exc.__traceback__, base_message),
            details=details,
        )
    finally:
        end_solution_run(previous_delay)

    return check_final_state(env)
