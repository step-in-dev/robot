# Linting

Pylint configuration lives in `lint/`.

- `lint/pylint-src.rc` — full pylint rule set (`enable=all`) on production paths, including `missing-function-docstring` (**C0116**), with **C1805** disabled.
- `lint/pylint-tests.rc` — the same rule set on `tests/`, with **C0116**, **C0115**, and **C1805** disabled.

## Docstrings in tests

Test code is not checked for `missing-function-docstring` (**C0116**) or `missing-class-docstring` (**C0115**). Module docstrings, descriptive `unittest` class names (for example `RobotMovementTest`), and test method names (for example `test_robot_moves_right_when_cell_is_free`) already scope each file and scenario; a per-class or per-method docstring would mostly repeat those names.

Production code still requires a short one-line docstring on every function and method (including `@property` getters), per **C0116**, and on public classes, per **C0115**.

## Comparisons to zero

Neither profile checks `use-implicit-booleaness-not-comparison-to-zero` (**C1805**). Explicit comparisons such as `exit_code != 0` or `count == 0` are preferred for return codes, counters, and indices because they read clearly and do not rely on implicit truthiness when a value might not be a plain `int`.

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
