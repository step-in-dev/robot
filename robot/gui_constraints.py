from __future__ import annotations

from .i18n import t

def task_has_any_constraints(
    *,
    operators_limit: int | None,
    custom_function_call_count: int | None,
    if_limit: int | None,
    while_limit: int | None,
    required_keywords: tuple[str, ...] | None,
    banned_keywords: tuple[str, ...] | None,
) -> bool:
    if operators_limit is not None:
        return True
    if custom_function_call_count is not None:
        return True
    if if_limit is not None:
        return True
    if while_limit is not None:
        return True
    if required_keywords:
        return True
    if banned_keywords:
        return True
    return False


def constraints_body_lines(
    *,
    operators_limit: int | None,
    custom_function_call_count: int | None,
    if_limit: int | None,
    while_limit: int | None,
    required_keywords: tuple[str, ...] | None,
    banned_keywords: tuple[str, ...] | None,
) -> list[str]:
    lines: list[str] = []
    if operators_limit is not None:
        lines.append(
            t("constraints.operators_max", limit=operators_limit)
        )
    if custom_function_call_count is not None:
        lines.append(
            t(
                "constraints.functions_min",
                required=custom_function_call_count,
            )
        )
    if if_limit is not None:
        lines.append(t("constraints.if_max", limit=if_limit))
    if while_limit is not None:
        lines.append(t("constraints.while_max", limit=while_limit))
    if required_keywords:
        joined = ", ".join(required_keywords)
        lines.append(
            t("constraints.required_keywords", keywords=joined)
        )
    if banned_keywords:
        joined = ", ".join(banned_keywords)
        lines.append(
            t("constraints.banned_keywords", keywords=joined)
        )
    return lines
