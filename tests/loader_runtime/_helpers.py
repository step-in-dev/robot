"""Shared fixtures for loader / runtime integration tests."""

from __future__ import annotations

import contextlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class LoaderRuntimeTestBase(unittest.TestCase):
    """Helpers used across split loader-runtime test modules."""

    @staticmethod
    def _minimal_env_dto() -> dict[str, int]:
        """Single-cell environment used by several loader tests."""
        return {
            "width": 1,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 0,
        }

    @staticmethod
    def _make_capture_robot_window_cls(captured: list) -> type:
        class CaptureRobotWindow:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            def run(self) -> None:
                pass  # Skip Tk mainloop in unit tests

        return CaptureRobotWindow

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
