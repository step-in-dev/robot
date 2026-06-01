# Project Overview

This project implements an educational Robot simulator for learning basic programming concepts. It lets students write Python solutions that control a robot on a grid, run those solutions against predefined task environments, and receive visual feedback through a desktop UI.

## Purpose

The main purpose is to provide a simple, school-friendly programming environment around the classic "Robot" executor. Learners practice sequencing, loops, conditions, grid navigation, painting cells, reading cell values, and printing numbers while solving small algorithmic tasks.

## Target Audience

The target audience is school students who are learning introductory programming and algorithmic thinking. The public API is intentionally compact and approachable, with commands such as `move_right()`, `paint()`, `is_free_right()`, `pol()`, `printn()`, `task()`, and `field(width=8, height=6)`.

## Technology Stack

- Python 3.7+ with standard-library modules such as `dataclasses`, `pathlib`, `json`, and `unittest`.
- `tkinter` for the desktop graphical interface.
- JSON task files for grid environments and validation data.
- Built-in `unittest` tests for model, loader, and runtime behavior.

## Documentation

- `Docs/task-env-format.md` describes the `.env` task-file format loaded by `robot/loader.py`.
- `Docs/task-viewer.md` describes the teacher task viewer (`viewer/viewer.py`) and viewer-mode behavior of `RobotWindow`.
- `Docs/localization-style.md` describes conventions for localized UI strings. Read it when you need to change localization.
- `Docs/linting.md` describes pylint usage.
- `Docs/website-screenshots.md` describes capturing PNGs for the static website (field canvas and full-window shots).
- UI string catalogs are JSON files in `robot/locales/`.

## Website

The `website/` directory holds a static landing page for the Robot project: `index.html` (English), `index_ru.html` (Russian), shared `styles.css` and `script.js`, and images under `website/img/`.

The task catalog HTML (`website/tasks/`, `website/commands*.html`, `website/sitemap.xml`) is **not** committed; it is listed in `.gitignore` and built on deploy by [`.github/workflows/static.yml`](.github/workflows/static.yml) via `python tools/build_website_content.py`. Run the same command locally before browsing task pages with `python -m http.server` in `website/`. Field PNGs under `website/img/tasks/` remain in the repository. For screenshot capture workflow, prerequisites, and batch commands, see [`Docs/website-screenshots.md`](Docs/website-screenshots.md).

## Architecture Overview

- `robot/model.py` contains the domain model: cells, valued cells, robot environments, wall handling, robot movement, painting, pollution values, printed numbers, and final-state validation.
- `robot/loader.py` loads task definitions from `.env` files (JSON body with `envDtos` array and optional `todoText`, optional `operatorsLimit` — counts robot commands plus calls to user-defined functions, optional `customFunctionCallCount`, optional `ifLimit`, optional `whileLimit`), either from `ROBOT_TASKS_DIR` or the bundled `robot/tasks` directory.
- `robot/results.py` defines run outcome types (`RunResult`, `RunStatus`) and final-state checking.
- `robot/runtime_state.py` holds shared mutable execution state (active environment, command delay) and small helpers (`begin_solution_run` / `end_solution_run`, `active_robot`, …) so executor and commands avoid ad-hoc global access.
- `robot/commands.py` implements the student-facing robot command functions (`move_*`, `paint`, probes, `pol`, `printn`).
- `robot/executor.py` compiles and runs student scripts against an environment and maps exceptions to `RunResult`; static checks (operator limits, minimum qualifying custom-function call count) run before `exec`.
- `robot/runtime.py` is a thin facade: `task()`, `field()`, compatibility re-exports, and script discovery; it wires loader, GUI, and executor (including synthetic environments for `field()` without reading a task file).
- `robot/gui.py` provides the `tkinter` `RobotWindow` and re-exports layout/theme helpers for tests; `robot/gui_theme.py` and `robot/gui_layout.py` hold UI constants and pure geometry; `robot/field_renderer.py` draws the grid; `robot/status_strip.py` implements the status row (`Canvas`, optional hatched success background). The same window supports two modes: **solution mode** (opened from `task()` with a student script — Run/Step enabled) and **viewer mode** (opened via `viewer/viewer.py` with `viewer_catalog` — browse tasks by theme/number, Run/Step disabled). See `Docs/task-viewer.md`.
- `viewer/viewer.py` is the teacher-facing launcher for viewer mode; `robot/task_catalog.py` indexes tasks for browsing; `robot/gui_viewer.py` implements the viewer toolbar and in-window task switching.
- `robot/__init__.py` re-exports the student-facing API for `from robot import *` usage.
- `tests/` at the repository root covers core model behavior, task loading, runtime execution, GUI behavior, and facade import compatibility (`tests/test_facade_imports.py`).

