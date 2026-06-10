"""Run student scripts with limits, stepping, and error mapping."""

from __future__ import annotations

import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Callable, Dict, List, Optional

from .i18n import t
from .loader import ScriptConstraints
from .model import RobotEnv, RobotPathError
from .operator_limits import (
    check_banned_keywords,
    check_custom_function_call_count,
    check_if_limit,
    check_operators_limit,
    check_required_keywords,
    check_while_limit,
)
from .results import RunResult, check_final_state
from .runtime_state import begin_solution_run, end_solution_run

DEFAULT_COMMAND_DELAY_SECONDS = 0.1
RUN_EVENT_POLL_INTERVAL_SECONDS = 0.01

ROBOT_PATH_COLLISION_USER_MESSAGE = t("error.path_collision")
EXECUTION_CANCELLED_MESSAGE = t("error.execution_cancelled")


class StepExecutionCancelled(BaseException):  # NOSONAR — must not inherit Exception (caught below)
    """Raised inside sys.settrace when the user cancels stepping (e.g. Restore).

    Inherits ``BaseException`` so ``except Exception`` in ``start()`` does not swallow it.
    """


class RunExecutionCancelled(BaseException):  # NOSONAR — must not inherit Exception
    """Raised inside sys.settrace when the user cancels a full Run."""


@dataclass(frozen=True)
class StudentLine:
    """One source line from the student script (lineno and text)."""

    lineno: int
    text: str


@dataclass(frozen=True)
class StepExecutionCallbacks:
    """GUI hooks invoked while stepping through student source."""

    show_line: Callable[[StudentLine], None]
    wait_for_next_step: Callable[[], None]


@dataclass(frozen=True)
class StepExecutionTarget:
    """Script file and task id for one stepping session."""

    script_path: Path
    task_id: str


def _student_frame_lineno(script_path: Path, tb: Optional[TracebackType]) -> Optional[int]:
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
    tb: Optional[TracebackType],
    message: str,
    exc: Optional[BaseException] = None,
) -> str:
    lineno = _student_frame_lineno(script_path, tb)
    if lineno is None and isinstance(exc, SyntaxError):
        if exc.lineno is not None and exc.filename:
            try:
                if Path(exc.filename).resolve() == script_path.resolve():
                    lineno = exc.lineno
            except OSError:
                lineno = None
    if lineno is None:
        return message
    return t("line.with_message", lineno=lineno, message=message)


def _handle_student_system_exit(
    exc: SystemExit, env: RobotEnv, script_path: Path
) -> RunResult:
    """Map student ``SystemExit`` to a ``RunResult`` (do not propagate to the host process)."""
    code = exc.code if exc.code is not None else 0
    if code == 0:
        return check_final_state(env)
    details = traceback.format_exc()
    print(details, file=sys.stderr)
    base_message = t("error.system_exit", code=code)
    return RunResult(
        status="error",
        message=_message_with_line(script_path, exc.__traceback__, base_message, exc),
        details=details,
    )


def _map_exec_exception(script_path: Path, env: RobotEnv, exc: BaseException) -> RunResult:
    if isinstance(exc, RobotPathError):
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        return RunResult(
            status="crashed",
            message=_message_with_line(
                script_path,
                exc.__traceback__,
                ROBOT_PATH_COLLISION_USER_MESSAGE,
                exc,
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
        message=_message_with_line(script_path, exc.__traceback__, base_message, exc),
        details=details,
    )


def check_limit_violations(
    source: str,
    *,
    filename: str,
    constraints: Optional[ScriptConstraints] = None,
) -> Optional[str]:
    """Run static limit checks; return the first violation message or ``None``."""
    c = constraints or ScriptConstraints()
    for checker, value in (
        (check_operators_limit, c.operators_limit),
        (check_custom_function_call_count, c.custom_function_call_count),
        (check_if_limit, c.if_limit),
        (check_while_limit, c.while_limit),
        (check_required_keywords, c.required_keywords),
        (check_banned_keywords, c.banned_keywords),
    ):
        violation = checker(source, value, filename=filename)
        if violation is not None:
            return violation.message
    return None


def _make_run_trace(
    script_path: Path,
    *,
    should_cancel: Optional[Callable[[], bool]] = None,
    poll_events: Optional[Callable[[], None]] = None,
):
    """Build a trace hook that keeps Run responsive and cancellable."""
    script_filename = str(script_path)
    last_poll_at = time.monotonic()

    def raise_if_cancelled() -> None:
        if should_cancel is not None and should_cancel():
            raise RunExecutionCancelled

    def trace(frame, event, _arg):
        nonlocal last_poll_at
        if event != "line":
            return trace
        if frame.f_code.co_filename != script_filename:
            return trace
        raise_if_cancelled()
        if poll_events is not None:
            now = time.monotonic()
            if now - last_poll_at >= RUN_EVENT_POLL_INTERVAL_SECONDS:
                poll_events()
                last_poll_at = time.monotonic()
        raise_if_cancelled()
        return trace

    return trace


@dataclass
class _StepScript:
    """Script path, source, and exec namespace for one stepping run."""

    script_path: Path
    resolved_script: Path
    task_id: str
    source_lines: List[str]
    namespace: Dict[str, object]


@dataclass
class _StepState:
    """Tracer gate and lifecycle flags for one stepping run."""

    steps_allowed: int = 0
    cancelled: bool = False
    is_started: bool = False
    is_finished: bool = False


class StepExecutionSession:
    """Single exec() of the student script with sys.settrace pauses between lines."""

    def __init__(
        self,
        target: StepExecutionTarget,
        env: RobotEnv,
        *,
        callbacks: StepExecutionCallbacks,
        command_delay_seconds: float = 0.0,
    ) -> None:
        script_path = target.script_path
        try:
            resolved_script = script_path.resolve()
        except OSError:
            resolved_script = script_path
        self.env = env
        self._callbacks = callbacks
        self._command_delay_seconds = command_delay_seconds
        self._script = _StepScript(
            script_path=script_path,
            resolved_script=resolved_script,
            task_id=target.task_id,
            source_lines=[],
            namespace={
                "__name__": "__main__",
                "__file__": str(script_path),
            },
        )
        self._state = _StepState()

    @property
    def namespace(self) -> Dict[str, object]:
        """Student script globals built during stepping."""
        return self._script.namespace

    @property
    def is_started(self) -> bool:
        """Whether ``start()`` has been entered."""
        return self._state.is_started

    @property
    def is_finished(self) -> bool:
        """Whether the stepping run has completed."""
        return self._state.is_finished

    def allow_one_step(self) -> None:
        """Allow the tracer to run past one more student line."""
        self._state.steps_allowed += 1

    def cancel(self) -> None:
        """Request cancellation of the stepping session."""
        self._state.cancelled = True

    @property
    def cancelled(self) -> bool:
        """Whether the user cancelled stepping."""
        return self._state.cancelled

    def _line_text(self, lineno: int) -> str:
        """Return stripped source text for a 1-based line number."""
        lines = self._script.source_lines
        if lineno < 1 or lineno > len(lines):
            return ""
        return lines[lineno - 1].strip()

    def _trace(self, frame, event, _arg):
        """``sys.settrace`` callback: pause on each student line until allowed.

        ``_arg`` is the trace protocol's third argument (exception info on other events).
        """
        if self._state.cancelled:
            raise StepExecutionCancelled
        if event != "line":
            return self._trace
        try:
            frame_path = Path(frame.f_code.co_filename).resolve()
        except OSError:
            return self._trace
        if frame_path != self._script.resolved_script:
            return self._trace

        lineno = frame.f_lineno
        self._callbacks.show_line(
            StudentLine(lineno=lineno, text=self._line_text(lineno))
        )

        if self._state.cancelled:
            raise StepExecutionCancelled
        if self._state.steps_allowed > 0:
            self._state.steps_allowed -= 1
            return self._trace

        self._callbacks.wait_for_next_step()

        if self._state.cancelled:
            raise StepExecutionCancelled
        if self._state.steps_allowed > 0:
            self._state.steps_allowed -= 1
        return self._trace

    def start(self) -> RunResult:
        """Run the student script until completion, error, or cancel."""
        self._state.is_started = True
        self.env.reset()
        previous_delay = begin_solution_run(
            self.env, self._script.task_id, self._command_delay_seconds
        )
        try:
            try:
                source = self._script.script_path.read_text(encoding="utf-8")
                self._script.source_lines = source.splitlines()
                code = compile(
                    source, str(self._script.script_path), "exec"
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Map read/compile failures to RunResult without changing step semantics.
                self._state.is_finished = True
                return _map_exec_exception(
                    self._script.script_path, self.env, exc
                )

            outcome: Optional[RunResult] = None
            old_trace = sys.gettrace()
            try:
                sys.settrace(self._trace)
                try:
                    # Student solutions are compile+exec'd from disk, not importable modules.
                    exec(code, self._script.namespace)  # pylint: disable=exec-used
                except StepExecutionCancelled:
                    outcome = RunResult(
                        status="error",
                        message=EXECUTION_CANCELLED_MESSAGE,
                        details="",
                    )
                except RobotPathError as exc:  # NOSONAR — map to RunResult like run_solution_on_env
                    outcome = _map_exec_exception(
                        self._script.script_path, self.env, exc
                    )
                except SystemExit as exc:  # NOSONAR — student code may call sys.exit
                    outcome = _handle_student_system_exit(
                        exc, self.env, self._script.script_path
                    )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    # Student exec may raise any Exception; StepExecutionCancelled is BaseException.
                    outcome = _map_exec_exception(
                        self._script.script_path, self.env, exc
                    )
            finally:
                sys.settrace(old_trace)

            self._state.is_finished = True
            if outcome is not None:
                return outcome
            return check_final_state(self.env)
        finally:
            end_solution_run(previous_delay)


def run_solution_on_env(
    script_path: Path,
    task_id: str,
    env: RobotEnv,
    command_delay_seconds: float = 0.0,
    *,
    should_cancel: Optional[Callable[[], bool]] = None,
    poll_events: Optional[Callable[[], None]] = None,
) -> RunResult:
    """Execute a student script on one environment and return the run outcome."""
    env.reset()
    previous_delay = begin_solution_run(env, task_id, command_delay_seconds)

    namespace = {
        "__name__": "__main__",
        "__file__": str(script_path),
    }

    try:
        source = script_path.read_text(encoding="utf-8")
        code = compile(source, str(script_path), "exec")
        if should_cancel is None and poll_events is None:
            exec(code, namespace)  # pylint: disable=exec-used
        else:
            trace = _make_run_trace(
                script_path,
                should_cancel=should_cancel,
                poll_events=poll_events,
            )
            old_trace = sys.gettrace()
            try:
                sys.settrace(trace)
                exec(code, namespace)  # pylint: disable=exec-used
            except RunExecutionCancelled:
                return RunResult(
                    status="error",
                    message=EXECUTION_CANCELLED_MESSAGE,
                    details="",
                )
            finally:
                sys.settrace(old_trace)
    except RobotPathError as exc:
        return _map_exec_exception(script_path, env, exc)
    except SystemExit as exc:  # NOSONAR — student code may call sys.exit; mapped to RunResult
        return _handle_student_system_exit(exc, env, script_path)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Student exec may raise any Exception; map all to RunResult (batch path).
        return _map_exec_exception(script_path, env, exc)
    finally:
        end_solution_run(previous_delay)

    return check_final_state(env)
