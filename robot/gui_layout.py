from __future__ import annotations

from .gui_theme import (
    COMPACT_CELL_MAX_HEIGHT,
    COMPACT_CELL_MAX_WIDTH,
    COMPACT_CELL_SIZE,
    DEFAULT_CELL_SIZE,
    MIN_CANVAS_WIDTH,
)
from .model import RobotEnv


def calculate_cell_size(envs: list[RobotEnv]) -> int:
    """Pixel side length for cells; compact when any env exceeds width/height thresholds."""
    max_width = max(env.width for env in envs)
    max_height = max(env.height for env in envs)
    if (
        max_width > COMPACT_CELL_MAX_WIDTH
        or max_height > COMPACT_CELL_MAX_HEIGHT
    ):
        return COMPACT_CELL_SIZE
    return DEFAULT_CELL_SIZE


def calculate_canvas_size(
    envs: list[RobotEnv], cell_size: int, wall_width: int
) -> tuple[int, int]:
    """Pixel size of the canvas needed to show the largest environment in envs."""
    max_width = max(env.width for env in envs)
    max_height = max(env.height for env in envs)
    calculated_width = max_width * cell_size + wall_width
    return (
        max(calculated_width, MIN_CANVAS_WIDTH),
        max_height * cell_size + wall_width,
    )


def calculate_field_offset(
    canvas_width: int,
    canvas_height: int,
    env: RobotEnv,
    cell_size: int,
    wall_width: int,
) -> tuple[int, int]:
    """Pixel offset to center env's field inside a canvas for the largest env."""
    field_width = env.width * cell_size + wall_width
    field_height = env.height * cell_size + wall_width
    return (
        (canvas_width - field_width) // 2,
        (canvas_height - field_height) // 2,
    )
