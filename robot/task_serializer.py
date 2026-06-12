"""Load and save Robot task ``.env`` files for the environment editor."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .i18n import DEFAULT_LANGUAGE, detect_language, normalize_language, t
from .loader import TaskLoadError, parse_task_payload
from .model import (
    Cell,
    RobotEnvDto,
    ValuedCell,
    cell_from_dict,
)

TASK_FILE_EXTENSION = ".env"

_EDITABLE_TOP_LEVEL_KEYS = frozenset({"envDtos", "todoText"})

_DEFAULT_WIDTH = 5
_DEFAULT_HEIGHT = 5


class TaskSaveError(Exception):
    """Raised when a task file cannot be written."""


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


def cell_to_dict(cell: Cell) -> dict:
    """Serialize a grid cell to task JSON."""
    return {"r": cell.r, "c": cell.c}


def valued_cell_to_dict(cell: ValuedCell) -> dict:
    """Serialize a valued grid cell to task JSON."""
    return {"r": cell.r, "c": cell.c, "value": cell.value}


def env_dto_to_dict(dto: RobotEnvDto) -> dict:
    """Serialize a validated DTO back to task JSON."""
    data: Dict[str, Any] = {
        "width": dto.width,
        "height": dto.height,
        "startRow": dto.start_row,
        "startCol": dto.start_col,
        "finalRow": dto.final_row,
        "finalCol": dto.final_col,
    }
    if dto.walls:
        data["walls"] = [
            [cell_to_dict(first), cell_to_dict(second)]
            for first, second in dto.walls
        ]
    if dto.painted_cells:
        data["paintedCells"] = [cell_to_dict(cell) for cell in dto.painted_cells]
    if dto.cells_to_paint:
        data["cellsToPaint"] = [cell_to_dict(cell) for cell in dto.cells_to_paint]
    if dto.polluted_cells:
        data["pollutedCells"] = [
            valued_cell_to_dict(cell) for cell in dto.polluted_cells
        ]
    if dto.cells_to_print:
        data["cellsToPrint"] = [
            valued_cell_to_dict(cell) for cell in dto.cells_to_print
        ]
    return data


def normalize_env_dto_dict(data: dict) -> dict:
    """Validate and canonicalize one environment object."""
    dto = RobotEnvDto.from_dict(data)
    return env_dto_to_dict(dto)


def normalize_env_dtos(env_dtos: List[dict]) -> List[dict]:
    """Validate and canonicalize every environment in *env_dtos*."""
    if not env_dtos:
        raise ValueError(t("editor.error.no_environments"))
    return [normalize_env_dto_dict(item) for item in env_dtos]


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

    env_dtos_data, _resolved_todo = parse_task_payload(data, path)
    preserved = {
        key: deepcopy(value)
        for key, value in data.items()
        if key not in _EDITABLE_TOP_LEVEL_KEYS
    }
    raw_todo = data.get("todoText", "")
    env_dtos = normalize_env_dtos(env_dtos_data)
    return EditorDocument(
        env_dtos=env_dtos,
        todo_text=deepcopy(raw_todo),
        selected_env_index=0,
        file_path=path,
        preserved_fields=preserved,
    )


def save_task_file(path: Path, document: EditorDocument) -> None:
    """Write *document* to a ``.env`` file."""
    document.env_dtos = normalize_env_dtos(document.env_dtos)
    payload = document_to_payload(document)
    try:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TaskSaveError(
            t("editor.error.cannot_save", task_path=path)
        ) from exc
    document.file_path = path


def update_todo_text(todo_raw: Any, new_text: str) -> Any:
    """Update display todo text while preserving localized maps when possible."""
    if isinstance(todo_raw, dict):
        updated: Dict[str, str] = {}
        for key, value in todo_raw.items():
            if isinstance(key, str) and isinstance(value, str):
                norm = normalize_language(key)
                if norm is not None:
                    updated[norm] = value
        lang = detect_language() or DEFAULT_LANGUAGE
        updated[lang] = new_text
        return updated
    return new_text


def snapshot_from_document(document: EditorDocument) -> dict:
    """Return a JSON-serializable undo/redo snapshot."""
    return {
        "envDtos": deepcopy(document.env_dtos),
        "selectedEnvIndex": document.selected_env_index,
        "todoText": deepcopy(document.todo_text),
    }


def apply_snapshot(document: EditorDocument, snapshot: dict) -> None:
    """Restore *document* from a snapshot produced by :func:`snapshot_from_document`."""
    document.env_dtos = normalize_env_dtos(deepcopy(snapshot["envDtos"]))
    document.selected_env_index = int(snapshot["selectedEnvIndex"])
    document.todo_text = deepcopy(snapshot.get("todoText", ""))


def snapshots_equal(left: dict, right: dict) -> bool:
    """Return whether two editor snapshots are semantically equal."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def wall_from_json(wall: list) -> Tuple[Cell, Cell]:
    """Parse a wall segment from task JSON."""
    return cell_from_dict(wall[0]), cell_from_dict(wall[1])


def wall_to_json(first: Cell, second: Cell) -> list:
    """Serialize a wall segment to task JSON."""
    return [cell_to_dict(first), cell_to_dict(second)]
