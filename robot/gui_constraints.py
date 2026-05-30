"""Task constraint detection and labels for the UI."""

from __future__ import annotations

from .i18n import t
from .loader import ScriptConstraints


def task_has_any_constraints(
    constraints: ScriptConstraints | None = None,
) -> bool:
    """Return whether any static script constraint is configured for the task."""
    c = constraints or ScriptConstraints()
    if c.operators_limit is not None:
        return True
    if c.custom_function_call_count is not None:
        return True
    if c.if_limit is not None:
        return True
    if c.while_limit is not None:
        return True
    if c.required_keywords:
        return True
    if c.banned_keywords:
        return True
    return False


def constraints_body_lines(
    constraints: ScriptConstraints | None = None,
) -> list[str]:
    """Build localized lines describing configured script constraints."""
    c = constraints or ScriptConstraints()
    lines: list[str] = []
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
