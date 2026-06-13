> Canonical English version. Russian translation: [task-editor.ru.md](task-editor.ru.md). Update the RU file manually whenever you change this document.

# Robot Environment Editor

The environment editor is a standalone desktop tool for creating and editing Robot task `.env` files.

## Launch

```bash
python editor/editor.py
```

The editor opens with a new empty environment (5×5 field, robot start at the top-left corner, goal at the bottom-right corner). Use the **File** menu to open an existing task file or save your work.

## Features

- Edit walls, painted cells, cells to paint, pollution values, and print targets by clicking the field.
- Switch between multiple environments in one task file.
- Resize the field, reset the current environment, add or remove environments.
- Edit the task condition (`todoText`) shown above the field.
- Undo and redo recent changes (Edit menu or toolbar buttons).
- Open, Save, and Save As via the **File** menu.
- Field size is limited to 20 columns by 15 rows; a task file may contain up to 7 environments.
- Saving over a bundled task under `robot/tasks/` asks for confirmation (both **Save** and **Save As**).

The editor preserves top-level solution-constraint fields (`operatorsLimit`, `customFunctionCallCount`, `ifLimit`, `whileLimit`, `requiredKeywords`, `bannedKeywords`) when loading and saving, but does not provide a UI to edit them.

## Keyboard shortcuts

- `Ctrl+O` — Open
- `Ctrl+S` — Save
- `Ctrl+Shift+S` — Save As
- `Ctrl+Z` — Undo
- `Ctrl+Y` — Redo

## Toolbar icons

Toolbar buttons use icon-only controls with hover tooltips (texts from `editor.tooltip.*` in locale JSON). The **File** and **Edit** menus keep text labels.

PNG icons live under `robot/assets/editor_icons/` (sources in `svg/`, 24×24 reference output in `png/`, runtime loads `png@2x/` downsampled to ~24×24). See [`robot/assets/editor_icons/SPEC.md`](../robot/assets/editor_icons/SPEC.md) for the inventory and regeneration command (`python tools/build_editor_icons.py`). Loading helpers are in `robot/editor_icons.py`; tooltips use `robot/gui_tooltip.py`.

## File format

Saved files use the same JSON `.env` format as bundled Robot tasks. See [task-env-format.md](task-env-format.md).
