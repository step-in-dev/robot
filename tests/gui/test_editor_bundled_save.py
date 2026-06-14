"""GUI tests for bundled-category save restrictions in the editor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.task_serializer import bundled_tasks_dir

from ._editor_harness import (
    close_editor_for_teardown,
    make_editor_window,
    save_as_to_path,
)
from ._helpers import GuiTestCase, requires_tk_display


@requires_tk_display
class EditorBundledSaveTest(GuiTestCase):
    def test_save_as_blocks_bundled_category_save(self) -> None:
        window = make_editor_window()
        try:
            bundled_path = bundled_tasks_dir() / "intro1.env"
            with patch(
                "robot.gui_editor_file.messagebox.showerror"
            ) as showerror, patch(
                "robot.gui_editor_file.save_task_file"
            ) as save_mock:
                save_as_to_path(window, bundled_path)
            showerror.assert_called_once()
            save_mock.assert_not_called()
        finally:
            close_editor_for_teardown(window)

    def test_save_as_allows_bundled_category_name_outside_bundled_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "intro1.env"
            window = make_editor_window()
            try:
                with patch(
                    "robot.gui_editor_file.messagebox.showerror"
                ) as showerror:
                    save_as_to_path(window, save_path)
                showerror.assert_not_called()
                self.assertTrue(save_path.is_file())
                self.assertEqual(window.document.file_path, save_path)
            finally:
                close_editor_for_teardown(window)

    def test_save_blocks_bundled_task_in_place(self) -> None:
        window = make_editor_window()
        try:
            bundled_path = bundled_tasks_dir() / "intro1.env"
            window.document.file_path = bundled_path
            with patch(
                "robot.gui_editor_file.messagebox.showerror"
            ) as showerror, patch(
                "robot.gui_editor_file.save_task_file"
            ) as save_mock:
                window.save_via_menu()
            showerror.assert_called_once()
            save_mock.assert_not_called()
        finally:
            close_editor_for_teardown(window)

    def test_save_as_blocks_new_bundled_category_task_name(self) -> None:
        window = make_editor_window()
        try:
            bundled_path = bundled_tasks_dir() / "intro100.env"
            with patch(
                "robot.gui_editor_file.messagebox.showerror"
            ) as showerror, patch(
                "robot.gui_editor_file.save_task_file"
            ) as save_mock:
                save_as_to_path(window, bundled_path)
            showerror.assert_called_once()
            save_mock.assert_not_called()
        finally:
            close_editor_for_teardown(window)

    def test_save_as_allows_custom_theme_in_bundled_dir(self) -> None:
        window = make_editor_window()
        try:
            bundled_path = bundled_tasks_dir() / "myexperiment1.env"
            with patch(
                "robot.gui_editor_file.messagebox.showerror"
            ) as showerror, patch(
                "robot.gui_editor_file.save_task_file"
            ) as save_mock:
                save_as_to_path(window, bundled_path)
            showerror.assert_not_called()
            save_mock.assert_called_once()
        finally:
            close_editor_for_teardown(window)


if __name__ == "__main__":
    unittest.main()
