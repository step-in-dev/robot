from __future__ import annotations

STATUS_RUNNING = "Выполнение..."
STATUS_READY = "Робот: Готов"
STATUS_WRONG = "Задание не выполнено"
STATUS_ALL_CORRECT = "Все верно"
ACTION_BUTTON_RUN = "Выполнить [Enter]"
ACTION_BUTTON_RESTORE = "Восстановить [Enter]"
ACTION_BUTTON_STEP = "Шаг"

# todoText panel and status row share border color; backgrounds match task UX states.
TODO_TEXT_BG = "#fdf9d3"
TODO_TEXT_BORDER = "#999999"
STATUS_BG_NEUTRAL = "#def1fb"  # ready, running, wrong (no runtime error)
STATUS_BG_ERROR = "#fde7e9"
STATUS_BG_SUCCESS = "#dff6dd"

STATUS_TEXT_PAD_X = 8
STATUS_TEXT_PAD_Y = 5

DEFAULT_CELL_SIZE = 80
COMPACT_CELL_SIZE = 60
COMPACT_CELL_MAX_WIDTH = 7
COMPACT_CELL_MAX_HEIGHT = 5
MIN_CANVAS_WIDTH = 450
