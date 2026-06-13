"""Load task definitions from bundled or custom .env files."""

from __future__ import annotations

import json
import keyword
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .i18n import DEFAULT_LANGUAGE, detect_language, normalize_language, t
from .model import RobotEnv, RobotEnvDto, _is_plain_int


TASKS_DIR_ENV = "ROBOT_TASKS_DIR"
TASK_FILE_EXTENSION = ".env"
PYTHON_KEYWORDS = frozenset(keyword.kwlist)


class TaskLoadError(Exception):
    """Raised when a task ``.env`` file cannot be loaded or parsed."""


@dataclass(frozen=True)
class ScriptConstraints:
    """Static script limits loaded from a task ``.env`` file."""

    operators_limit: Optional[int] = None
    custom_function_call_count: Optional[int] = None
    if_limit: Optional[int] = None
    while_limit: Optional[int] = None
    required_keywords: Optional[Tuple[str, ...]] = None
    banned_keywords: Optional[Tuple[str, ...]] = None

    @classmethod
    def from_task(cls, task: RobotTask) -> ScriptConstraints:
        """Copy constraint fields from a loaded task."""
        return task.script_constraints


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

    env_dtos_data, todo_text = parse_task_payload(data, task_path)
    operators_limit = parse_operators_limit(data, task_path)
    custom_function_call_count = parse_custom_function_call_count(data, task_path)
    if_limit = parse_if_limit(data, task_path)
    while_limit = parse_while_limit(data, task_path)
    required_keywords = parse_keyword_list(
        data,
        task_path,
        json_key="requiredKeywords",
        invalid_message_key="loader.required_keywords_invalid",
    )
    banned_keywords = parse_keyword_list(
        data,
        task_path,
        json_key="bannedKeywords",
        invalid_message_key="loader.banned_keywords_invalid",
    )
    validate_keyword_lists(required_keywords, banned_keywords, task_path)
    environments = [
        RobotEnv(RobotEnvDto.from_dict(env)) for env in env_dtos_data
    ]
    if not environments:
        raise TaskLoadError(t("loader.no_environments", task_path=task_path))
    return RobotTask(
        envs=environments,
        todo_text=todo_text,
        script_constraints=ScriptConstraints(
            operators_limit=operators_limit,
            custom_function_call_count=custom_function_call_count,
            if_limit=if_limit,
            while_limit=while_limit,
            required_keywords=required_keywords,
            banned_keywords=banned_keywords,
        ),
    )


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


def parse_task_payload(data: Any, task_path: Path) -> Tuple[List[dict], str]:
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
                t("loader.env_dtos_index_must_be_object", index=index, task_path=task_path)
            )
        result.append(item)

    return result, todo_text


@dataclass(frozen=True)
class ResolvedTodoText:
    """Task condition text resolved for the current UI language."""

    text: str
    source_lang: Optional[str] = None


def normalized_todo_text_map(raw: dict) -> Dict[str, str]:
    """Return supported language keys from a localized ``todoText`` object."""
    by_lang: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        norm = normalize_language(key)
        if norm is not None:
            by_lang[norm] = value
    return by_lang


def resolve_todo_text_for_ui(raw: Any) -> ResolvedTodoText:
    """Resolve ``todoText`` for display and single-locale editing in the editor.

    Plain strings are returned as-is with no ``source_lang``. For localized
    maps, ``source_lang`` is the key whose value was chosen: current UI
    language, then :data:`DEFAULT_LANGUAGE` (``en``), or ``None`` when no
    suitable entry exists.
    """
    if isinstance(raw, str):
        return ResolvedTodoText(text=raw)
    if not isinstance(raw, dict):
        return ResolvedTodoText(text="")
    by_lang = normalized_todo_text_map(raw)
    if not by_lang:
        return ResolvedTodoText(text="")
    ui = detect_language()
    if ui in by_lang:
        return ResolvedTodoText(text=by_lang[ui], source_lang=ui)
    if DEFAULT_LANGUAGE in by_lang:
        return ResolvedTodoText(
            text=by_lang[DEFAULT_LANGUAGE], source_lang=DEFAULT_LANGUAGE
        )
    return ResolvedTodoText(text="")


def resolve_todo_text(raw: Any) -> str:
    """Return task condition text: plain string, or localized map resolved to UI language.

    If ``raw`` is a string, it is returned as-is (legacy format).
    If ``raw`` is a dict mapping locale keys to strings, pick the value for
    :func:`detect_language`, then fall back to :data:`DEFAULT_LANGUAGE` (``en``),
    then ``""``. Only string keys and string values contribute; keys are
    normalized with :func:`normalize_language` (e.g. ``ru_RU`` → ``ru``).
    Any other type yields ``""``.
    """
    return resolve_todo_text_for_ui(raw).text


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
