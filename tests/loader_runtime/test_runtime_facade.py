"""Tests for runtime facade (task, field, imports)."""

from typing import Dict, List

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from robot import runtime
from robot.executor import StudentSolution, run_solution_on_env
from robot.i18n import clear_translation_cache, t
from robot.model import RobotError

from robot.loader import ScriptConstraints

from tests.env_fixtures import cell_1x1, make_env

from ._helpers import LoaderRuntimeTestBase, TaskFileWrite, make_capture_robot_window_cls


class RuntimeFacadeTest(LoaderRuntimeTestBase):
    def test_task_under_global_trace_uses_standard_gui_path(self) -> None:
        """IDE trace must not switch task(); localized todoText resolves before RobotWindow."""
        captured: List[Dict[str, object]] = []
        CaptureRobotWindow = make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "student.py"
            script.write_text("# student\n", encoding="utf-8")
            self.write_task(
                temp_dir,
                TaskFileWrite(
                    task_id="trace_task",
                    env_dtos=[self._minimal_env_dto()],
                    todo_text={"en": "Note", "ru": "Записка"},
                    constraints=ScriptConstraints(
                        operators_limit=42,
                        custom_function_call_count=7,
                        if_limit=3,
                        while_limit=0,
                        required_keywords=("for", "def"),
                        banned_keywords=("while",),
                    ),
                ),
            )

            fake_main = types.ModuleType("fake_main")
            fake_main.__file__ = str(script)

            def ide_global(_frame, _event, _arg):
                return ide_global

            old_trace = sys.gettrace()
            sys.settrace(ide_global)
            try:
                with patch.dict(
                    "os.environ",
                    {"ROBOT_TASKS_DIR": temp_dir, "ROBOT_LANGUAGE": "ru"},
                    clear=False,
                ):
                    with patch.dict(sys.modules, {"__main__": fake_main}):
                        with patch("robot.gui.RobotWindow", CaptureRobotWindow):
                            with self.assertRaises(SystemExit) as ctx:
                                runtime.task("trace_task")
            finally:
                sys.settrace(old_trace)

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(captured), 1)
        call = captured[0]
        task_def = call["task_definition"]
        opts = call["options"]
        self.assertIsNotNone(opts)
        self.assertEqual(call["task_id"], "trace_task")
        self.assertEqual(task_def.todo_text, "Записка")
        self.assertEqual(task_def.operators_limit, 42)
        self.assertEqual(task_def.custom_function_call_count, 7)
        self.assertEqual(task_def.if_limit, 3)
        self.assertEqual(task_def.while_limit, 0)
        self.assertEqual(task_def.required_keywords, ("def", "for"))
        self.assertEqual(task_def.banned_keywords, ("while",))
        self.assertIsNotNone(call["run_env"])
        self.assertTrue(callable(call["run_env"]))
        self.assertEqual(opts.script_path, Path(script).resolve())

    def test_field_wires_robot_window_and_sys_exit(self) -> None:
        captured: List[Dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "student_field.py"
            script.write_text("# student field\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit) as ctx:
                    runtime.field(7, 5)

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(len(captured), 1)
        call = captured[0]
        task_def = call["task_definition"]
        opts = call["options"]
        self.assertIsNotNone(opts)
        self.assertEqual(call["task_id"], "field(7, 5)")
        self.assertEqual(task_def.todo_text, "")
        self.assertIsNone(task_def.operators_limit)
        self.assertIsNone(task_def.custom_function_call_count)
        self.assertIsNone(task_def.if_limit)
        self.assertIsNone(task_def.while_limit)
        self.assertIsNone(task_def.required_keywords)
        self.assertIsNone(task_def.banned_keywords)
        envs = task_def.envs
        self.assertEqual(len(envs), 1)
        env = envs[0]
        self.assertEqual(env.width, 7)
        self.assertEqual(env.height, 5)
        self.assertEqual(env.start_row, 0)
        self.assertEqual(env.start_col, 0)
        self.assertEqual(env.final_row, 4)
        self.assertEqual(env.final_col, 6)
        self.assertEqual(opts.script_path, Path(script).resolve())

    def test_field_defaults_eight_by_six(self) -> None:
        captured: List[Dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "def_field.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field()

        env = captured[0]["task_definition"].envs[0]
        self.assertEqual(env.width, 8)
        self.assertEqual(env.height, 6)

    def test_field_positional_width_only(self) -> None:
        captured: List[Dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "w10.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field(10)

        env = captured[0]["task_definition"].envs[0]
        self.assertEqual(env.width, 10)
        self.assertEqual(env.height, 6)

    def test_field_keyword_height_only(self) -> None:
        captured: List[Dict[str, object]] = []
        Capture = self._make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "h7.py"
            script.write_text("#\n", encoding="utf-8")
            with self._patched_main_as_script(script), patch(
                "robot.gui.RobotWindow", Capture
            ):
                with self.assertRaises(SystemExit):
                    runtime.field(height=7)

        env = captured[0]["task_definition"].envs[0]
        self.assertEqual(env.width, 8)
        self.assertEqual(env.height, 7)

    def test_field_rejects_non_integers(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "bad.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        getattr(runtime, "field")(1.5, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_integers"))

    def test_field_rejects_bool_values(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "bad.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(True, 3)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_integers"))

    def test_field_rejects_width_out_of_range(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badw.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(0, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_width_range"))
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badw2.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(21, 6)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_width_range"))

    def test_field_rejects_height_out_of_range(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badh.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(8, 0)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_height_range"))
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "badh2.py"
                script.write_text("#\n", encoding="utf-8")
                with self._patched_main_as_script(script):
                    with self.assertRaises(RobotError) as ctx:
                        runtime.field(8, 16)
            self.assertEqual(str(ctx.exception), t("runtime.error.field_height_range"))

    def test_field_noop_during_solution_run(self) -> None:
        one = make_env(cell_1x1())
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "sol.py"
            script.write_text(
                "from robot import field\n"
                "field(9, 9)\n",
                encoding="utf-8",
            )
            result = run_solution_on_env(
                StudentSolution(script, "dummy_task"),
                one,
                command_delay_seconds=0.0,
            )
        self.assertEqual(result.status, "success")

    def test_field_validates_before_noop_in_solution_run(self) -> None:
        one = make_env(cell_1x1())
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            clear_translation_cache()
            with tempfile.TemporaryDirectory() as temp_dir:
                script = Path(temp_dir) / "bad_sol.py"
                script.write_text(
                    "from robot import field\n"
                    "field(2.0, 3)\n",
                    encoding="utf-8",
                )
                result = run_solution_on_env(
                    StudentSolution(script, "dummy_task"),
                    one,
                    command_delay_seconds=0.0,
                )
        self.assertEqual(result.status, "error")
        self.assertIn(t("runtime.error.field_integers"), result.message)


if __name__ == "__main__":
    unittest.main()
