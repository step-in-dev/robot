"""Tests for environment editor toolbar icon assets."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import tkinter as tk

from robot.editor_icons import (
    ACTION_ICON_STEMS,
    TOOL_ICON_STEMS,
    DISPLAY_ICON_SIZE,
    editor_icons_dir,
    icon_png_path,
    load_editor_icon_images,
)
from robot.editor_env import EnvEditTool


class EditorIconsTest(unittest.TestCase):
    def test_every_tool_has_png(self) -> None:
        for tool in EnvEditTool:
            stem = TOOL_ICON_STEMS[tool]
            path = icon_png_path(stem)
            self.assertTrue(path.is_file(), msg=f"missing {path}")
            self.assertIn("png@2x", str(path))

    def test_every_action_has_png(self) -> None:
        for stem in ACTION_ICON_STEMS.values():
            path = icon_png_path(stem)
            self.assertTrue(path.is_file(), msg=f"missing {path}")

    def test_svg_sources_match_png_stems(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        svg_dir = repo_root / "robot" / "assets" / "editor_icons" / "svg"
        svg_stems = {path.stem for path in svg_dir.glob("*.svg")}
        png_stems = {path.stem for path in editor_icons_dir().glob("*.png")}
        self.assertEqual(svg_stems, png_stems)

    @unittest.skipUnless(os.environ.get("DISPLAY"), "requires a display")
    def test_load_editor_icon_images_subsampled_size(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            images = load_editor_icon_images(root)
            expected_count = len(TOOL_ICON_STEMS) + len(ACTION_ICON_STEMS)
            self.assertEqual(len(images), expected_count)
            for image in images.values():
                self.assertEqual(image.width(), DISPLAY_ICON_SIZE)
                self.assertEqual(image.height(), DISPLAY_ICON_SIZE)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
