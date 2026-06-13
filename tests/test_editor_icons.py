"""Tests for environment editor toolbar icon assets."""

from __future__ import annotations

import unittest
from pathlib import Path

from robot.editor_icons import (
    ACTION_ICON_STEMS,
    TOOL_ICON_STEMS,
    editor_icons_dir,
    icon_png_path,
)
from robot.editor_env import EnvEditTool


class EditorIconsTest(unittest.TestCase):
    def test_every_tool_has_png(self) -> None:
        for tool in EnvEditTool:
            stem = TOOL_ICON_STEMS[tool]
            path = icon_png_path(stem)
            self.assertTrue(path.is_file(), msg=f"missing {path}")

    def test_every_action_has_png(self) -> None:
        for stem in ACTION_ICON_STEMS.values():
            path = icon_png_path(stem)
            self.assertTrue(path.is_file(), msg=f"missing {path}")

    def test_png_directory_exists(self) -> None:
        png_dir = editor_icons_dir()
        self.assertTrue(png_dir.is_dir())
        self.assertGreater(len(list(png_dir.glob("*.png"))), 0)

    def test_svg_sources_match_png_stems(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        svg_dir = repo_root / "robot" / "assets" / "editor_icons" / "svg"
        svg_stems = {path.stem for path in svg_dir.glob("*.svg")}
        png_stems = {path.stem for path in editor_icons_dir().glob("*.png")}
        self.assertEqual(svg_stems, png_stems)


if __name__ == "__main__":
    unittest.main()
