"""Toolbar icon paths and Tkinter loading for the environment editor."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Optional
import tkinter as tk

from .editor_env import EnvEditTool

_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "editor_icons"
_PNG_2X_DIR = _ASSETS_DIR / "png@2x"
_SOURCE_ICON_SIZE = 48
# At 150% display scaling (≥144 DPI) and above, show 48×48 sources without downsampling.
_HIDPI_SUBSAMPLE_THRESHOLD_DPI = 144.0

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


def icon_subsample_factor(master: tk.Misc) -> int:
    """Return ``PhotoImage`` subsample divisor for *master*'s display DPI."""
    master.update_idletasks()
    pixels_per_inch = float(master.winfo_fpixels("1i"))
    if pixels_per_inch >= _HIDPI_SUBSAMPLE_THRESHOLD_DPI:
        return 1
    return 2


def display_icon_size(master: tk.Misc) -> int:
    """Return toolbar icon edge length in pixels for *master*'s display DPI."""
    return _SOURCE_ICON_SIZE // icon_subsample_factor(master)


def load_editor_icon_images(master: tk.Misc) -> Dict[str, tk.PhotoImage]:
    """Load toolbar icons as ``PhotoImage`` instances for the current display DPI.

    Sources are 48×48 PNGs from ``png@2x/``. At ~96 DPI they are downsampled to
    24×24 via ``subsample(2, 2)``; at ≥144 DPI the full 48×48 asset is used.
    Keep the returned mapping alive for the lifetime of the widgets that use
    the images (standard Tkinter requirement).
    """
    subsample = icon_subsample_factor(master)
    images: Dict[str, tk.PhotoImage] = {}
    stems = set(TOOL_ICON_STEMS.values())
    stems.update(ACTION_ICON_STEMS.values())
    for stem in sorted(stems):
        path = icon_png_path(stem)
        image = tk.PhotoImage(master=master, file=str(path))
        if subsample > 1:
            image = image.subsample(subsample, subsample)
        images[stem] = image
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
