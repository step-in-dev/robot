from __future__ import annotations

import time
import webbrowser
import tkinter as tk
from pathlib import Path
from typing import Callable

from .executor import (
    EXECUTION_CANCELLED_MESSAGE,
    StepExecutionSession,
    StudentLine,
)

from .command_help import iter_command_help_lines
from .field_renderer import FieldColors, FieldRenderer
from .gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from .i18n import t
from .gui_theme import (
    ACTION_BUTTON_HELP,
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

_ESCAPE_BINDING = "<Escape>"

# Source repository URL (shown as a clickable link in the help dialog).
_HELP_PROJECT_REPOSITORY_URL = "https://github.com/step-in-dev/robot"
_HELP_AUTHOR_NAME = "Виктор Терещук (Viktar Tserashchuk)"
_HELP_BODY_LINK_TAG = "help_repo_link"

_HELP_TEXT_KP_NAV_KEYS = frozenset(
    {
        "KP_Left",
        "KP_Right",
        "KP_Up",
        "KP_Down",
        "KP_Prior",
        "KP_Next",
        "KP_Home",
        "KP_End",
        "KP_Begin",
    }
)


def _help_text_readonly_key_action(event: tk.Event) -> str | None:
    """Return ``\"break\"`` to block edits; ``None`` to keep copy, selection, and navigation."""
    if event.keysym == "Escape":
        return None

    state = event.state or 0
    ctrl = bool(state & 0x0004)
    meta = bool(state & 0x0008)
    ks = event.keysym or ""

    if (ctrl or meta) and ks.lower() in ("c", "a", "insert"):
        return None
    if (ctrl or meta) and ks.lower() in ("v", "x"):
        return "break"

    if ks in (
        "BackSpace",
        "Delete",
        "Return",
        "KP_Enter",
        "Linefeed",
        "Tab",
        "ISO_Left_Tab",
        "space",
    ):
        return "break"

    if ks.startswith("KP_") and ks not in _HELP_TEXT_KP_NAV_KEYS:
        return "break"

    ch = event.char
    if ch and ch.isprintable() and not (ctrl or meta):
        return "break"

    return None


def _help_text_block_paste(_event: tk.Event) -> str:
    return "break"


# Pause between environments during Run so the user can see the final state
# before switching (matches blocking sleep style used for command delays).
INTER_ENV_PAUSE_SECONDS = 0.2

_CONSTRAINTS_TEXT_WIDTH = 51


def _open_help_project_repository() -> None:
    """Open the public project repository in the user's browser."""
    webbrowser.open(_HELP_PROJECT_REPOSITORY_URL)


def _populate_robot_help_text(text: tk.Text) -> None:
    """Fill the help ``Text`` with module info, repo link, and command list (read-only)."""
    text.insert(tk.END, t("help.module_intro") + "\n\n")
    text.insert(tk.END, t("help.author", author=_HELP_AUTHOR_NAME) + "\n")
    text.insert(tk.END, t("help.project_repo_label") + "\n")
    text.insert(tk.END, _HELP_PROJECT_REPOSITORY_URL, (_HELP_BODY_LINK_TAG,))
    text.insert(tk.END, "\n\n")
    body = "\n".join(iter_command_help_lines()).rstrip() + "\n"
    text.insert(tk.END, body)

    text.tag_configure(_HELP_BODY_LINK_TAG, foreground="#0645ad", underline=True)

    def _on_help_text_button1(event: tk.Event) -> None:
        try:
            idx = text.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        if _HELP_BODY_LINK_TAG in text.tag_names(idx):
            _open_help_project_repository()

    def _link_enter(_event: tk.Event) -> None:
        text.config(cursor="hand2")

    def _link_leave(_event: tk.Event) -> None:
        text.config(cursor="")

    text.bind("<Button-1>", _on_help_text_button1)
    text.tag_bind(_HELP_BODY_LINK_TAG, "<Enter>", _link_enter)
    text.tag_bind(_HELP_BODY_LINK_TAG, "<Leave>", _link_leave)

    text.bind("<Key>", _help_text_readonly_key_action)
    text.bind("<<Paste>>", _help_text_block_paste)


def _task_has_any_constraints(
    *,
    operators_limit: int | None,
    custom_function_call_count: int | None,
    if_limit: int | None,
    while_limit: int | None,
    required_keywords: tuple[str, ...] | None,
    banned_keywords: tuple[str, ...] | None,
) -> bool:
    if operators_limit is not None:
        return True
    if custom_function_call_count is not None:
        return True
    if if_limit is not None:
        return True
    if while_limit is not None:
        return True
    if required_keywords:
        return True
    if banned_keywords:
        return True
    return False


class RobotWindow:
    def __init__(
        self,
        task_id: str,
        envs: list[RobotEnv],
        run_env: Callable[[RobotEnv], RunResult] | None,
        initial_index: int = 0,
        todo_text: str = "",
        script_path: Path | None = None,
        operators_limit: int | None = None,
        custom_function_call_count: int | None = None,
        if_limit: int | None = None,
        while_limit: int | None = None,
        required_keywords: tuple[str, ...] | None = None,
        banned_keywords: tuple[str, ...] | None = None,
    ):
        self.task_id = task_id
        self.envs = envs
        self.run_env = run_env
        self.script_path = script_path
        self.operators_limit = operators_limit
        self.custom_function_call_count = custom_function_call_count
        self.if_limit = if_limit
        self.while_limit = while_limit
        self.required_keywords = required_keywords
        self.banned_keywords = banned_keywords
        self.selected_index = initial_index
        self.todo_text = todo_text.strip()
        self.current_listener: Callable[[], None] | None = None
        self.is_closed = False
        self._ignore_action_enter_until_idle = False
        self._is_run_all_active = False
        self._step_session: StepExecutionSession | None = None
        self._step_tabs_locked = False
        self._help_window: tk.Toplevel | None = None
        self._help_window_close_handler: Callable[[], None] | None = None
        self._constraints_window: tk.Toplevel | None = None
        self._constraints_window_close_handler: Callable[[], None] | None = None

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
        self.root.title(t("window.title", task_id=task_id))
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

        self.top_toolbar: tk.Frame | None = None
        self.tab_frame: tk.Frame | None = None
        self.tab_buttons: list[tk.Button] = []
        self.constraints_button: tk.Button | None = None
        has_env_tabs = len(envs) > 1
        has_constraints = _task_has_any_constraints(
            operators_limit=operators_limit,
            custom_function_call_count=custom_function_call_count,
            if_limit=if_limit,
            while_limit=while_limit,
            required_keywords=required_keywords,
            banned_keywords=banned_keywords,
        )
        if has_env_tabs or has_constraints:
            tab_top_pady = (2, 2) if self.todo_label is not None else (6, 2)
            self.top_toolbar = tk.Frame(self.root)
            self.top_toolbar.pack(
                side=tk.TOP, fill=tk.X, padx=6, pady=tab_top_pady
            )
            self.tab_frame = tk.Frame(self.top_toolbar)
            self.tab_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if has_env_tabs:
                for index in range(len(envs)):
                    button = tk.Button(
                        self.tab_frame,
                        text=str(index + 1),
                        command=lambda index=index: self.select_env(index),
                        width=1,
                        padx='4.5m',
                        pady='2m'
                    )
                    button.pack(side=tk.LEFT)
                    self.tab_buttons.append(button)
            if has_constraints:
                self.constraints_button = tk.Button(
                    self.top_toolbar,
                    text=t("constraints.button"),
                    command=self.show_constraints,
                )
                self.constraints_button.pack(side=tk.RIGHT)
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
        )
        self.action_button.pack(side=tk.LEFT)
        self.step_button = tk.Button(
            self.controls_left,
            text=ACTION_BUTTON_STEP,
            command=self.step_once,
        )
        self.step_button.pack(side=tk.LEFT, padx=(4, 0))
        if self.script_path is None:
            self.step_button.configure(state=tk.DISABLED)
        self.help_button = tk.Button(
            self.controls_right,
            text=ACTION_BUTTON_HELP,
            command=self.show_help,
        )
        self.help_button.pack(side=tk.RIGHT)
        self.root.bind("<Return>", self._handle_action_enter_key)
        self.root.bind("<KP_Enter>", self._handle_action_enter_key)
        self.root.bind("<KeyRelease-Return>", self._handle_action_enter_release)
        self.root.bind(
            "<KeyRelease-KP_Enter>", self._handle_action_enter_release
        )
        self.root.bind(_ESCAPE_BINDING, self._handle_escape_close)

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
            t("step.line", lineno=line.lineno, text=line.text),
            STATUS_BG_NEUTRAL,
        )
        self.root.update_idletasks()

    def _show_failed_result(self, result: RunResult) -> None:
        if result.status == "wrong":
            self._set_status(result.message or STATUS_WRONG, STATUS_BG_NEUTRAL)
        else:
            self._set_status(result.message, STATUS_BG_ERROR)

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
                operators_limit=self.operators_limit,
                custom_function_call_count=self.custom_function_call_count,
                if_limit=self.if_limit,
                while_limit=self.while_limit,
                required_keywords=self.required_keywords,
                banned_keywords=self.banned_keywords,
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
        self.root.mainloop()

    def close(self) -> None:
        if self.is_closed:
            return
        self._cancel_step_wake_only()
        self._cancel_pending_restore_enable_after()
        if self._help_window is not None:
            try:
                self._help_window.destroy()
            except tk.TclError:
                pass
            self._help_window = None
            self._help_window_close_handler = None
        if self._constraints_window is not None:
            try:
                self._constraints_window.destroy()
            except tk.TclError:
                pass
            self._constraints_window = None
            self._constraints_window_close_handler = None
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

    def _handle_escape_close(self, _event: tk.Event) -> str | None:
        """Close the robot window like the window manager close button."""
        self.close()
        return "break"

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

    def _focus_toplevel_dialog(self, win: tk.Toplevel) -> None:
        """Raise and focus a secondary dialog (main window may be ``-topmost``)."""
        win.lift()
        win.focus_set()

    def _show_step_button_in_controls(self) -> None:
        """Pack the step button to the right of the main action button and set enabled state."""
        if self.step_button is None:
            return
        if self.step_button not in self.controls_left.pack_slaves():
            self.step_button.pack(side=tk.LEFT, padx=(4, 0))
        if self.script_path is not None:
            self.step_button.configure(state=tk.NORMAL)
        else:
            self.step_button.configure(state=tk.DISABLED)

    def show_help(self) -> None:
        """Open or focus a window with module info, project link, and Robot command help."""
        if self.is_closed:
            return
        if self._help_window is not None:
            try:
                if self._help_window.winfo_exists():
                    self._focus_toplevel_dialog(self._help_window)
                    return
            except tk.TclError:
                pass
            self._help_window = None

        help_win = tk.Toplevel(self.root)
        self._help_window = help_win
        help_win.title(t("help.title"))
        help_win.transient(self.root)

        def _clear_help_ref() -> None:
            try:
                help_win.destroy()
            except tk.TclError:
                pass
            self._help_window = None
            self._help_window_close_handler = None

        self._help_window_close_handler = _clear_help_ref
        help_win.protocol("WM_DELETE_WINDOW", self._help_window_close_handler)

        def _handle_help_escape(_event: tk.Event) -> str | None:
            _clear_help_ref()
            return "break"

        help_win.bind(_ESCAPE_BINDING, _handle_help_escape)

        frame = tk.Frame(help_win, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(
            frame,
            wrap=tk.WORD,
            width=72,
            height=24,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        scroll = tk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        _populate_robot_help_text(text)
        self._focus_toplevel_dialog(help_win)

    def _constraints_body_lines(self) -> list[str]:
        lines: list[str] = []
        if self.operators_limit is not None:
            lines.append(
                t("constraints.operators_max", limit=self.operators_limit)
            )
        if self.custom_function_call_count is not None:
            lines.append(
                t(
                    "constraints.functions_min",
                    required=self.custom_function_call_count,
                )
            )
        if self.if_limit is not None:
            lines.append(t("constraints.if_max", limit=self.if_limit))
        if self.while_limit is not None:
            lines.append(t("constraints.while_max", limit=self.while_limit))
        if self.required_keywords:
            joined = ", ".join(self.required_keywords)
            lines.append(
                t("constraints.required_keywords", keywords=joined)
            )
        if self.banned_keywords:
            joined = ", ".join(self.banned_keywords)
            lines.append(
                t("constraints.banned_keywords", keywords=joined)
            )
        return lines

    def show_constraints(self) -> None:
        """Open or focus a window listing task limits that apply to this task."""
        if self.is_closed:
            return
        if self._constraints_window is not None:
            try:
                if self._constraints_window.winfo_exists():
                    self._focus_toplevel_dialog(self._constraints_window)
                    return
            except tk.TclError:
                pass
            self._constraints_window = None

        body_lines = self._constraints_body_lines()
        if not body_lines:
            return

        c_win = tk.Toplevel(self.root)
        self._constraints_window = c_win
        c_win.title(t("constraints.title"))
        c_win.transient(self.root)

        def _clear_constraints_ref() -> None:
            try:
                c_win.destroy()
            except tk.TclError:
                pass
            self._constraints_window = None
            self._constraints_window_close_handler = None

        self._constraints_window_close_handler = _clear_constraints_ref
        c_win.protocol("WM_DELETE_WINDOW", self._constraints_window_close_handler)

        def _handle_constraints_escape(_event: tk.Event) -> str | None:
            _clear_constraints_ref()
            return "break"

        c_win.bind(_ESCAPE_BINDING, _handle_constraints_escape)

        frame = tk.Frame(c_win, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(
            frame,
            wrap=tk.WORD,
            width=_CONSTRAINTS_TEXT_WIDTH,
            height=min(24, max(6, len(body_lines) + 2)),
            relief=tk.FLAT,
            highlightthickness=0,
        )
        scroll = tk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = "\n".join(body_lines).rstrip() + "\n"
        text.insert(tk.END, body)
        text.configure(state=tk.DISABLED)
        self._focus_toplevel_dialog(c_win)

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

    def _set_action_to_restore(
        self,
        *,
        disabled: bool,
        hide_step: bool,
        enable_after_idle: bool = False,
    ) -> None:
        """Main button becomes Restore; optionally hide Step and defer enabling after idle."""
        self._cancel_pending_restore_enable_after()
        if self.action_button is None:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RESTORE,
            command=self.restore,
            state=tk.DISABLED if disabled else tk.NORMAL,
        )
        if hide_step:
            self._hide_step_button_from_controls()
        if enable_after_idle:
            self._pending_restore_enable_after_id = self.root.after_idle(
                self._enable_action_button_if_current
            )

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

            self._set_status(STATUS_ALL_CORRECT, STATUS_BG_SUCCESS)
        finally:
            try:
                self._set_action_to_restore(
                    disabled=True, hide_step=True, enable_after_idle=True
                )
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
]
