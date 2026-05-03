"""Localized short descriptions for student-facing Robot commands."""

from __future__ import annotations

from typing import Iterable

from .i18n import t

# (i18n key suffix under help.command.*, display signature)
COMMAND_HELP_SPECS: tuple[tuple[str, str], ...] = (
    ("task", "task(task_id)"),
    ("move_right", "move_right()"),
    ("move_left", "move_left()"),
    ("move_up", "move_up()"),
    ("move_down", "move_down()"),
    ("paint", "paint()"),
    ("is_free_left", "is_free_left()"),
    ("is_free_right", "is_free_right()"),
    ("is_free_up", "is_free_up()"),
    ("is_free_down", "is_free_down()"),
    ("is_wall_left", "is_wall_left()"),
    ("is_wall_right", "is_wall_right()"),
    ("is_wall_up", "is_wall_up()"),
    ("is_wall_down", "is_wall_down()"),
    ("is_cell_painted", "is_cell_painted()"),
    ("is_cell_not_painted", "is_cell_not_painted()"),
    ("pol", "pol()"),
    ("printn", "printn(value)"),
)


def command_help_public_keys() -> frozenset[str]:
    """Set of command names covered by the help dialog (matches public API names)."""
    return frozenset(key for key, _ in COMMAND_HELP_SPECS)


def iter_command_help() -> list[tuple[str, str]]:
    """Pairs of (signature, localized description)."""
    return [
        (signature, t(f"help.command.{command_key}"))
        for command_key, signature in COMMAND_HELP_SPECS
    ]


def iter_command_help_lines() -> Iterable[str]:
    """Lines for a plain-text help body."""
    yield t("help.intro")
    yield ""
    for signature, description in iter_command_help():
        yield signature
        yield f"  {description}"
        yield ""
