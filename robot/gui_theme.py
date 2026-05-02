from __future__ import annotations

from .i18n import t

STATUS_RUNNING = t("status.running")
STATUS_READY = t("status.ready")
STATUS_WRONG = t("status.wrong")
STATUS_ALL_CORRECT = t("status.all_correct")
ACTION_BUTTON_RUN = t("button.run")
ACTION_BUTTON_RESTORE = t("button.restore")
ACTION_BUTTON_STEP = t("button.step")

# todoText panel and status row share border color; backgrounds match task UX states.
TODO_TEXT_BG = "#fdf9d3"
TODO_TEXT_BORDER = "#999999"
STATUS_BG_NEUTRAL = "#def1fb"  # ready, running, wrong (no runtime error)
STATUS_BG_ERROR = "#fde7e9"
STATUS_BG_SUCCESS = "#dff6dd"

STATUS_TEXT_PAD_X = 8
STATUS_TEXT_PAD_Y = 5
STATUS_CANVAS_MIN_HEIGHT = 20
STATUS_CANVAS_WIDGET_HEIGHT = STATUS_CANVAS_MIN_HEIGHT + STATUS_TEXT_PAD_Y * 2
STATUS_HATCH_SPACING = 18
STATUS_HATCH_WIDTH = 6

DEFAULT_CELL_SIZE = 80
COMPACT_CELL_SIZE = 60
COMPACT_CELL_MAX_WIDTH = 7
COMPACT_CELL_MAX_HEIGHT = 5
MIN_CANVAS_WIDTH = 450
