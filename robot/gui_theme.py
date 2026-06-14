"""Colors, fonts, and visual constants for the UI."""

from __future__ import annotations

from .i18n import t

STATUS_RUNNING = t("status.running")
STATUS_READY = t("status.ready")
STATUS_WRONG = t("status.wrong")
STATUS_ALL_CORRECT = t("status.all_correct")
ACTION_BUTTON_RUN = t("button.run")
ACTION_BUTTON_RESTORE = t("button.restore")
ACTION_BUTTON_STEP = t("button.step")
ACTION_BUTTON_STOP = t("button.stop")
ACTION_BUTTON_HELP = t("button.help")

# tk.Button internal padding (text ↔ border). Omitting padx/pady lets the platform
# theme decide, which makes Windows noticeably tighter than typical Linux/X11.
# Screen distances in "m" (mm) track DPI better than a fixed pixel padding.
ENV_SELECT_BUTTON_PAD_X = "4.5m"
ENV_SELECT_BUTTON_PAD_Y = "1.5m"
BUTTON_PAD_X = "2.5m"
BUTTON_PAD_Y = "1.5m"
ICON_BUTTON_PAD_X = "1.5m"
ICON_BUTTON_PAD_Y = "1m"

# Readable body text: help/constraints dialogs and task condition (`todoText`) banner.
DIALOG_BODY_FONT = ("TkDefaultFont", 11)

# todoText panel and status row share border color; backgrounds match task UX states.
TODO_TEXT_BG = "#fdf9d3"
TODO_TEXT_BORDER = "#999999"
TODO_TEXT_HEIGHT = 2
TODO_TEXT_PAD_X = 8
TODO_TEXT_PAD_Y = 6
TODO_TEXT_SCROLLBAR_WIDTH = 16
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
SUPER_COMPACT_CELL_SIZE = 52
COMPACT_CELL_MAX_WIDTH = 7
COMPACT_CELL_MAX_HEIGHT = 5
SUPER_COMPACT_CELL_MAX_WIDTH = 20
SUPER_COMPACT_CELL_MAX_HEIGHT = 12
MIN_CANVAS_WIDTH = 530
MIN_EDITOR_WINDOW_WIDTH = 850
