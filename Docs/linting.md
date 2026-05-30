# Linting

Pylint configuration lives in `lint/`.

- `lint/pylint-src.rc` — pylint’s default enabled messages on production paths (no extra `enable`/`disable` in the rcfile), including `missing-function-docstring` (**C0116**) and `missing-class-docstring` (**C0115**).
- `lint/pylint-tests.rc` — the same defaults on `tests/`, with **C0116** and **C0115** disabled.

## Docstrings in tests

Test code is not checked for `missing-function-docstring` (**C0116**) or `missing-class-docstring` (**C0115**). Module docstrings, descriptive `unittest` class names (for example `RobotMovementTest`), and test method names (for example `test_robot_moves_right_when_cell_is_free`) already scope each file and scenario; a per-class or per-method docstring would mostly repeat those names.

Production code still requires a short one-line docstring on every function and method (including `@property` getters), per **C0116**, and on public classes, per **C0115**.

## Too many instance attributes (R0902)

Pylint’s default limit is seven attributes per class. Prefer grouping real state (for example `RobotTask.script_constraints`, `StepExecutionSession`’s `_StepScript` / `_StepState`, `RobotWindow`’s `_task` / `_layout` / `_chrome` / `_execution`) over raising the global limit.

Flat value-object types that mirror JSON or a single job struct (`RobotEnvDto`, `FieldColors`, `LanguageCaptureJob`) and grouped helper dataclasses on `RobotWindow` may use a **class-level** `# pylint: disable=too-many-instance-attributes` with a short comment. `ViewerMixin` uses the same exception because viewer fields are stored on the host window instance.

## Broad exception caught (W0718)

Pylint flags `except Exception` as **W0718**. Use a **line-level** `# pylint: disable=broad-exception-caught` only when a broad catch is intentional and changing it would alter behavior.

In [`robot/executor.py`](../robot/executor.py), student scripts are read, compiled, and `exec`’d. Failures must become a `RunResult` via `_map_exec_exception`, including arbitrary exceptions from student code. [`StepExecutionCancelled`](../robot/executor.py) inherits `BaseException` so step cancel is not swallowed by those handlers. Suppressions on the three existing `except Exception` blocks document that contract; do not refactor the step/batch paths just to satisfy W0718.

In [`tools/capture_robot_task_screenshots.py`](../tools/capture_robot_task_screenshots.py), `_try_capture` records any per-language failure and continues the batch. A local suppression preserves that tool semantics; keep `# noqa: BLE001` if ruff still requires it.

Do not disable W0718 globally in `lint/pylint-src.rc`.

## Scope

**Production** (`lint/pylint-src.rc`): `robot/`, `viewer/viewer.py` (not bare `viewer/` — there is no `viewer/__init__.py`), `tools/`.

**Tests** (`lint/pylint-tests.rc`): `tests/`.

`sample_solution.py` is not linted.

## How to run

From the repository root:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pylint --rcfile=lint/pylint-src.rc robot viewer/viewer.py tools
.venv/bin/python -m pylint --rcfile=lint/pylint-tests.rc tests
```

Expect `0` issues from each command.
