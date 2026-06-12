#!/usr/bin/env python3
"""Edit Robot task environments (.env files)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# robot imports follow sys.path setup so this script runs without package install.
# pylint: disable=wrong-import-position
from robot.gui_editor import EditorWindow
# pylint: enable=wrong-import-position


def main() -> int:
    """Open the environment editor with a new empty environment."""
    window = EditorWindow()
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
