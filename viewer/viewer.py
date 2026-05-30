#!/usr/bin/env python3
"""Browse Robot task environments (teacher task picker)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# robot imports follow sys.path setup so this script runs without package install.
# pylint: disable=wrong-import-position
from robot.gui import RobotWindow, RobotWindowOptions
from robot.i18n import t
from robot.loader import load_task_definition
from robot.task_catalog import TaskCatalog
# pylint: enable=wrong-import-position


def main() -> int:
    """Open viewer mode with the first task in the first catalog theme."""
    catalog = TaskCatalog.discover()
    first_task_id = (
        catalog.first_task_id(catalog.themes[0]) if catalog.themes else None
    )
    if first_task_id is None:
        return 1

    task_definition = load_task_definition(first_task_id)
    window = RobotWindow(
        first_task_id,
        task_definition,
        None,
        RobotWindowOptions(viewer_catalog=catalog),
    )
    window.run()
    return 0


def _run_as_script() -> None:
    """Entry point when executed as ``python viewer/viewer.py``."""
    exit_code = main()
    if exit_code != 0:
        print(t("viewer.no_tasks"))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    _run_as_script()
