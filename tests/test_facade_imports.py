"""Compatibility: facade modules re-export canonical symbols."""


import unittest

from robot import executor, gui, gui_layout, gui_theme, results, runtime


class FacadeImportCompatibilityTest(unittest.TestCase):
    def test_runtime_reexports_results_types(self) -> None:
        self.assertIs(runtime.RunResult, results.RunResult)
        self.assertIs(runtime.RunStatus, results.RunStatus)

    def test_runtime_reexports_executor_symbols(self) -> None:
        self.assertIs(runtime.run_solution_on_env, executor.run_solution_on_env)
        self.assertIs(
            runtime.DEFAULT_COMMAND_DELAY_SECONDS,
            executor.DEFAULT_COMMAND_DELAY_SECONDS,
        )
        self.assertIs(
            runtime.ROBOT_PATH_COLLISION_USER_MESSAGE,
            executor.ROBOT_PATH_COLLISION_USER_MESSAGE,
        )
        self.assertIs(runtime.StepExecutionSession, executor.StepExecutionSession)
        self.assertIs(runtime.StudentSolution, executor.StudentSolution)
        self.assertIs(runtime.StudentLine, executor.StudentLine)

    def test_gui_reexports_layout_and_theme(self) -> None:
        self.assertIs(gui.calculate_cell_size, gui_layout.calculate_cell_size)
        self.assertIs(gui.calculate_canvas_size, gui_layout.calculate_canvas_size)
        self.assertIs(gui.calculate_field_offset, gui_layout.calculate_field_offset)
        self.assertIs(gui.STATUS_READY, gui_theme.STATUS_READY)
        self.assertIs(gui.ACTION_BUTTON_STEP, gui_theme.ACTION_BUTTON_STEP)
        self.assertIs(gui.ACTION_BUTTON_STOP, gui_theme.ACTION_BUTTON_STOP)
        self.assertIs(gui.ACTION_BUTTON_HELP, gui_theme.ACTION_BUTTON_HELP)
        self.assertIs(gui.DEFAULT_CELL_SIZE, gui_theme.DEFAULT_CELL_SIZE)
        self.assertIs(gui.SUPER_COMPACT_CELL_SIZE, gui_theme.SUPER_COMPACT_CELL_SIZE)
