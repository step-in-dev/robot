# Project Overview

This project implements an educational Robot executor for learning basic programming concepts. It lets students write Python solutions that control a robot on a grid, run those solutions against predefined task environments, and receive visual feedback through a desktop UI.

## Purpose

The main purpose is to provide a simple, school-friendly programming environment around the classic "Robot" executor. Learners practice sequencing, loops, conditions, grid navigation, painting cells, reading cell values, and printing numbers while solving small algorithmic tasks.

## Target Audience

The target audience is school students who are learning introductory programming and algorithmic thinking. The public API is intentionally compact and approachable, with commands such as `move_right()`, `paint()`, `is_free_right()`, `pol()`, `printn()`, and `task()`.

## Technology Stack

- Python 3 with standard-library modules such as `dataclasses`, `pathlib`, `json`, and `unittest`.
- `tkinter` for the desktop graphical interface.
- JSON task files for grid environments and validation data.
- Built-in `unittest` tests for model, loader, and runtime behavior.

## Architecture Overview

- `robot/model.py` contains the domain model: cells, valued cells, robot environments, wall handling, robot movement, painting, pollution values, printed numbers, and final-state validation.
- `robot/loader.py` loads task definitions from JSON files (`envDtos` array and optional `todoText`), either from `ROBOT_TASKS_DIR` or the bundled `robot/tasks` directory.
- `robot/runtime.py` exposes the student-facing command API, executes student solution files in a controlled robot context, and converts outcomes into run results.
- `robot/gui.py` provides the `tkinter` window that displays task environments, runs solutions across all environments, and redraws the grid as the robot state changes.
- `robot/__init__.py` re-exports the student-facing API for `from robot import *` usage.
- `tests/` at the repository root covers core model behavior, task loading, and runtime execution.
