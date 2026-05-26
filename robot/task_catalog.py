"""Discover and order Robot task files for browsing (viewer, help lists)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .loader import TASKS_DIR_ENV, TASK_FILE_EXTENSION

# Ordered theme ids for bundled tasks; matches help task list order in command_help.
KNOWN_TASK_GROUP_PREFIXES: tuple[str, ...] = (
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

_NUMBER_RE = re.compile(r"(\d+)$")


def resolve_tasks_dir() -> Path:
    """Directory scanned for task files: ``ROBOT_TASKS_DIR`` if set, else bundled tasks."""
    external = os.environ.get(TASKS_DIR_ENV)
    if external:
        path = Path(external)
        if path.is_dir():
            return path
    return Path(__file__).resolve().parent / "tasks"


def theme_from_task_id(task_id: str) -> str | None:
    """Theme string before trailing digits, or ``None`` if stem has no numeric suffix."""
    match = _NUMBER_RE.search(task_id)
    if not match:
        return None
    return task_id[: match.start()]


def natural_sort_key(task_id: str) -> tuple[str, int]:
    """Sort key that orders numbers numerically within the same theme."""
    match = _NUMBER_RE.search(task_id)
    num = int(match.group(1)) if match else 0
    return (task_id[: match.start()] if match else task_id, num)


def discover_task_groups(tasks_dir: Path | None = None) -> dict[str, list[str]]:
    """Scan a tasks directory and group task IDs (stems of ``*.env``) by theme before trailing digits."""
    directory = tasks_dir if tasks_dir is not None else resolve_tasks_dir()
    groups: dict[str, list[str]] = {}
    if not directory.is_dir():
        return groups
    for entry in os.scandir(directory):
        if not entry.name.endswith(TASK_FILE_EXTENSION):
            continue
        task_id = entry.name[: -len(TASK_FILE_EXTENSION)]
        theme = theme_from_task_id(task_id)
        if theme is not None:
            groups.setdefault(theme, []).append(task_id)
    return groups


def ordered_theme_prefixes(groups: dict[str, list[str]]) -> list[str]:
    """Known themes in help order, then unknown themes alphabetically; only non-empty."""
    known = [
        prefix
        for prefix in KNOWN_TASK_GROUP_PREFIXES
        if groups.get(prefix)
    ]
    unknown = sorted(
        prefix
        for prefix in groups
        if prefix not in KNOWN_TASK_GROUP_PREFIXES and groups[prefix]
    )
    return known + unknown


def task_number_from_id(task_id: str) -> int | None:
    """Trailing digits in a task id, e.g. ``intro8`` -> ``8``."""
    match = _NUMBER_RE.search(task_id)
    return int(match.group(1)) if match else None


def task_id_for_theme(prefix: str, number: int) -> str:
    return f"{prefix}{number}"


@dataclass(frozen=True)
class TaskCatalog:
    """Read-only index of available tasks grouped by theme."""

    themes: tuple[str, ...]
    groups: dict[str, tuple[str, ...]]

    @classmethod
    def discover(cls, tasks_dir: Path | None = None) -> TaskCatalog:
        raw = discover_task_groups(tasks_dir)
        sorted_groups = {
            prefix: tuple(sorted(task_ids, key=natural_sort_key))
            for prefix, task_ids in raw.items()
            if task_ids
        }
        themes = tuple(ordered_theme_prefixes(sorted_groups))
        groups = {theme: sorted_groups[theme] for theme in themes}
        return cls(themes=themes, groups=groups)

    def task_ids_for(self, prefix: str) -> tuple[str, ...]:
        return self.groups.get(prefix, ())

    def first_task_id(self, prefix: str) -> str | None:
        ids = self.task_ids_for(prefix)
        return ids[0] if ids else None

    def current_theme_for_task(self, task_id: str) -> str | None:
        theme = theme_from_task_id(task_id)
        if theme is None:
            return None
        if task_id in self.task_ids_for(theme):
            return theme
        return None
