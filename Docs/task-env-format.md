> Canonical English version. Russian translation: [task-env-format.ru.md](task-env-format.ru.md). Update the RU file manually whenever you change this document.

# Robot Task `.env` Format

Task files use the `.env` extension, but their contents are UTF-8 JSON.

## File Location

The loader searches for task files in this order:

1. The directory from the `ROBOT_TASKS_DIR` environment variable.
2. The bundled `robot/tasks` directory inside the project.

The task identifier may be passed either with or without the `.env` suffix. It must match the file stem exactly (including spaces and punctuation). For viewer grouping and navigation, see [task-viewer.md](task-viewer.md#task-catalog).

## Top-Level Structure

Each task file must contain a JSON object with the following fields:

- `envDtos` (required): array of environment definitions. The task is invalid if this field is missing, is not an array, or resolves to an empty environment list.
- `todoText` (optional): task description shown in the UI.

Optional solution-constraint fields (`operatorsLimit`, `customFunctionCallCount`, `ifLimit`, `whileLimit`, `requiredKeywords`, `bannedKeywords`) — see [Solution constraints](#solution-constraints).

## `todoText`

`todoText` supports two forms:

- Plain string, for example `"Reach the goal"`.
- Localized object whose keys are **UI language codes** from `SUPPORTED_LANGUAGES` in [`robot/i18n.py`](../robot/i18n.py) (for example `en`, `ru`, `zh-hans`, `ar`, `ur`, …). Example: `{ "en": "Reach the goal", "ru": "Дойди до цели" }`.

When a localized object is used, the loader:

1. Normalizes language keys such as `ru_RU.UTF-8` to `ru`.
2. Tries the current UI language.
3. Falls back to `en`.
4. Uses an empty string if no suitable value is found.

Non-string values inside the localization object are ignored.

For **Arabic** (`ar`) and **Urdu** (`ur`) strings, follow the same Unicode bidirectional isolation rules as other UI copy: wrap embedded left-to-right fragments (Python tokens such as `"for"`, `paint()`, Latin identifiers, and Western digits) with U+2066 LRI … U+2069 PDI as described in [`localization-style.md`](localization-style.md#unicode-bidirectional-isolation-rtl-locales).

## Solution constraints

Optional top-level fields that constrain the student's Python solution. All are enforced by **static** analysis of the student source code (AST parsing or Python tokenization, not runtime tracing).

Supported fields:

- `operatorsLimit` (optional): non-negative integer limit for the number of robot action commands and calls to user-defined functions in the student solution.
- `customFunctionCallCount` (optional): non-negative integer requirement for the number of qualifying calls to user-defined functions.
- `ifLimit` (optional): non-negative integer limit for how many times the Python keyword `if` may appear as a real token in the student solution.
- `whileLimit` (optional): non-negative integer limit for how many times the Python keyword `while` may appear as a real token in the student solution.
- `requiredKeywords` (optional): comma-separated list of Python keywords that must appear in the student solution as real Python keywords.
- `bannedKeywords` (optional): comma-separated list of Python keywords that must not appear in the student solution as real Python keywords.

### When checks run

The GUI invokes these checks in [`robot/gui.py`](../robot/gui.py) **after a successful run**: when **Run** completes all environments successfully, or when a **Step** session finishes with success. [`run_solution_on_env`](../robot/executor.py) does not perform them. If the program errors, crashes, or leaves a wrong final state, constraint violations are not reported.

### `customFunctionCallCount`

A call counts only when all of the following are true:

1. The target is a top-level user-defined function from the same solution.
2. That function is reachable from module-level calls under the same AST rules used by the checker.
3. The function body contains Robot commands such as `move_right()`, `move_left()`, `move_up()`, `move_down()`, `paint()`, or `printn()`.
4. The counted call itself is outside nested scopes that the checker ignores, such as nested `def`, `class`, or `lambda`.

Examples:

- `customFunctionCallCount: 2` is satisfied by one user-defined function called twice.
- `customFunctionCallCount: 2` is also satisfied by two different qualifying user-defined functions called once each.

### `operatorsLimit`

The checker parses the AST and counts:

1. Direct calls to robot action commands: `move_right()`, `move_left()`, `move_up()`, `move_down()`, `paint()`, `printn()`.
2. Any calls to user-defined functions (`def` or `async def`) declared in the same source file, regardless of nesting level. This includes:
   - Calls from module-level code.
   - Calls inside other user-defined functions.
   - Recursive self-calls.

Built-in calls such as `task()`, `field()`, `range()`, `len()`, etc. are **not** counted, unless the student happens to define a function with the same name.

Example:

```python
def step():
    move_right()
step()
step()
```

This counts as 3: `move_right` (1) + `step` (2).

### `ifLimit` and `whileLimit`

- The value must be a non-negative integer.
- The checker uses Python tokenization, so keywords inside comments or string literals do not count.
- Each occurrence of the keyword as a real token counts, including the `if` in a conditional expression such as `x if cond else y`.

Examples:

- `ifLimit: 1` allows a single `if` statement or a single ternary `if`, but rejects two separate `if` tokens.
- `whileLimit: 0` rejects any solution that uses `while`.

### `requiredKeywords` and `bannedKeywords`

- The value format is a comma-separated string such as `"for,def"` or `"while, if"`.
- Spaces around items are ignored.
- Empty items are ignored.
- Each item must be a real Python keyword supported by the current Python version.
- Only regular hard keywords are accepted. Soft keywords such as `match` and `case` are intentionally rejected by the loader and do not count during source-code checks.
- The checker uses Python tokenization, so keywords inside comments or string literals do not count.

If the same keyword is listed in both `requiredKeywords` and `bannedKeywords`, task loading fails with an error.

Examples:

- `requiredKeywords: "for,def"` requires the solution to use both `for` and `def`.
- `bannedKeywords: "while"` rejects any solution that uses `while`.
- `requiredKeywords: "for"` is satisfied by `for _ in range(3): ...`, but not by a comment like `# for`.

## `envDtos` Entry Format

Each item in `envDtos` must be an object with these required fields:

- `width`: field width.
- `height`: field height.
- `startRow`: robot start row.
- `startCol`: robot start column.
- `finalRow`: target row.
- `finalCol`: target column.

Supported optional fields:

- `walls`: array of wall segments.
- `paintedCells`: array of already painted cells at start.
- `cellsToPaint`: array of cells that must be painted by the solution.
- `pollutedCells`: array of valued cells readable through `pol()`.
- `cellsToPrint`: array of valued cells that must be printed by `printn()`.

### Cell Formats

Simple cell object:

```json
{ "r": 1, "c": 3 }
```

Valued cell object:

```json
{ "r": 1, "c": 4, "value": 7 }
```

Wall segment:

```json
[
  { "r": 0, "c": 0 },
  { "r": 0, "c": 1 }
]
```

`walls` should describe a barrier between two neighboring cells.

## Minimal Example

```json
{
  "envDtos": [
    {
      "width": 5,
      "height": 1,
      "startRow": 0,
      "startCol": 0,
      "finalRow": 0,
      "finalCol": 4
    }
  ],
  "todoText": "Reach the end"
}
```

## Extended Example

```json
{
  "envDtos": [
    {
      "width": 7,
      "height": 5,
      "startRow": 0,
      "startCol": 0,
      "finalRow": 4,
      "finalCol": 6,
      "walls": [
        [
          { "r": 0, "c": 1 },
          { "r": 0, "c": 2 }
        ]
      ],
      "paintedCells": [
        { "r": 1, "c": 2 }
      ],
      "cellsToPaint": [
        { "r": 1, "c": 3 }
      ],
      "pollutedCells": [
        { "r": 1, "c": 4, "value": 1 }
      ],
      "cellsToPrint": [
        { "r": 1, "c": 5, "value": 1 }
      ]
    }
  ],
  "todoText": {
    "en": "Paint and print required cells",
    "ru": "Закрась и выведи нужные клетки"
  },
  "operatorsLimit": 10,
  "customFunctionCallCount": 1,
  "ifLimit": 2,
  "whileLimit": 0,
  "requiredKeywords": "for,def",
  "bannedKeywords": "while"
}
```
