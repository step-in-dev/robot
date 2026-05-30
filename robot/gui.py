"""Main Robot window for solution and viewer modes."""

from __future__ import annotations

import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .executor import (
    EXECUTION_CANCELLED_MESSAGE,
    StepExecutionCallbacks,
    StepExecutionSession,
    StudentLine,
    check_limit_violations,
)

from .field_renderer import DEFAULT_FIELD_COLORS, FieldColors, FieldRenderer
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


@dataclass
class _TaskSession:  # pylint: disable=too-many-instance-attributes
    """Task identity, environments, and solution hooks (grouped on ``RobotWindow``)."""

    task_id: str
    envs: list[RobotEnv]
    run_env: Callable[[RobotEnv], RunResult] | None
    script_path: Path | None
    script_constraints: ScriptConstraints
    open_constraints_on_startup: bool
    viewer_catalog: TaskCatalog | None
    selected_index: int
    todo_text: str
    current_listener: Callable[[], None] | None


@dataclass
class _LayoutState:
    """Field canvas geometry and renderer."""

    colors: FieldColors
    wall_width: int
    cell_size: int = 0
    canvas_width: int = 0
    canvas_height: int = 0
    canvas: tk.Canvas | None = None
    renderer: FieldRenderer | None = None


@dataclass
class _ChromeState:  # pylint: disable=too-many-instance-attributes
    """Toolbars, tabs, and Run/Step/Help controls (grouped on ``RobotWindow``)."""

    viewer_toolbar: tk.Frame | None = None
    todo_label: tk.Label | None = None
    top_toolbar: tk.Frame | None = None
    tab_frame: tk.Frame | None = None
    tab_buttons: list[tk.Button] = field(default_factory=list)
    constraints_button: tk.Button | None = None
    controls: tk.Frame | None = None
    controls_left: tk.Frame | None = None
    controls_right: tk.Frame | None = None
    action_button: tk.Button | None = None
    step_button: tk.Button | None = None
    help_button: tk.Button | None = None
    pending_restore_enable_after_id: str | None = None


@dataclass
class _ExecutionState:
    """Step/run lifecycle flags and active stepping session."""

    is_closed: bool = False
    step_session: StepExecutionSession | None = None
    step_tabs_locked: bool = False
    step_release_token: int = 0
    ignore_action_enter_until_idle: bool = False
    is_run_all_active: bool = False


class RobotWindow(
    DialogManagerMixin, KeyboardHandlerMixin, ActionButtonMixin, ViewerMixin
):
    """Main tkinter window for student solutions and task viewer."""

    def __init__(
        self,
        task_id: str,
        task_definition: RobotTask,
        run_env: Callable[[RobotEnv], RunResult] | None,
        options: RobotWindowOptions | None = None,
    ):
        opts = options or RobotWindowOptions()
        script_path = opts.script_path
        effective_run_env = run_env
        if opts.viewer_catalog is not None:
            effective_run_env = None
            script_path = None
        self._task = _TaskSession(
            task_id=task_id,
            envs=list(task_definition.envs),
            run_env=effective_run_env,
            script_path=script_path,
            script_constraints=ScriptConstraints.from_task(task_definition),
            open_constraints_on_startup=opts.open_constraints_on_startup,
            viewer_catalog=opts.viewer_catalog,
            selected_index=opts.initial_index,
            todo_text=task_definition.todo_text.strip(),
            current_listener=None,
        )
        self._execution = _ExecutionState()
        self._layout = _LayoutState(
            colors=DEFAULT_FIELD_COLORS, wall_width=4
        )
        self._chrome = _ChromeState()
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

    @property
    def is_closed(self) -> bool:
        return self._execution.is_closed

    @is_closed.setter
    def is_closed(self, value: bool) -> None:
        self._execution.is_closed = value

    @property
    def task_id(self) -> str:
        return self._task.task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        self._task.task_id = value

    @property
    def envs(self) -> list[RobotEnv]:
        return self._task.envs

    @envs.setter
    def envs(self, value: list[RobotEnv]) -> None:
        self._task.envs = value

    @property
    def run_env(self) -> Callable[[RobotEnv], RunResult] | None:
        return self._task.run_env

    @run_env.setter
    def run_env(self, value: Callable[[RobotEnv], RunResult] | None) -> None:
        self._task.run_env = value

    @property
    def script_path(self) -> Path | None:
        return self._task.script_path

    @property
    def _script_constraints(self) -> ScriptConstraints:
        return self._task.script_constraints

    @_script_constraints.setter
    def _script_constraints(self, value: ScriptConstraints) -> None:
        self._task.script_constraints = value

    @property
    def _viewer_catalog(self) -> TaskCatalog | None:
        return self._task.viewer_catalog

    @property
    def selected_index(self) -> int:
        return self._task.selected_index

    @selected_index.setter
    def selected_index(self, value: int) -> None:
        self._task.selected_index = value

    @property
    def todo_text(self) -> str:
        return self._task.todo_text

    @todo_text.setter
    def todo_text(self, value: str) -> None:
        self._task.todo_text = value

    @property
    def current_listener(self) -> Callable[[], None] | None:
        return self._task.current_listener

    @current_listener.setter
    def current_listener(self, value: Callable[[], None] | None) -> None:
        self._task.current_listener = value

    @property
    def viewer_toolbar(self) -> tk.Frame | None:
        return self._chrome.viewer_toolbar

    @viewer_toolbar.setter
    def viewer_toolbar(self, value: tk.Frame | None) -> None:
        self._chrome.viewer_toolbar = value

    @property
    def todo_label(self) -> tk.Label | None:
        return self._chrome.todo_label

    @todo_label.setter
    def todo_label(self, value: tk.Label | None) -> None:
        self._chrome.todo_label = value

    @property
    def top_toolbar(self) -> tk.Frame | None:
        return self._chrome.top_toolbar

    @top_toolbar.setter
    def top_toolbar(self, value: tk.Frame | None) -> None:
        self._chrome.top_toolbar = value

    @property
    def tab_frame(self) -> tk.Frame | None:
        return self._chrome.tab_frame

    @tab_frame.setter
    def tab_frame(self, value: tk.Frame | None) -> None:
        self._chrome.tab_frame = value

    @property
    def tab_buttons(self) -> list[tk.Button]:
        return self._chrome.tab_buttons

    @tab_buttons.setter
    def tab_buttons(self, value: list[tk.Button]) -> None:
        self._chrome.tab_buttons = value

    @property
    def constraints_button(self) -> tk.Button | None:
        return self._chrome.constraints_button

    @constraints_button.setter
    def constraints_button(self, value: tk.Button | None) -> None:
        self._chrome.constraints_button = value

    @property
    def canvas(self) -> tk.Canvas:
        assert self._layout.canvas is not None
        return self._layout.canvas

    @property
    def controls(self) -> tk.Frame:
        assert self._chrome.controls is not None
        return self._chrome.controls

    @property
    def controls_left(self) -> tk.Frame:
        assert self._chrome.controls_left is not None
        return self._chrome.controls_left

    @property
    def controls_right(self) -> tk.Frame:
        assert self._chrome.controls_right is not None
        return self._chrome.controls_right

    @property
    def action_button(self) -> tk.Button | None:
        return self._chrome.action_button

    @action_button.setter
    def action_button(self, value: tk.Button | None) -> None:
        self._chrome.action_button = value

    @property
    def step_button(self) -> tk.Button:
        assert self._chrome.step_button is not None
        return self._chrome.step_button

    @property
    def help_button(self) -> tk.Button:
        assert self._chrome.help_button is not None
        return self._chrome.help_button

    @property
    def cell_size(self) -> int:
        return self._layout.cell_size

    @cell_size.setter
    def cell_size(self, value: int) -> None:
        self._layout.cell_size = value

    @property
    def canvas_width(self) -> int:
        return self._layout.canvas_width

    @property
    def canvas_height(self) -> int:
        return self._layout.canvas_height

    @property
    def wall_width(self) -> int:
        return self._layout.wall_width

    @property
    def status_var(self):
        return self._status_strip.status_var

    @property
    def status_frame(self) -> tk.Frame:
        return self._status_strip.status_frame

    @property
    def status_canvas(self) -> tk.Canvas:
        return self._status_strip.status_canvas

    @property
    def _step_session(self) -> StepExecutionSession | None:
        return self._execution.step_session

    @_step_session.setter
    def _step_session(self, value: StepExecutionSession | None) -> None:
        self._execution.step_session = value

    @property
    def _step_tabs_locked(self) -> bool:
        return self._execution.step_tabs_locked

    @_step_tabs_locked.setter
    def _step_tabs_locked(self, value: bool) -> None:
        self._execution.step_tabs_locked = value

    @property
    def _step_release_token(self) -> int:
        return self._execution.step_release_token

    @_step_release_token.setter
    def _step_release_token(self, value: int) -> None:
        self._execution.step_release_token = value

    @property
    def _ignore_action_enter_until_idle(self) -> bool:
        return self._execution.ignore_action_enter_until_idle

    @_ignore_action_enter_until_idle.setter
    def _ignore_action_enter_until_idle(self, value: bool) -> None:
        self._execution.ignore_action_enter_until_idle = value

    @property
    def _is_run_all_active(self) -> bool:
        return self._execution.is_run_all_active

    @_is_run_all_active.setter
    def _is_run_all_active(self, value: bool) -> None:
        self._execution.is_run_all_active = value

    @property
    def _pending_restore_enable_after_id(self) -> str | None:
        return self._chrome.pending_restore_enable_after_id

    @_pending_restore_enable_after_id.setter
    def _pending_restore_enable_after_id(self, value: str | None) -> None:
        self._chrome.pending_restore_enable_after_id = value

    def _init_root_and_geometry(self) -> None:
        self._layout.cell_size = calculate_cell_size(self.envs)
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self._execution.step_release_token = 0
        self.root.title(t("window.title", task_id=self.task_id, version=__version__))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        # Hide shell until layout is ready (reduces visible startup jitter).
        self.root.withdraw()

        self._layout.canvas_width, self._layout.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )

        self._chrome.todo_label = None
        self._chrome.top_toolbar = None
        self._chrome.tab_frame = None
        self._chrome.tab_buttons = []
        self._chrome.constraints_button = None

    def _top_section_pack_after(self) -> tk.Misc | None:
        if self.todo_label is not None:
            return self.todo_label
        return self.viewer_toolbar

    def _rebuild_todo_banner(self) -> None:
        if self._chrome.todo_label is not None:
            self._chrome.todo_label.destroy()
            self._chrome.todo_label = None
        if not self.todo_text:
            return
        self._chrome.todo_label = tk.Label(
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
            self._chrome.todo_label.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=(2, 2), after=pack_after
            )
        else:
            self._chrome.todo_label.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

    def _build_todo_banner(self) -> None:
        self._rebuild_todo_banner()

    def _rebuild_env_toolbar(self) -> None:
        if self._chrome.top_toolbar is not None:
            self._chrome.top_toolbar.destroy()
            self._chrome.top_toolbar = None
            self._chrome.tab_frame = None
            self._chrome.tab_buttons = []
            self._chrome.constraints_button = None

        has_env_tabs = len(self.envs) > 1
        has_constraints = task_has_any_constraints(self._script_constraints)
        if not (has_env_tabs or has_constraints):
            return
        tab_top_pady = (2, 2) if self._chrome.todo_label is not None else (6, 2)
        self._chrome.top_toolbar = tk.Frame(self.root)
        pack_after = self._top_section_pack_after()
        if pack_after is not None:
            self._chrome.top_toolbar.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady, after=pack_after
            )
        else:
            self._chrome.top_toolbar.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady
            )
        self._chrome.tab_frame = tk.Frame(self._chrome.top_toolbar)
        self._chrome.tab_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if has_env_tabs:
            for index in range(len(self.envs)):
                button = tk.Button(
                    self._chrome.tab_frame,
                    text=str(index + 1),
                    command=lambda index=index: self.select_env(index),
                    width=1,
                    padx=ENV_SELECT_BUTTON_PAD_X,
                    pady=ENV_SELECT_BUTTON_PAD_Y,
                )
                button.pack(side=tk.LEFT)
                self._chrome.tab_buttons.append(button)
        if has_constraints:
            self._chrome.constraints_button = tk.Button(
                self._chrome.top_toolbar,
                text=t("constraints.button"),
                command=self.show_constraints,
                padx=BUTTON_PAD_X,
                pady=BUTTON_PAD_Y,
            )
            self._chrome.constraints_button.pack(side=tk.RIGHT)

    def _build_env_toolbar(self) -> None:
        self._rebuild_env_toolbar()

    def _update_task_canvas_geometry(self) -> None:
        self._layout.cell_size = calculate_cell_size(self.envs)
        self._layout.canvas_width, self._layout.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )
        self.canvas.configure(width=self.canvas_width, height=self.canvas_height)
        if self.todo_label is not None:
            self.todo_label.configure(wraplength=max(self.canvas_width, 320))

    def apply_task_payload(self, task_id: str, task_definition: RobotTask) -> None:
        """Replace the displayed task (viewer navigation)."""
        self.close_dialogs()

        if self._task.current_listener is not None:
            self.envs[self.selected_index].remove_listener(
                self._task.current_listener
            )
            self._task.current_listener = None

        self._task.task_id = task_id
        self._task.envs = list(task_definition.envs)
        self._task.todo_text = task_definition.todo_text.strip()
        self._task.script_constraints = ScriptConstraints.from_task(
            task_definition
        )

        self.root.title(t("window.title", task_id=self.task_id, version=__version__))
        if self._viewer_catalog is not None:
            self._refresh_viewer_top_chrome()
        else:
            self._rebuild_todo_banner()
            self._rebuild_env_toolbar()
        self._update_task_canvas_geometry()
        self._task.selected_index = 0
        self.select_env(0)
        self._set_status(STATUS_READY, STATUS_BG_NEUTRAL)
        self.draw_field()
        self.root.update_idletasks()
        self.lock_window_size()

    def _build_field_area(self) -> None:
        self._layout.canvas = tk.Canvas(
            self.root,
            bg=self.root.cget("bg"),
            highlightthickness=0,
            width=self.canvas_width,
            height=self.canvas_height,
        )
        self._layout.canvas.pack(padx=6, pady=6)

        self._layout.renderer = FieldRenderer(
            self._layout.canvas, self.cell_size, self.wall_width
        )

    def _build_control_row(self) -> None:
        self._chrome.controls = tk.Frame(self.root)
        self._chrome.controls.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 2))

        self._chrome.controls_right = tk.Frame(self._chrome.controls)
        self._chrome.controls_right.pack(side=tk.RIGHT)
        self._chrome.controls_left = tk.Frame(self._chrome.controls)
        self._chrome.controls_left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._chrome.action_button = tk.Button(
            self.controls_left,
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
            width=max(len(ACTION_BUTTON_RUN), len(ACTION_BUTTON_RESTORE)),
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        self.action_button.pack(side=tk.LEFT)
        self._chrome.step_button = tk.Button(
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
        self._chrome.help_button = tk.Button(
            self._chrome.controls_right,
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
        self._status_strip.status_frame.pack(
            side=tk.TOP, fill=tk.X, padx=6, pady=(0, 6)
        )

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
        self._execution.step_tabs_locked = False
        self._execution.step_session = None
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
        self._execution.step_release_token += 1

    def step_once(self) -> None:
        """Run or resume the student script for one source line."""
        if self.is_closed or self.script_path is None or self._is_run_all_active:
            return
        if self._step_session is None:
            env = self.envs[self.selected_index]
            self._execution.step_session = StepExecutionSession(
                self.script_path,
                self.task_id,
                env,
                callbacks=StepExecutionCallbacks(
                    show_line=self._show_step_line,
                    wait_for_next_step=self._wait_for_next_step_impl,
                ),
                command_delay_seconds=0.0,
            )
            self._execution.step_tabs_locked = True
            self.configure_tab_buttons()
            self._set_action_to_restore(disabled=False, hide_step=False)

        self._step_session.allow_one_step()
        self._execution.step_release_token += 1

        if not self._step_session.is_started:
            result = self._step_session.start()
            self._finish_step_run(result)

    def run(self) -> None:
        """Start the Tk event loop."""
        if self._task.open_constraints_on_startup:
            self.root.after(300, self.show_constraints)
        self.root.mainloop()

    def close(self) -> None:
        """Tear down stepping, dialogs, and the root window."""
        if self.is_closed:
            return
        self._cancel_step_wake_only()
        self._cancel_pending_restore_enable_after()
        self.close_dialogs()
        self._execution.is_closed = True
        self.root.destroy()

    def select_env(self, index: int) -> None:
        """Switch the visible environment tab and redraw the field."""
        if self._task.current_listener is not None:
            self.envs[self.selected_index].remove_listener(
                self._task.current_listener
            )

        self._task.selected_index = index
        self._task.current_listener = self.on_env_change
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

        self._execution.is_run_all_active = True
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
                self._execution.is_run_all_active = False

    def on_env_change(self) -> None:
        """Redraw the field when robot state changes."""
        if self.is_closed:
            return
        try:
            self.draw_field()
            self.root.update_idletasks()
        except tk.TclError:
            self._execution.is_closed = True

    def draw_field(self) -> None:
        """Paint the current environment on the canvas."""
        if self.is_closed:
            return

        env = self.envs[self.selected_index]
        assert self._layout.renderer is not None
        self._layout.renderer.set_dimensions(self.cell_size, self.wall_width)
        self._layout.renderer.draw_field(
            env,
            self.canvas_width,
            self.canvas_height,
            self._layout.colors,
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
