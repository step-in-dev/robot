"""Editable task-constraints dialog for the environment editor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import messagebox

from .gui_theme import DIALOG_BODY_FONT
from .i18n import t
from .task_serializer import (
    ConstraintFieldInput,
    constraint_field_display_values,
    parse_constraint_field_input,
)

_EDITOR_ERROR_TITLE_KEY = "editor.error.title"


@dataclass
class _ConstraintsDialogState:
    """Tracks the open constraints editor dialog for one editor window."""

    dialog: Optional[tk.Toplevel] = None


_CONSTRAINT_FIELD_SPECS = (
    ("operators_limit", "editor.constraints.field.operators_limit"),
    ("custom_function_call_count", "editor.constraints.field.custom_function_call_count"),
    ("if_limit", "editor.constraints.field.if_limit"),
    ("while_limit", "editor.constraints.field.while_limit"),
    ("required_keywords", "editor.constraints.field.required_keywords"),
    ("banned_keywords", "editor.constraints.field.banned_keywords"),
)


def _constraint_field_rows(
    parent: tk.Frame,
    display: Dict[str, str],
) -> Tuple[Tuple[tk.StringVar, ...], List[tk.Entry]]:
    variables: List[tk.StringVar] = []
    entries: List[tk.Entry] = []
    for row_index, (field_key, label_key) in enumerate(_CONSTRAINT_FIELD_SPECS):
        variable = tk.StringVar(parent, value=display[field_key])
        variables.append(variable)
        label = tk.Label(
            parent,
            text=t(label_key),
            font=DIALOG_BODY_FONT,
            anchor=tk.W,
            justify=tk.LEFT,
        )
        label.grid(row=row_index, column=0, sticky=tk.W, pady=(0, 6))
        entry = tk.Entry(parent, textvariable=variable, width=36, font=DIALOG_BODY_FONT)
        entry.grid(row=row_index, column=1, sticky=tk.EW, pady=(0, 6))
        entries.append(entry)
    parent.grid_columnconfigure(1, weight=1)
    return tuple(variables), entries


def _read_constraint_fields(variables: Tuple[tk.StringVar, ...]) -> ConstraintFieldInput:
    keys = [spec[0] for spec in _CONSTRAINT_FIELD_SPECS]
    values = {key: variable.get() for key, variable in zip(keys, variables)}
    return ConstraintFieldInput(**values)


def _pack_constraint_buttons(
    parent: tk.Frame,
    *,
    row: int,
    on_ok,
    on_cancel,
) -> None:
    button_row = tk.Frame(parent)
    button_row.grid(row=row, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))
    tk.Button(
        button_row,
        text=t("editor.constraints.ok"),
        width=10,
        command=on_ok,
    ).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(
        button_row,
        text=t("editor.constraints.cancel"),
        width=10,
        command=on_cancel,
    ).pack(side=tk.LEFT)


def prompt_edit_constraints(
    root: tk.Tk,
    preserved_fields: Dict[str, object],
    state: _ConstraintsDialogState,
) -> Optional[ConstraintFieldInput]:
    """Open the constraints editor dialog and return validated field input."""
    if state.dialog is not None:
        try:
            if state.dialog.winfo_exists():
                state.dialog.lift()
                state.dialog.focus_set()
                return None
        except tk.TclError:
            pass
        state.dialog = None

    display = constraint_field_display_values(preserved_fields)
    dialog = tk.Toplevel(root)
    dialog.withdraw()
    state.dialog = dialog
    dialog.title(t("editor.edit_constraints_title"))
    dialog.transient(root)
    dialog.resizable(False, False)

    result: Dict[str, Optional[ConstraintFieldInput]] = {"values": None}

    def _close_dialog() -> None:
        try:
            dialog.destroy()
        except tk.TclError:
            pass
        state.dialog = None

    frame = tk.Frame(dialog, padx=12, pady=12)
    frame.pack(fill=tk.BOTH, expand=True)

    variables, entries = _constraint_field_rows(frame, display)
    if entries:
        entries[0].focus_set()

    def _on_ok() -> None:
        fields = _read_constraint_fields(variables)
        try:
            parse_constraint_field_input(fields)
        except ValueError as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=dialog
            )
            return
        result["values"] = fields
        _close_dialog()

    def _on_cancel() -> None:
        _close_dialog()

    dialog.protocol("WM_DELETE_WINDOW", _on_cancel)

    def _handle_escape(_event: tk.Event) -> str:
        _on_cancel()
        return "break"

    dialog.bind("<Escape>", _handle_escape)

    _pack_constraint_buttons(
        frame,
        row=len(entries),
        on_ok=_on_ok,
        on_cancel=_on_cancel,
    )

    dialog.update_idletasks()
    dialog.deiconify()
    dialog.lift()
    dialog.focus_set()
    dialog.grab_set()
    dialog.wait_window()
    return result["values"]
