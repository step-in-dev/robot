from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .loader import load_task
from .model import RobotEnv, RobotError, RobotPathError


RunStatus = Literal["success", "wrong", "crashed", "error"]

_active_env: RobotEnv | None = None
_expected_task_id: str | None = None
_is_executing_solution = False


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    details: str = ""

    @property
    def success(self) -> bool:
        return self.status == "success"


def task(task_id: str) -> None:
    if _is_executing_solution:
        if _expected_task_id is not None and task_id != _expected_task_id:
            raise RobotError(
                f"Expected task '{_expected_task_id}', got '{task_id}'"
            )
        return

    script_path = _detect_student_script()
    envs = load_task(task_id)

    from .gui import RobotWindow

    window = RobotWindow(
        task_id=task_id,
        envs=envs,
        run_env=lambda env: run_solution_on_env(script_path, task_id, env),
    )
    window.run()
    raise SystemExit(0)


def run_solution_on_env(script_path: Path, task_id: str, env: RobotEnv) -> RunResult:
    global _active_env, _expected_task_id, _is_executing_solution

    env.reset()
    _active_env = env
    _expected_task_id = task_id
    _is_executing_solution = True

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
            message="робот уперся в стену или границу поля",
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

    return _check_final_state(env)


def move_right() -> None:
    _robot().move_right()


def move_left() -> None:
    _robot().move_left()


def move_up() -> None:
    _robot().move_up()


def move_down() -> None:
    _robot().move_down()


def paint() -> None:
    _robot().paint()


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
    _robot().print_number(value)


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


def _detect_student_script() -> Path:
    main_module = sys.modules.get("__main__")
    script = getattr(main_module, "__file__", None)
    if not script:
        raise RobotError("task() must be called from a Python file")
    return Path(script).resolve()
