"""Parse top-level fields from desktop task ``.env`` JSON payloads."""

from __future__ import annotations

import keyword
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .i18n import t
from .model import _is_plain_int
from .script_constraints import ScriptConstraints
from .task_errors import TaskLoadError
from .task_todo import resolve_todo_text

PYTHON_KEYWORDS = frozenset(keyword.kwlist)


def parse_task_payload(
    data: Any,
    task_path: Optional[Path],
) -> Tuple[List[dict], str]:
    """Extract ``envDtos`` and resolved ``todoText`` from parsed task JSON."""
    if not isinstance(data, dict):
        raise TaskLoadError(
            t("loader.must_be_object_with_env_dtos", task_path=task_path)
        )

    env_dtos = data.get("envDtos")
    if not isinstance(env_dtos, list):
        raise TaskLoadError(
            t("loader.must_contain_env_dtos_array", task_path=task_path)
        )

    raw_todo = data.get("todoText", "")
    todo_text = resolve_todo_text(raw_todo)

    result: List[dict] = []
    for index, item in enumerate(env_dtos):
        if not isinstance(item, dict):
            raise TaskLoadError(
                t(
                    "loader.env_dtos_index_must_be_object",
                    index=index,
                    task_path=task_path,
                )
            )
        result.append(item)

    return result, todo_text


def _format_task_path_suffix(task_path: Optional[Path]) -> str:
    if task_path is None:
        return ""
    return t("loader.task_path_suffix", task_path=task_path)


def _parse_optional_non_negative_int(
    data: dict,
    task_path: Optional[Path],
    *,
    json_key: str,
    invalid_message_key: str,
    field_name: Optional[str] = None,
) -> Optional[int]:
    if json_key not in data:
        return None
    display_name = field_name if field_name is not None else json_key
    value = data[json_key]
    if not _is_plain_int(value) or value < 0:
        raise TaskLoadError(
            t(
                invalid_message_key,
                field_name=display_name,
                task_path_suffix=_format_task_path_suffix(task_path),
            )
        )
    return value


def parse_script_constraints(
    data: Dict[str, Any],
    task_path: Optional[Path],
    *,
    field_names: Optional[Dict[str, str]] = None,
) -> ScriptConstraints:
    """Parse and validate script constraint fields from task JSON."""
    labels = field_names or {}
    operators_limit = parse_operators_limit(
        data, task_path, field_name=labels.get("operatorsLimit")
    )
    custom_function_call_count = parse_custom_function_call_count(
        data, task_path, field_name=labels.get("customFunctionCallCount")
    )
    if_limit = parse_if_limit(data, task_path, field_name=labels.get("ifLimit"))
    while_limit = parse_while_limit(
        data, task_path, field_name=labels.get("whileLimit")
    )
    required_keywords = parse_keyword_list(
        data,
        task_path,
        json_key="requiredKeywords",
        field_name=labels.get("requiredKeywords"),
        invalid_message_key="loader.required_keywords_invalid",
    )
    banned_keywords = parse_keyword_list(
        data,
        task_path,
        json_key="bannedKeywords",
        field_name=labels.get("bannedKeywords"),
        invalid_message_key="loader.banned_keywords_invalid",
    )
    validate_keyword_lists(
        required_keywords,
        banned_keywords,
        task_path,
        required_field_name=labels.get("requiredKeywords", "requiredKeywords"),
        banned_field_name=labels.get("bannedKeywords", "bannedKeywords"),
    )
    return ScriptConstraints(
        operators_limit=operators_limit,
        custom_function_call_count=custom_function_call_count,
        if_limit=if_limit,
        while_limit=while_limit,
        required_keywords=required_keywords,
        banned_keywords=banned_keywords,
    )


def parse_operators_limit(
    data: dict,
    task_path: Optional[Path],
    *,
    field_name: Optional[str] = None,
) -> Optional[int]:
    """Parse optional ``operatorsLimit`` from task JSON."""
    return _parse_optional_non_negative_int(
        data,
        task_path,
        json_key="operatorsLimit",
        invalid_message_key="loader.operators_limit_invalid",
        field_name=field_name,
    )


def parse_custom_function_call_count(
    data: dict,
    task_path: Optional[Path],
    *,
    field_name: Optional[str] = None,
) -> Optional[int]:
    """Parse optional ``customFunctionCallCount`` from task JSON."""
    return _parse_optional_non_negative_int(
        data,
        task_path,
        json_key="customFunctionCallCount",
        invalid_message_key="loader.custom_function_call_count_invalid",
        field_name=field_name,
    )


def parse_if_limit(
    data: dict,
    task_path: Optional[Path],
    *,
    field_name: Optional[str] = None,
) -> Optional[int]:
    """Parse optional ``ifLimit`` from task JSON."""
    return _parse_optional_non_negative_int(
        data,
        task_path,
        json_key="ifLimit",
        invalid_message_key="loader.if_limit_invalid",
        field_name=field_name,
    )


def parse_while_limit(
    data: dict,
    task_path: Optional[Path],
    *,
    field_name: Optional[str] = None,
) -> Optional[int]:
    """Parse optional ``whileLimit`` from task JSON."""
    return _parse_optional_non_negative_int(
        data,
        task_path,
        json_key="whileLimit",
        invalid_message_key="loader.while_limit_invalid",
        field_name=field_name,
    )


def parse_keyword_list(
    data: dict,
    task_path: Optional[Path],
    *,
    json_key: str,
    invalid_message_key: str,
    field_name: Optional[str] = None,
) -> Optional[Tuple[str, ...]]:
    """Parse a comma-separated Python keyword list from task JSON."""
    display_name = field_name if field_name is not None else json_key
    if json_key not in data:
        return None

    value = data[json_key]
    if not isinstance(value, str):
        raise TaskLoadError(
            t(
                invalid_message_key,
                field_name=display_name,
                task_path_suffix=_format_task_path_suffix(task_path),
            )
        )

    keywords = tuple(sorted({part.strip() for part in value.split(",") if part.strip()}))
    invalid_keywords = tuple(
        keyword_name for keyword_name in keywords if keyword_name not in PYTHON_KEYWORDS
    )
    if invalid_keywords:
        raise TaskLoadError(
            t(
                "loader.keyword_list_unknown_keywords",
                field_name=display_name,
                keywords=", ".join(invalid_keywords),
                task_path_suffix=_format_task_path_suffix(task_path),
            )
        )
    return keywords


def validate_keyword_lists(
    required_keywords: Optional[Tuple[str, ...]],
    banned_keywords: Optional[Tuple[str, ...]],
    task_path: Optional[Path],
    *,
    required_field_name: str = "requiredKeywords",
    banned_field_name: str = "bannedKeywords",
) -> None:
    """Raise ``TaskLoadError`` when required and banned keyword sets overlap."""
    if not required_keywords or not banned_keywords:
        return

    overlap = tuple(sorted(set(required_keywords) & set(banned_keywords)))
    if overlap:
        raise TaskLoadError(
            t(
                "loader.keyword_lists_conflict",
                required_field_name=required_field_name,
                banned_field_name=banned_field_name,
                keywords=", ".join(overlap),
                task_path_suffix=_format_task_path_suffix(task_path),
            )
        )
