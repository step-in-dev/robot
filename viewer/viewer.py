#!/usr/bin/env python3
"""Browse Robot task environments (teacher task picker)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from robot.gui import RobotWindow
from robot.i18n import t
from robot.loader import load_task_definition
from robot.task_catalog import TaskCatalog


def main() -> int:
    catalog = TaskCatalog.discover()
    first_task_id = (
        catalog.first_task_id(catalog.themes[0]) if catalog.themes else None
    )
    if first_task_id is None:
        return 1

    task_definition = load_task_definition(first_task_id)
    window = RobotWindow(
        task_id=first_task_id,
        envs=task_definition.envs,
        run_env=None,
        todo_text=task_definition.todo_text,
        operators_limit=task_definition.operators_limit,
        custom_function_call_count=task_definition.custom_function_call_count,
        if_limit=task_definition.if_limit,
        while_limit=task_definition.while_limit,
        required_keywords=task_definition.required_keywords,
        banned_keywords=task_definition.banned_keywords,
        viewer_catalog=catalog,
    )
    window.run()
    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        print(t("viewer.no_tasks"))
    raise SystemExit(exit_code)
