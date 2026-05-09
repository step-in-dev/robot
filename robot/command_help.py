"""Localized short descriptions for student-facing Robot commands."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from .i18n import t

# (i18n key suffix under help.command.*, display signature)
COMMAND_HELP_SPECS: tuple[tuple[str, str], ...] = (
    ("task", "task(task_id)"),
    ("field", "field(width=8, height=6)"),
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
    yield t("help.commands_title")
    yield ""
    for signature, description in iter_command_help():
        yield signature
        yield f"  {description}"
        yield ""


# Ordered mapping from filename prefix to i18n key suffix under help.task_group.*
_TASK_GROUP_PREFIXES: tuple[str, ...] = (
    "intro",
    "fun",
    "for",
    "forfun",
    "w",
    "wfun",
    "if",
    "wif",
    "ifelse",
    "compound",
)

_TASKS_DIR = Path(__file__).resolve().parent / "tasks"
_TASK_FILE_EXT = ".env"
_PREFIX_RE = re.compile(r"^([a-zA-Z]+)")
_NUMBER_RE = re.compile(r"(\d+)$")


def _natural_sort_key(task_id: str) -> tuple[str, int]:
    """Sort key that orders numbers numerically within the same prefix."""
    m = _NUMBER_RE.search(task_id)
    num = int(m.group(1)) if m else 0
    return (task_id[: m.start()] if m else task_id, num)


def _discover_task_ids() -> dict[str, list[str]]:
    """Scan the bundled tasks directory and group task IDs by their prefix."""
    groups: dict[str, list[str]] = {}
    if not _TASKS_DIR.is_dir():
        return groups
    for entry in os.scandir(_TASKS_DIR):
        if not entry.name.endswith(_TASK_FILE_EXT):
            continue
        task_id = entry.name[: -len(_TASK_FILE_EXT)]
        m = _PREFIX_RE.match(task_id)
        if m:
            groups.setdefault(m.group(1), []).append(task_id)
    return groups


def iter_task_list_lines() -> Iterable[str]:
    """Yield localized lines listing available task IDs grouped by topic."""
    groups = _discover_task_ids()

    yield t("help.tasks_title")
    yield ""

    for prefix in _TASK_GROUP_PREFIXES:
        task_ids = groups.get(prefix)
        if not task_ids:
            continue
        task_ids.sort(key=_natural_sort_key)
        if len(task_ids) > 2:
            id_list = f"{task_ids[0]}, ..., {task_ids[-1]}"
        else:
            id_list = ", ".join(task_ids)
        yield t(f"help.task_group.{prefix}")
        yield id_list
        yield ""
