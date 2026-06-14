"""Load and save Robot task ``.env`` files for the environment editor."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .env_dto_json import cell_to_dict
from .i18n import DEFAULT_LANGUAGE, detect_language, t
from .script_constraints import ScriptConstraints
from .task_errors import TaskLoadError
from .model import (
    Cell,
    cell_from_dict,
)
from .task_catalog import KNOWN_TASK_GROUP_PREFIXES, theme_from_task_id
from .task_payload import parse_script_constraints
from .task_todo import normalized_todo_text_map
from .task_validation import validate_desktop_task_payload

TASK_FILE_EXTENSION = ".env"

_EDITABLE_TOP_LEVEL_KEYS = frozenset({"envDtos", "todoText"})

_CONSTRAINT_JSON_KEYS = (
    "operatorsLimit",
    "customFunctionCallCount",
    "ifLimit",
    "whileLimit",
    "requiredKeywords",
    "bannedKeywords",
)

_CONSTRAINT_FIELD_LABEL_KEYS = {
    "operatorsLimit": "editor.constraints.field.operators_limit",
    "customFunctionCallCount": "editor.constraints.field.custom_function_call_count",
    "ifLimit": "editor.constraints.field.if_limit",
    "whileLimit": "editor.constraints.field.while_limit",
    "requiredKeywords": "editor.constraints.field.required_keywords",
    "bannedKeywords": "editor.constraints.field.banned_keywords",
}

_DEFAULT_WIDTH = 5
_DEFAULT_HEIGHT = 5


class TaskSaveError(Exception):
    """Raised when a task file cannot be written."""


@dataclass
class ConstraintFieldInput:
    """Raw constraint field values from the editor dialog."""

    operators_limit: str = ""
    custom_function_call_count: str = ""
    if_limit: str = ""
    while_limit: str = ""
    required_keywords: str = ""
    banned_keywords: str = ""


@dataclass
class EditorDocument:
    """In-memory task payload for the environment editor."""

    env_dtos: List[dict]
    todo_text: Any = ""
    selected_env_index: int = 0
    file_path: Optional[Path] = None
    preserved_fields: Dict[str, Any] = field(default_factory=dict)


def bundled_tasks_dir() -> Path:
    """Return the packaged ``robot/tasks`` directory."""
    return Path(__file__).resolve().parent / "tasks"


def is_bundled_task_path(path: Path) -> bool:
    """Return whether *path* lives under the bundled tasks directory."""
    try:
        path.resolve().relative_to(bundled_tasks_dir().resolve())
    except ValueError:
        return False
    return True


def is_bundled_category_save_forbidden(path: Path) -> bool:
    """Return whether saving *path* into bundled tasks must be blocked."""
    if not is_bundled_task_path(path):
        return False
    theme = theme_from_task_id(path.stem)
    return theme is not None and theme in KNOWN_TASK_GROUP_PREFIXES


def create_default_env_dto(
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> dict:
    """Return a new empty environment DTO dict."""
    return {
        "width": width,
        "height": height,
        "startRow": 0,
        "startCol": 0,
        "finalRow": height - 1,
        "finalCol": width - 1,
    }


def create_empty_document() -> EditorDocument:
    """Return a new editor document with one default environment."""
    return EditorDocument(env_dtos=[create_default_env_dto()])


def document_to_payload(document: EditorDocument) -> dict:
    """Build the top-level JSON object for saving."""
    payload = dict(document.preserved_fields)
    payload["envDtos"] = deepcopy(document.env_dtos)
    if document.todo_text != "":
        payload["todoText"] = deepcopy(document.todo_text)
    elif "todoText" in payload:
        del payload["todoText"]
    return payload


def load_task_file(path: Path) -> EditorDocument:
    """Load a task file into an editor document."""
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except OSError as exc:
        raise TaskLoadError(
            t("loader.cannot_read_task_file", task_path=path)
        ) from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(t("loader.invalid_json", task_path=path)) from exc

    validated = validate_desktop_task_payload(data, path)
    preserved = {
        key: deepcopy(value)
        for key, value in data.items()
        if key not in _EDITABLE_TOP_LEVEL_KEYS
    }
    return EditorDocument(
        env_dtos=validated.env_dtos,
        todo_text=deepcopy(validated.raw_todo),
        selected_env_index=0,
        file_path=path,
        preserved_fields=preserved,
    )


def save_task_file(path: Path, document: EditorDocument) -> None:
    """Write *document* to a ``.env`` file."""
    payload = document_to_payload(document)
    try:
        validated = validate_desktop_task_payload(payload, path)
    except TaskLoadError as exc:
        raise ValueError(str(exc)) from exc
    write_payload = dict(payload)
    write_payload["envDtos"] = validated.env_dtos
    try:
        path.write_text(
            json.dumps(write_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaskSaveError(
            t("editor.error.cannot_save", task_path=path)
        ) from exc
    document.env_dtos = validated.env_dtos
    document.file_path = path


def _constraint_snapshot_slice(preserved_fields: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: deepcopy(preserved_fields[key])
        for key in _CONSTRAINT_JSON_KEYS
        if key in preserved_fields
    }


def _apply_constraint_snapshot_slice(
    preserved_fields: Dict[str, Any],
    snapshot_slice: Dict[str, Any],
) -> None:
    for key in _CONSTRAINT_JSON_KEYS:
        preserved_fields.pop(key, None)
    preserved_fields.update(deepcopy(snapshot_slice))


def constraint_field_display_values(preserved_fields: Dict[str, Any]) -> Dict[str, str]:
    """Return dialog initial values for all supported constraint fields."""
    values = {
        "operators_limit": "",
        "custom_function_call_count": "",
        "if_limit": "",
        "while_limit": "",
        "required_keywords": "",
        "banned_keywords": "",
    }
    int_keys = {
        "operators_limit": "operatorsLimit",
        "custom_function_call_count": "customFunctionCallCount",
        "if_limit": "ifLimit",
        "while_limit": "whileLimit",
    }
    for field_name, json_key in int_keys.items():
        raw = preserved_fields.get(json_key)
        if raw is not None:
            values[field_name] = str(raw)
    for field_name, json_key in (
        ("required_keywords", "requiredKeywords"),
        ("banned_keywords", "bannedKeywords"),
    ):
        raw = preserved_fields.get(json_key)
        if isinstance(raw, str):
            values[field_name] = raw
    return values


def _constraint_field_labels() -> Dict[str, str]:
    return {
        json_key: t(label_key)
        for json_key, label_key in _CONSTRAINT_FIELD_LABEL_KEYS.items()
    }


def _optional_dialog_int_payload(raw: str) -> Optional[Any]:
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return stripped


def parse_constraint_field_input(fields: ConstraintFieldInput) -> ScriptConstraints:
    """Parse and validate constraint dialog input.

    Raises :class:`ValueError` with a localized message when validation fails.
    """
    labels = _constraint_field_labels()
    data: Dict[str, Any] = {}
    for json_key, raw in (
        ("operatorsLimit", fields.operators_limit),
        ("customFunctionCallCount", fields.custom_function_call_count),
        ("ifLimit", fields.if_limit),
        ("whileLimit", fields.while_limit),
    ):
        value = _optional_dialog_int_payload(raw)
        if value is not None:
            data[json_key] = value
    for json_key, raw in (
        ("requiredKeywords", fields.required_keywords),
        ("bannedKeywords", fields.banned_keywords),
    ):
        stripped = raw.strip()
        if stripped:
            data[json_key] = stripped
    try:
        return parse_script_constraints(data, None, field_names=labels)
    except TaskLoadError as exc:
        raise ValueError(str(exc)) from exc


def _write_parsed_constraints_to_preserved(
    preserved_fields: Dict[str, Any],
    constraints: ScriptConstraints,
) -> None:
    for key in _CONSTRAINT_JSON_KEYS:
        preserved_fields.pop(key, None)
    if constraints.operators_limit is not None:
        preserved_fields["operatorsLimit"] = constraints.operators_limit
    if constraints.custom_function_call_count is not None:
        preserved_fields["customFunctionCallCount"] = (
            constraints.custom_function_call_count
        )
    if constraints.if_limit is not None:
        preserved_fields["ifLimit"] = constraints.if_limit
    if constraints.while_limit is not None:
        preserved_fields["whileLimit"] = constraints.while_limit
    if constraints.required_keywords:
        preserved_fields["requiredKeywords"] = ", ".join(
            constraints.required_keywords
        )
    if constraints.banned_keywords:
        preserved_fields["bannedKeywords"] = ", ".join(constraints.banned_keywords)


def apply_constraint_fields_to_preserved(
    preserved_fields: Dict[str, Any],
    fields: ConstraintFieldInput,
) -> None:
    """Validate dialog input and update ``preserved_fields`` constraint keys.

    Raises :class:`ValueError` with a localized message when validation fails.
    """
    constraints = parse_constraint_field_input(fields)
    _write_parsed_constraints_to_preserved(preserved_fields, constraints)


def update_todo_text(
    todo_raw: Any,
    new_text: str,
    *,
    target_lang: Optional[str] = None,
) -> Any:
    """Update task condition text while preserving its JSON shape.

    Plain strings stay plain strings. For localized maps, update
    *target_lang* when provided (the locale that supplied the displayed
    text); otherwise use the current UI language.
    """
    if isinstance(todo_raw, dict):
        updated = dict(normalized_todo_text_map(todo_raw))
        lang = target_lang if target_lang is not None else (
            detect_language() or DEFAULT_LANGUAGE
        )
        updated[lang] = new_text
        return updated
    return new_text


def snapshot_from_document(document: EditorDocument) -> dict:
    """Return a JSON-serializable undo/redo snapshot."""
    return {
        "envDtos": deepcopy(document.env_dtos),
        "selectedEnvIndex": document.selected_env_index,
        "todoText": deepcopy(document.todo_text),
        "preservedConstraints": _constraint_snapshot_slice(
            document.preserved_fields
        ),
    }


def persisted_snapshot_from_document(document: EditorDocument) -> dict:
    """Return a snapshot of task content that would be written to disk.

    Excludes view-only state such as the selected environment tab index.
    """
    snapshot = snapshot_from_document(document)
    snapshot.pop("selectedEnvIndex", None)
    return snapshot


def apply_snapshot(document: EditorDocument, snapshot: dict) -> None:
    """Restore *document* from a snapshot produced by :func:`snapshot_from_document`."""
    snapshot_payload: Dict[str, Any] = {
        "envDtos": deepcopy(snapshot["envDtos"]),
        **deepcopy(snapshot.get("preservedConstraints", {})),
    }
    if "todoText" in snapshot:
        snapshot_payload["todoText"] = deepcopy(snapshot["todoText"])
    validated = validate_desktop_task_payload(snapshot_payload, None)
    document.env_dtos = validated.env_dtos
    document.selected_env_index = int(snapshot["selectedEnvIndex"])
    document.todo_text = deepcopy(snapshot.get("todoText", ""))
    _apply_constraint_snapshot_slice(
        document.preserved_fields,
        deepcopy(snapshot.get("preservedConstraints", {})),
    )


def snapshots_equal(left: dict, right: dict) -> bool:
    """Return whether two editor snapshots are semantically equal."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def wall_from_json(wall: list) -> Tuple[Cell, Cell]:
    """Parse a wall segment from task JSON."""
    return cell_from_dict(wall[0]), cell_from_dict(wall[1])


def wall_to_json(first: Cell, second: Cell) -> list:
    """Serialize a wall segment to task JSON."""
    return [cell_to_dict(first), cell_to_dict(second)]
