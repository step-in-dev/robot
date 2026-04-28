from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .model import RobotEnv, RobotEnvDto


TASKS_DIR_ENV = "ROBOT_TASKS_DIR"


class TaskLoadError(Exception):
    pass


def load_task(task_id: str) -> list[RobotEnv]:
    task_path = find_task_file(task_id)
    try:
        with task_path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except OSError as exc:
        raise TaskLoadError(f"Cannot read task file: {task_path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(f"Invalid JSON in task file: {task_path}") from exc

    environments_data = extract_environments(data, task_path)
    environments = [RobotEnv(RobotEnvDto.from_dict(env)) for env in environments_data]
    if not environments:
        raise TaskLoadError(f"Task file has no environments: {task_path}")
    return environments


def find_task_file(task_id: str) -> Path:
    task_name = task_id if task_id.endswith(".json") else f"{task_id}.json"
    candidates = []

    external_dir = os.environ.get(TASKS_DIR_ENV)
    if external_dir:
        candidates.append(Path(external_dir) / task_name)

    candidates.append(Path(__file__).resolve().parent / "tasks" / task_name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise TaskLoadError(f"Task '{task_id}' was not found. Searched: {searched}")


def extract_environments(data: Any, task_path: Path) -> list[dict]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        environments = data.get("environments")
        if isinstance(environments, list):
            return environments

    raise TaskLoadError(
        f"Task file must contain an 'environments' array: {task_path}"
    )
