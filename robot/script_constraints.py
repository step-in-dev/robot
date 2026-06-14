"""Script constraint fields loaded from task ``.env`` files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ScriptConstraints:
    """Static script limits loaded from a task ``.env`` file."""

    operators_limit: Optional[int] = None
    custom_function_call_count: Optional[int] = None
    if_limit: Optional[int] = None
    while_limit: Optional[int] = None
    required_keywords: Optional[Tuple[str, ...]] = None
    banned_keywords: Optional[Tuple[str, ...]] = None
