"""Toolbar icon paths and Tkinter loading for the environment editor."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Optional
import tkinter as tk

from .editor_env import EnvEditTool

_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "editor_icons"
_PNG_2X_DIR = _ASSETS_DIR / "png@2x"
_ICON_SUBSAMPLE = 2
DISPLAY_ICON_SIZE = 24

TOOL_ICON_STEMS: Mapping[EnvEditTool, str] = {
    EnvEditTool.START: "editor_start",
    EnvEditTool.FINAL: "editor_final",
    EnvEditTool.WALL: "editor_wall",
    EnvEditTool.PAINTED: "editor_painted",
    EnvEditTool.TO_PAINT: "editor_to_paint",
    EnvEditTool.POLLUTION: "editor_pollution",
    EnvEditTool.NUMBER: "editor_number",
    EnvEditTool.REMOVE_POLLUTION: "editor_remove_pollution",
    EnvEditTool.REMOVE_NUMBER: "editor_remove_number",
}

ACTION_ICON_STEMS = {
    "add_env": "editor_add_env",
    "remove_env": "editor_remove_env",
    "reset_env": "editor_reset_env",
    "todo": "editor_todo",
    "constraints": "editor_constraints",
    "undo": "editor_undo",
    "redo": "editor_redo",
}


def editor_icons_dir() -> Path:
    """Return the directory containing rasterized editor toolbar icons (HiDPI sources)."""
    return _PNG_2X_DIR


def icon_png_path(name: str) -> Path:
    """Return the path to a named editor icon PNG stem (``png@2x/``, 48×48)."""
    return editor_icons_dir() / f"{name}.png"


def load_editor_icon_images(master: tk.Misc) -> Dict[str, tk.PhotoImage]:
    """Load toolbar icons as ``PhotoImage`` instances at display size (~24×24).

    Sources are 48×48 PNGs from ``png@2x/``, downsampled with ``subsample(2, 2)``.
    Keep the returned mapping alive for the lifetime of the widgets that use
    the images (standard Tkinter requirement).
    """
    images: Dict[str, tk.PhotoImage] = {}
    stems = set(TOOL_ICON_STEMS.values())
    stems.update(ACTION_ICON_STEMS.values())
    for stem in sorted(stems):
        path = icon_png_path(stem)
        image = tk.PhotoImage(master=master, file=str(path))
        images[stem] = image.subsample(_ICON_SUBSAMPLE, _ICON_SUBSAMPLE)
    return images


def tool_icon(
    images: Mapping[str, tk.PhotoImage],
    tool: EnvEditTool,
) -> Optional[tk.PhotoImage]:
    """Return the toolbar image for an editing tool, if loaded."""
    stem = TOOL_ICON_STEMS.get(tool)
    if stem is None:
        return None
    return images.get(stem)


def action_icon(
    images: Mapping[str, tk.PhotoImage],
    action: str,
) -> Optional[tk.PhotoImage]:
    """Return a utility-toolbar image by action key (see ``ACTION_ICON_STEMS``)."""
    stem = ACTION_ICON_STEMS.get(action)
    if stem is None:
        return None
    return images.get(stem)
