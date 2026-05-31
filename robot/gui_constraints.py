"""Task constraint detection and labels for the UI."""

from __future__ import annotations

from typing import List, Optional
from .i18n import t
from .loader import ScriptConstraints


def task_has_any_constraints(
    constraints: Optional[ScriptConstraints] = None,
) -> bool:
    """Return whether any static script constraint is configured for the task."""
    c = constraints or ScriptConstraints()
    return any(
        (
            c.operators_limit is not None,
            c.custom_function_call_count is not None,
            c.if_limit is not None,
            c.while_limit is not None,
            bool(c.required_keywords),
            bool(c.banned_keywords),
        )
    )


def constraints_body_lines(
    constraints: Optional[ScriptConstraints] = None,
) -> List[str]:
    """Build localized lines describing configured script constraints."""
    c = constraints or ScriptConstraints()
    lines: List[str] = []
    if c.operators_limit is not None:
        lines.append(
            t("constraints.operators_max", limit=c.operators_limit)
        )
    if c.custom_function_call_count is not None:
        lines.append(
            t(
                "constraints.functions_min",
                required=c.custom_function_call_count,
            )
        )
    if c.if_limit is not None:
        lines.append(t("constraints.if_max", limit=c.if_limit))
    if c.while_limit is not None:
        lines.append(t("constraints.while_max", limit=c.while_limit))
    if c.required_keywords:
        joined = ", ".join(c.required_keywords)
        lines.append(
            t("constraints.required_keywords", keywords=joined)
        )
    if c.banned_keywords:
        joined = ", ".join(c.banned_keywords)
        lines.append(
            t("constraints.banned_keywords", keywords=joined)
        )
    return lines
