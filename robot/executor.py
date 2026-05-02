from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Callable

from .model import RobotEnv, RobotPathError
from .results import RunResult, check_final_state
from .runtime_state import begin_solution_run, end_solution_run

DEFAULT_COMMAND_DELAY_SECONDS = 0.1

ROBOT_PATH_COLLISION_USER_MESSAGE = "Робот уперся в стену"


class StepExecutionCancelled(BaseException):  # NOSONAR — must not inherit Exception (caught below)
    """Raised inside sys.settrace when the user cancels stepping (e.g. Restore).

    Inherits ``BaseException`` so ``except Exception`` in ``start()`` does not swallow it.
    """


@dataclass(frozen=True)
class StudentLine:
    lineno: int
    text: str


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


def _map_exec_exception(script_path: Path, env: RobotEnv, exc: BaseException) -> RunResult:
    if isinstance(exc, RobotPathError):
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="crashed",
            message=_message_with_line(
                script_path, exc.__traceback__, ROBOT_PATH_COLLISION_USER_MESSAGE
            ),
            details=details,
        )
    if isinstance(exc, SystemExit):
        return _handle_student_system_exit(exc, env, script_path)
    details = traceback.format_exc()
    print(details, file=sys.stderr)
    base_message = f"{type(exc).__name__}: {exc}"
    return RunResult(
        status="error",
        message=_message_with_line(script_path, exc.__traceback__, base_message),
        details=details,
    )


class StepExecutionSession:
    """Single exec() of the student script with sys.settrace pauses between lines."""

    def __init__(
        self,
        script_path: Path,
        task_id: str,
        env: RobotEnv,
        *,
        show_line: Callable[[StudentLine], None],
        wait_for_next_step: Callable[[], None],
        command_delay_seconds: float = 0.0,
    ) -> None:
        self._script_path = script_path
        try:
            self._resolved_script = script_path.resolve()
        except OSError:
            self._resolved_script = script_path
        self._task_id = task_id
        self.env = env
        self._show_line = show_line
        self._wait_for_next_step = wait_for_next_step
        self._command_delay_seconds = command_delay_seconds
        self._steps_allowed = 0
        self._cancelled = False
        self.is_started = False
        self.is_finished = False
        self._source_lines: list[str] = []
        self.namespace: dict[str, object] = {
            "__name__": "__main__",
            "__file__": str(script_path),
        }

    def allow_one_step(self) -> None:
        self._steps_allowed += 1

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def _line_text(self, lineno: int) -> str:
        if lineno < 1 or lineno > len(self._source_lines):
            return ""
        return self._source_lines[lineno - 1].strip()

    def _trace(self, frame, event, arg):
        if self._cancelled:
            raise StepExecutionCancelled
        if event != "line":
            return self._trace
        try:
            frame_path = Path(frame.f_code.co_filename).resolve()
        except OSError:
            return self._trace
        if frame_path != self._resolved_script:
            return self._trace

        lineno = frame.f_lineno
        self._show_line(StudentLine(lineno=lineno, text=self._line_text(lineno)))

        if self._cancelled:
            raise StepExecutionCancelled
        if self._steps_allowed > 0:
            self._steps_allowed -= 1
            return self._trace

        self._wait_for_next_step()

        if self._cancelled:
            raise StepExecutionCancelled
        if self._steps_allowed > 0:
            self._steps_allowed -= 1
        return self._trace

    def start(self) -> RunResult:
        """Run the student script until completion, error, or cancel."""
        self.is_started = True
        self.env.reset()
        previous_delay = begin_solution_run(
            self.env, self._task_id, self._command_delay_seconds
        )
        old_trace = sys.gettrace()
        source = self._script_path.read_text(encoding="utf-8")
        self._source_lines = source.splitlines()
        code = compile(source, str(self._script_path), "exec")
        outcome: RunResult | None = None
        try:
            sys.settrace(self._trace)
            try:
                exec(code, self.namespace)
            except StepExecutionCancelled:
                outcome = RunResult(
                    status="error",
                    message="Выполнение прервано",
                    details="",
                )
            except RobotPathError as exc:  # NOSONAR — map to RunResult like run_solution_on_env
                outcome = _map_exec_exception(self._script_path, self.env, exc)
            except SystemExit as exc:
                outcome = _handle_student_system_exit(
                    exc, self.env, self._script_path
                )
            except Exception as exc:
                outcome = _map_exec_exception(self._script_path, self.env, exc)
        finally:
            sys.settrace(old_trace)
            end_solution_run(previous_delay)

        self.is_finished = True
        if outcome is not None:
            return outcome
        return check_final_state(self.env)


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
        return _map_exec_exception(script_path, env, exc)
    except SystemExit as exc:  # NOSONAR — student code may call sys.exit; mapped to RunResult
        return _handle_student_system_exit(exc, env, script_path)
    except Exception as exc:
        return _map_exec_exception(script_path, env, exc)
    finally:
        end_solution_run(previous_delay)

    return check_final_state(env)
