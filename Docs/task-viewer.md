# Task Viewer (Teacher Browse Mode)

The task viewer is a separate launcher for teachers who need to browse task environments without running a student solution. It reuses the same `RobotWindow` as the student workflow, but opens in **viewer mode**: navigation toolbar, no script execution.

## Launching

From the repository root:

```bash
python viewer/viewer.py
```

The script adds the repo root to `sys.path`, builds a `TaskCatalog`, loads the first task of the first available theme, and opens `RobotWindow` with `viewer_catalog` set. If no `*.env` task files are found, it exits with code `1` and prints the localized `viewer.no_tasks` message.

The `viewer/` folder is included in release artifacts alongside `robot/` and `sample_solution.py`.

## Two `RobotWindow` Modes

| Mode | How it opens | Run / Step | Script |
|------|----------------|------------|--------|
| **Solution** (default) | `task()` / runtime with a student script | Enabled when a script path is present | Required for execution |
| **Viewer** | `viewer/viewer.py` or `RobotWindow(..., viewer_catalog=catalog)` | Always disabled | Not used (`run_env` and `script_path` are cleared) |

Viewer mode is selected by passing a non-`None` `viewer_catalog` to `RobotWindow`. Implementation is split between `robot/gui_viewer.py` (`ViewerMixin`: toolbar and navigation) and task switching via `apply_task_payload()` in `robot/gui.py`.

## Task Catalog

`robot/task_catalog.py` provides a read-only index shared by the viewer and help task lists (`command_help.py` uses the same ordering constants).

**Task directory** (same rules as `robot/loader.py`):

1. `ROBOT_TASKS_DIR` if set and the path is a directory.
2. Otherwise bundled `robot/tasks`.

**Grouping**: each `*.env` file stem is parsed as `{letter-prefix}{number}` (e.g. `intro8.env` → theme `intro`, number `8`). Files without a leading letter prefix are ignored for grouping.

**Theme order**:

1. Known prefixes from `KNOWN_TASK_GROUP_PREFIXES` in catalog order (`intro`, `fun`, `for`, `forfun`, `w`, `wfun`, `if`, `wif`, `ifelse`, `compound`) — only themes that actually have tasks.
2. Unknown prefixes appended alphabetically.

**Sorting within a theme**: natural numeric order on the trailing digits (`intro2` before `intro10`).

`TaskCatalog.discover()` returns frozen `themes` and `groups` used for navigation; individual tasks are still loaded through `load_task_definition()` from `robot/loader.py`.

## Viewer Toolbar and Navigation

When viewer mode is active, a toolbar is packed above the environment tabs and constraints button:

- **Theme** — read-only `ttk.Combobox` showing theme ids (`intro`, `fun`, `for`, …).
- **Previous / Next** — move within the current theme only (`viewer.previous`, `viewer.next` in locale JSON).
- **Task number** — entry field for the numeric suffix; commit on Enter or focus loss.

**Behavior**:

- Changing the theme loads the **first** task of that theme (by catalog order).
- Previous/Next walk the ordered task list for the current theme; out-of-range clicks do nothing.
- Manual number entry builds `{theme}{number}`; if that task id is missing, the field reverts to the last successfully shown number.
- On a successful switch, the window updates in place (no second `Tk` instance): `task_id`, window title, `todoText` banner, env tabs, constraints button, selected environment, field drawing, and limits metadata.
- **Run** and **Step** stay disabled for the lifetime of the window.

## Localization

Viewer-specific strings live under the `viewer.*` keys in `robot/locales/*.json`. Follow `Docs/localization-style.md` when adding or changing them.

## Tests

- `tests/test_task_catalog.py` — catalog discovery, theme order, `ROBOT_TASKS_DIR`, natural sort.
- `tests/test_viewer_launcher.py` — viewer entry script behavior.
- GUI viewer scenarios in `tests/test_gui.py` — disabled Run/Step, theme change, invalid number rollback, prev/next navigation.
