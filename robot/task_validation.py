"""Shared desktop validation for Robot task ``.env`` payloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .env_dto_json import env_dto_to_dict
from .i18n import t
from .model import MAX_ENV_COUNT, RobotEnvDto
from .script_constraints import ScriptConstraints
from .task_errors import TaskLoadError
from .task_payload import parse_script_constraints, parse_task_payload


@dataclass(frozen=True)
class ValidatedTaskPayload:
    """Normalized and validated desktop task payload."""

    env_dtos: List[dict]
    raw_todo: Any
    resolved_todo: str
    script_constraints: ScriptConstraints


def _raise_env_validation_error(
    exc: ValueError,
    *,
    index: int,
    task_path: Optional[Path],
) -> None:
    if task_path is None:
        raise exc
    raise TaskLoadError(
        t(
            "loader.env_dto_invalid",
            index=index,
            detail=str(exc),
            task_path=task_path,
        )
    ) from exc


def validate_env_dto_count(
    env_dtos: List[dict],
    task_path: Optional[Path],
) -> None:
    """Raise when *env_dtos* is empty or exceeds :data:`MAX_ENV_COUNT`."""
    if not env_dtos:
        if task_path is None:
            raise ValueError(t("editor.error.no_environments"))
        raise TaskLoadError(t("loader.no_environments", task_path=task_path))
    if len(env_dtos) > MAX_ENV_COUNT:
        error = TaskLoadError(
            t(
                "loader.too_many_environments",
                count=len(env_dtos),
                max=MAX_ENV_COUNT,
                task_path=task_path,
            )
        )
        if task_path is None:
            raise ValueError(str(error)) from error
        raise error


def normalize_env_dto_dict(data: dict) -> dict:
    """Validate and canonicalize one environment object."""
    dto = RobotEnvDto.from_dict(data)
    return env_dto_to_dict(dto)


def normalize_env_dtos(
    env_dtos: List[dict],
    task_path: Optional[Path] = None,
) -> List[dict]:
    """Validate and canonicalize every environment in *env_dtos*."""
    validate_env_dto_count(env_dtos, task_path)
    result: List[dict] = []
    for index, item in enumerate(env_dtos):
        try:
            result.append(normalize_env_dto_dict(item))
        except ValueError as exc:
            _raise_env_validation_error(exc, index=index, task_path=task_path)
    return result


def validate_desktop_task_payload(
    data: Dict[str, Any],
    task_path: Optional[Path],
    *,
    field_names: Optional[Dict[str, str]] = None,
) -> ValidatedTaskPayload:
    """Validate a parsed desktop task JSON object."""
    env_dtos_data, resolved_todo = parse_task_payload(data, task_path)
    script_constraints = parse_script_constraints(
        data,
        task_path,
        field_names=field_names,
    )
    normalized_envs = normalize_env_dtos(env_dtos_data, task_path)
    raw_todo = data.get("todoText", "")
    return ValidatedTaskPayload(
        env_dtos=normalized_envs,
        raw_todo=raw_todo,
        resolved_todo=resolved_todo,
        script_constraints=script_constraints,
    )
