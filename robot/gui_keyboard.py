"""Keyboard shortcut handling for RobotWindow."""

from __future__ import annotations

import tkinter as tk

_ESCAPE_BINDING = "<Escape>"


class KeyboardHandlerMixin:
    """Root-level Enter invokes the action button; Escape closes the window."""

    root: tk.Tk
    is_closed: bool
    action_button: tk.Button | None
    _ignore_action_enter_until_idle: bool
    _is_run_all_active: bool

    def bind_action_keyboard(self) -> None:
        """Bind Enter to the action button and Escape to close the window."""
        self.root.bind("<Return>", self._handle_action_enter_key)
        self.root.bind("<KP_Enter>", self._handle_action_enter_key)
        self.root.bind("<KeyRelease-Return>", self._handle_action_enter_release)
        self.root.bind(
            "<KeyRelease-KP_Enter>", self._handle_action_enter_release
        )
        self.root.bind(_ESCAPE_BINDING, self._handle_escape_close)

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
