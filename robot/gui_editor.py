"""Tkinter window for editing Robot task environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from ._version import __version__
from .editor_env import (
    MAX_FIELD_HEIGHT,
    MAX_FIELD_WIDTH,
    POLLUTION_VALUE_MAX,
    POLLUTION_VALUE_MIN,
    PRINT_VALUE_MAX,
    PRINT_VALUE_MIN,
    CanvasHitContext,
    EnvEditTool,
    add_environment,
    apply_tool_to_env,
    can_add_environment,
    can_remove_environment,
    canvas_to_cell,
    dto_dict_to_env,
    remove_environment,
    reset_env_dto,
    resize_env_dto,
    toggle_wall,
)
from .editor_icons import action_icon, load_editor_icon_images, tool_icon
from .field_renderer import DEFAULT_FIELD_COLORS, FieldRenderer
from .gui_layout import (
    calculate_canvas_size,
    calculate_cell_size,
    calculate_field_offset,
)
from .gui_theme import (
    DIALOG_BODY_FONT,
    ENV_SELECT_BUTTON_PAD_X,
    ENV_SELECT_BUTTON_PAD_Y,
    ICON_BUTTON_PAD_X,
    ICON_BUTTON_PAD_Y,
    MIN_EDITOR_WINDOW_WIDTH,
    TODO_TEXT_BG,
    TODO_TEXT_BORDER,
)
from .gui_tooltip import bind_tooltip
from .i18n import t
from .loader import TaskLoadError, resolve_todo_text
from .model import RobotEnv
from .task_serializer import (
    TASK_FILE_EXTENSION,
    EditorDocument,
    apply_snapshot,
    create_empty_document,
    is_bundled_task_path,
    load_task_file,
    save_task_file,
    snapshot_from_document,
    snapshots_equal,
    TaskSaveError,
    update_todo_text,
)
from .tk_util import destroy_tk_root, pack_ipady_for_target_height, widget_reqheight

_UNDO_DEPTH = 200
_WALL_WIDTH = 4
_EDITOR_ERROR_TITLE_KEY = "editor.error.title"


@dataclass
class _EditorState:
    """Mutable editor document, history, and active tool."""

    document: EditorDocument
    undo_stack: List[dict] = field(default_factory=list)
    redo_stack: List[dict] = field(default_factory=list)
    active_tool: EnvEditTool = EnvEditTool.START


@dataclass
class _EditorLayout:
    """Canvas geometry derived from the current environments."""

    envs: List[RobotEnv] = field(default_factory=list)
    cell_size: int = 0
    canvas_width: int = 0
    canvas_height: int = 0


@dataclass
class _EditorChrome:  # pylint: disable=too-many-instance-attributes
    """Tk widgets owned by the editor window."""

    todo_frame: Optional[tk.Frame] = None
    todo_label: Optional[tk.Label] = None
    todo_section: Optional[tk.Frame] = None
    todo_edit_button: Optional[tk.Button] = None
    task_toolbar: Optional[tk.Frame] = None
    env_tabs_bar: Optional[tk.Frame] = None
    tab_frame: Optional[tk.Frame] = None
    edit_menu: Optional[tk.Menu] = None
    undo_button: Optional[tk.Button] = None
    redo_button: Optional[tk.Button] = None
    add_env_button: Optional[tk.Button] = None
    remove_env_button: Optional[tk.Button] = None
    pollution_spin: Optional[tk.Spinbox] = None
    print_spin: Optional[tk.Spinbox] = None
    height_spin: Optional[tk.Spinbox] = None
    width_spin: Optional[tk.Spinbox] = None
    toolbar_icon_height: int = 0
    canvas: Optional[tk.Canvas] = None
    renderer: Optional[FieldRenderer] = None
    tool_buttons: dict = field(default_factory=dict)
    tab_buttons: List[tk.Button] = field(default_factory=list)


@dataclass
class _EditorVars:
    """Tk variables bound to editor controls."""

    pollution_value: tk.IntVar
    print_value: tk.IntVar
    width_var: tk.IntVar
    height_var: tk.IntVar


class EditorWindow:
    """Standalone environment editor window."""

    def __init__(self, document: Optional[EditorDocument] = None) -> None:
        initial_document = document or create_empty_document()
        self._state = _EditorState(document=initial_document)
        self._layout = _EditorLayout()
        self._chrome = _EditorChrome()
        self._is_closed = False

        self.root = tk.Tk()
        self.root.withdraw()
        self._icon_images = load_editor_icon_images(self.root)
        self._vars = _EditorVars(
            pollution_value=tk.IntVar(self.root, value=1),
            print_value=tk.IntVar(self.root, value=0),
            width_var=tk.IntVar(self.root, value=initial_document.env_dtos[0]["width"]),
            height_var=tk.IntVar(self.root, value=initial_document.env_dtos[0]["height"]),
        )
        self.root.title(self._window_title())
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_menu()
        self._build_task_toolbar()
        self._build_todo_section()
        self._build_env_tabs()
        self._build_canvas()
        self._refresh_all()

        self.root.update_idletasks()
        self._lock_window_size()
        self.root.deiconify()
        self.root.lift()

    @property
    def is_closed(self) -> bool:
        """Return whether the editor window has been closed."""
        return self._is_closed

    @property
    def document(self) -> EditorDocument:
        """Return the in-memory task document."""
        return self._state.document

    def run(self) -> None:
        """Start the Tk event loop."""
        if not self.is_closed:
            self.root.mainloop()

    def close(self) -> None:
        """Close the editor window."""
        if self.is_closed:
            return
        self._is_closed = True
        destroy_tk_root(self.root)

    def _window_title(self) -> str:
        if self._state.document.file_path is None:
            return t("editor.window.title_new", version=__version__)
        return t(
            "editor.window.title_file",
            version=__version__,
            filename=self._state.document.file_path.name,
        )

    def _current_env_dict(self) -> dict:
        return self._state.document.env_dtos[self._state.document.selected_env_index]

    def _build_env_previews(self) -> List[RobotEnv]:
        return [dto_dict_to_env(env) for env in self._state.document.env_dtos]

    def _current_env_preview(self) -> RobotEnv:
        return self._layout.envs[self._state.document.selected_env_index]

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
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

    def _icon_button(
        self,
        parent: tk.Misc,
        *,
        image: tk.PhotoImage,
        command,
        tooltip_key: str,
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text="",
            image=image,
            compound=tk.CENTER,
            command=command,
            padx=ICON_BUTTON_PAD_X,
            pady=ICON_BUTTON_PAD_Y,
        )
        bind_tooltip(button, t(tooltip_key))
        return button

    @staticmethod
    def _tool_tooltip_key(tool: EnvEditTool) -> str:
        return f"editor.tooltip.tool.{tool.value}"

    @staticmethod
    def _require_icon(image: Optional[tk.PhotoImage], icon_name: str) -> tk.PhotoImage:
        if image is None:
            raise RuntimeError(f"Missing editor icon: {icon_name}")
        return image

    def _build_todo_section(self) -> None:
        self._chrome.todo_section = tk.Frame(self.root)

    def _rebuild_todo_banner(self) -> None:
        if self._chrome.todo_frame is not None:
            self._chrome.todo_frame.destroy()
            self._chrome.todo_frame = None
            self._chrome.todo_label = None

        if self._chrome.todo_section is not None:
            self._chrome.todo_section.pack_forget()

        display_text = resolve_todo_text(self._state.document.todo_text)
        if not display_text:
            return

        self._chrome.todo_section.pack(
            side=tk.TOP,
            fill=tk.X,
            padx=6,
            pady=(2, 2),
            before=self._chrome.env_tabs_bar,
        )
        self._chrome.todo_frame = tk.Frame(
            self._chrome.todo_section,
            bg=TODO_TEXT_BORDER,
            bd=0,
            highlightthickness=0,
        )
        self._chrome.todo_label = tk.Label(
            self._chrome.todo_frame,
            text=display_text,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=max(self._layout.canvas_width, 320),
            font=DIALOG_BODY_FONT,
            bg=TODO_TEXT_BG,
            fg="#000000",
            padx=8,
            pady=6,
            bd=0,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self._chrome.todo_label.pack(side=tk.TOP, fill=tk.X, padx=1, pady=1)
        self._chrome.todo_frame.pack(side=tk.TOP, fill=tk.X)

    def _build_env_tabs(self) -> None:
        self._chrome.env_tabs_bar = tk.Frame(self.root)
        self._chrome.env_tabs_bar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(2, 2))
        self._chrome.tab_frame = tk.Frame(self._chrome.env_tabs_bar)
        self._chrome.tab_frame.pack(side=tk.LEFT)

    def _build_task_toolbar(self) -> None:
        self._chrome.task_toolbar = tk.Frame(self.root)
        self._chrome.task_toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 2))
        toolbar = self._chrome.task_toolbar
        group_padx = (12, 0)

        for tool in EnvEditTool:
            button = self._icon_button(
                toolbar,
                image=self._require_icon(tool_icon(self._icon_images, tool), tool.value),
                command=lambda selected=tool: self._select_tool(selected),
                tooltip_key=self._tool_tooltip_key(tool),
            )
            button.pack(side=tk.LEFT, padx=(0, 4))
            self._chrome.tool_buttons[tool] = button

            if tool is EnvEditTool.POLLUTION:
                self._chrome.pollution_spin = tk.Spinbox(
                    toolbar,
                    from_=POLLUTION_VALUE_MIN,
                    to=POLLUTION_VALUE_MAX,
                    width=4,
                    textvariable=self._vars.pollution_value,
                )
                bind_tooltip(
                    self._chrome.pollution_spin, t("editor.tooltip.pollution_value")
                )

            if tool is EnvEditTool.NUMBER:
                self._chrome.print_spin = tk.Spinbox(
                    toolbar,
                    from_=PRINT_VALUE_MIN,
                    to=PRINT_VALUE_MAX,
                    width=4,
                    textvariable=self._vars.print_value,
                )
                bind_tooltip(self._chrome.print_spin, t("editor.tooltip.print_value"))

        first_tool_button = self._chrome.tool_buttons[EnvEditTool.START]
        self._chrome.toolbar_icon_height = widget_reqheight(first_tool_button)

        self._chrome.add_env_button = self._icon_button(
            toolbar,
            image=self._require_icon(action_icon(self._icon_images, "add_env"), "add_env"),
            command=self._add_environment,
            tooltip_key="editor.tooltip.add_env",
        )
        self._chrome.add_env_button.pack(side=tk.LEFT, padx=group_padx)
        self._chrome.remove_env_button = self._icon_button(
            toolbar,
            image=self._require_icon(
                action_icon(self._icon_images, "remove_env"), "remove_env"
            ),
            command=self._remove_environment,
            tooltip_key="editor.tooltip.remove_env",
        )
        self._chrome.remove_env_button.pack(side=tk.LEFT, padx=(4, 0))
        reset_env_button = self._icon_button(
            toolbar,
            image=self._require_icon(
                action_icon(self._icon_images, "reset_env"), "reset_env"
            ),
            command=self._reset_environment,
            tooltip_key="editor.tooltip.reset_env",
        )
        reset_env_button.pack(side=tk.LEFT, padx=(4, 0))

        size_frame = tk.Frame(toolbar)
        size_frame.pack(side=tk.LEFT, padx=group_padx)
        tk.Label(size_frame, text=t("editor.rows")).pack(side=tk.LEFT)
        icon_height = self._chrome.toolbar_icon_height
        self._chrome.height_spin = tk.Spinbox(
            size_frame,
            from_=1,
            to=MAX_FIELD_HEIGHT,
            width=3,
            textvariable=self._vars.height_var,
            command=self._on_size_commit,
        )
        self._chrome.height_spin.pack(
            side=tk.LEFT,
            padx=(4, 8),
            ipady=pack_ipady_for_target_height(
                self._chrome.height_spin, target_height=icon_height
            ),
        )
        self._chrome.height_spin.bind("<Return>", self._on_size_commit)
        self._chrome.height_spin.bind("<FocusOut>", self._on_size_commit)
        bind_tooltip(self._chrome.height_spin, t("editor.tooltip.row_count"))
        tk.Label(size_frame, text=t("editor.cols")).pack(side=tk.LEFT)
        self._chrome.width_spin = tk.Spinbox(
            size_frame,
            from_=1,
            to=MAX_FIELD_WIDTH,
            width=3,
            textvariable=self._vars.width_var,
            command=self._on_size_commit,
        )
        self._chrome.width_spin.pack(
            side=tk.LEFT,
            padx=(4, 0),
            ipady=pack_ipady_for_target_height(
                self._chrome.width_spin, target_height=icon_height
            ),
        )
        self._chrome.width_spin.bind("<Return>", self._on_size_commit)
        self._chrome.width_spin.bind("<FocusOut>", self._on_size_commit)
        bind_tooltip(self._chrome.width_spin, t("editor.tooltip.col_count"))

        self._chrome.todo_edit_button = self._icon_button(
            toolbar,
            image=self._require_icon(action_icon(self._icon_images, "todo"), "todo"),
            command=self._edit_todo_text,
            tooltip_key="editor.tooltip.todo",
        )
        self._chrome.todo_edit_button.pack(side=tk.LEFT, padx=(8, 0))

        self._chrome.undo_button = self._icon_button(
            toolbar,
            image=self._require_icon(action_icon(self._icon_images, "undo"), "undo"),
            command=self.undo,
            tooltip_key="editor.tooltip.undo",
        )
        self._chrome.undo_button.pack(side=tk.LEFT, padx=group_padx)
        self._chrome.redo_button = self._icon_button(
            toolbar,
            image=self._require_icon(action_icon(self._icon_images, "redo"), "redo"),
            command=self.redo,
            tooltip_key="editor.tooltip.redo",
        )
        self._chrome.redo_button.pack(side=tk.LEFT, padx=(4, 0))

        self._update_tool_highlight()
        self._update_value_spinners()

    def _rebuild_env_tabs(self) -> None:
        if self._chrome.tab_frame is None:
            return
        for button in self._chrome.tab_buttons:
            button.destroy()
        self._chrome.tab_buttons = []
        for index in range(len(self._state.document.env_dtos)):
            button = tk.Button(
                self._chrome.tab_frame,
                text=str(index + 1),
                command=lambda idx=index: self._select_env(idx),
                width=1,
                padx=ENV_SELECT_BUTTON_PAD_X,
                pady=ENV_SELECT_BUTTON_PAD_Y,
            )
            button.pack(side=tk.LEFT)
            self._chrome.tab_buttons.append(button)
        self._update_tab_highlight()

    def _update_tab_highlight(self) -> None:
        for index, button in enumerate(self._chrome.tab_buttons):
            if index == self._state.document.selected_env_index:
                button.configure(relief=tk.SUNKEN)
            else:
                button.configure(relief=tk.RAISED)

    def _build_canvas(self) -> None:
        self._chrome.canvas = tk.Canvas(
            self.root,
            width=self._layout.canvas_width,
            height=self._layout.canvas_height,
            highlightthickness=0,
        )
        self._chrome.canvas.pack(side=tk.TOP, padx=6, pady=(2, 6))
        self._chrome.renderer = FieldRenderer(
            self._chrome.canvas, self._layout.cell_size, _WALL_WIDTH
        )
        self._chrome.canvas.bind("<Button-1>", self._on_canvas_click)

    def _refresh_all(self) -> None:
        self._layout.envs = self._build_env_previews()
        self._layout.cell_size = calculate_cell_size(self._layout.envs)
        self._layout.canvas_width, self._layout.canvas_height = calculate_canvas_size(
            self._layout.envs, self._layout.cell_size, _WALL_WIDTH
        )
        self._chrome.canvas.configure(
            width=self._layout.canvas_width, height=self._layout.canvas_height
        )
        self._chrome.renderer.set_dimensions(self._layout.cell_size, _WALL_WIDTH)
        self._vars.width_var.set(self._current_env_dict()["width"])
        self._vars.height_var.set(self._current_env_dict()["height"])
        self.root.title(self._window_title())
        self._rebuild_todo_banner()
        self._rebuild_env_tabs()
        self._update_tool_highlight()
        self._update_value_spinners()
        self._update_undo_redo_state()
        self._update_env_action_buttons_state()
        self.draw_field()
        if self._chrome.todo_label is not None:
            self._chrome.todo_label.configure(
                wraplength=max(self._layout.canvas_width, 320)
            )
        self.root.update_idletasks()
        self._lock_window_size()

    def _refresh_after_env_edit(self) -> None:
        """Redraw the field after an in-place environment change."""
        self._layout.envs = self._build_env_previews()
        self.draw_field()

    def draw_field(self) -> None:
        """Redraw the current environment on the canvas."""
        if self.is_closed:
            return
        self._chrome.renderer.draw_field(
            self._current_env_preview(),
            self._layout.canvas_width,
            self._layout.canvas_height,
            DEFAULT_FIELD_COLORS,
        )

    def _lock_window_size(self) -> None:
        self.root.update_idletasks()
        width = max(self.root.winfo_reqwidth(), MIN_EDITOR_WINDOW_WIDTH)
        height = self.root.winfo_reqheight()
        if width > 1 and height > 1:
            self.root.wm_geometry(f"{width}x{height}")

    def _select_tool(self, tool: EnvEditTool) -> None:
        self._state.active_tool = tool
        self._update_tool_highlight()
        self._update_value_spinners()

    def _update_tool_highlight(self) -> None:
        for tool, button in self._chrome.tool_buttons.items():
            if tool is self._state.active_tool:
                button.configure(relief=tk.SUNKEN)
            else:
                button.configure(relief=tk.RAISED)

    def _update_value_spinners(self) -> None:
        if self._chrome.pollution_spin is None or self._chrome.print_spin is None:
            return
        pollution_button = self._chrome.tool_buttons[EnvEditTool.POLLUTION]
        number_button = self._chrome.tool_buttons[EnvEditTool.NUMBER]
        self._chrome.pollution_spin.pack_forget()
        self._chrome.print_spin.pack_forget()
        if self._state.active_tool is EnvEditTool.POLLUTION:
            self._chrome.pollution_spin.pack(
                side=tk.LEFT,
                padx=(0, 4),
                after=pollution_button,
                ipady=pack_ipady_for_target_height(
                    self._chrome.pollution_spin,
                    target_height=self._chrome.toolbar_icon_height,
                ),
            )
        elif self._state.active_tool is EnvEditTool.NUMBER:
            self._chrome.print_spin.pack(
                side=tk.LEFT,
                padx=(0, 4),
                after=number_button,
                ipady=pack_ipady_for_target_height(
                    self._chrome.print_spin,
                    target_height=self._chrome.toolbar_icon_height,
                ),
            )
        self._lock_window_size()

    def _update_undo_redo_state(self) -> None:
        undo_state = tk.NORMAL if self._state.undo_stack else tk.DISABLED
        redo_state = tk.NORMAL if self._state.redo_stack else tk.DISABLED
        self._chrome.undo_button.configure(state=undo_state)
        self._chrome.redo_button.configure(state=redo_state)
        if self._chrome.edit_menu is not None:
            self._chrome.edit_menu.entryconfigure(0, state=undo_state)
            self._chrome.edit_menu.entryconfigure(1, state=redo_state)

    def _update_env_action_buttons_state(self) -> None:
        env_dtos = self._state.document.env_dtos
        self._chrome.add_env_button.configure(
            state=tk.NORMAL if can_add_environment(env_dtos) else tk.DISABLED
        )
        self._chrome.remove_env_button.configure(
            state=tk.NORMAL if can_remove_environment(env_dtos) else tk.DISABLED
        )

    def _push_undo_snapshot(self) -> None:
        snapshot = snapshot_from_document(self._state.document)
        if self._state.undo_stack and snapshots_equal(self._state.undo_stack[-1], snapshot):
            return
        self._state.undo_stack.append(snapshot)
        if len(self._state.undo_stack) > _UNDO_DEPTH:
            self._state.undo_stack.pop(0)
        self._state.redo_stack.clear()
        self._update_undo_redo_state()

    def _mutate(self, mutator, *, full_refresh: bool = True) -> None:
        self._push_undo_snapshot()
        try:
            mutator()
        except ValueError as exc:
            self._state.undo_stack.pop()
            self._update_undo_redo_state()
            messagebox.showerror(t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root)
            return
        if full_refresh:
            self._refresh_all()
        else:
            self._refresh_after_env_edit()

    def undo(self) -> None:
        """Restore the previous editor snapshot."""
        if not self._state.undo_stack or self.is_closed:
            return
        current = snapshot_from_document(self._state.document)
        snapshot = self._state.undo_stack.pop()
        self._state.redo_stack.append(current)
        apply_snapshot(self._state.document, snapshot)
        self._refresh_all()

    def redo(self) -> None:
        """Reapply a snapshot that was undone."""
        if not self._state.redo_stack or self.is_closed:
            return
        current = snapshot_from_document(self._state.document)
        snapshot = self._state.redo_stack.pop()
        self._state.undo_stack.append(current)
        apply_snapshot(self._state.document, snapshot)
        self._refresh_all()

    def _select_env(self, index: int) -> None:
        if index == self._state.document.selected_env_index:
            return

        def switch() -> None:
            self._state.document.selected_env_index = index

        self._mutate(switch)

    def _add_environment(self) -> None:
        if not can_add_environment(self._state.document.env_dtos):
            return

        def add() -> None:
            self._state.document.env_dtos = add_environment(self._state.document.env_dtos)
            self._state.document.selected_env_index = len(self._state.document.env_dtos) - 1

        self._mutate(add)

    def _remove_environment(self) -> None:
        if not can_remove_environment(self._state.document.env_dtos):
            return

        index = self._state.document.selected_env_index

        def remove() -> None:
            self._state.document.env_dtos = remove_environment(
                self._state.document.env_dtos, index
            )
            if self._state.document.selected_env_index >= len(self._state.document.env_dtos):
                self._state.document.selected_env_index = len(self._state.document.env_dtos) - 1

        self._mutate(remove)

    def _reset_environment(self) -> None:
        index = self._state.document.selected_env_index

        def reset() -> None:
            self._state.document.env_dtos[index] = reset_env_dto(
                self._state.document.env_dtos[index]
            )

        self._mutate(reset)

    def _on_size_commit(self, _event: object = None) -> None:
        try:
            width = int(self._vars.width_var.get())
            height = int(self._vars.height_var.get())
        except (tk.TclError, ValueError):
            self._vars.width_var.set(self._current_env_dict()["width"])
            self._vars.height_var.set(self._current_env_dict()["height"])
            return
        if (
            width == self._current_env_dict()["width"]
            and height == self._current_env_dict()["height"]
        ):
            return
        index = self._state.document.selected_env_index

        def resize() -> None:
            self._state.document.env_dtos[index] = resize_env_dto(
                self._state.document.env_dtos[index], width=width, height=height
            )

        self._mutate(resize)

    def _edit_todo_text(self) -> None:
        current = resolve_todo_text(self._state.document.todo_text)
        new_text = simpledialog.askstring(
            t("editor.edit_todo_title"),
            t("editor.edit_todo_prompt"),
            initialvalue=current,
            parent=self.root,
        )
        if new_text is None:
            return

        def edit() -> None:
            self._state.document.todo_text = update_todo_text(
                self._state.document.todo_text, new_text
            )

        self._mutate(edit)

    def _on_canvas_click(self, event: tk.Event) -> None:
        env = self._current_env_dict()
        half_wall = _WALL_WIDTH // 2
        offset_x, offset_y = calculate_field_offset(
            self._layout.canvas_width,
            self._layout.canvas_height,
            self._current_env_preview(),
            self._layout.cell_size,
            _WALL_WIDTH,
        )
        cell, wall = canvas_to_cell(
            event.x,
            event.y,
            context=CanvasHitContext(
                offset_x=offset_x,
                offset_y=offset_y,
                half_wall_width=half_wall,
                cell_size=self._layout.cell_size,
                width=env["width"],
                height=env["height"],
            ),
        )
        if cell is None:
            return
        if self._state.active_tool is EnvEditTool.WALL and wall is None:
            return
        index = self._state.document.selected_env_index
        tool = self._state.active_tool

        def apply_click() -> None:
            if tool is EnvEditTool.WALL:
                assert wall is not None
                self._state.document.env_dtos[index] = toggle_wall(
                    self._state.document.env_dtos[index], wall[0], wall[1]
                )
            else:
                self._state.document.env_dtos[index] = apply_tool_to_env(
                    self._state.document.env_dtos[index],
                    tool,
                    cell,
                    pollution_value=self._vars.pollution_value.get(),
                    print_value=self._vars.print_value.get(),
                )

        self._mutate(apply_click, full_refresh=False)

    def _confirm_bundled_overwrite(self, path: Path) -> bool:
        if not is_bundled_task_path(path):
            return True
        return messagebox.askyesno(
            t("editor.confirm.overwrite_bundled_title"),
            t("editor.confirm.overwrite_bundled"),
            parent=self.root,
        )

    def _menu_open(self) -> None:
        if self.is_closed:
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

    def _menu_save(self) -> None:
        if self.is_closed:
            return
        if self._state.document.file_path is None:
            self._menu_save_as()
            return
        if not self._confirm_bundled_overwrite(self._state.document.file_path):
            return
        self._save_to_path(self._state.document.file_path)

    def _menu_save_as(self) -> None:
        if self.is_closed:
            return
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
            return
        target = Path(path)
        if not self._confirm_bundled_overwrite(target):
            return
        self._save_to_path(target)

    def _save_to_path(self, path: Path) -> None:
        if self.is_closed:
            return
        try:
            save_task_file(path, self._state.document)
        except ValueError as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root
            )
            return
        except TaskSaveError as exc:
            messagebox.showerror(
                t(_EDITOR_ERROR_TITLE_KEY), str(exc), parent=self.root
            )
            return
        self.root.title(self._window_title())
