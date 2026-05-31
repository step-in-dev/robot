"""Canonical environment DTO dicts and ``RobotEnv`` builders for tests."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

from robot.model import RobotEnv, RobotEnvDto


def env_dict(  # pylint: disable=too-many-arguments
    width: int,
    height: int,
    *,
    start_row: int = 0,
    start_col: int = 0,
    final_row: int = 0,
    final_col: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "width": width,
        "height": height,
        "startRow": start_row,
        "startCol": start_col,
        "finalRow": final_row,
        "finalCol": final_col,
    }
    data.update(extra)
    return data


def cell_1x1(**extra: Any) -> Dict[str, Any]:
    return env_dict(1, 1, final_col=0, **extra)


def corridor(*, width: int = 2, height: int = 1, **extra: Any) -> Dict[str, Any]:
    return env_dict(width, height, final_col=width - 1, **extra)


def corridor_with_paint(*, target_col: int = 1, **extra: Any) -> Dict[str, Any]:
    return corridor(cellsToPaint=[{"r": 0, "c": target_col}], **extra)


def make_env(data: Dict[str, Any]) -> RobotEnv:
    return RobotEnv(RobotEnvDto.from_dict(data))


def attach_mock_listener(env: RobotEnv) -> MagicMock:
    listener = MagicMock()
    env.add_listener(listener)
    return listener
