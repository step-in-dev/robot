"""Pure environment-editing helpers for the task environment editor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .i18n import t
from .model import (
    MAX_FIELD_HEIGHT,
    MAX_FIELD_WIDTH,
    Cell,
    RobotEnv,
    RobotEnvDto,
    _canonical_wall,
)
from .task_serializer import (
    create_default_env_dto,
    normalize_env_dto_dict,
    wall_from_json,
    wall_to_json,
)

MAX_ENV_COUNT = 7
POLLUTION_VALUE_MIN = 1
POLLUTION_VALUE_MAX = 99
PRINT_VALUE_MIN = -99
PRINT_VALUE_MAX = 99


class EnvEditTool(Enum):
    """Canvas editing tools matching the web embedded environment editor."""

    START = "start"
    FINAL = "final"
    WALL = "wall"
    PAINTED = "painted"
    TO_PAINT = "to_paint"
    POLLUTION = "pollution"
    NUMBER = "number"
    REMOVE_POLLUTION = "remove_pollution"
    REMOVE_NUMBER = "remove_number"


def _cell_in_bounds(cell: Cell, width: int, height: int) -> bool:
    return 0 <= cell.r < height and 0 <= cell.c < width


def _find_cell_index(cells: List[dict], row: int, col: int) -> Optional[int]:
    for index, item in enumerate(cells):
        if item.get("r") == row and item.get("c") == col:
            return index
    return None


def _remove_cell(cells: List[dict], row: int, col: int) -> None:
    index = _find_cell_index(cells, row, col)
    if index is not None:
        cells.pop(index)


def _toggle_cell(cells: List[dict], row: int, col: int) -> None:
    index = _find_cell_index(cells, row, col)
    if index is None:
        cells.append({"r": row, "c": col})
    else:
        cells.pop(index)


def _set_valued_cell(
    cells: List[dict], row: int, col: int, value: int
) -> None:
    index = _find_cell_index(cells, row, col)
    payload = {"r": row, "c": col, "value": value}
    if index is None:
        cells.append(payload)
    else:
        cells[index] = payload


def reset_env_dto(env: dict) -> dict:
    """Clear walls and cell collections; reset start/final to corners."""
    return normalize_env_dto_dict(
        create_default_env_dto(
            width=int(env["width"]),
            height=int(env["height"]),
        )
    )


def resize_env_dto(env: dict, *, width: int, height: int) -> dict:
    """Resize an environment and drop out-of-bounds data."""
    if not 1 <= width <= MAX_FIELD_WIDTH:
        raise ValueError(
            t("editor.error.width_out_of_range", max=MAX_FIELD_WIDTH)
        )
    if not 1 <= height <= MAX_FIELD_HEIGHT:
        raise ValueError(
            t("editor.error.height_out_of_range", max=MAX_FIELD_HEIGHT)
        )

    def keep_cell(item: dict) -> bool:
        return 0 <= int(item["r"]) < height and 0 <= int(item["c"]) < width

    def keep_wall(wall: list) -> bool:
        first, second = wall_from_json(wall)
        return _cell_in_bounds(first, width, height) and _cell_in_bounds(
            second, width, height
        )

    updated = deepcopy(env)
    updated["width"] = width
    updated["height"] = height
    updated["startRow"] = min(int(updated.get("startRow", 0)), height - 1)
    updated["startCol"] = min(int(updated.get("startCol", 0)), width - 1)
    updated["finalRow"] = min(int(updated.get("finalRow", height - 1)), height - 1)
    updated["finalCol"] = min(int(updated.get("finalCol", width - 1)), width - 1)

    for key in ("paintedCells", "cellsToPaint"):
        if key in updated:
            updated[key] = [item for item in updated[key] if keep_cell(item)]
    for key in ("pollutedCells", "cellsToPrint"):
        if key in updated:
            updated[key] = [item for item in updated[key] if keep_cell(item)]
    if "walls" in updated:
        updated["walls"] = [wall for wall in updated["walls"] if keep_wall(wall)]
    return normalize_env_dto_dict(updated)


@dataclass(frozen=True)
class WallHitContext:
    """Field geometry for resolving the nearest wall edge."""

    cell_size: int
    width: int
    height: int


def nearest_wall_cells(
    row: int,
    col: int,
    local_x: float,
    local_y: float,
    context: WallHitContext,
) -> Optional[Tuple[Cell, Cell]]:
    """Return adjacent cells for the nearest internal wall edge, if any."""
    distances = {
        "left": local_x,
        "right": context.cell_size - local_x,
        "top": local_y,
        "bottom": context.cell_size - local_y,
    }
    edge = min(distances, key=distances.get)
    cell = Cell(row, col)
    if edge == "left" and col > 0:
        return cell, Cell(row, col - 1)
    if edge == "right" and col < context.width - 1:
        return cell, Cell(row, col + 1)
    if edge == "top" and row > 0:
        return cell, Cell(row - 1, col)
    if edge == "bottom" and row < context.height - 1:
        return cell, Cell(row + 1, col)
    return None


@dataclass(frozen=True)
class CanvasHitContext:
    """Geometry needed to map canvas clicks to grid cells."""

    offset_x: int
    offset_y: int
    half_wall_width: int
    cell_size: int
    width: int
    height: int


def canvas_to_cell(
    canvas_x: float,
    canvas_y: float,
    *,
    context: CanvasHitContext,
) -> Tuple[Optional[Cell], Optional[Tuple[Cell, Cell]]]:
    """Map canvas coordinates to a cell and optional wall segment."""
    field_x = canvas_x - context.offset_x - context.half_wall_width
    field_y = canvas_y - context.offset_y - context.half_wall_width
    if field_x < 0 or field_y < 0:
        return None, None

    col = int(field_x // context.cell_size)
    row = int(field_y // context.cell_size)
    if not (0 <= row < context.height and 0 <= col < context.width):
        return None, None

    local_x = field_x - col * context.cell_size
    local_y = field_y - row * context.cell_size
    cell = Cell(row, col)
    wall = nearest_wall_cells(
        row,
        col,
        local_x,
        local_y,
        WallHitContext(
            cell_size=context.cell_size,
            width=context.width,
            height=context.height,
        ),
    )
    return cell, wall


def toggle_wall(env: dict, first: Cell, second: Cell) -> dict:
    """Add or remove a wall between two adjacent cells."""
    if not _cell_in_bounds(first, env["width"], env["height"]):
        return env
    if not _cell_in_bounds(second, env["width"], env["height"]):
        return env
    updated = deepcopy(env)
    walls = updated.setdefault("walls", [])
    key = _canonical_wall(first, second)
    for index, wall in enumerate(walls):
        current = wall_from_json(wall)
        if _canonical_wall(current[0], current[1]) == key:
            walls.pop(index)
            return normalize_env_dto_dict(updated)
    walls.append(wall_to_json(first, second))
    return normalize_env_dto_dict(updated)


def apply_tool_to_env(
    env: dict,
    tool: EnvEditTool,
    cell: Cell,
    *,
    pollution_value: int = 1,
    print_value: int = 0,
) -> dict:
    """Apply one editor tool click to an environment DTO dict."""
    if not _cell_in_bounds(cell, env["width"], env["height"]):
        return env

    updated = deepcopy(env)
    if tool is EnvEditTool.START:
        updated["startRow"] = cell.r
        updated["startCol"] = cell.c
    elif tool is EnvEditTool.FINAL:
        updated["finalRow"] = cell.r
        updated["finalCol"] = cell.c
    elif tool is EnvEditTool.PAINTED:
        painted = updated.setdefault("paintedCells", [])
        to_paint = updated.setdefault("cellsToPaint", [])
        _remove_cell(to_paint, cell.r, cell.c)
        _toggle_cell(painted, cell.r, cell.c)
    elif tool is EnvEditTool.TO_PAINT:
        painted = updated.setdefault("paintedCells", [])
        to_paint = updated.setdefault("cellsToPaint", [])
        _remove_cell(painted, cell.r, cell.c)
        _toggle_cell(to_paint, cell.r, cell.c)
    elif tool is EnvEditTool.POLLUTION:
        value = max(POLLUTION_VALUE_MIN, min(POLLUTION_VALUE_MAX, pollution_value))
        _set_valued_cell(
            updated.setdefault("pollutedCells", []), cell.r, cell.c, value
        )
    elif tool is EnvEditTool.NUMBER:
        value = max(PRINT_VALUE_MIN, min(PRINT_VALUE_MAX, print_value))
        _set_valued_cell(
            updated.setdefault("cellsToPrint", []), cell.r, cell.c, value
        )
    elif tool is EnvEditTool.REMOVE_POLLUTION:
        _remove_cell(updated.setdefault("pollutedCells", []), cell.r, cell.c)
    elif tool is EnvEditTool.REMOVE_NUMBER:
        _remove_cell(updated.setdefault("cellsToPrint", []), cell.r, cell.c)
    else:
        return env
    return normalize_env_dto_dict(updated)


def can_add_environment(env_dtos: List[dict]) -> bool:
    """Return whether another environment may be appended."""
    return len(env_dtos) < MAX_ENV_COUNT


def can_remove_environment(env_dtos: List[dict]) -> bool:
    """Return whether an environment may be removed."""
    return len(env_dtos) > 1


def add_environment(env_dtos: List[dict]) -> List[dict]:
    """Append a cloned or default environment."""
    if not can_add_environment(env_dtos):
        raise ValueError("environment count limit reached")
    if env_dtos:
        env_dtos = env_dtos + [deepcopy(env_dtos[-1])]
    else:
        env_dtos = [create_default_env_dto()]
    return env_dtos


def remove_environment(env_dtos: List[dict], index: int) -> List[dict]:
    """Remove one environment when more than one exists."""
    if not can_remove_environment(env_dtos):
        raise ValueError("cannot remove the only environment")
    updated = deepcopy(env_dtos)
    updated.pop(index)
    return updated


def dto_dict_to_env(env: dict) -> RobotEnv:
    """Build a ``RobotEnv`` preview object from a DTO dict."""
    preview = RobotEnv(RobotEnvDto.from_dict(env))
    preview.reset()
    return preview
