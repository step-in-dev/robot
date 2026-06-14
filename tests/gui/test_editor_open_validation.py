"""GUI tests for rejecting invalid task files on editor open."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tests.env_fixtures import oversized_width_env_dto
from tests.gui._editor_harness import (
    close_editor_for_teardown,
    make_editor_window,
    open_task_via_menu,
    write_task_env_file,
)


class EditorOpenValidationTest(unittest.TestCase):
    def test_open_invalid_env_width_shows_error_and_keeps_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            current_path = write_task_env_file(Path(temp_dir), filename="current.env")
            invalid_path = Path(temp_dir) / "invalid.env"
            invalid_path.write_text(
                json.dumps({"envDtos": [oversized_width_env_dto()]}),
                encoding="utf-8",
            )
            window = make_editor_window()
            try:
                open_task_via_menu(window, current_path)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.filedialog.askopenfilename",
                    return_value=str(invalid_path),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror",
                ) as showerror:
                    window.open_via_menu()
                showerror.assert_called_once()
                self.assertEqual(window.document.env_dtos[0], original)
                self.assertEqual(window.document.file_path, current_path)
            finally:
                close_editor_for_teardown(window)

    def test_open_invalid_constraints_shows_error_and_keeps_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            current_path = write_task_env_file(Path(temp_dir), filename="current.env")
            invalid_path = Path(temp_dir) / "invalid_constraints.env"
            invalid_path.write_text(
                json.dumps(
                    {
                        "envDtos": [
                            {
                                "width": 2,
                                "height": 2,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 1,
                                "finalCol": 1,
                            }
                        ],
                        "operatorsLimit": "bad",
                    }
                ),
                encoding="utf-8",
            )
            window = make_editor_window()
            try:
                open_task_via_menu(window, current_path)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.filedialog.askopenfilename",
                    return_value=str(invalid_path),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror",
                ) as showerror:
                    window.open_via_menu()
                showerror.assert_called_once()
                self.assertEqual(window.document.env_dtos[0], original)
                self.assertEqual(window.document.file_path, current_path)
            finally:
                close_editor_for_teardown(window)


if __name__ == "__main__":
    unittest.main()
