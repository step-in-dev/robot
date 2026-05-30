"""Main Robot window for solution and viewer modes."""

from __future__ import annotations

import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .executor import (
    EXECUTION_CANCELLED_MESSAGE,
    StepExecutionCallbacks,
    StepExecutionSession,
    StudentLine,
    check_limit_violations,
)

from .field_renderer import FieldColors, FieldRenderer
from .gui_action_buttons import ActionButtonMixin
from .gui_constraints import task_has_any_constraints
from .gui_dialogs import DialogManagerMixin
from .gui_keyboard import KeyboardHandlerMixin
from .gui_viewer import ViewerMixin
from .gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from .gui_theme import (
    ACTION_BUTTON_HELP,
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_STEP,
    BUTTON_PAD_X,
    BUTTON_PAD_Y,
    COMPACT_CELL_SIZE,
    ENV_SELECT_BUTTON_PAD_X,
    ENV_SELECT_BUTTON_PAD_Y,
    DEFAULT_CELL_SIZE,
    DIALOG_BODY_FONT,
    MIN_CANVAS_WIDTH,
    STATUS_ALL_CORRECT,
    STATUS_BG_ERROR,
    STATUS_BG_NEUTRAL,
    STATUS_BG_SUCCESS,
    STATUS_READY,
    STATUS_RUNNING,
    STATUS_WRONG,
    TODO_TEXT_BG,
    TODO_TEXT_BORDER,
)
from ._version import __version__
from .i18n import t
from .loader import RobotTask, ScriptConstraints
from .model import RobotEnv
from .results import RunResult
from .status_strip import StatusStrip, StatusStripHost
from .task_catalog import TaskCatalog

# Pause between environments during Run so the user can see the final state
# before switching (matches blocking sleep style used for command delays).
INTER_ENV_PAUSE_SECONDS = 0.2


@dataclass(frozen=True)
class RobotWindowOptions:
    """Optional settings when opening a ``RobotWindow``."""

    initial_index: int = 0
    script_path: Path | None = None
    open_constraints_on_startup: bool = False
    viewer_catalog: TaskCatalog | None = None


class RobotWindow(
    DialogManagerMixin, KeyboardHandlerMixin, ActionButtonMixin, ViewerMixin
):
    """Main tkinter window for student solutions and task viewer."""

    cell_size: int
    canvas_width: int
    canvas_height: int
    todo_label: tk.Label | None
    top_toolbar: tk.Frame | None
    tab_frame: tk.Frame | None
    tab_buttons: list[tk.Button]
    constraints_button: tk.Button | None

    def __init__(
        self,
        task_id: str,
        task_definition: RobotTask,
        run_env: Callable[[RobotEnv], RunResult] | None,
        options: RobotWindowOptions | None = None,
    ):
        opts = options or RobotWindowOptions()
        self.task_id = task_id
        self.envs = list(task_definition.envs)
        self.run_env = run_env
        self.script_path = opts.script_path
        self._script_constraints = ScriptConstraints.from_task(task_definition)
        self._open_constraints_on_startup = opts.open_constraints_on_startup
        self._viewer_catalog = opts.viewer_catalog
        self.viewer_toolbar: tk.Frame | None = None
        if opts.viewer_catalog is not None:
            self.run_env = None
            self.script_path = None
        self.selected_index = opts.initial_index
        self.todo_text = task_definition.todo_text.strip()
        self.current_listener: Callable[[], None] | None = None
        self.is_closed = False
        self._ignore_action_enter_until_idle = False
        self._is_run_all_active = False
        self._step_session: StepExecutionSession | None = None
        self._step_tabs_locked = False
        self._init_dialog_manager()

        self._init_root_and_geometry()
        if opts.viewer_catalog is not None:
            self._init_viewer_state(opts.viewer_catalog)
            self._build_viewer_toolbar()
        self._build_todo_banner()
        self._build_env_toolbar()
        self._build_field_area()
        self._build_control_row()
        self._build_status_area()
        self._finish_initial_placement(opts.initial_index)

    def _init_root_and_geometry(self) -> None:
        self.grid_color = "#428bca"
        self.wall_color = "#428bca"
        self.robot_color = "#428bca"
        self.robot_outline = "#ffffff"
        self.cell_to_paint_color = "#f0ad4e"
        self.cell_to_paint_when_painted_color = "#ffffff"
        self.home_color = "#a93b20"
        self.pollution_color = "#404C51"
        self.print_color = "#712903"
        self.cell_background_color = "#ffffff"
        self.wall_width = 4
        self.cell_size = calculate_cell_size(self.envs)

        self.root = tk.Tk()
        self.root.resizable(False, False)
        self._step_release_token = 0
        self.root.title(t("window.title", task_id=self.task_id, version=__version__))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        # Hide shell until layout is ready (reduces visible startup jitter).
        self.root.withdraw()

        self.canvas_width, self.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )

        self.todo_label = None
        self.top_toolbar = None
        self.tab_frame = None
        self.tab_buttons = []
        self.constraints_button = None

    def _top_section_pack_after(self) -> tk.Misc | None:
        if self.todo_label is not None:
            return self.todo_label
        return self.viewer_toolbar

    def _rebuild_todo_banner(self) -> None:
        if self.todo_label is not None:
            self.todo_label.destroy()
            self.todo_label = None
        if not self.todo_text:
            return
        self.todo_label = tk.Label(
            self.root,
            text=f"{self.todo_text}",
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=max(self.canvas_width, 320),
            font=DIALOG_BODY_FONT,
            bg=TODO_TEXT_BG,
            fg="#000000",
            padx=8,
            pady=6,
            bd=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=TODO_TEXT_BORDER,
            highlightcolor=TODO_TEXT_BORDER,
        )
        pack_after = self.viewer_toolbar
        if pack_after is not None:
            self.todo_label.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=(2, 2), after=pack_after
            )
        else:
            self.todo_label.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

    def _build_todo_banner(self) -> None:
        self._rebuild_todo_banner()

    def _rebuild_env_toolbar(self) -> None:
        if self.top_toolbar is not None:
            self.top_toolbar.destroy()
            self.top_toolbar = None
            self.tab_frame = None
            self.tab_buttons = []
            self.constraints_button = None

        has_env_tabs = len(self.envs) > 1
        has_constraints = task_has_any_constraints(self._script_constraints)
        if not (has_env_tabs or has_constraints):
            return
        tab_top_pady = (2, 2) if self.todo_label is not None else (6, 2)
        self.top_toolbar = tk.Frame(self.root)
        pack_after = self._top_section_pack_after()
        if pack_after is not None:
            self.top_toolbar.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady, after=pack_after
            )
        else:
            self.top_toolbar.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady
            )
        self.tab_frame = tk.Frame(self.top_toolbar)
        self.tab_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if has_env_tabs:
            for index in range(len(self.envs)):
                button = tk.Button(
                    self.tab_frame,
                    text=str(index + 1),
                    command=lambda index=index: self.select_env(index),
                    width=1,
                    padx=ENV_SELECT_BUTTON_PAD_X,
                    pady=ENV_SELECT_BUTTON_PAD_Y,
                )
                button.pack(side=tk.LEFT)
                self.tab_buttons.append(button)
        if has_constraints:
            self.constraints_button = tk.Button(
                self.top_toolbar,
                text=t("constraints.button"),
                command=self.show_constraints,
                padx=BUTTON_PAD_X,
                pady=BUTTON_PAD_Y,
            )
            self.constraints_button.pack(side=tk.RIGHT)

    def _build_env_toolbar(self) -> None:
        self._rebuild_env_toolbar()

    def _update_task_canvas_geometry(self) -> None:
        self.cell_size = calculate_cell_size(self.envs)
        self.canvas_width, self.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )
        self.canvas.configure(width=self.canvas_width, height=self.canvas_height)
        if self.todo_label is not None:
            self.todo_label.configure(wraplength=max(self.canvas_width, 320))

    def apply_task_payload(self, task_id: str, task_definition: RobotTask) -> None:
        """Replace the displayed task (viewer navigation)."""
        self.close_dialogs()

        if self.current_listener is not None:
            self.envs[self.selected_index].remove_listener(self.current_listener)
            self.current_listener = None

        self.task_id = task_id
        self.envs = list(task_definition.envs)
        self.todo_text = task_definition.todo_text.strip()
        self._script_constraints = ScriptConstraints.from_task(task_definition)

        self.root.title(t("window.title", task_id=self.task_id, version=__version__))
        if self._viewer_catalog is not None:
            self._refresh_viewer_top_chrome()
        else:
            self._rebuild_todo_banner()
            self._rebuild_env_toolbar()
        self._update_task_canvas_geometry()
        self.selected_index = 0
        self.select_env(0)
        self._set_status(STATUS_READY, STATUS_BG_NEUTRAL)
        self.draw_field()
        self.root.update_idletasks()
        self.lock_window_size()

    def _build_field_area(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            bg=self.root.cget("bg"),
            highlightthickness=0,
            width=self.canvas_width,
            height=self.canvas_height,
        )
        self.canvas.pack(padx=6, pady=6)

        self._field_renderer = FieldRenderer(
            self.canvas, self.cell_size, self.wall_width
        )

    def _build_control_row(self) -> None:
        self.controls = tk.Frame(self.root)
        self.controls.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 2))

        self.controls_right = tk.Frame(self.controls)
        self.controls_right.pack(side=tk.RIGHT)
        self.controls_left = tk.Frame(self.controls)
        self.controls_left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.action_button: tk.Button | None = None
        self._pending_restore_enable_after_id: str | None = None
        self.action_button = tk.Button(
            self.controls_left,
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
            width=max(len(ACTION_BUTTON_RUN), len(ACTION_BUTTON_RESTORE)),
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        self.action_button.pack(side=tk.LEFT)
        self.step_button = tk.Button(
            self.controls_left,
            text=ACTION_BUTTON_STEP,
            command=self.step_once,
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        self.step_button.pack(side=tk.LEFT, padx=(4, 0))
        if self.script_path is None:
            self.step_button.configure(state=tk.DISABLED)
        if self._viewer_catalog is not None:
            self._configure_viewer_execution_disabled()
        self.help_button = tk.Button(
            self.controls_right,
            text=ACTION_BUTTON_HELP,
            command=self.show_help,
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        self.help_button.pack(side=tk.RIGHT)
        self.bind_action_keyboard()

    def _build_status_area(self) -> None:
        initial_status = STATUS_READY
        self._status_strip = StatusStrip(
            self.root,
            StatusStripHost(
                get_canvas_width=lambda: self.canvas_width,
                is_closed=lambda: self.is_closed,
            ),
            initial_text=initial_status,
            initial_bg=STATUS_BG_NEUTRAL,
        )
        self.status_var = self._status_strip.status_var
        self.status_frame = self._status_strip.status_frame
        self.status_canvas = self._status_strip.status_canvas
        self.status_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 6))

    def _finish_initial_placement(self, initial_index: int) -> None:
        self.select_env(initial_index)
        self.root.update_idletasks()
        self.lock_window_size()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.update()

    def lock_window_size(self) -> None:
        """Set window geometry from requested size; no-op when unchanged."""
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        if width <= 1 or height <= 1:
            width = max(width, self.root.winfo_width())
            height = max(height, self.root.winfo_height())
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        if width == current_width and height == current_height:
            return
        self.root.wm_geometry(f"{width}x{height}")

    @property
    def _status_background(self) -> str:
        return self._status_strip.background

    @property
    def _status_hatched(self) -> bool:
        return self._status_strip.hatched

    def _set_status(
        self, text: str, background: str, *, hatched: bool = False
    ) -> None:
        self._status_strip.set_status(text, background, hatched=hatched)

    def _wait_for_next_step_impl(self) -> None:
        start_token = self._step_release_token
        while self._step_release_token == start_token and not self.is_closed:
            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.001)

    def _show_step_line(self, line: StudentLine) -> None:
        if self.is_closed:
            return
        self._set_status(
            t("step.line", lineno=line.lineno, text=line.text),
            STATUS_BG_NEUTRAL,
        )
        self.root.update_idletasks()

    def _show_failed_result(self, result: RunResult) -> None:
        if result.status == "wrong":
            self._set_status(result.message or STATUS_WRONG, STATUS_BG_NEUTRAL)
        else:
            self._set_status(result.message, STATUS_BG_ERROR)

    def _check_script_constraints(self) -> str | None:
        if self.script_path is None:
            return None
        try:
            source = self.script_path.read_text(encoding="utf-8")
        except OSError:
            return None
        return check_limit_violations(
            source,
            filename=str(self.script_path),
            constraints=self._script_constraints,
        )

    def _finish_step_run(self, result: RunResult) -> None:
        self._step_tabs_locked = False
        self._step_session = None
        if self.is_closed:
            return
        self.configure_tab_buttons()
        interrupted = (
            result.status == "error"
            and result.message == EXECUTION_CANCELLED_MESSAGE
        )
        if interrupted:
            if self.action_button is not None:
                self.action_button.configure(state=tk.NORMAL)
            if self.step_button is not None and self.script_path is not None:
                self.step_button.configure(state=tk.NORMAL)
            return
        if self.step_button is not None:
            self.step_button.configure(state=tk.DISABLED)
        if not result.success:
            self._show_failed_result(result)
        else:
            violation = self._check_script_constraints()
            if violation is not None:
                self._set_status(violation, STATUS_BG_NEUTRAL)
            else:
                env_label = self.selected_index + 1
                self._set_status(
                    t("step.success_for_env", env_label=env_label),
                    STATUS_BG_SUCCESS,
                    hatched=True,
                )
        self.draw_field()
        self._set_action_to_restore(
            disabled=True, hide_step=True, enable_after_idle=True
        )

    def _cancel_step_wake_only(self) -> None:
        if self._step_session is None:
            return
        if not self._step_session.is_started or self._step_session.is_finished:
            return
        self._step_session.cancel()
        self._step_release_token += 1

    def step_once(self) -> None:
        """Run or resume the student script for one source line."""
        if self.is_closed or self.script_path is None or self._is_run_all_active:
            return
        if self._step_session is None:
            env = self.envs[self.selected_index]
            self._step_session = StepExecutionSession(
                self.script_path,
                self.task_id,
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=self._show_step_line,
                    wait_for_next_step=self._wait_for_next_step_impl,
                ),
                command_delay_seconds=0.0,
            )
            self._step_tabs_locked = True
            self.configure_tab_buttons()
            self._set_action_to_restore(disabled=False, hide_step=False)

        self._step_session.allow_one_step()
        self._step_release_token += 1

        if not self._step_session.is_started:
            result = self._step_session.start()
            self._finish_step_run(result)

    def run(self) -> None:
        """Start the Tk event loop."""
        if self._open_constraints_on_startup:
            self.root.after(300, self.show_constraints)
        self.root.mainloop()

    def close(self) -> None:
        """Tear down stepping, dialogs, and the root window."""
        if self.is_closed:
            return
        self._cancel_step_wake_only()
        self._cancel_pending_restore_enable_after()
        self.close_dialogs()
        self.is_closed = True
        self.root.destroy()

    def select_env(self, index: int) -> None:
        """Switch the visible environment tab and redraw the field."""
        if self.current_listener is not None:
            self.envs[self.selected_index].remove_listener(self.current_listener)

        self.selected_index = index
        self.current_listener = self.on_env_change
        self.envs[self.selected_index].add_listener(self.current_listener)

        self.configure_tab_buttons()

        self.draw_field()

    def configure_tab_buttons(self) -> None:
        """Update environment tab button relief and enabled state."""
        if self.is_closed:
            return
        for tab_index, button in enumerate(self.tab_buttons):
            if self._step_tabs_locked:
                state = tk.DISABLED
            else:
                state = tk.DISABLED if tab_index == self.selected_index else tk.NORMAL
            button.configure(
                relief=tk.SUNKEN
                if tab_index == self.selected_index
                else tk.RAISED,
                state=state,
            )

    def restore(self) -> None:
        """Reset all environments and return the UI to the ready state."""
        self._cancel_step_wake_only()
        for env in self.envs:
            env.reset()
        self._set_status(STATUS_READY, STATUS_BG_NEUTRAL)
        self.select_env(0)
        self._set_action_to_run()

    def run_all(self) -> None:
        """Run the student script on every environment in sequence."""
        if self.run_env is None:
            raise RuntimeError("run_env is required")

        self._is_run_all_active = True
        try:
            if self.step_button is not None:
                self.step_button.configure(state=tk.DISABLED)
            self._set_action_to_restore(disabled=True, hide_step=False)
            self._set_status(STATUS_RUNNING, STATUS_BG_NEUTRAL)
            self.root.update_idletasks()

            for index, env in enumerate(self.envs):
                self.select_env(index)
                result = self.run_env(env)
                self.draw_field()
                if not result.success:
                    self._show_failed_result(result)
                    return
                if index + 1 < len(self.envs):
                    self.root.update_idletasks()
                    time.sleep(INTER_ENV_PAUSE_SECONDS)

            violation = self._check_script_constraints()
            if violation is not None:
                self._set_status(violation, STATUS_BG_NEUTRAL)
            else:
                self._set_status(STATUS_ALL_CORRECT, STATUS_BG_SUCCESS)
        finally:
            try:
                self._set_action_to_restore(
                    disabled=True, hide_step=True, enable_after_idle=True
                )
            finally:
                self._is_run_all_active = False

    def on_env_change(self) -> None:
        """Redraw the field when robot state changes."""
        if self.is_closed:
            return
        try:
            self.draw_field()
            self.root.update_idletasks()
        except tk.TclError:
            self.is_closed = True

    def draw_field(self) -> None:
        """Paint the current environment on the canvas."""
        if self.is_closed:
            return

        env = self.envs[self.selected_index]
        self._field_renderer.set_dimensions(self.cell_size, self.wall_width)
        colors = FieldColors(
            grid_color=self.grid_color,
            wall_color=self.wall_color,
            robot_color=self.robot_color,
            robot_outline=self.robot_outline,
            cell_to_paint_color=self.cell_to_paint_color,
            cell_to_paint_when_painted_color=self.cell_to_paint_when_painted_color,
            home_color=self.home_color,
            pollution_color=self.pollution_color,
            print_color=self.print_color,
            cell_background_color=self.cell_background_color,
        )
        self._field_renderer.draw_field(
            env, self.canvas_width, self.canvas_height, colors
        )


__all__ = [
    "RobotWindow",
    "ACTION_BUTTON_HELP",
    "ACTION_BUTTON_RESTORE",
    "ACTION_BUTTON_RUN",
    "ACTION_BUTTON_STEP",
    "COMPACT_CELL_SIZE",
    "DEFAULT_CELL_SIZE",
    "MIN_CANVAS_WIDTH",
    "STATUS_ALL_CORRECT",
    "STATUS_READY",
    "STATUS_WRONG",
    "STATUS_BG_ERROR",
    "STATUS_BG_NEUTRAL",
    "STATUS_BG_SUCCESS",
    "TODO_TEXT_BORDER",
    "calculate_canvas_size",
    "calculate_cell_size",
    "calculate_field_offset",
    "INTER_ENV_PAUSE_SECONDS",
]
