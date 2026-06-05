"""Export the Robot field tkinter canvas to PNG (website screenshot tooling)."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from robot.gui import RobotWindow


def write_robot_window_field_canvas(window: RobotWindow, path: Path) -> None:
    """Draw the current environment and save the field canvas to *path*."""
    if window.is_closed:
        raise RuntimeError("Cannot export field canvas from a closed window")
    window.draw_field()
    write_field_canvas_png(window.canvas, path)


def write_field_canvas_png(canvas: tk.Canvas, path: Path) -> None:
    """Save the on-screen field canvas to *path* (PNG), 1:1 pixels when possible."""
    canvas.update_idletasks()
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"Field canvas has no drawable size ({width}x{height})"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    root = canvas.winfo_toplevel()
    root.update_idletasks()
    root.lift()
    root.update()

    if _command_available("import"):
        _write_via_screen_crop(canvas, path, width=width, height=height)
        return

    _write_via_postscript(canvas, path, width=width, height=height)


def _command_available(name: str) -> bool:
    return shutil.which(name) is not None


def _write_via_screen_crop(
    canvas: tk.Canvas, path: Path, *, width: int, height: int
) -> None:
    """Grab the canvas rectangle from the root window (sharp, native pixels)."""
    x = canvas.winfo_rootx()
    y = canvas.winfo_rooty()
    proc = subprocess.run(
        [
            "import",
            "-silent",
            "-window",
            "root",
            "-crop",
            f"{width}x{height}+{x}+{y}",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not path.is_file():
        detail = proc.stderr.strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"import screen crop failed: {detail}")


def _write_via_postscript(
    canvas: tk.Canvas, path: Path, *, width: int, height: int
) -> None:
    """Fallback: vector export via PostScript (less sharp than screen crop)."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".ps",
        delete=False,
    ) as ps_file:
        ps_path = Path(ps_file.name)

    try:
        canvas.postscript(
            file=str(ps_path),
            colormode="color",
            width=width,
            height=height,
            pagewidth=width,
            pageheight=height,
        )
        _postscript_to_png(ps_path, path, width=width, height=height)
    finally:
        ps_path.unlink(missing_ok=True)


def _postscript_to_png(
    ps_path: Path, png_path: Path, *, width: int, height: int
) -> None:
    size = f"{width}x{height}!"
    errors: list[str] = []
    for command in _png_converter_commands(ps_path, png_path, size=size):
        # Skip missing converters (common on Windows) instead of FileNotFoundError.
        if not _command_available(command[0]):
            errors.append(f"{' '.join(command)}: command not found")
            continue
        proc = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and png_path.is_file():
            return
        errors.append(
            f"{' '.join(command)}: {proc.stderr.strip() or f'exit {proc.returncode}'}"
        )
    raise RuntimeError(
        "Could not convert field canvas PostScript to PNG "
        "(install ImageMagick `convert` or Ghostscript `gs`). "
        + "; ".join(errors)
    )


def _png_converter_commands(
    ps_path: Path, png_path: Path, *, size: str
) -> list[list[str]]:
    ps = str(ps_path)
    png = str(png_path)
    resize = ["-filter", "Point", "-resize", size]
    return [
        ["convert", "-density", "96", ps, *resize, png],
        ["convert", ps, *resize, png],
        ["magick", "convert", "-density", "96", ps, *resize, png],
        [
            "gs",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=pngalpha",
            f"-sOutputFile={png}",
            ps,
        ],
    ]
