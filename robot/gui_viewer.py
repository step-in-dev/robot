"""Task browser toolbar and in-window task switching for teacher viewer mode."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gui_theme import BUTTON_PAD_X, BUTTON_PAD_Y
from .i18n import t
from .loader import RobotTask, TaskLoadError, load_task_definition
from .task_catalog import TaskCatalog, task_id_for_theme, task_number_from_id

_VIEWER_TOOLBAR_COMBO_STYLE = "Viewer.TCombobox"


def _widget_reqheight(widget: tk.Misc) -> int:
    widget.update_idletasks()
    return widget.winfo_reqheight()


def _configure_viewer_combobox_height(
    root: tk.Misc,
    combo: ttk.Combobox,
    *,
    target_height: int,
) -> None:
    style = ttk.Style(root)
    style.configure(_VIEWER_TOOLBAR_COMBO_STYLE, padding=0)
    combo.configure(style=_VIEWER_TOOLBAR_COMBO_STYLE)
    combo.update_idletasks()
    current = combo.winfo_reqheight()
    if current < target_height:
        pad = (target_height - current) // 2
        style.configure(_VIEWER_TOOLBAR_COMBO_STYLE, padding=(4, pad, 4, pad))


def _entry_pack_ipady(entry: tk.Entry, *, target_height: int) -> int:
    entry.update_idletasks()
    return max(0, (target_height - entry.winfo_reqheight()) // 2)


class ViewerMixin:
    """Theme dropdown and task navigation for ``RobotWindow`` viewer mode."""

    root: tk.Tk
    is_closed: bool
    task_id: str
    action_button: tk.Button | None
    step_button: tk.Button
    viewer_toolbar: tk.Frame | None
    _viewer_catalog: TaskCatalog | None
    _viewer_theme_var: tk.StringVar
    _viewer_number_var: tk.StringVar
    _viewer_last_valid_number: int
    _viewer_switching: bool
    _viewer_prev_button: tk.Button
    _viewer_next_button: tk.Button

    def _init_viewer_state(self, catalog: TaskCatalog) -> None:
        theme = catalog.current_theme_for_task(self.task_id) or catalog.themes[0]
        number = task_number_from_id(self.task_id)
        self._viewer_last_valid_number = number if number is not None else 1
        self._viewer_theme_var = tk.StringVar(value=theme)
        self._viewer_number_var = tk.StringVar(
            value=str(self._viewer_last_valid_number)
        )
        self._viewer_switching = False

    def _build_viewer_toolbar(self) -> None:
        catalog = self._viewer_catalog
        assert catalog is not None
        self.viewer_toolbar = tk.Frame(self.root)
        self.viewer_toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))

        self._viewer_prev_button = tk.Button(
            self.viewer_toolbar,
            text=t("viewer.previous"),
            command=lambda: self._viewer_show_relative(-1),
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        nav_height = _widget_reqheight(self._viewer_prev_button)

        theme_combo = ttk.Combobox(
            self.viewer_toolbar,
            textvariable=self._viewer_theme_var,
            values=list(catalog.themes),
            state="readonly",
            width=16,
        )
        _configure_viewer_combobox_height(
            self.root, theme_combo, target_height=nav_height
        )
        theme_combo.pack(side=tk.LEFT)
        theme_combo.bind("<<ComboboxSelected>>", self._on_viewer_theme_selected)

        self._viewer_prev_button.pack(side=tk.LEFT, padx=(8, 0))

        self._viewer_next_button = tk.Button(
            self.viewer_toolbar,
            text=t("viewer.next"),
            command=lambda: self._viewer_show_relative(1),
            padx=BUTTON_PAD_X,
            pady=BUTTON_PAD_Y,
        )
        self._viewer_next_button.pack(side=tk.LEFT, padx=(4, 0))

        number_entry = tk.Entry(
            self.viewer_toolbar,
            textvariable=self._viewer_number_var,
            width=5,
            justify=tk.CENTER,
        )
        number_entry.pack(
            side=tk.LEFT,
            padx=(8, 0),
            ipady=_entry_pack_ipady(number_entry, target_height=nav_height),
        )
        number_entry.bind("<Return>", self._on_viewer_number_commit)
        number_entry.bind("<KP_Enter>", self._on_viewer_number_commit)
        number_entry.bind("<FocusOut>", self._on_viewer_number_commit)
        self._viewer_update_nav_button_states()

    def _viewer_update_nav_button_states(self) -> None:
        catalog = self._viewer_catalog
        assert catalog is not None
        prefix = self._viewer_theme_var.get()
        task_ids = catalog.task_ids_for(prefix)
        if not task_ids:
            self._viewer_prev_button.configure(state=tk.DISABLED)
            self._viewer_next_button.configure(state=tk.DISABLED)
            return
        try:
            index = task_ids.index(self.task_id)
        except ValueError:
            self._viewer_prev_button.configure(state=tk.DISABLED)
            self._viewer_next_button.configure(state=tk.DISABLED)
            return
        prev_state = tk.NORMAL if index > 0 else tk.DISABLED
        next_state = tk.NORMAL if index < len(task_ids) - 1 else tk.DISABLED
        self._viewer_prev_button.configure(state=prev_state)
        self._viewer_next_button.configure(state=next_state)

    def _configure_viewer_execution_disabled(self) -> None:
        if self.action_button is not None:
            self.action_button.configure(state=tk.DISABLED)
        self.step_button.configure(state=tk.DISABLED)

    def _viewer_active_catalog(self) -> TaskCatalog | None:
        if self._viewer_switching or self.is_closed:
            return None
        return self._viewer_catalog

    def _on_viewer_theme_selected(self, _event: object = None) -> None:
        catalog = self._viewer_active_catalog()
        if catalog is None:
            return
        prefix = self._viewer_theme_var.get()
        first_id = catalog.first_task_id(prefix)
        if first_id is None:
            return
        self._viewer_show_task(first_id)

    def _viewer_show_relative(self, delta: int) -> None:
        catalog = self._viewer_active_catalog()
        if catalog is None:
            return
        prefix = self._viewer_theme_var.get()
        task_ids = catalog.task_ids_for(prefix)
        if not task_ids:
            return
        try:
            index = task_ids.index(self.task_id)
        except ValueError:
            self._viewer_show_task(task_ids[0])
            return
        target = index + delta
        if 0 <= target < len(task_ids):
            self._viewer_show_task(task_ids[target])

    def _on_viewer_number_commit(self, _event: object = None) -> str | None:
        catalog = self._viewer_active_catalog()
        if catalog is None:
            return None
        prefix = self._viewer_theme_var.get()
        raw = self._viewer_number_var.get().strip()
        try:
            number = int(raw)
        except ValueError:
            self._viewer_restore_number_field()
            return "break"
        candidate = task_id_for_theme(prefix, number)
        if candidate not in catalog.task_ids_for(prefix):
            self._viewer_restore_number_field()
            return "break"
        self._viewer_show_task(candidate)
        return "break"

    def _viewer_restore_number_field(self) -> None:
        self._viewer_number_var.set(str(self._viewer_last_valid_number))

    def _viewer_sync_navigation_widgets(self) -> None:
        catalog = self._viewer_catalog
        assert catalog is not None
        theme = catalog.current_theme_for_task(self.task_id)
        if theme is not None:
            self._viewer_theme_var.set(theme)
        number = task_number_from_id(self.task_id)
        if number is not None:
            self._viewer_last_valid_number = number
            self._viewer_number_var.set(str(number))
        self._viewer_update_nav_button_states()

    def _refresh_viewer_top_chrome(self) -> None:
        """Rebuild todo banner and env toolbar after a viewer task switch."""
        self._rebuild_todo_banner()
        self._rebuild_env_toolbar()

    def _viewer_show_task(self, task_id: str) -> None:
        if self.is_closed or task_id == self.task_id:
            return
        try:
            task_definition = load_task_definition(task_id)
        except TaskLoadError:
            self._viewer_restore_number_field()
            return
        self._viewer_switching = True
        try:
            self.apply_task_payload(task_id, task_definition)
            self._viewer_sync_navigation_widgets()
        finally:
            self._viewer_switching = False
