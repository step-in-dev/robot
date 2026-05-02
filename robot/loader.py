from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import RobotEnv, RobotEnvDto


TASKS_DIR_ENV = "ROBOT_TASKS_DIR"


class TaskLoadError(Exception):
    pass


@dataclass(frozen=True)
class RobotTask:
    envs: list[RobotEnv]
    todo_text: str
    operators_limit: int | None = None


def load_task(task_id: str) -> list[RobotEnv]:
    return load_task_definition(task_id).envs


def load_task_definition(task_id: str) -> RobotTask:
    task_path = find_task_file(task_id)
    try:
        with task_path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except OSError as exc:
        raise TaskLoadError(f"Cannot read task file: {task_path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(f"Invalid JSON in task file: {task_path}") from exc

    env_dtos_data, todo_text = parse_task_payload(data, task_path)
    operators_limit = parse_operators_limit(data, task_path)
    environments = [
        RobotEnv(RobotEnvDto.from_dict(env)) for env in env_dtos_data
    ]
    if not environments:
        raise TaskLoadError(f"Task file has no environments in envDtos: {task_path}")
    return RobotTask(
        envs=environments,
        todo_text=todo_text,
        operators_limit=operators_limit,
    )


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


def parse_task_payload(data: Any, task_path: Path) -> tuple[list[dict], str]:
    if not isinstance(data, dict):
        raise TaskLoadError(
            f"Task file must be a JSON object with an 'envDtos' array: {task_path}"
        )

    env_dtos = data.get("envDtos")
    if not isinstance(env_dtos, list):
        raise TaskLoadError(
            f"Task file must contain an 'envDtos' array: {task_path}"
        )

    raw_todo = data.get("todoText", "")
    todo_text = raw_todo if isinstance(raw_todo, str) else ""

    result: list[dict] = []
    for index, item in enumerate(env_dtos):
        if not isinstance(item, dict):
            raise TaskLoadError(
                f"envDtos[{index}] must be an object: {task_path}"
            )
        result.append(item)

    return result, todo_text


def parse_operators_limit(data: dict, task_path: Path) -> int | None:
    if "operatorsLimit" not in data:
        return None
    value = data["operatorsLimit"]
    if type(value) is not int or value < 0:
        raise TaskLoadError(
            f"operatorsLimit must be a non-negative integer: {task_path}"
        )
    return value
