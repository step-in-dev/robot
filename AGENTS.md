# Project Overview

This project implements an educational Robot simulator for learning basic programming concepts. It lets students write Python solutions that control a robot on a grid, run those solutions against predefined task environments, and receive visual feedback through a desktop UI.

## Purpose

The main purpose is to provide a simple, school-friendly programming environment around the classic "Robot" executor. Learners practice sequencing, loops, conditions, grid navigation, painting cells, reading cell values, and printing numbers while solving small algorithmic tasks.

## Target Audience

The target audience is school students who are learning introductory programming and algorithmic thinking. The public API is intentionally compact and approachable, with commands such as `move_right()`, `paint()`, `is_free_right()`, `pol()`, `printn()`, `task()`, and `field(width=8, height=6)`.

## Technology Stack

- Python 3 with standard-library modules such as `dataclasses`, `pathlib`, `json`, and `unittest`.
- `tkinter` for the desktop graphical interface.
- JSON task files for grid environments and validation data.
- Built-in `unittest` tests for model, loader, and runtime behavior.

## Documentation

- `Docs/task-env-format.md` describes the `.env` task-file format loaded by `robot/loader.py`.
- `Docs/localization-style.md` describes conventions for localized UI strings (Python keywords, `True`/`False`/`None`, and the proper name Robot).

## Status strip localization

Localized strings shown in the Robot window status strip must not exceed **50 characters**, so they remain visible when the window is at its minimum size.

## Architecture Overview

- `robot/model.py` contains the domain model: cells, valued cells, robot environments, wall handling, robot movement, painting, pollution values, printed numbers, and final-state validation.
- `robot/loader.py` loads task definitions from `.env` files (JSON body with `envDtos` array and optional `todoText`, optional `operatorsLimit`, optional `customFunctionCallCount`, optional `ifLimit`, optional `whileLimit`), either from `ROBOT_TASKS_DIR` or the bundled `robot/tasks` directory.
- `robot/results.py` defines run outcome types (`RunResult`, `RunStatus`) and final-state checking.
- `robot/runtime_state.py` holds shared mutable execution state (active environment, command delay) and small helpers (`begin_solution_run` / `end_solution_run`, `active_robot`, …) so executor and commands avoid ad-hoc global access.
- `robot/commands.py` implements the student-facing robot command functions (`move_*`, `paint`, probes, `pol`, `printn`).
- `robot/executor.py` compiles and runs student scripts against an environment and maps exceptions to `RunResult`; static checks (operator limits, minimum qualifying custom-function call count) run before `exec`.
- `robot/runtime.py` is a thin facade: `task()`, `field()`, compatibility re-exports, and script discovery; it wires loader, GUI, and executor (including synthetic environments for `field()` without reading a task file).
- `robot/gui.py` provides the `tkinter` `RobotWindow` and re-exports layout/theme helpers for tests; `robot/gui_theme.py` and `robot/gui_layout.py` hold UI constants and pure geometry; `robot/field_renderer.py` draws the grid; `robot/status_strip.py` implements the status row (`Canvas`, optional hatched success background).
- `robot/__init__.py` re-exports the student-facing API for `from robot import *` usage.
- `tests/` at the repository root covers core model behavior, task loading, runtime execution, GUI behavior, and facade import compatibility (`tests/test_facade_imports.py`).
