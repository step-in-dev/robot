"""GUI tests for the environment editor window."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tkinter as tk

from robot.editor_env import EnvEditTool, apply_tool_to_env
from robot.gui_editor import EditorWindow
from robot.model import Cell
from robot.task_serializer import (
    EditorDocument,
    TaskSaveError,
    bundled_tasks_dir,
    create_default_env_dto,
    create_empty_document,
)

from ._helpers import GuiTestCase, requires_tk_display


class _EditorWindowHarness(EditorWindow):
    def undo_redo_states(self) -> tuple[str, str]:
        assert self._chrome.undo_button is not None
        assert self._chrome.redo_button is not None
        return (
            self._chrome.undo_button.cget("state"),
            self._chrome.redo_button.cget("state"),
        )

    def env_action_button_states(self) -> tuple[str, str]:
        assert self._chrome.add_env_button is not None
        assert self._chrome.remove_env_button is not None
        return (
            self._chrome.add_env_button.cget("state"),
            self._chrome.remove_env_button.cget("state"),
        )

    def add_environment_via_button(self) -> None:
        self._add_environment()

    def paint_cell(self, row: int, col: int) -> None:
        index = self.document.selected_env_index
        self._mutate(
            lambda: self.document.env_dtos.__setitem__(
                index,
                apply_tool_to_env(
                    self.document.env_dtos[index],
                    EnvEditTool.PAINTED,
                    Cell(row, col),
                ),
            ),
            full_refresh=False,
        )

    def open_via_menu(self) -> None:
        self._menu_open()

    def save_via_menu(self) -> None:
        self._menu_save()

    def save_as_via_menu(self) -> None:
        self._menu_save_as()

    def select_tool(self, tool: EnvEditTool) -> None:
        self._select_tool(tool)

    def todo_section_is_mapped(self) -> bool:
        assert self._chrome.todo_section is not None
        return self._chrome.todo_section.winfo_ismapped()

    def layout_section_y_positions(self) -> dict[str, int]:
        self.root.update_idletasks()
        chrome = self._chrome
        assert chrome.task_toolbar is not None
        assert chrome.env_tabs_bar is not None
        assert chrome.canvas is not None
        positions = {
            "toolbar": chrome.task_toolbar.winfo_y(),
            "tabs": chrome.env_tabs_bar.winfo_y(),
            "canvas": chrome.canvas.winfo_y(),
        }
        if chrome.todo_section is not None and chrome.todo_section.winfo_ismapped():
            positions["todo"] = chrome.todo_section.winfo_y()
        return positions

    def value_spinner_x_after_tool_button(self, tool: EnvEditTool) -> tuple[int, int]:
        self.root.update_idletasks()
        button = self._chrome.tool_buttons[tool]
        if tool is EnvEditTool.POLLUTION:
            assert self._chrome.pollution_spin is not None
            spinner = self._chrome.pollution_spin
        else:
            assert self._chrome.print_spin is not None
            spinner = self._chrome.print_spin
        return button.winfo_x(), spinner.winfo_x()

    def value_spinner_is_mapped(self, tool: EnvEditTool) -> bool:
        if tool is EnvEditTool.POLLUTION:
            assert self._chrome.pollution_spin is not None
            return self._chrome.pollution_spin.winfo_ismapped()
        assert self._chrome.print_spin is not None
        return self._chrome.print_spin.winfo_ismapped()


def _make_editor_window() -> _EditorWindowHarness:
    return _EditorWindowHarness(create_empty_document())


@requires_tk_display
class EditorWindowTest(GuiTestCase):
    def test_undo_redo_restores_previous_state(self) -> None:
        window = _make_editor_window()
        try:
            undo_state, redo_state = window.undo_redo_states()
            self.assertEqual(undo_state, tk.DISABLED)
            self.assertEqual(redo_state, tk.DISABLED)
            original = json.loads(json.dumps(window.document.env_dtos[0]))
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.document.env_dtos[0], original)
            window.redo()
            self.assertIn({"r": 2, "c": 2}, window.document.env_dtos[0]["paintedCells"])
        finally:
            window.close()

    def test_env_action_buttons_disabled_for_single_environment(self) -> None:
        window = _make_editor_window()
        try:
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.NORMAL)
            self.assertEqual(remove_state, tk.DISABLED)
        finally:
            window.close()

    def test_env_action_buttons_enabled_for_multiple_environments(self) -> None:
        window = _make_editor_window()
        try:
            window.add_environment_via_button()
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.NORMAL)
            self.assertEqual(remove_state, tk.NORMAL)
        finally:
            window.close()

    def test_add_env_button_disabled_at_max_count(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto() for _ in range(7)]
        )
        window = _EditorWindowHarness(document)
        try:
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.DISABLED)
            self.assertEqual(remove_state, tk.NORMAL)
        finally:
            window.close()

    def test_open_file_loads_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "task.env"
            path.write_text(
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
                                "paintedCells": [{"r": 0, "c": 0}],
                            }
                        ],
                        "todoText": "Paint",
                    }
                ),
                encoding="utf-8",
            )
            window = _make_editor_window()
            try:
                with patch(
                    "robot.gui_editor.filedialog.askopenfilename",
                    return_value=str(path),
                ):
                    window.open_via_menu()
                window.root.update()
                self.assertEqual(window.document.file_path, path)
                self.assertEqual(
                    window.document.env_dtos[0]["paintedCells"], [{"r": 0, "c": 0}]
                )
            finally:
                window.close()

    def test_save_as_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "new.env"
            window = _make_editor_window()
            try:
                with patch(
                    "robot.gui_editor.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ):
                    window.save_as_via_menu()
                saved = json.loads(save_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["envDtos"][0]["width"], 5)
                self.assertEqual(window.document.file_path, save_path)
            finally:
                window.close()

    def test_save_as_confirms_bundled_overwrite(self) -> None:
        window = _make_editor_window()
        try:
            bundled_path = bundled_tasks_dir() / "intro1.env"
            with patch(
                "robot.gui_editor.filedialog.asksaveasfilename",
                return_value=str(bundled_path),
            ), patch(
                "robot.gui_editor.messagebox.askyesno",
                return_value=False,
            ) as askyesno, patch(
                "robot.gui_editor.save_task_file"
            ) as save_mock:
                window.save_as_via_menu()
            askyesno.assert_called_once()
            save_mock.assert_not_called()
        finally:
            window.close()

    def test_save_failure_shows_error_dialog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = _make_editor_window()
            try:
                save_path = Path(temp_dir) / "new.env"
                with patch(
                    "robot.gui_editor.save_task_file",
                    side_effect=TaskSaveError("cannot save"),
                ), patch(
                    "robot.gui_editor.messagebox.showerror"
                ) as showerror, patch(
                    "robot.gui_editor.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ):
                    window.save_as_via_menu()
                showerror.assert_called_once()
            finally:
                window.close()

    def test_save_commands_are_noops_after_close(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = _make_editor_window()
            try:
                window.document.file_path = Path(temp_dir) / "existing.env"
                window.close()
                with patch(
                    "robot.gui_editor.filedialog.asksaveasfilename"
                ) as asksaveasfilename, patch(
                    "robot.gui_editor.save_task_file"
                ) as save_mock:
                    window.save_via_menu()
                    window.save_as_via_menu()
                asksaveasfilename.assert_not_called()
                save_mock.assert_not_called()
            finally:
                if not window.is_closed:
                    window.close()

    def test_layout_section_order_without_todo(self) -> None:
        window = _make_editor_window()
        try:
            positions = window.layout_section_y_positions()
            self.assertFalse(window.todo_section_is_mapped())
            self.assertLess(positions["toolbar"], positions["tabs"])
            self.assertLess(positions["tabs"], positions["canvas"])
        finally:
            window.close()

    def test_layout_section_order_with_todo(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = _EditorWindowHarness(document)
        try:
            positions = window.layout_section_y_positions()
            self.assertTrue(window.todo_section_is_mapped())
            self.assertLess(positions["toolbar"], positions["todo"])
            self.assertLess(positions["todo"], positions["tabs"])
            self.assertLess(positions["tabs"], positions["canvas"])
        finally:
            window.close()

    def test_value_spinners_appear_inline_after_tool_buttons(self) -> None:
        window = _make_editor_window()
        try:
            window.select_tool(EnvEditTool.POLLUTION)
            self.assertTrue(window.value_spinner_is_mapped(EnvEditTool.POLLUTION))
            button_x, spinner_x = window.value_spinner_x_after_tool_button(
                EnvEditTool.POLLUTION
            )
            self.assertGreater(spinner_x, button_x)

            window.select_tool(EnvEditTool.NUMBER)
            self.assertTrue(window.value_spinner_is_mapped(EnvEditTool.NUMBER))
            button_x, spinner_x = window.value_spinner_x_after_tool_button(
                EnvEditTool.NUMBER
            )
            self.assertGreater(spinner_x, button_x)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
