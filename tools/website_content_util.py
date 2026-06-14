"""Shared filesystem helpers for the Robot website generator."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable


def newest_mtime(paths: Iterable[Path]) -> float:
    """Return the largest mtime among ``paths``, ignoring unreadable files."""
    newest = 0.0
    for path in paths:
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return newest


def iso_date_from_mtime(newest: float, fallback: str) -> str:
    """Format ``newest`` as an ISO date, or return ``fallback`` when it is zero."""
    if newest <= 0:
        return fallback
    return date.fromtimestamp(newest).isoformat()
