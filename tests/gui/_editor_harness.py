"""Shared harness and helpers for environment editor GUI tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

import tkinter as tk

from robot.editor_env import EnvEditTool, apply_tool_to_env
from robot.gui_editor import EditorWindow
from robot.model import Cell
from robot.task_serializer import ConstraintFieldInput, create_empty_document


class EditorWindowHarness(EditorWindow):  # pylint: disable=too-many-public-methods
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

    def new_via_menu(self) -> None:
        self._menu_new()

    def select_env_tab(self, index: int) -> None:
        self._select_env(index)

    def is_document_dirty(self) -> bool:
        return self._is_document_dirty()

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

    def commit_field_size(self) -> None:
        self._on_size_commit()

    def set_field_size_spinboxes(self, width: object, height: object) -> None:
        self._vars.width_var.set(width)
        self._vars.height_var.set(height)

    def field_size_spinbox_values(self) -> tuple[int, int]:
        return self._vars.width_var.get(), self._vars.height_var.get()

    def set_pollution_spinbox_value(self, value: object) -> None:
        self._vars.pollution_value.set(value)

    def commit_pollution_value(self) -> None:
        self._on_pollution_commit()

    def pollution_spinbox_value(self) -> int:
        return self._vars.pollution_value.get()

    def set_print_spinbox_value(self, value: object) -> None:
        self._vars.print_value.set(value)

    def commit_print_value(self) -> None:
        self._on_print_commit()

    def print_spinbox_value(self) -> int:
        return self._vars.print_value.get()

    def todo_label_id(self) -> int:
        assert self._chrome.todo_label is not None
        return self._chrome.todo_label.winfo_id()

    def tab_button_ids(self) -> list[int]:
        return [button.winfo_id() for button in self._chrome.tab_buttons]

    def pollution_spin_host_id(self) -> int:
        assert self._chrome.pollution_spin_host is not None
        return self._chrome.pollution_spin_host.winfo_id()

    def todo_text_width_chars(self) -> int:
        assert self._chrome.todo_label is not None
        return int(self._chrome.todo_label.cget("width"))

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

    def edit_todo_text(self, new_text: str) -> None:
        with patch(
            "robot.gui_editor.prompt_string_dialog",
            return_value=new_text,
        ):
            self._edit_todo_text()

    def toolbar_slaves_after_todo(self) -> list:
        assert self._chrome.task_toolbar is not None
        assert self._chrome.todo_edit_button is not None
        slaves = list(self._chrome.task_toolbar.pack_slaves())
        todo_index = slaves.index(self._chrome.todo_edit_button)
        return slaves[todo_index + 1 :]


def make_editor_window() -> EditorWindowHarness:
    return EditorWindowHarness(create_empty_document())


def close_editor_for_teardown(window: EditorWindowHarness) -> None:
    """Close an editor window in test cleanup, discarding unsaved changes."""
    if window.is_closed:
        return
    with patch(
        "robot.gui_editor_file.messagebox.askyesnocancel",
        return_value=False,
    ):
        window.close()


def write_task_env_file(
    directory: Path,
    *,
    filename: str = "task.env",
    painted_cells: Optional[List[dict]] = None,
    todo_text: Optional[str] = None,
) -> Path:
    env_dto = {
        "width": 2,
        "height": 2,
        "startRow": 0,
        "startCol": 0,
        "finalRow": 1,
        "finalCol": 1,
    }
    if painted_cells is not None:
        env_dto["paintedCells"] = painted_cells
    payload: dict = {"envDtos": [env_dto]}
    if todo_text is not None:
        payload["todoText"] = todo_text
    path = directory / filename
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path


def assert_open_document_matches(
    testcase: unittest.TestCase,
    window: EditorWindowHarness,
    path: Path,
    *,
    painted_cells: List[dict],
) -> None:
    testcase.assertEqual(window.document.file_path, path)
    testcase.assertEqual(window.document.env_dtos[0]["paintedCells"], painted_cells)


def open_task_via_menu(window: EditorWindowHarness, path: Path) -> None:
    with patch(
        "robot.gui_editor_file.filedialog.askopenfilename",
        return_value=str(path),
    ):
        window.open_via_menu()
    window.root.update()


def open_and_assert_painted_task(
    testcase: unittest.TestCase,
    window: EditorWindowHarness,
    path: Path,
    *,
    painted_cells: List[dict],
) -> None:
    open_task_via_menu(window, path)
    assert_open_document_matches(
        testcase,
        window,
        path,
        painted_cells=painted_cells,
    )
