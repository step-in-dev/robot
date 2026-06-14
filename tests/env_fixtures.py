"""Canonical environment DTO dicts and ``RobotEnv`` builders for tests."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

from robot.model import RobotEnv, RobotEnvDto


def env_dict(width: int, height: int, **extra: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "width": width,
        "height": height,
        "startRow": extra.pop("start_row", 0),
        "startCol": extra.pop("start_col", 0),
        "finalRow": extra.pop("final_row", 0),
        "finalCol": extra.pop("final_col", 0),
    }
    data.update(extra)
    return data


def cell_1x1(**extra: Any) -> Dict[str, Any]:
    return env_dict(1, 1, final_col=0, **extra)


def corridor(*, width: int = 2, height: int = 1, **extra: Any) -> Dict[str, Any]:
    return env_dict(width, height, final_col=width - 1, **extra)


def oversized_width_env_dto(*, width: int = 30) -> Dict[str, Any]:
    """Environment DTO dict with width above the desktop maximum."""
    return env_dict(width, 2, final_row=0, final_col=1)


def corridor_with_paint(*, target_col: int = 1, **extra: Any) -> Dict[str, Any]:
    return corridor(cellsToPaint=[{"r": 0, "c": target_col}], **extra)


def make_env(data: Dict[str, Any]) -> RobotEnv:
    return RobotEnv(RobotEnvDto.from_dict(data))


def attach_mock_listener(env: RobotEnv) -> MagicMock:
    listener = MagicMock()
    env.add_listener(listener)
    return listener
