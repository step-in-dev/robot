# Robot Environment Editor

The environment editor is a standalone desktop tool for creating and editing Robot task `.env` files.

## Launch

```bash
python editor/editor.py
```

The editor opens with a new empty environment (5×5 field, robot start at the top-left corner, goal at the bottom-right corner). Use **File → New Task** to start another empty task at any time, or use the **File** menu to open an existing task file or save your work.

## Features

- Edit walls, painted cells, cells to paint, pollution values, and print targets by clicking the field.
- Switch between multiple environments in one task file.
- Resize the field, reset the current environment, add or remove environments.
- Edit the task condition (`todoText`) shown above the field.
- `todoText` is saved as a plain string for new tasks and for files that already use a plain string. Localized files keep their dictionary shape; the editor shows the condition for the current UI language (or English as a fallback) and updates only that locale when you edit the condition.
- Edit solution constraints (`operatorsLimit`, `customFunctionCallCount`, `ifLimit`, `whileLimit`, `requiredKeywords`, `bannedKeywords`) via the toolbar constraints button (icon after the task-condition button).
- Undo and redo recent changes (Edit menu or toolbar buttons).
- New Task, Open, Save, and Save As via the **File** menu.
- Field size is limited to 25 columns by 16 rows; a task file may contain up to 7 environments.
- Saving over a bundled task under `robot/tasks/` asks for confirmation (both **Save** and **Save As**).

Constraint edits use the same validation rules as task loading. Empty fields remove the corresponding limit from the saved file.

## Keyboard shortcuts

- `Ctrl+N` — New Task
- `Ctrl+O` — Open
- `Ctrl+S` — Save
- `Ctrl+Shift+S` — Save As
- `Ctrl+Z` — Undo
- `Ctrl+Y` — Redo

## Toolbar icons

Toolbar buttons use icon-only controls with hover tooltips (texts from `editor.tooltip.*` in locale JSON). The **File** and **Edit** menus keep text labels.

PNG icons live under `robot/assets/editor_icons/` (sources in `svg/`, committed raster output in `png@2x/` at 48×48, displayed at ~24×24). See [editor-icons.md](editor-icons.md) for the inventory and regeneration command (`python tools/build_editor_icons.py`). Loading helpers are in `robot/editor_icons.py`; tooltips use `robot/gui_tooltip.py`.

## File format

Saved files use the same JSON `.env` format as bundled Robot tasks. See [task-env-format.md](task-env-format.md).
