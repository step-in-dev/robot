#!/usr/bin/env python3
"""Rasterize environment-editor SVG icons to PNG (requires ImageMagick convert)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SVG_DIR = _REPO_ROOT / "robot" / "assets" / "editor_icons" / "svg"
_PNG_2X_DIR = _REPO_ROOT / "robot" / "assets" / "editor_icons" / "png@2x"
_ICON_SIZE = 48


def _convert_svg(svg_path: Path, png_path: Path, size: int) -> None:
    convert = shutil.which("convert")
    if convert is None:
        raise RuntimeError(
            "ImageMagick 'convert' not found; install imagemagick to build editor icons."
        )
    png_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            convert,
            "-background",
            "none",
            "-density",
            "192",
            str(svg_path),
            "-resize",
            f"{size}x{size}",
            str(png_path),
        ],
        check=True,
    )


def main() -> int:
    """Rasterize every SVG in the editor icons source directory to PNG."""
    svg_files = sorted(_SVG_DIR.glob("*.svg"))
    if not svg_files:
        print(f"No SVG files in {_SVG_DIR}", file=sys.stderr)
        return 1

    for svg_path in svg_files:
        stem = svg_path.stem
        png_path = _PNG_2X_DIR / f"{stem}.png"
        _convert_svg(svg_path, png_path, _ICON_SIZE)
        print(f"Wrote {png_path.relative_to(_REPO_ROOT)} ({_ICON_SIZE}x{_ICON_SIZE})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
