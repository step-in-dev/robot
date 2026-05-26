"""Shared fixtures for loader / runtime integration tests."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.loader import TASKS_DIR_ENV


def minimal_env_dto(*, width: int = 1, height: int = 1) -> dict[str, int]:
    """Single-row environment used by viewer and loader tests."""
    return {
        "width": width,
        "height": height,
        "startRow": 0,
        "startCol": 0,
        "finalRow": 0,
        "finalCol": width - 1,
    }


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


def make_capture_robot_window_cls(captured: list) -> type:
    class CaptureRobotWindow:
        def __init__(self, **kwargs):
            captured.append(kwargs)

        @classmethod
        def from_task_definition(
            cls,
            *,
            task_id: str,
            task_definition,
            run_env=None,
            initial_index: int = 0,
            script_path=None,
            open_constraints_on_startup: bool = False,
            viewer_catalog=None,
        ):
            return cls(
                task_id=task_id,
                envs=task_definition.envs,
                run_env=run_env,
                initial_index=initial_index,
                todo_text=task_definition.todo_text,
                script_path=script_path,
                operators_limit=task_definition.operators_limit,
                custom_function_call_count=task_definition.custom_function_call_count,
                if_limit=task_definition.if_limit,
                while_limit=task_definition.while_limit,
                required_keywords=task_definition.required_keywords,
                banned_keywords=task_definition.banned_keywords,
                open_constraints_on_startup=open_constraints_on_startup,
                viewer_catalog=viewer_catalog,
            )

        def run(self) -> None:
            pass  # Skip Tk mainloop in unit tests.

    return CaptureRobotWindow


@contextlib.contextmanager
def patched_tasks_dir(temp_dir: str | Path):
    """Keep ``ROBOT_TASKS_DIR`` set for catalog discovery and task loads."""
    with patch.dict(os.environ, {TASKS_DIR_ENV: str(temp_dir)}, clear=False):
        yield


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

    def write_task(
        self,
        temp_dir,
        task_id,
        env_dtos,
        todo_text=None,
        operators_limit=None,
        custom_function_call_count=None,
        if_limit=None,
        while_limit=None,
        required_keywords=None,
        banned_keywords=None,
    ):
        task_file = Path(temp_dir) / f"{task_id}.env"
        payload = {"envDtos": env_dtos}
        if todo_text is not None:
            payload["todoText"] = todo_text
        if operators_limit is not None:
            payload["operatorsLimit"] = operators_limit
        if custom_function_call_count is not None:
            payload["customFunctionCallCount"] = custom_function_call_count
        if if_limit is not None:
            payload["ifLimit"] = if_limit
        if while_limit is not None:
            payload["whileLimit"] = while_limit
        if required_keywords is not None:
            payload["requiredKeywords"] = required_keywords
        if banned_keywords is not None:
            payload["bannedKeywords"] = banned_keywords
        task_file.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
