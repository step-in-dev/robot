"""Tests for RobotWindow viewer mode (teacher task browser)."""

import tempfile
import unittest
from pathlib import Path

import tkinter as tk

from robot.gui import RobotWindow, RobotWindowOptions
from robot.i18n import t
from robot.loader import load_task_definition
from robot.task_catalog import TaskCatalog
from tests.loader_runtime._helpers import patched_tasks_dir, write_minimal_task_env

from ._helpers import requires_tk_display


def _make_viewer_window() -> RobotWindow:
    """Build a viewer window; caller must keep ``patched_tasks_dir`` active."""
    catalog = TaskCatalog.discover()
    first_id = catalog.first_task_id(catalog.themes[0])
    assert first_id is not None
    task_def = load_task_definition(first_id)
    return RobotWindow(
        first_id,
        task_def,
        None,
        RobotWindowOptions(viewer_catalog=catalog),
    )


@requires_tk_display
class RobotWindowViewerTest(unittest.TestCase):
    def test_viewer_disables_run_and_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    self.assertEqual(window.action_button.cget("state"), tk.DISABLED)
                    self.assertEqual(window.step_button.cget("state"), tk.DISABLED)
                finally:
                    window.close()

    def test_viewer_theme_switch_loads_first_task_in_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            write_minimal_task_env(base / "fun1.env", "fun1")
            write_minimal_task_env(base / "fun2.env", "fun2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    window._viewer_theme_var.set("fun")
                    window._on_viewer_theme_selected()
                    window.root.update()
                    self.assertEqual(window.task_id, "fun1")
                    self.assertEqual(window._viewer_number_var.get(), "1")
                    self.assertEqual(
                        window._viewer_task_count_label.cget("text"),
                        t("viewer.theme_task_count", count=2),
                    )
                finally:
                    window.close()

    def test_viewer_invalid_number_restores_last_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    window._viewer_show_task("intro2")
                    window.root.update()
                    window._viewer_number_var.set("999")
                    window._on_viewer_number_commit()
                    window.root.update()
                    self.assertEqual(window.task_id, "intro2")
                    self.assertEqual(window._viewer_number_var.get(), "2")
                finally:
                    window.close()

    def test_viewer_kp_enter_commits_task_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    assert window.viewer_toolbar is not None
                    entry = next(
                        w
                        for w in window.viewer_toolbar.winfo_children()
                        if w.winfo_class() == "Entry"
                    )
                    entry.focus_set()
                    window._viewer_number_var.set("2")
                    entry.event_generate("<KP_Enter>", when="tail")
                    window.root.update()
                    self.assertEqual(window.task_id, "intro2")
                    self.assertEqual(window._viewer_number_var.get(), "2")
                finally:
                    window.close()

    def test_viewer_number_commit_spaced_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "урок 1.env", "урок 1")
            write_minimal_task_env(base / "урок 2.env", "урок 2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    window._viewer_theme_var.set("урок ")
                    window._viewer_number_var.set("2")
                    window._on_viewer_number_commit()
                    window.root.update()
                    self.assertEqual(window.task_id, "урок 2")
                    self.assertEqual(window._viewer_number_var.get(), "2")
                finally:
                    window.close()

    def test_viewer_next_and_previous(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    window._viewer_show_relative(1)
                    window.root.update()
                    self.assertEqual(window.task_id, "intro2")
                    window._viewer_show_relative(-1)
                    window.root.update()
                    self.assertEqual(window.task_id, "intro1")
                finally:
                    window.close()

    def test_viewer_nav_buttons_disabled_at_theme_ends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    self.assertEqual(
                        window._viewer_prev_button.cget("state"), tk.DISABLED
                    )
                    self.assertEqual(
                        window._viewer_next_button.cget("state"), tk.NORMAL
                    )
                    window._viewer_show_task("intro2")
                    window.root.update()
                    self.assertEqual(
                        window._viewer_prev_button.cget("state"), tk.NORMAL
                    )
                    self.assertEqual(
                        window._viewer_next_button.cget("state"), tk.DISABLED
                    )
                finally:
                    window.close()

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    self.assertEqual(
                        window._viewer_prev_button.cget("state"), tk.DISABLED
                    )
                    self.assertEqual(
                        window._viewer_next_button.cget("state"), tk.DISABLED
                    )
                finally:
                    window.close()

    def test_apply_task_payload_keeps_root_and_non_resizable(self) -> None:
        """Task switches must not recreate the Tk wrapper HWND (Windows taskbar)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            write_minimal_task_env(base / "intro1.env", "intro1")
            write_minimal_task_env(base / "intro2.env", "intro2")
            with patched_tasks_dir(temp_dir):
                window = _make_viewer_window()
                try:
                    root_id = window.root.winfo_id()
                    self.assertEqual(window.root.wm_resizable(), (0, 0))
                    for task_id in ("intro2", "intro1", "intro2"):
                        task_def = load_task_definition(task_id)
                        window.apply_task_payload(task_id, task_def)
                        window.root.update()
                        self.assertEqual(window.root.winfo_id(), root_id)
                        self.assertEqual(window.root.wm_resizable(), (0, 0))
                finally:
                    window.close()



if __name__ == "__main__":
    unittest.main()
