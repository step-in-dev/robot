"""Shared fixtures for loader / runtime integration tests."""


from __future__ import annotations

import contextlib
import json
import os
import sys
import types
import unittest
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from robot.executor import StepExecutionCallbacks
from tests.env_fixtures import corridor
from robot.loader import TASKS_DIR_ENV, ScriptConstraints

NOOP_STEP_CALLBACKS = StepExecutionCallbacks(
    show_line=lambda _line: None,
    wait_for_next_step=lambda: None,
)


def minimal_env_dto(*, width: int = 1, height: int = 1) -> dict[str, int]:
    """Single-row environment used by viewer and loader tests."""
    return corridor(width=width, height=height)


@contextlib.contextmanager
def temp_script(body: str, *, name: str = "solution.py") -> Iterator[Path]:
    with TemporaryDirectory() as temp_dir:
        script = Path(temp_dir) / name
        script.write_text(body, encoding="utf-8")
        yield script


def write_minimal_task_env(
    path: Path, task_id: str, *, width: int = 2, todo_text: str | None = None
) -> None:
    """Write a minimal valid ``.env`` task file."""
    payload: dict[str, object] = {"envDtos": [minimal_env_dto(width=width, height=1)]}
    if todo_text is not None:
        payload["todoText"] = todo_text
    else:
        payload["todoText"] = f"todo for {task_id}"
    path.write_text(json.dumps(payload), encoding="utf-8")


def _capture_robot_window_call(
    captured: list,
    *,
    task_id: str,
    task_definition,
    run_env=None,
    options=None,
) -> None:
    captured.append(
        {
            "task_id": task_id,
            "task_definition": task_definition,
            "run_env": run_env,
            "options": options,
        }
    )


def make_capture_robot_window_cls(captured: list) -> type:
    from robot.gui import RobotWindowOptions

    class CaptureRobotWindow:
        def __init__(
            self,
            task_id: str,
            task_definition,
            run_env=None,
            options: RobotWindowOptions | None = None,
        ):
            _capture_robot_window_call(
                captured,
                task_id=task_id,
                task_definition=task_definition,
                run_env=run_env,
                options=options,
            )

        def run(self) -> None:
            pass  # Skip Tk mainloop in unit tests.

    return CaptureRobotWindow


@contextlib.contextmanager
def patched_tasks_dir(temp_dir: str | Path):
    """Keep ``ROBOT_TASKS_DIR`` set for catalog discovery and task loads."""
    with patch.dict(os.environ, {TASKS_DIR_ENV: str(temp_dir)}, clear=False):
        yield


_SCALAR_CONSTRAINT_ENV_KEYS: tuple[tuple[str, str], ...] = (
    ("operators_limit", "operatorsLimit"),
    ("custom_function_call_count", "customFunctionCallCount"),
    ("if_limit", "ifLimit"),
    ("while_limit", "whileLimit"),
)

_KEYWORD_CONSTRAINT_ENV_KEYS: tuple[tuple[str, str], ...] = (
    ("required_keywords", "requiredKeywords"),
    ("banned_keywords", "bannedKeywords"),
)


def _constraints_to_env_payload(constraints: ScriptConstraints) -> dict[str, object]:
    """Map ``ScriptConstraints`` fields to ``.env`` JSON keys."""
    payload: dict[str, object] = {}
    for attr, key in _SCALAR_CONSTRAINT_ENV_KEYS:
        value = getattr(constraints, attr)
        if value is not None:
            payload[key] = value
    for attr, key in _KEYWORD_CONSTRAINT_ENV_KEYS:
        value = getattr(constraints, attr)
        if value is not None:
            payload[key] = ",".join(value)
    return payload


@dataclass
class TaskFileWrite:
    """Parameters for writing a test ``.env`` task file."""

    task_id: str
    env_dtos: list
    todo_text: str | dict[str, str] | None = None
    constraints: ScriptConstraints | None = None


class LoaderRuntimeTestBase(unittest.TestCase):
    """Helpers used across split loader-runtime test modules."""

    @staticmethod
    def _minimal_env_dto() -> dict[str, int]:
        """Single-cell environment used by several loader tests."""
        return minimal_env_dto()

    @staticmethod
    def _make_capture_robot_window_cls(captured: list) -> type:
        return make_capture_robot_window_cls(captured)

    @staticmethod
    @contextlib.contextmanager
    def _patched_main_as_script(script: Path):
        fake_main = types.ModuleType("fake_main")
        fake_main.__file__ = str(script)
        with patch.dict(sys.modules, {"__main__": fake_main}):
            yield

    def write_task(self, temp_dir, spec: TaskFileWrite) -> Path:
        task_file = Path(temp_dir) / f"{spec.task_id}.env"
        payload: dict[str, object] = {"envDtos": spec.env_dtos}
        if spec.todo_text is not None:
            payload["todoText"] = spec.todo_text
        if spec.constraints is not None:
            payload.update(_constraints_to_env_payload(spec.constraints))
        task_file.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
        return task_file
