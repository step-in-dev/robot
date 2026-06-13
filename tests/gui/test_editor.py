"""GUI tests for the environment editor window."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import tkinter as tk

from robot.editor_env import EnvEditTool
from robot.gui_editor_constraints import (
    _ConstraintsDialogState,
    prompt_edit_constraints,
)
from robot.i18n import t
from robot._version import __version__
from robot.task_serializer import (
    EditorDocument,
    TaskSaveError,
    bundled_tasks_dir,
    create_default_env_dto,
    create_empty_document,
)

from ._editor_harness import (
    EditorWindowHarness,
    assert_open_document_matches,
    close_editor_for_teardown,
    make_editor_window,
    open_and_assert_painted_task,
    open_task_via_menu,
    write_task_env_file,
)
from ._helpers import (
    GuiTestCase,
    dialog_test_root,
    emit_keypad_enter,
    emit_return,
    requires_tk_display,
    withdrawn_root,
)


def _find_first_entry_widget(parent: tk.Misc) -> tk.Entry | None:
    for child in parent.winfo_children():
        if isinstance(child, tk.Entry):
            return child
        nested = _find_first_entry_widget(child)
        if nested is not None:
            return nested
    return None


def _invoke_first_button(parent: tk.Misc) -> bool:
    for child in parent.winfo_children():
        if isinstance(child, tk.Button):
            child.invoke()
            return True
        if _invoke_first_button(child):
            return True
    return False


def _wait_window_then_click_ok(
    dialog: tk.Toplevel,
    original_wait_window,
) -> None:
    if _invoke_first_button(dialog):
        return
    original_wait_window(dialog)


@requires_tk_display
class EditorWindowTest(GuiTestCase):  # pylint: disable=too-many-public-methods
    def test_undo_redo_restores_previous_state(self) -> None:
        window = make_editor_window()
        try:
            undo_state, redo_state = window.undo_redo_states()
            self.assertEqual(undo_state, tk.DISABLED)
            self.assertEqual(redo_state, tk.DISABLED)
            original = deepcopy(window.document.env_dtos[0])
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.document.env_dtos[0], original)
            window.redo()
            self.assertIn({"r": 2, "c": 2}, window.document.env_dtos[0]["paintedCells"])
        finally:
            close_editor_for_teardown(window)

    def test_env_action_buttons_disabled_for_single_environment(self) -> None:
        window = make_editor_window()
        try:
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.NORMAL)
            self.assertEqual(remove_state, tk.DISABLED)
        finally:
            close_editor_for_teardown(window)

    def test_env_action_buttons_enabled_for_multiple_environments(self) -> None:
        window = make_editor_window()
        try:
            window.add_environment_via_button()
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.NORMAL)
            self.assertEqual(remove_state, tk.NORMAL)
        finally:
            close_editor_for_teardown(window)

    def test_add_env_button_disabled_at_max_count(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto() for _ in range(7)]
        )
        window = EditorWindowHarness(document)
        try:
            add_state, remove_state = window.env_action_button_states()
            self.assertEqual(add_state, tk.DISABLED)
            self.assertEqual(remove_state, tk.NORMAL)
        finally:
            close_editor_for_teardown(window)

    def test_open_file_loads_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(
                Path(temp_dir),
                painted_cells=[{"r": 0, "c": 0}],
                todo_text="Paint",
            )
            window = make_editor_window()
            try:
                open_and_assert_painted_task(
                    self,
                    window,
                    path,
                    painted_cells=[{"r": 0, "c": 0}],
                )
            finally:
                close_editor_for_teardown(window)

    def test_new_via_menu_resets_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(
                Path(temp_dir),
                painted_cells=[{"r": 0, "c": 0}],
                todo_text="Paint",
            )
            window = make_editor_window()
            try:
                open_task_via_menu(window, path)
                self.assertEqual(window.document.file_path, path)

                window.new_via_menu()
                window.root.update()

                expected = create_empty_document()
                self.assertIsNone(window.document.file_path)
                self.assertEqual(window.document.env_dtos, expected.env_dtos)
                self.assertEqual(window.document.todo_text, expected.todo_text)
                self.assertEqual(
                    window.root.title(),
                    t("editor.window.title_new", version=__version__),
                )
            finally:
                close_editor_for_teardown(window)

    def test_save_as_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "new.env"
            window = make_editor_window()
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
                close_editor_for_teardown(window)

    def test_save_as_confirms_bundled_overwrite(self) -> None:
        window = make_editor_window()
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
            close_editor_for_teardown(window)

    def test_save_failure_shows_error_dialog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = make_editor_window()
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
                close_editor_for_teardown(window)

    def test_save_commands_are_noops_after_close(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = make_editor_window()
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
                close_editor_for_teardown(window)

    def test_layout_section_order_without_todo(self) -> None:
        window = make_editor_window()
        try:
            positions = window.layout_section_y_positions()
            self.assertFalse(window.todo_section_is_mapped())
            self.assertLess(positions["toolbar"], positions["tabs"])
            self.assertLess(positions["tabs"], positions["canvas"])
        finally:
            close_editor_for_teardown(window)

    def test_layout_section_order_with_todo(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = EditorWindowHarness(document)
        try:
            positions = window.layout_section_y_positions()
            self.assertTrue(window.todo_section_is_mapped())
            self.assertLess(positions["toolbar"], positions["todo"])
            self.assertLess(positions["todo"], positions["tabs"])
            self.assertLess(positions["tabs"], positions["canvas"])
        finally:
            close_editor_for_teardown(window)

    def test_toolbar_spinbox_hosts_are_visible(self) -> None:
        window = make_editor_window()
        try:
            widths = window.toolbar_spinbox_host_widths()
            self.assertGreater(widths["height_spin"], 0)
            self.assertGreater(widths["width_spin"], 0)
            self.assertEqual(widths["pollution_mapped"], 1)
            self.assertGreater(widths["pollution_spin"], 0)
        finally:
            close_editor_for_teardown(window)

    def test_toolbar_size_labels_are_vertically_centered(self) -> None:
        window = make_editor_window()
        try:
            offsets = window.size_label_vertical_offsets()
            self.assertLessEqual(abs(offsets["rows_label"] - offsets["height_spin"]), 1)
            self.assertLessEqual(abs(offsets["cols_label"] - offsets["width_spin"]), 1)
        finally:
            close_editor_for_teardown(window)

    def test_toolbar_spinbox_height_matches_icon_button(self) -> None:
        window = make_editor_window()
        try:
            heights = window.toolbar_spinbox_heights()
            icon_height = heights["icon"]
            for key in ("height_spin", "width_spin", "pollution_spin", "print_spin"):
                with self.subTest(spinner=key):
                    self.assertEqual(heights[key], icon_height)
        finally:
            close_editor_for_teardown(window)

    def test_toolbar_value_spinner_top_aligns_with_tool_button(self) -> None:
        window = make_editor_window()
        try:
            offsets = window.toolbar_value_spinner_top_offsets()
            for tool in (EnvEditTool.POLLUTION, EnvEditTool.NUMBER):
                with self.subTest(tool=tool.value):
                    button_y = offsets[f"{tool.value}_button"]
                    spin_y = offsets[f"{tool.value}_spin"]
                    self.assertEqual(spin_y, button_y)
        finally:
            close_editor_for_teardown(window)

    def test_value_spinners_appear_inline_after_tool_buttons(self) -> None:
        window = make_editor_window()
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
            close_editor_for_teardown(window)

    def test_todo_label_widget_stable_after_undo(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = EditorWindowHarness(document)
        try:
            label_id = window.todo_label_id()
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.todo_label_id(), label_id)
        finally:
            close_editor_for_teardown(window)

    def test_env_tab_buttons_stable_after_undo(self) -> None:
        window = make_editor_window()
        try:
            tab_ids = window.tab_button_ids()
            window.paint_cell(2, 2)
            window.undo()
            self.assertEqual(window.tab_button_ids(), tab_ids)
        finally:
            close_editor_for_teardown(window)

    def test_value_spinner_stable_after_resize(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = EditorWindowHarness(document)
        try:
            window.select_tool(EnvEditTool.POLLUTION)
            host_id = window.pollution_spin_host_id()
            window.resize_field(8, 5)
            self.assertEqual(window.pollution_spin_host_id(), host_id)
            self.assertTrue(window.value_spinner_is_mapped(EnvEditTool.POLLUTION))
        finally:
            close_editor_for_teardown(window)

    def test_out_of_range_field_size_rolls_back_without_error_dialog(self) -> None:
        window = make_editor_window()
        try:
            original_width = window.document.env_dtos[0]["width"]
            original_height = window.document.env_dtos[0]["height"]
            window.set_field_size_spinboxes(99, original_height)
            with patch("robot.gui_editor.messagebox.showerror") as showerror:
                window.commit_field_size()
            showerror.assert_not_called()
            self.assertEqual(window.field_size_spinbox_values(), (original_width, original_height))
            self.assertEqual(window.document.env_dtos[0]["width"], original_width)
            self.assertEqual(window.document.env_dtos[0]["height"], original_height)
        finally:
            close_editor_for_teardown(window)

    def test_out_of_range_pollution_value_rolls_back(self) -> None:
        window = make_editor_window()
        try:
            window.select_tool(EnvEditTool.POLLUTION)
            window.set_pollution_spinbox_value(5)
            window.commit_pollution_value()
            with patch("robot.gui_editor.messagebox.showerror") as showerror:
                window.set_pollution_spinbox_value(500)
                window.commit_pollution_value()
            showerror.assert_not_called()
            self.assertEqual(window.pollution_spinbox_value(), 5)
        finally:
            close_editor_for_teardown(window)

    def test_out_of_range_print_value_rolls_back(self) -> None:
        window = make_editor_window()
        try:
            window.select_tool(EnvEditTool.NUMBER)
            window.set_print_spinbox_value(-7)
            window.commit_print_value()
            with patch("robot.gui_editor.messagebox.showerror") as showerror:
                window.set_print_spinbox_value(500)
                window.commit_print_value()
            showerror.assert_not_called()
            self.assertEqual(window.print_spinbox_value(), -7)
        finally:
            close_editor_for_teardown(window)

    def test_todo_wraplength_updates_on_resize(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Paint the cell"},
        )
        window = EditorWindowHarness(document)
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
            close_editor_for_teardown(window)

    def test_constraints_button_follows_todo_button(self) -> None:
        window = make_editor_window()
        try:
            following = window.toolbar_slaves_after_todo()
            self.assertEqual(following[0], window.constraints_button())
        finally:
            close_editor_for_teardown(window)

    def test_edit_todo_text_preserves_plain_string_shape(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text="Old condition",
        )
        window = EditorWindowHarness(document)
        try:
            window.edit_todo_text("New condition")
            self.assertEqual(window.document.todo_text, "New condition")
            self.assertIsInstance(window.document.todo_text, str)
        finally:
            close_editor_for_teardown(window)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False)
    def test_edit_todo_text_updates_current_ui_locale(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Old", "ru": "Старое"},
        )
        window = EditorWindowHarness(document)
        try:
            window.edit_todo_text("Новое")
            self.assertEqual(window.document.todo_text["ru"], "Новое")
            self.assertEqual(window.document.todo_text["en"], "Old")
        finally:
            close_editor_for_teardown(window)

    @patch.dict("os.environ", {"ROBOT_LANGUAGE": "de"}, clear=False)
    def test_edit_todo_text_updates_fallback_locale_only(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text={"en": "Old English", "ru": "Старое"},
        )
        window = EditorWindowHarness(document)
        try:
            window.edit_todo_text("New English")
            self.assertEqual(window.document.todo_text["en"], "New English")
            self.assertEqual(window.document.todo_text["ru"], "Старое")
            self.assertNotIn("de", window.document.todo_text)
        finally:
            close_editor_for_teardown(window)

    def test_edit_constraints_updates_preserved_fields(self) -> None:
        window = make_editor_window()
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
            close_editor_for_teardown(window)

    def test_edit_constraints_cancel_leaves_document_unchanged(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            preserved_fields={"operatorsLimit": 3},
        )
        window = EditorWindowHarness(document)
        try:
            window.cancel_edit_constraints()
            self.assertEqual(window.document.preserved_fields["operatorsLimit"], 3)
            undo_state, redo_state = window.undo_redo_states()
            self.assertEqual(undo_state, tk.DISABLED)
            self.assertEqual(redo_state, tk.DISABLED)
        finally:
            close_editor_for_teardown(window)

    def test_undo_redo_restores_constraint_fields(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            preserved_fields={"operatorsLimit": 3, "requiredKeywords": "for"},
        )
        window = EditorWindowHarness(document)
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
            close_editor_for_teardown(window)

    def test_constraints_dialog_shows_error_on_invalid_input(self) -> None:
        state = _ConstraintsDialogState()
        with withdrawn_root() as root:
            original_wait_window = tk.Toplevel.wait_window

            def wait_then_click_ok(dialog: tk.Toplevel) -> None:
                _wait_window_then_click_ok(dialog, original_wait_window)

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

    def test_constraints_dialog_return_commits_valid_input(self) -> None:
        state = _ConstraintsDialogState()
        with withdrawn_root() as root:
            original_wait_window = tk.Toplevel.wait_window

            def wait_then_press_return(dialog_self: tk.Toplevel) -> None:
                entry = _find_first_entry_widget(dialog_self)
                if entry is None:
                    original_wait_window(dialog_self)
                    return
                entry.focus_set()
                dialog_self.update_idletasks()
                emit_return(entry, dialog_self)

            with patch.object(tk.Toplevel, "wait_window", wait_then_press_return):
                result = prompt_edit_constraints(
                    root,
                    {"operatorsLimit": 5},
                    state,
                )
            self.assertIsNotNone(result)
            self.assertEqual(result.operators_limit, "5")

    def test_constraints_dialog_kp_enter_commits_valid_input(self) -> None:
        state = _ConstraintsDialogState()
        with dialog_test_root() as root:
            original_wait_window = tk.Toplevel.wait_window

            def wait_then_press_kp_enter(dialog_self: tk.Toplevel) -> None:
                entry = _find_first_entry_widget(dialog_self)
                if entry is None:
                    original_wait_window(dialog_self)
                    return
                entry.focus_set()
                dialog_self.update_idletasks()
                emit_keypad_enter(entry, dialog_self)

            with patch.object(tk.Toplevel, "wait_window", wait_then_press_kp_enter):
                result = prompt_edit_constraints(
                    root,
                    {"operatorsLimit": 5},
                    state,
                )
            self.assertIsNotNone(result)
            self.assertEqual(result.operators_limit, "5")


@requires_tk_display
class EditorUnsavedChangesTest(GuiTestCase):
    def test_new_without_changes_skips_unsaved_prompt(self) -> None:
        window = make_editor_window()
        try:
            with patch("robot.gui_editor_file.messagebox.askyesnocancel") as prompt:
                window.new_via_menu()
            prompt.assert_not_called()
        finally:
            close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_cancel_keeps_document(self) -> None:
        window = make_editor_window()
        try:
            window.paint_cell(2, 2)
            original = deepcopy(window.document.env_dtos[0])
            with patch(
                "robot.gui_editor_file.messagebox.askyesnocancel",
                return_value=None,
            ) as prompt:
                window.new_via_menu()
            prompt.assert_called_once()
            self.assertEqual(window.document.env_dtos[0], original)
        finally:
            close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_discard_resets_document(self) -> None:
        window = make_editor_window()
        try:
            window.paint_cell(2, 2)
            with patch(
                "robot.gui_editor_file.messagebox.askyesnocancel",
                return_value=False,
            ):
                window.new_via_menu()
            expected = create_empty_document()
            self.assertEqual(window.document.env_dtos, expected.env_dtos)
        finally:
            close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_save_then_save_as(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "saved.env"
            window = make_editor_window()
            try:
                window.paint_cell(2, 2)
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ):
                    window.new_via_menu()
                self.assertTrue(save_path.exists())
                expected = create_empty_document()
                self.assertEqual(window.document.env_dtos, expected.env_dtos)
            finally:
                close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_save_cancelled_keeps_document(self) -> None:
        window = make_editor_window()
        try:
            window.paint_cell(2, 2)
            original = deepcopy(window.document.env_dtos[0])
            with patch(
                "robot.gui_editor_file.messagebox.askyesnocancel",
                return_value=True,
            ), patch(
                "robot.gui_editor_file.filedialog.asksaveasfilename",
                return_value="",
            ):
                window.new_via_menu()
            self.assertEqual(window.document.env_dtos[0], original)
        finally:
            close_editor_for_teardown(window)

    def test_open_with_unsaved_changes_cancel_keeps_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(Path(temp_dir))
            window = make_editor_window()
            try:
                window.paint_cell(2, 2)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=None,
                ) as prompt, patch(
                    "robot.gui_editor_file.filedialog.askopenfilename",
                    return_value=str(path),
                ) as askopen:
                    window.open_via_menu()
                prompt.assert_called_once()
                askopen.assert_not_called()
                self.assertEqual(window.document.env_dtos[0], original)
            finally:
                close_editor_for_teardown(window)

    def test_open_with_unsaved_changes_discard_loads_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(
                Path(temp_dir),
                painted_cells=[{"r": 0, "c": 0}],
            )
            window = make_editor_window()
            try:
                window.paint_cell(2, 2)
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=False,
                ):
                    open_task_via_menu(window, path)
                assert_open_document_matches(
                    self,
                    window,
                    path,
                    painted_cells=[{"r": 0, "c": 0}],
                )
            finally:
                close_editor_for_teardown(window)

    def test_close_with_unsaved_changes_cancel_stays_open(self) -> None:
        window = make_editor_window()
        try:
            window.paint_cell(2, 2)
            with patch(
                "robot.gui_editor_file.messagebox.askyesnocancel",
                return_value=None,
            ) as prompt:
                window.close()
            prompt.assert_called_once()
            self.assertFalse(window.is_closed)
        finally:
            close_editor_for_teardown(window)

    def test_close_with_unsaved_changes_discard_closes(self) -> None:
        window = make_editor_window()
        try:
            window.paint_cell(2, 2)
            with patch(
                "robot.gui_editor_file.messagebox.askyesnocancel",
                return_value=False,
            ):
                window.close()
            self.assertTrue(window.is_closed)
        finally:
            close_editor_for_teardown(window)

    def test_dirty_state_tracks_edits_and_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "saved.env"
            window = make_editor_window()
            try:
                self.assertFalse(window.is_document_dirty())
                window.paint_cell(2, 2)
                self.assertTrue(window.is_document_dirty())
                with patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ):
                    window.save_as_via_menu()
                self.assertFalse(window.is_document_dirty())
            finally:
                close_editor_for_teardown(window)

    def test_env_tab_switch_does_not_mark_document_dirty(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto(), create_default_env_dto()]
        )
        window = EditorWindowHarness(document)
        try:
            self.assertFalse(window.is_document_dirty())
            window.select_env_tab(1)
            self.assertFalse(window.is_document_dirty())
            window.select_env_tab(0)
            self.assertFalse(window.is_document_dirty())
        finally:
            close_editor_for_teardown(window)

    def test_undo_back_to_saved_state_clears_dirty(self) -> None:
        window = make_editor_window()
        try:
            self.assertFalse(window.is_document_dirty())
            window.paint_cell(2, 2)
            self.assertTrue(window.is_document_dirty())
            window.undo()
            self.assertFalse(window.is_document_dirty())
        finally:
            close_editor_for_teardown(window)

    def test_open_with_unsaved_changes_save_then_loads_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "saved.env"
            open_path = write_task_env_file(
                Path(temp_dir),
                filename="other.env",
                painted_cells=[{"r": 0, "c": 0}],
            )
            window = make_editor_window()
            try:
                window.paint_cell(2, 2)
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ) as asksave, patch(
                    "robot.gui_editor_file.filedialog.askopenfilename",
                    return_value=str(open_path),
                ) as askopen:
                    window.open_via_menu()
                asksave.assert_called_once()
                askopen.assert_called_once()
                self.assertEqual(window.document.file_path, open_path)
                self.assertEqual(
                    window.document.env_dtos[0]["paintedCells"],
                    [{"r": 0, "c": 0}],
                )
            finally:
                close_editor_for_teardown(window)

    def test_close_with_unsaved_changes_save_then_closes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "saved.env"
            window = make_editor_window()
            try:
                window.paint_cell(2, 2)
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
                    return_value=str(save_path),
                ):
                    window.close()
                self.assertTrue(save_path.exists())
                self.assertTrue(window.is_closed)
            finally:
                if not window.is_closed:
                    close_editor_for_teardown(window)

    def test_dirty_state_tracks_todo_edits(self) -> None:
        document = EditorDocument(
            env_dtos=[create_default_env_dto()],
            todo_text="Old condition",
        )
        window = EditorWindowHarness(document)
        try:
            self.assertFalse(window.is_document_dirty())
            window.edit_todo_text("New condition")
            self.assertTrue(window.is_document_dirty())
        finally:
            close_editor_for_teardown(window)

    def test_dirty_state_tracks_constraint_edits(self) -> None:
        window = make_editor_window()
        try:
            self.assertFalse(window.is_document_dirty())
            window.edit_constraints(operators_limit="5")
            self.assertTrue(window.is_document_dirty())
        finally:
            close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_saves_existing_path_before_reset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(Path(temp_dir))
            window = make_editor_window()
            try:
                open_task_via_menu(window, path)
                window.paint_cell(1, 1)
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.save_task_file",
                ) as save_mock, patch(
                    "robot.gui_editor_file.filedialog.asksaveasfilename",
                ) as asksaveas:
                    window.new_via_menu()
                save_mock.assert_called_once()
                self.assertEqual(save_mock.call_args[0][0], path)
                saved_document = save_mock.call_args[0][1]
                self.assertIn(
                    {"r": 1, "c": 1},
                    saved_document.env_dtos[0]["paintedCells"],
                )
                asksaveas.assert_not_called()
                expected = create_empty_document()
                self.assertEqual(window.document.env_dtos, expected.env_dtos)
            finally:
                close_editor_for_teardown(window)

    def test_new_with_unsaved_changes_save_failure_keeps_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(Path(temp_dir))
            window = make_editor_window()
            try:
                open_task_via_menu(window, path)
                window.paint_cell(1, 1)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.save_task_file",
                    side_effect=TaskSaveError("cannot save"),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror",
                ) as showerror:
                    window.new_via_menu()
                showerror.assert_called_once()
                self.assertEqual(window.document.env_dtos[0], original)
                self.assertEqual(window.document.file_path, path)
            finally:
                close_editor_for_teardown(window)

    def test_open_with_unsaved_changes_save_failure_keeps_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            current_path = write_task_env_file(
                Path(temp_dir),
                filename="current.env",
            )
            other_path = write_task_env_file(
                Path(temp_dir),
                filename="other.env",
                painted_cells=[{"r": 0, "c": 0}],
            )
            window = make_editor_window()
            try:
                open_task_via_menu(window, current_path)
                window.paint_cell(1, 1)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.save_task_file",
                    side_effect=TaskSaveError("cannot save"),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror",
                ) as showerror, patch(
                    "robot.gui_editor_file.filedialog.askopenfilename",
                    return_value=str(other_path),
                ) as askopen:
                    window.open_via_menu()
                showerror.assert_called_once()
                askopen.assert_not_called()
                self.assertEqual(window.document.env_dtos[0], original)
                self.assertEqual(window.document.file_path, current_path)
            finally:
                close_editor_for_teardown(window)

    def test_close_with_unsaved_changes_save_failure_stays_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_task_env_file(Path(temp_dir))
            window = make_editor_window()
            try:
                open_task_via_menu(window, path)
                window.paint_cell(1, 1)
                original = deepcopy(window.document.env_dtos[0])
                with patch(
                    "robot.gui_editor_file.messagebox.askyesnocancel",
                    return_value=True,
                ), patch(
                    "robot.gui_editor_file.save_task_file",
                    side_effect=TaskSaveError("cannot save"),
                ), patch(
                    "robot.gui_editor_file.messagebox.showerror",
                ) as showerror:
                    window.close()
                showerror.assert_called_once()
                self.assertFalse(window.is_closed)
                self.assertEqual(window.document.env_dtos[0], original)
                self.assertEqual(window.document.file_path, path)
            finally:
                close_editor_for_teardown(window)


if __name__ == "__main__":
    unittest.main()
