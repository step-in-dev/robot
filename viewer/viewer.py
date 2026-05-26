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
    window = RobotWindow.from_task_definition(
        task_id=first_task_id,
        task_definition=task_definition,
        run_env=None,
        viewer_catalog=catalog,
    )
    window.run()
    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        print(t("viewer.no_tasks"))
    raise SystemExit(exit_code)
