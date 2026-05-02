from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from typing import Callable

from .executor import StepExecutionSession, StudentLine

from .field_renderer import FieldColors, FieldRenderer
from .gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from .gui_theme import (
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_STEP,
    COMPACT_CELL_SIZE,
    DEFAULT_CELL_SIZE,
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
from .model import RobotEnv
from .results import RunResult
from .status_strip import StatusStrip


class RobotWindow:
    def __init__(
        self,
        task_id: str,
        envs: list[RobotEnv],
        run_env: Callable[[RobotEnv], RunResult] | None,
        initial_index: int = 0,
        todo_text: str = "",
        script_path: Path | None = None,
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.script_path = script_path
        self.selected_index = initial_index
        self.todo_text = todo_text.strip()
        self.current_listener: Callable[[], None] | None = None
        self.is_closed = False
        self._ignore_action_enter_until_idle = False
        self._is_run_all_active = False
        self._step_session: StepExecutionSession | None = None
        self._step_tabs_locked = False

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
        self._step_release_token = 0
        self.root.title(f"Robot: {task_id}")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.lift()
        self.root.attributes("-topmost", True)

        self.canvas_width, self.canvas_height = calculate_canvas_size(
            self.envs, self.cell_size, self.wall_width
        )

        self.todo_label: tk.Label | None = None
        if self.todo_text:
            self.todo_label = tk.Label(
                self.root,
                text=f"{self.todo_text}",
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=max(self.canvas_width, 320),
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
            self.todo_label.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

        self.tab_frame: tk.Frame | None = None
        self.tab_buttons: list[tk.Button] = []
        if len(envs) > 1:
            tab_top_pady = (2, 2) if self.todo_label is not None else (6, 2)
            self.tab_frame = tk.Frame(self.root)
            self.tab_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady)
            for index in range(len(envs)):
                button = tk.Button(
                    self.tab_frame,
                    text=str(index + 1),
                    command=lambda index=index: self.select_env(index),
                    width=4,
                )
                button.pack(side=tk.LEFT)
                self.tab_buttons.append(button)
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

        self.controls = tk.Frame(self.root)
        self.controls.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 2))

        self.action_button: tk.Button | None = None
        self._pending_restore_enable_after_id: str | None = None
        self.action_button = tk.Button(
            self.controls,
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
        )
        self.action_button.pack(side=tk.LEFT)
        self.step_button = tk.Button(
            self.controls,
            text=ACTION_BUTTON_STEP,
            command=self.step_once,
        )
        self.step_button.pack(side=tk.LEFT, padx=(4, 0))
        if self.script_path is None:
            self.step_button.configure(state=tk.DISABLED)
        self.root.bind("<Return>", self._handle_action_enter_key)
        self.root.bind("<KP_Enter>", self._handle_action_enter_key)
        self.root.bind("<KeyRelease-Return>", self._handle_action_enter_release)
        self.root.bind(
            "<KeyRelease-KP_Enter>", self._handle_action_enter_release
        )

        initial_status = STATUS_READY
        self._status_strip = StatusStrip(
            self.root,
            get_canvas_width=lambda: self.canvas_width,
            is_closed=lambda: self.is_closed,
            initial_text=initial_status,
            initial_bg=STATUS_BG_NEUTRAL,
        )
        self.status_var = self._status_strip.status_var
        self.status_frame = self._status_strip.status_frame
        self.status_canvas = self._status_strip.status_canvas
        self.status_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 6))

        self.select_env(initial_index)
        self.lock_window_size()

    def lock_window_size(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self.root.minsize(width, height)
        self.root.maxsize(width, height)

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
            f"Строка {line.lineno}: {line.text}",
            STATUS_BG_NEUTRAL,
        )
        self.root.update_idletasks()

    def _finish_step_run(self, result: RunResult) -> None:
        self._step_tabs_locked = False
        self._step_session = None
        if self.is_closed:
            return
        self.configure_tab_buttons()
        interrupted = (
            result.status == "error" and result.message == "Выполнение прервано"
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
            if result.status == "wrong":
                self._set_status(STATUS_WRONG, STATUS_BG_NEUTRAL)
            else:
                self._set_status(result.message, STATUS_BG_ERROR)
        else:
            self._set_status(STATUS_ALL_CORRECT, STATUS_BG_SUCCESS, hatched=True)
        self.draw_field()
        self._set_action_to_restore_after_idle()

    def _cancel_step_wake_only(self) -> None:
        if self._step_session is None:
            return
        if not self._step_session.is_started or self._step_session.is_finished:
            return
        self._step_session.cancel()
        self._step_release_token += 1

    def step_once(self) -> None:
        if self.is_closed or self.script_path is None or self._is_run_all_active:
            return
        if self._step_session is None:
            env = self.envs[self.selected_index]
            self._step_session = StepExecutionSession(
                self.script_path,
                self.task_id,
                env,
                show_line=self._show_step_line,
                wait_for_next_step=self._wait_for_next_step_impl,
                command_delay_seconds=0.0,
            )
            self._step_tabs_locked = True
            self.configure_tab_buttons()
            if self.action_button is not None:
                self.action_button.configure(state=tk.DISABLED)

        self._step_session.allow_one_step()
        self._step_release_token += 1

        if not self._step_session.is_started:
            result = self._step_session.start()
            self._finish_step_run(result)

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        if self.is_closed:
            return
        self._cancel_step_wake_only()
        self._cancel_pending_restore_enable_after()
        self.is_closed = True
        self.root.destroy()

    def select_env(self, index: int) -> None:
        if self.current_listener is not None:
            self.envs[self.selected_index].remove_listener(self.current_listener)

        self.selected_index = index
        self.current_listener = self.on_env_change
        self.envs[self.selected_index].add_listener(self.current_listener)

        self.configure_tab_buttons()

        self.draw_field()

    def _handle_action_enter_key(self, _event: tk.Event) -> str | None:
        """Invoke the main action button like a mouse click when Enter is pressed."""
        if self.action_button is None:
            return None
        if self._ignore_action_enter_until_idle:
            return "break"
        if self.action_button.cget("state") == tk.DISABLED:
            self._ignore_action_enter_until_idle = True
            return "break"
        self._ignore_action_enter_until_idle = True
        self.action_button.invoke()
        return "break"

    def _handle_action_enter_release(self, _event: tk.Event) -> str | None:
        if self.action_button is None:
            return None
        if self._ignore_action_enter_until_idle:
            self.root.after_idle(self._deferred_clear_enter_ignore)
            return "break"
        return None

    def _deferred_clear_enter_ignore(self) -> None:
        if self.is_closed:
            return
        if self._is_run_all_active:
            self.root.after_idle(self._deferred_clear_enter_ignore)
            return
        self._ignore_action_enter_until_idle = False

    def configure_tab_buttons(self) -> None:
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

    def _show_step_button_in_controls(self) -> None:
        """Pack the step button to the right of the main action button and set enabled state."""
        if self.step_button is None:
            return
        if self.step_button not in self.controls.pack_slaves():
            self.step_button.pack(side=tk.LEFT, padx=(4, 0))
        if self.script_path is not None:
            self.step_button.configure(state=tk.NORMAL)
        else:
            self.step_button.configure(state=tk.DISABLED)

    def _hide_step_button_from_controls(self) -> None:
        """Hide the step button while the UI is in post-run restore mode."""
        if self.step_button is None:
            return
        self.step_button.pack_forget()

    def _set_action_to_run(self) -> None:
        self._cancel_pending_restore_enable_after()
        if self.action_button is None:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
            state=tk.NORMAL,
        )
        self._show_step_button_in_controls()

    def _cancel_pending_restore_enable_after(self) -> None:
        if self._pending_restore_enable_after_id is None:
            return
        pending = self._pending_restore_enable_after_id
        self._pending_restore_enable_after_id = None
        try:
            self.root.after_cancel(pending)
        except tk.TclError:
            pass

    def _enable_action_button_if_current(self) -> None:
        self._pending_restore_enable_after_id = None
        if self.action_button is None or self.is_closed:
            return
        if self.action_button.cget("text") != ACTION_BUTTON_RESTORE:
            return
        if self.action_button.cget("state") != tk.DISABLED:
            return
        self.action_button.configure(state=tk.NORMAL)

    def _set_action_to_restore_after_idle(self) -> None:
        """Show Restore while disabled so queued clicks drain before the button is clickable."""
        self._cancel_pending_restore_enable_after()
        if self.action_button is None:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RESTORE,
            command=self.restore,
            state=tk.DISABLED,
        )
        self._hide_step_button_from_controls()
        self._pending_restore_enable_after_id = self.root.after_idle(
            self._enable_action_button_if_current
        )

    def _disable_action_button(self) -> None:
        if self.action_button is None:
            return
        self.action_button.configure(state=tk.DISABLED)

    def restore(self) -> None:
        self._cancel_step_wake_only()
        for env in self.envs:
            env.reset()
        self._set_status(STATUS_READY, STATUS_BG_NEUTRAL)
        self.select_env(0)
        self._set_action_to_run()

    def run_all(self) -> None:
        if self.run_env is None:
            raise RuntimeError("run_env is required")

        self._is_run_all_active = True
        try:
            if self.step_button is not None:
                self.step_button.configure(state=tk.DISABLED)
            self._disable_action_button()
            self._set_status(STATUS_RUNNING, STATUS_BG_NEUTRAL)
            self.root.update_idletasks()

            for index, env in enumerate(self.envs):
                self.select_env(index)
                result = self.run_env(env)
                self.draw_field()
                if not result.success:
                    if result.status == "wrong":
                        self._set_status(STATUS_WRONG, STATUS_BG_NEUTRAL)
                    else:
                        self._set_status(result.message, STATUS_BG_ERROR)
                    return

            self._set_status(STATUS_ALL_CORRECT, STATUS_BG_SUCCESS)
        finally:
            try:
                self._set_action_to_restore_after_idle()
            finally:
                self._is_run_all_active = False

    def on_env_change(self) -> None:
        if self.is_closed:
            return
        try:
            self.draw_field()
            self.root.update_idletasks()
        except tk.TclError:
            self.is_closed = True

    def draw_field(self) -> None:
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
]
