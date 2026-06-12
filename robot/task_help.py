"""Localized task catalog text for the help dialog."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .i18n import t
from .task_catalog import KNOWN_TASK_GROUP_PREFIXES, TaskCatalog


def iter_task_list_lines() -> Iterable[str]:
    """Yield localized lines listing available task IDs grouped by topic."""
    bundled_tasks = Path(__file__).resolve().parent / "tasks"
    catalog = TaskCatalog.discover(bundled_tasks)

    yield t("help.tasks_title")
    yield ""

    for prefix in KNOWN_TASK_GROUP_PREFIXES:
        task_ids = catalog.task_ids_for(prefix)
        if not task_ids:
            continue
        if len(task_ids) > 2:
            id_list = f"{task_ids[0]}, ..., {task_ids[-1]}"
        else:
            id_list = ", ".join(task_ids)
        yield t(f"help.task_group.{prefix}")
        yield id_list
        yield ""
