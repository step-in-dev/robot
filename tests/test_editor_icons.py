"""Tests for environment editor toolbar icon assets."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

import tkinter as tk

from robot.editor_icons import (
    ACTION_ICON_STEMS,
    TOOL_ICON_STEMS,
    display_icon_size,
    editor_icons_dir,
    icon_png_path,
    icon_subsample_factor,
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
    def test_icon_subsample_factor_follows_display_dpi(self) -> None:
        """Subsample follows Tk display DPI on any platform (mocked winfo_fpixels)."""
        root = tk.Tk()
        root.withdraw()
        try:
            with mock.patch.object(
                root, "winfo_fpixels", side_effect=lambda _unit: 96.0
            ):
                self.assertEqual(icon_subsample_factor(root), 2)
                self.assertEqual(display_icon_size(root), 24)
            with mock.patch.object(
                root, "winfo_fpixels", side_effect=lambda _unit: 144.0
            ):
                self.assertEqual(icon_subsample_factor(root), 1)
                self.assertEqual(display_icon_size(root), 48)
        finally:
            root.destroy()

    @unittest.skipUnless(os.environ.get("DISPLAY"), "requires a display")
    def test_load_editor_icon_images_subsampled_size(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            images = load_editor_icon_images(root)
            expected_count = len(TOOL_ICON_STEMS) + len(ACTION_ICON_STEMS)
            self.assertEqual(len(images), expected_count)
            expected_size = display_icon_size(root)
            for image in images.values():
                self.assertEqual(image.width(), expected_size)
                self.assertEqual(image.height(), expected_size)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
