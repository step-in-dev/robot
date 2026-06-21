"""Load Robot task payloads directly from explicit paths for site generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from robot.loader import RobotTask, TaskLoadError
from robot.model import RobotEnv, RobotEnvDto
from robot.task_validation import validate_desktop_task_payload


def _load_json_payload(path: Path) -> dict:
    """Return parsed JSON from ``path`` or raise ``TaskLoadError``."""
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except OSError as exc:
        raise TaskLoadError(f"Cannot read task file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(f"Invalid JSON in task file: {path}") from exc
    if not isinstance(data, dict):
        raise TaskLoadError(f"Task payload must be a JSON object: {path}")
    return data


def load_task_from_path(path: Path) -> RobotTask:
    """Load task metadata and environments from an explicit ``.env`` path."""
    data = _load_json_payload(path)
    validated = validate_desktop_task_payload(data, path)
    environments = [
        RobotEnv(RobotEnvDto.from_dict(env))
        for env in validated.env_dtos
    ]
    return RobotTask(
        envs=environments,
        todo_text=validated.resolved_todo,
        script_constraints=validated.script_constraints,
    )


def load_raw_todo_from_path(path: Path) -> Any:
    """Read raw ``todoText`` from ``path`` without language resolution."""
    data = _load_json_payload(path)
    return data.get("todoText", "")


__all__ = ["load_raw_todo_from_path", "load_task_from_path"]
