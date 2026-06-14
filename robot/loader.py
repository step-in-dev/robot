"""Load task definitions from bundled or custom .env files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .i18n import t
from .model import RobotEnv, RobotEnvDto
from .script_constraints import ScriptConstraints
from .task_errors import TaskLoadError
from .task_validation import validate_desktop_task_payload

TASKS_DIR_ENV = "ROBOT_TASKS_DIR"
TASK_FILE_EXTENSION = ".env"


@dataclass(frozen=True)
class RobotTask:
    """Loaded task: environments, todo text, and constraint limits."""

    envs: List[RobotEnv]
    todo_text: str
    script_constraints: ScriptConstraints = field(default_factory=ScriptConstraints)

    @property
    def operators_limit(self) -> Optional[int]:
        """Operator count limit from the task file."""
        return self.script_constraints.operators_limit

    @property
    def custom_function_call_count(self) -> Optional[int]:
        """Minimum custom-function call count from the task file."""
        return self.script_constraints.custom_function_call_count

    @property
    def if_limit(self) -> Optional[int]:
        """``if`` keyword use limit from the task file."""
        return self.script_constraints.if_limit

    @property
    def while_limit(self) -> Optional[int]:
        """``while`` keyword use limit from the task file."""
        return self.script_constraints.while_limit

    @property
    def required_keywords(self) -> Optional[Tuple[str, ...]]:
        """Keywords that must appear in the solution."""
        return self.script_constraints.required_keywords

    @property
    def banned_keywords(self) -> Optional[Tuple[str, ...]]:
        """Keywords that must not appear in the solution."""
        return self.script_constraints.banned_keywords


def load_task(task_id: str) -> List[RobotEnv]:
    """Load all environments for a task id."""
    return load_task_definition(task_id).envs


def find_task_file(task_id: str) -> Path:
    """Resolve a task id to an existing ``.env`` file path."""
    task_name = (
        task_id
        if task_id.endswith(TASK_FILE_EXTENSION)
        else f"{task_id}{TASK_FILE_EXTENSION}"
    )
    candidates = []

    external_dir = os.environ.get(TASKS_DIR_ENV)
    if external_dir:
        candidates.append(Path(external_dir) / task_name)

    candidates.append(Path(__file__).resolve().parent / "tasks" / task_name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise TaskLoadError(
        t("loader.task_not_found", task_id=task_id, searched=searched)
    )


def load_task_definition(task_id: str) -> RobotTask:
    """Load task metadata and environments from a ``.env`` file."""
    task_path = find_task_file(task_id)
    try:
        with task_path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except OSError as exc:
        raise TaskLoadError(
            t("loader.cannot_read_task_file", task_path=task_path)
        ) from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(
            t("loader.invalid_json", task_path=task_path)
        ) from exc

    validated = validate_desktop_task_payload(data, task_path)
    environments = [
        RobotEnv(RobotEnvDto.from_dict(env)) for env in validated.env_dtos
    ]
    return RobotTask(
        envs=environments,
        todo_text=validated.resolved_todo,
        script_constraints=validated.script_constraints,
    )


__all__ = [
    "TASKS_DIR_ENV",
    "TASK_FILE_EXTENSION",
    "RobotTask",
    "ScriptConstraints",
    "TaskLoadError",
    "find_task_file",
    "load_task",
    "load_task_definition",
]
