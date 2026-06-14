"""Run, Step, and Reset toolbar controls for RobotWindow."""

from __future__ import annotations

from typing import Optional
import tkinter as tk

from .gui_theme import (
    ACTION_BUTTON_RESTORE,
    ACTION_BUTTON_RUN,
)


class ActionButtonMixin:
    """Run / Restore label and command transitions; step button pack visibility."""

    root: tk.Tk
    is_closed: bool
    action_button: Optional[tk.Button]
    step_button: tk.Button
    stop_button: tk.Button
    controls_left: tk.Frame
    script_path: Optional[object]
    _pending_restore_enable_after_id: Optional[str]

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

    def _hide_step_button_from_controls(self) -> None:
        """Hide the step button while the UI is in post-run restore mode."""
        if self.step_button is None:
            return
        self.step_button.pack_forget()

    def _show_stop_button_in_controls(self) -> None:
        """Pack the stop button to the right of the main action button and enable it."""
        if self.stop_button is None:
            return
        if self.stop_button not in self.controls_left.pack_slaves():
            self.stop_button.pack(side=tk.LEFT, padx=(4, 0))
        self.stop_button.configure(state=tk.NORMAL)

    def _hide_stop_button_from_controls(self) -> None:
        """Hide the stop button outside of Run mode."""
        if self.stop_button is None:
            return
        self.stop_button.pack_forget()

    def _set_action_to_run(self) -> None:
        self._cancel_pending_restore_enable_after()
        if self.action_button is None or self.is_closed:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RUN,
            command=self.run_all,
            state=tk.NORMAL,
        )
        self._hide_stop_button_from_controls()
        self._show_step_button_in_controls()

    def _set_action_to_running(self) -> None:
        """Main button becomes disabled Restore; Step hides and Stop becomes active."""
        self._cancel_pending_restore_enable_after()
        if self.action_button is None or self.is_closed:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RESTORE,
            command=self.restore,
            state=tk.DISABLED,
        )
        self._hide_step_button_from_controls()
        self._show_stop_button_in_controls()

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
        if self.action_button is None or self.is_closed:
            return
        self.action_button.configure(
            text=ACTION_BUTTON_RESTORE,
            command=self.restore,
            state=tk.DISABLED if disabled else tk.NORMAL,
        )
        self._hide_stop_button_from_controls()
        if hide_step:
            self._hide_step_button_from_controls()
        if enable_after_idle:
            self._pending_restore_enable_after_id = self.root.after_idle(
                self._enable_action_button_if_current
            )
