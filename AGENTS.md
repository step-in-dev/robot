# Project Overview

This project implements an educational Robot simulator for learning basic programming concepts. It lets students write Python solutions that control a robot on a grid, run those solutions against predefined task environments, and receive visual feedback through a desktop UI.

## Purpose

The main purpose is to provide a simple, school-friendly programming environment around the classic "Robot" simulator. Learners practice sequencing, loops, conditions, grid navigation, painting cells, reading cell values, and printing numbers while solving small algorithmic tasks.

## Target Audience

The target audience is school students who are learning introductory programming and algorithmic thinking. The public API is intentionally compact and approachable, with commands such as `move_right()`, `paint()`, `is_free_right()`, `pol()`, `printn()`, `task()`, and `field(width=8, height=6)`.

## Technology Stack

- Python 3.7+ with standard-library modules such as `dataclasses`, `pathlib`, `json`, and `unittest`.
- `tkinter` for the desktop graphical interface.
- JSON task files for grid environments and validation data.
- Built-in `unittest` tests for model, loader, and runtime behavior.

## Documentation

- `Docs/task-env-format.md` describes the `.env` task-file format loaded by `robot/loader.py` (canonical English).
- `Docs/task-env-format.ru.md` is the Russian translation; keep it in sync manually when the English doc changes.
- `Docs/task-viewer.md` describes the teacher task viewer (`viewer/viewer.py`) and viewer-mode behavior of `RobotWindow`.
- `Docs/task-editor.md` describes the environment editor (`editor/editor.py`) for creating and editing `.env` task files.
- `Docs/editor-icons.md` describes toolbar icon assets for the environment editor (`robot/assets/editor_icons/`).
- `Docs/localization-style.md` describes conventions for localized UI strings and task conditions (`todoText` in `.env` files). Read it when you change localization or add or edit task conditions.
- `Docs/linting.md` describes pylint usage.
- `Docs/website-screenshots.md` describes capturing PNGs for the static website (field canvas and full-window shots).
- `Docs/articles.md` describes the `articles/` directory layout, `meta.yaml`, and locale markdown files for site publishing.
- UI string catalogs are JSON files in `robot/locales/`.

## Website

The `website/` directory holds a static landing page for the Robot project: `index.html` (English), `index_ru.html` (Russian), shared `styles.css` and `script.js`, and images under `website/img/`.

Generated site HTML (`website/tasks/`, `website/articles/`, `website/commands*.html`, `website/sitemap.xml`) is **not** committed; it is listed in `.gitignore` and built on deploy by [`.github/workflows/static.yml`](.github/workflows/static.yml). Install build dependencies once (`python -m pip install -r requirements-build.txt`), then run `python tools/build_website_content.py` (same locally and in CI). Serve with `python -m http.server` in `website/` to preview task and article pages. Article sources live under `articles/`; see [`Docs/articles.md`](Docs/articles.md). Field PNGs under `website/img/tasks/` remain in the repository. For screenshot capture workflow, prerequisites, and batch commands, see [`Docs/website-screenshots.md`](Docs/website-screenshots.md).

## Architecture Overview

- `robot/model.py` contains the domain model: cells, valued cells, robot environments, wall handling, robot movement, painting, pollution values, printed numbers, and final-state validation.
- `robot/loader.py` loads task definitions from `.env` files (JSON body with `envDtos` array and optional `todoText` — follow `Docs/localization-style.md` when writing localized task conditions, optional `operatorsLimit` — counts robot commands plus calls to user-defined functions, optional `customFunctionCallCount`, optional `ifLimit`, optional `whileLimit`), either from `ROBOT_TASKS_DIR` or the bundled `robot/tasks` directory.
- `robot/results.py` defines run outcome types (`RunResult`, `RunStatus`) and final-state checking.
- `robot/runtime_state.py` holds shared mutable execution state (active environment, command delay) and small helpers (`begin_solution_run` / `end_solution_run`, `active_robot`, …) so the simulator and commands avoid ad-hoc global access.
- `robot/commands.py` implements the student-facing robot command functions (`move_*`, `paint`, probes, `pol`, `printn`).
- `robot/executor.py` compiles and runs student scripts against an environment and maps exceptions to `RunResult`; it defines `check_limit_violations` for static script-constraint checks (`operatorsLimit`, `customFunctionCallCount`, keyword limits).
- `robot/runtime.py` is a thin facade: `task()`, `field()`, compatibility re-exports, and script discovery; it wires loader, GUI, and simulator (including synthetic environments for `field()` without reading a task file).
- `robot/gui.py` provides the `tkinter` `RobotWindow` and re-exports layout/theme helpers for tests; `robot/gui_theme.py` and `robot/gui_layout.py` hold UI constants and pure geometry; `robot/field_renderer.py` draws the grid; `robot/status_strip.py` implements the status row (`Canvas`, optional hatched success background). The same window supports two modes: **solution mode** (opened from `task()` with a student script — Run/Step enabled; after a successful Run or step session, static script-constraint checks run on the student source) and **viewer mode** (opened via `viewer/viewer.py` with `viewer_catalog` — browse tasks by theme/number, Run/Step disabled). See `Docs/task-viewer.md`.
- `viewer/viewer.py` is the teacher-facing launcher for viewer mode; `robot/task_catalog.py` indexes tasks for browsing; `robot/gui_viewer.py` implements the viewer toolbar and in-window task switching.
- `editor/editor.py` is the environment editor launcher; `robot/gui_editor.py` provides the standalone editor window; `robot/task_serializer.py` and `robot/editor_env.py` handle `.env` round-trip and editing logic.
- `robot/__init__.py` re-exports the student-facing API for `from robot import *` usage.
- `tests/` at the repository root covers core model behavior, task loading, runtime execution, GUI behavior, and facade import compatibility (`tests/test_facade_imports.py`).

## Linting after code changes

After every code change, run pylint on the files you modified and fix **all new** linter findings before finishing the task.

- Production paths (`robot/`, `viewer/viewer.py`, `tools/`): `.venv/bin/python -m pylint --rcfile=lint/pylint-src.rc <changed-files>`
- Tests (`tests/`): `.venv/bin/python -m pylint --rcfile=lint/pylint-tests.rc <changed-files>`

Use the rcfile that matches the path. See `Docs/linting.md` for project conventions and existing suppressions.

Do **not** add `# pylint: disable=…`, `# noqa`, or rcfile `disable`/`enable` changes to silence warnings unless the user explicitly asks you to. Fix the code instead, or follow an already-documented exception in `Docs/linting.md`.

## Cursor Cloud specific instructions

This repo has no backend server or Docker stack. Development is Python stdlib + a local `.venv` (see `Docs/linting.md`).

### System packages (Ubuntu/Debian)

On a minimal Linux image, install once (not covered by the VM update script):

- `python3-tk` — required for the desktop UI and GUI tests
- `python3-venv` — required to create `.venv`
- `imagemagick` and `ghostscript` — optional; needed only for `tests/test_field_canvas_export.py` and screenshot tooling (`Docs/website-screenshots.md`)

`DISPLAY` must be set for interactive GUI and GUI tests (Cloud Agent VMs provide `:1`).

### Commands

Use the project venv after the update script runs:

| Task | Command |
|------|---------|
| Tests | `.venv/bin/python -m unittest discover -s tests -t .` |
| Lint (src) | `.venv/bin/python -m pylint --rcfile=lint/pylint-src.rc robot viewer/viewer.py tools` |
| Lint (tests) | `.venv/bin/python -m pylint --rcfile=lint/pylint-tests.rc tests` |
| Student app | `.venv/bin/python sample_solution.py` (opens tkinter window; calls `task("intro1")`) |
| Teacher viewer | `.venv/bin/python viewer/viewer.py` |
| Environment editor | `.venv/bin/python editor/editor.py` |
| Build website | `.venv/bin/python tools/build_website_content.py` |

There is no dev server to keep running. `sample_solution.py`, `viewer/viewer.py`, and `editor/editor.py` block on `mainloop()` until the window is closed.

