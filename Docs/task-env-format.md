# Robot Task `.env` Format

Task files use the `.env` extension, but their contents are UTF-8 JSON.

## File Location

The loader searches for task files in this order:

1. The directory from the `ROBOT_TASKS_DIR` environment variable.
2. The bundled `robot/tasks` directory inside the project.

The task identifier may be passed either with or without the `.env` suffix.

## Top-Level Structure

Each task file must contain a JSON object with the following fields:

- `envDtos` (required): array of environment definitions. The task is invalid if this field is missing, is not an array, or resolves to an empty environment list.
- `todoText` (optional): task description shown in the UI.
- `operatorsLimit` (optional): non-negative integer limit for the number of written operators in the student solution.
- `minUsedUserFunctions` (optional): non-negative integer requirement for the number of user-defined functions that must be both declared and called.

## `todoText`

`todoText` supports two forms:

- Plain string, for example `"Reach the goal"`.
- Localized object, for example `{ "en": "Reach the goal", "ru": "Дойди до цели" }`.

When a localized object is used, the loader:

1. Normalizes language keys such as `ru_RU.UTF-8` to `ru`.
2. Tries the current UI language.
3. Falls back to `en`.
4. Uses an empty string if no suitable value is found.

Non-string values inside the localization object are ignored.

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
  "minUsedUserFunctions": 1
}
```
