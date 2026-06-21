"""Shared YAML front matter parsing for Markdown sources in tools/."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import yaml


def parse_markdown_front_matter(
    path: Path,
    *,
    source_label: str,
) -> Tuple[dict, str]:
    """Parse YAML front matter and Markdown body from a ``.md`` file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SystemExit(
            f"{source_label} {path} must start with YAML front matter (---)"
        )
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SystemExit(f"Invalid front matter in {path}")
    front = yaml.safe_load(parts[1])
    if not isinstance(front, dict):
        raise SystemExit(f"Front matter in {path} must be a mapping")
    body = parts[2].lstrip("\n")
    return front, body
