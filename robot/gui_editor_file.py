"""File menu and open/save helpers for the environment editor."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

from .i18n import t
from .loader import TaskLoadError
from .task_serializer import (
    TASK_FILE_EXTENSION,
    EditorDocument,
    TaskSaveError,
    create_empty_document,
    is_bundled_task_path,
    load_task_file,
    persisted_snapshot_from_document,
    save_task_file,
    snapshots_equal,
)

_EDITOR_ERROR_TITLE_KEY = "editor.error.title"


class EditorFileMixin:
    """Open, save, and menu wiring for :class:`EditorWindow`."""

    root: tk.Tk
    is_closed: bool
    _chrome: object
    _state: object

    def close(self) -> None:
        """Close the editor window."""

    def undo(self) -> None:
        """Restore the previous editor snapshot."""

    def redo(self) -> None:
        """Reapply a snapshot that was undone."""

    def _window_title(self) -> str:
        """Return the editor window title."""

    def _refresh_all(self) -> None:
        """Refresh editor widgets after document changes."""

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label=t("editor.menu.new"),
            command=self._menu_new,
            accelerator="Ctrl+N",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=t("editor.menu.open"),
            command=self._menu_open,
            accelerator="Ctrl+O",
        )
        file_menu.add_command(
            label=t("editor.menu.save"),
            command=self._menu_save,
            accelerator="Ctrl+S",
        )
        file_menu.add_command(
            label=t("editor.menu.save_as"),
            command=self._menu_save_as,
            accelerator="Ctrl+Shift+S",
        )
        file_menu.add_separator()
        file_menu.add_command(label=t("editor.menu.exit"), command=self.close)
        menubar.add_cascade(label=t("editor.menu.file"), menu=file_menu)

        self._chrome.edit_menu = tk.Menu(menubar, tearoff=0)
        self._chrome.edit_menu.add_command(
            label=t("editor.menu.undo"),
            command=self.undo,
            accelerator="Ctrl+Z",
        )
        self._chrome.edit_menu.add_command(
            label=t("editor.menu.redo"),
            command=self.redo,
            accelerator="Ctrl+Y",
        )
        menubar.add_cascade(label=t("editor.menu.edit"), menu=self._chrome.edit_menu)
        self.root.config(menu=menubar)

        self.root.bind("<Control-n>", lambda _event: self._menu_new())
        self.root.bind("<Control-N>", lambda _event: self._menu_new())
        self.root.bind("<Control-o>", lambda _event: self._menu_open())
        self.root.bind("<Control-O>", lambda _event: self._menu_open())
        self.root.bind("<Control-s>", lambda _event: self._menu_save())
        self.root.bind("<Control-S>", lambda _event: self._menu_save())
        self.root.bind(
            "<Control-Shift-S>", lambda _event: self._menu_save_as()
        )
        self.root.bind(
            "<Control-Shift-s>", lambda _event: self._menu_save_as()
        )
        self.root.bind("<Control-z>", lambda _event: self.undo())
        self.root.bind("<Control-Z>", lambda _event: self.undo())
        self.root.bind("<Control-y>", lambda _event: self.redo())
        self.root.bind("<Control-Y>", lambda _event: self.redo())

    def _confirm_bundled_overwrite(self, path: Path) -> bool:
        if not is_bundled_task_path(path):
            return True
        return messagebox.askyesno(
            t("editor.confirm.overwrite_bundled_title"),
            t("editor.confirm.overwrite_bundled"),
            parent=self.root,
        )

    def _prompt_save_as_path(self) -> Optional[Path]:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t("editor.dialog.save_title"),
            defaultextension=TASK_FILE_EXTENSION,
            filetypes=[
                (t("editor.dialog.env_files"), f"*{TASK_FILE_EXTENSION}"),
                (t("editor.dialog.all_files"), "*.*"),
            ],
        )
        if not path:
            return None
        target = Path(path)
        if not self._confirm_bundled_overwrite(target):
            return None
        return target

    def _is_document_dirty(self) -> bool:
        current = persisted_snapshot_from_document(self._state.document)
        return not snapshots_equal(current, self._state.saved_snapshot)

    def _mark_document_saved(self) -> None:
        self._state.saved_snapshot = persisted_snapshot_from_document(
            self._state.document
        )

    def _confirm_discard_or_save_unsaved_changes(self) -> bool:
        """Return whether a pending navigation/close action may proceed."""
        if not self._is_document_dirty():
            return True
        choice = messagebox.askyesnocancel(
            t("editor.confirm.unsaved_title"),
            t("editor.confirm.unsaved"),
            parent=self.root,
        )
        if choice is None:
            return False
        if choice:
            return self._save_document_interactive()
        return True

    def _save_document_interactive(self) -> bool:
        """Save the current document, prompting for a path when needed."""
        if self.is_closed:
            return False
        if self._state.document.file_path is None:
            target = self._prompt_save_as_path()
            if target is None:
                return False
            return self._save_to_path(target)
        if not self._confirm_bundled_overwrite(self._state.document.file_path):
            return False
        return self._save_to_path(self._state.document.file_path)

    def _menu_new(self) -> None:
        if self.is_closed:
            return
        if not self._confirm_discard_or_save_unsaved_changes():
            return
        self._load_document(create_empty_document())

    def _menu_open(self) -> None:
        if self.is_closed:
            return
        if not self._confirm_discard_or_save_unsaved_changes():
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t("editor.dialog.open_title"),
            filetypes=[
                (t("editor.dialog.env_files"), f"*{TASK_FILE_EXTENSION}"),
                (t("editor.dialog.all_files"), "*.*"),
            ],
        )
        if not path:
            return
        try:
            document = load_task_file(Path(path))
        except (TaskLoadError, ValueError) as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root
            )
            return
        self._load_document(document)

    def _load_document(self, document: EditorDocument) -> None:
        self._state.document = document
        self._state.undo_stack.clear()
        self._state.redo_stack.clear()
        self._refresh_all()
        self._mark_document_saved()

    def _menu_save(self) -> None:
        if self.is_closed:
            return
        self._save_document_interactive()

    def _menu_save_as(self) -> None:
        if self.is_closed:
            return
        target = self._prompt_save_as_path()
        if target is None:
            return
        self._save_to_path(target)

    def _save_to_path(self, path: Path) -> bool:
        if self.is_closed:
            return False
        try:
            save_task_file(path, self._state.document)
        except ValueError as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root
            )
            return False
        except TaskSaveError as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root
            )
            return False
        self._mark_document_saved()
        self.root.title(self._window_title())
        return True
