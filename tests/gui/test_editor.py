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
from robot.gui_editor_constraints import (
    _ConstraintsDialogState,
    prompt_edit_constraints,
)
from robot.task_serializer import (
    ConstraintFieldInput,
    EditorDocument,
    TaskSaveError,
    bundled_tasks_dir,
    create_default_env_dto,
    create_empty_document,
)
from robot.model import Cell

from ._helpers import GuiTestCase, requires_tk_display


class _EditorWindowHarness(EditorWindow):  # pylint: disable=too-many-public-methods
    """Test harness exposing editor internals and UI probes."""
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
            assert self._chrome.pollution_spin_host is not None
            spinner = self._chrome.pollution_spin_host
        else:
            assert self._chrome.print_spin_host is not None
            spinner = self._chrome.print_spin_host
        return button.winfo_x(), spinner.winfo_x()

    def value_spinner_is_mapped(self, tool: EnvEditTool) -> bool:
        if tool is EnvEditTool.POLLUTION:
            assert self._chrome.pollution_spin_host is not None
            return self._chrome.pollution_spin_host.winfo_ismapped()
        assert self._chrome.print_spin_host is not None
        return self._chrome.print_spin_host.winfo_ismapped()

    def toolbar_spinbox_heights(self) -> dict[str, int]:
        self.root.update_idletasks()
        icon_button = self._chrome.tool_buttons[EnvEditTool.START]
        heights = {"icon": icon_button.winfo_height()}
        assert self._chrome.height_spin_host is not None
        assert self._chrome.width_spin_host is not None
        heights["height_spin"] = self._chrome.height_spin_host.winfo_height()
        heights["width_spin"] = self._chrome.width_spin_host.winfo_height()

        self.select_tool(EnvEditTool.POLLUTION)
        self.root.update_idletasks()
        assert self._chrome.pollution_spin_host is not None
        heights["pollution_spin"] = self._chrome.pollution_spin_host.winfo_height()

        self.select_tool(EnvEditTool.NUMBER)
        self.root.update_idletasks()
        assert self._chrome.print_spin_host is not None
        heights["print_spin"] = self._chrome.print_spin_host.winfo_height()
        return heights

    def toolbar_value_spinner_top_offsets(self) -> dict[str, int]:
        self.root.update_idletasks()
        offsets: dict[str, int] = {}
        for tool in (EnvEditTool.POLLUTION, EnvEditTool.NUMBER):
            self.select_tool(tool)
            self.root.update_idletasks()
            button = self._chrome.tool_buttons[tool]
            if tool is EnvEditTool.POLLUTION:
                assert self._chrome.pollution_spin_host is not None
                host = self._chrome.pollution_spin_host
            else:
                assert self._chrome.print_spin_host is not None
                host = self._chrome.print_spin_host
            offsets[f"{tool.value}_button"] = button.winfo_y()
            offsets[f"{tool.value}_spin"] = host.winfo_y()
        return offsets

    def toolbar_spinbox_host_widths(self) -> dict[str, int]:
        self.root.update_idletasks()
        assert self._chrome.height_spin_host is not None
        assert self._chrome.width_spin_host is not None
        widths = {
            "height_spin": self._chrome.height_spin_host.winfo_width(),
            "width_spin": self._chrome.width_spin_host.winfo_width(),
        }
        self.select_tool(EnvEditTool.POLLUTION)
        self.root.update_idletasks()
        assert self._chrome.pollution_spin_host is not None
        widths["pollution_spin"] = self._chrome.pollution_spin_host.winfo_width()
        widths["pollution_mapped"] = int(
            self._chrome.pollution_spin_host.winfo_ismapped()
        )
        return widths

    def size_label_vertical_offsets(self) -> dict[str, int]:
        self.root.update_idletasks()
        assert self._chrome.rows_label is not None
        assert self._chrome.height_spin_host is not None
        assert self._chrome.cols_label is not None
        assert self._chrome.width_spin_host is not None

        def center_y(widget: tk.Misc) -> int:
            return widget.winfo_y() + widget.winfo_height() // 2

        return {
            "rows_label": center_y(self._chrome.rows_label),
            "height_spin": center_y(self._chrome.height_spin_host),
            "cols_label": center_y(self._chrome.cols_label),
            "width_spin": center_y(self._chrome.width_spin_host),
        }

    def resize_field(self, width: int, height: int) -> None:
        self._vars.width_var.set(width)
        self._vars.height_var.set(height)
        self._on_size_commit()

    def todo_label_id(self) -> int:
        assert self._chrome.todo_label is not None
        return self._chrome.todo_label.winfo_id()

    def tab_button_ids(self) -> list[int]:
        return [button.winfo_id() for button in self._chrome.tab_buttons]

    def pollution_spin_host_id(self) -> int:
        assert self._chrome.pollution_spin_host is not None
        return self._chrome.pollution_spin_host.winfo_id()

    def todo_label_wraplength(self) -> int:
        assert self._chrome.todo_label is not None
        return int(self._chrome.todo_label.cget("wraplength"))

    def expected_todo_wraplength(self) -> int:
        return max(self._layout.canvas_width, 320)

    def edit_constraints(self, **values: str) -> None:
        fields = ConstraintFieldInput(**values)
        with patch(
            "robot.gui_editor.prompt_edit_constraints",
            return_value=fields,
        ):
            self._edit_constraints()

    def constraints_button(self) -> tk.Button:
        assert self._chrome.constraints_edit_button is not None
        return self._chrome.constraints_edit_button

    def cancel_edit_constraints(self) -> None:
        with patch(
            "robot.gui_editor.prompt_edit_constraints",
            return_value=None,
        ):
            self._edit_constraints()

    def toolbar_slaves_after_todo(self) -> list:
        assert self._chrome.task_toolbar is not None
        assert self._chrome.todo_edit_button is not None
        slaves = list(self._chrome.task_toolbar.pack_slaves())
        todo_index = slaves.index(self._chrome.todo_edit_button)
        return slaves[todo_index + 1 :]


def _make_editor_window() -> _EditorWindowHarness:
    return _EditorWindowHarness(create_empty_document())


@requires_tk_display
class EditorWindowTest(GuiTestCase):  # pylint: disable=too-many-public-methods
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
                    "robot.gui_editor_file.filedialog.askopenfilename",
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
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
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
                "robot.gui_editor_file.filedialog.asksaveasfilename",
                return_value=str(bundled_path),
            ), patch(
                "robot.gui_editor_file.messagebox.askyesno",
                return_value=False,
            ) as askyesno, patch(
                "robot.gui_editor_file.save_task_file"
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
                    "robot.gui_editor_file.save_task_file",
                    side_effect=TaskSaveError("cannot save"),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror"
                ) as showerror, patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
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
                    "robot.gui_editor_file.filedialog.asksaveasfilename"
                ) as asksaveasfilename, patch(
                    "robot.gui_editor_file.save_task_file"
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

    def test_toolbar_spinbox_hosts_are_visible(self) -> None:
        window = _make_editor_window()
        try:
            widths = window.toolbar_spinbox_host_widths()
            self.assertGreater(widths["height_spin"], 0)
            self.assertGreater(widths["width_spin"], 0)
            self.assertEqual(widths["pollution_mapped"], 1)
            self.assertGreater(widths["pollution_spin"], 0)
        finally:
            window.close()

    def test_toolbar_size_labels_are_vertically_centered(self) -> None:
        window = _make_editor_window()
        try:
            offsets = window.size_label_vertical_offsets()
            self.assertLessEqual(abs(offsets["rows_label"] - offsets["height_spin"]), 1)
            self.assertLessEqual(abs(offsets["cols_label"] - offsets["width_spin"]), 1)
        finally:
            window.close()

    def test_toolbar_spinbox_height_matches_icon_button(self) -> None:
        window = _make_editor_window()
        try:
            heights = window.toolbar_spinbox_heights()
            icon_height = heights["icon"]
            for key in ("height_spin", "width_spin", "pollution_spin", "print_spin"):
                with self.subTest(spinner=key):
                    self.assertEqual(heights[key], icon_height)
        finally:
            window.close()

    def test_toolbar_value_spinner_top_aligns_with_tool_button(self) -> None:
        window = _make_editor_window()
        try:
            offsets = window.toolbar_value_spinner_top_offsets()
            for tool in (EnvEditTool.POLLUTION, EnvEditTool.NUMBER):
                with self.subTest(tool=tool.value):
                    button_y = offsets[f"{tool.value}_button"]
                    spin_y = offsets[f"{tool.value}_spin"]
                    self.assertEqual(spin_y, button_y)
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

    def test_todo_label_widget_stable_after_undo(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = _EditorWindowHarness(document)
        try:
            label_id = window.todo_label_id()
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.todo_label_id(), label_id)
        finally:
            window.close()

    def test_env_tab_buttons_stable_after_undo(self) -> None:
        window = _make_editor_window()
        try:
            tab_ids = window.tab_button_ids()
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.tab_button_ids(), tab_ids)
        finally:
            window.close()

    def test_value_spinner_stable_after_resize(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = _EditorWindowHarness(document)
        try:
            window.select_tool(EnvEditTool.POLLUTION)
            host_id = window.pollution_spin_host_id()
            window.resize_field(8, 5)
            self.assertEqual(window.pollution_spin_host_id(), host_id)
            self.assertTrue(window.value_spinner_is_mapped(EnvEditTool.POLLUTION))
        finally:
            window.close()

    def test_todo_wraplength_updates_on_resize(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = _EditorWindowHarness(document)
        try:
            window.root.update_idletasks()
            self.assertEqual(
                window.todo_label_wraplength(), window.expected_todo_wraplength()
            )
            window.resize_field(12, 12)
            window.root.update_idletasks()
            self.assertEqual(
                window.todo_label_wraplength(), window.expected_todo_wraplength()
            )
        finally:
            window.close()

    def test_constraints_button_follows_todo_button(self) -> None:
        window = _make_editor_window()
        try:
            following = window.toolbar_slaves_after_todo()
            self.assertEqual(following[0], window.constraints_button())
        finally:
            window.close()

    def test_edit_constraints_updates_preserved_fields(self) -> None:
        window = _make_editor_window()
        try:
            window.edit_constraints(
                operators_limit="5",
                custom_function_call_count="2",
                if_limit="1",
                while_limit="0",
                required_keywords="for, def",
                banned_keywords="while",
            )
            preserved = window.document.preserved_fields
            self.assertEqual(preserved["operatorsLimit"], 5)
            self.assertEqual(preserved["customFunctionCallCount"], 2)
            self.assertEqual(preserved["ifLimit"], 1)
            self.assertEqual(preserved["whileLimit"], 0)
            self.assertEqual(preserved["requiredKeywords"], "def, for")
            self.assertEqual(preserved["bannedKeywords"], "while")
        finally:
            window.close()

    def test_edit_constraints_cancel_leaves_document_unchanged(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            preserved_fields={"operatorsLimit": 3},
        )
        window = _EditorWindowHarness(document)
        try:
            window.cancel_edit_constraints()
            self.assertEqual(window.document.preserved_fields["operatorsLimit"], 3)
            undo_state, redo_state = window.undo_redo_states()
            self.assertEqual(undo_state, tk.DISABLED)
            self.assertEqual(redo_state, tk.DISABLED)
        finally:
            window.close()

    def test_undo_redo_restores_constraint_fields(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            preserved_fields={"operatorsLimit": 3, "requiredKeywords": "for"},
        )
        window = _EditorWindowHarness(document)
        try:
            window.edit_constraints(
                operators_limit="7",
                custom_function_call_count="",
                if_limit="",
                while_limit="",
                required_keywords="while",
                banned_keywords="",
            )
            self.assertEqual(window.document.preserved_fields["operatorsLimit"], 7)
            self.assertEqual(
                window.document.preserved_fields["requiredKeywords"], "while"
            )
            window.undo()
            self.assertEqual(window.document.preserved_fields["operatorsLimit"], 3)
            self.assertEqual(
                window.document.preserved_fields["requiredKeywords"], "for"
            )
            window.redo()
            self.assertEqual(window.document.preserved_fields["operatorsLimit"], 7)
            self.assertEqual(
                window.document.preserved_fields["requiredKeywords"], "while"
            )
        finally:
            window.close()

    def test_constraints_dialog_shows_error_on_invalid_input(self) -> None:
        root = tk.Tk()
        root.withdraw()
        state = _ConstraintsDialogState()
        try:
            original_wait_window = tk.Toplevel.wait_window

            def wait_then_click_ok(dialog_self: tk.Toplevel) -> None:
                for frame in dialog_self.winfo_children():
                    for widget in frame.winfo_children():
                        if not isinstance(widget, tk.Frame):
                            continue
                        for button in widget.winfo_children():
                            if isinstance(button, tk.Button):
                                button.invoke()
                                return
                original_wait_window(dialog_self)

            with patch(
                "robot.gui_editor_constraints.parse_constraint_field_input",
                side_effect=ValueError("invalid"),
            ), patch(
                "robot.gui_editor_constraints.messagebox.showerror"
            ) as showerror, patch.object(
                tk.Toplevel, "wait_window", wait_then_click_ok
            ):
                result = prompt_edit_constraints(root, {}, state)
            showerror.assert_called_once()
            self.assertIsNone(result)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
