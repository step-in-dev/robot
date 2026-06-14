"""Serialize validated environment DTOs to task JSON."""

from __future__ import annotations

from typing import Any, Dict

from .model import Cell, RobotEnvDto, ValuedCell


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
