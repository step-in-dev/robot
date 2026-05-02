from __future__ import annotations

import ast
from dataclasses import dataclass

COUNTED_OPERATOR_NAMES = frozenset(
    {
        "move_right",
        "move_left",
        "move_up",
        "move_down",
        "paint",
        "printn",
    }
)

OPERATORS_LIMIT_MESSAGE_TEMPLATE = (
    "Использовано {actual} команд робота, разрешено не более {limit}"
)


def _is_counted_operator_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Name)
        and node.func.id in COUNTED_OPERATOR_NAMES
    )


def count_robot_operators(source: str, *, filename: str = "<student>") -> int:
    tree = ast.parse(source, filename=filename)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_counted_operator_call(node)
    )


@dataclass(frozen=True)
class OperatorsLimitViolation:
    actual: int
    limit: int

    @property
    def message(self) -> str:
        return OPERATORS_LIMIT_MESSAGE_TEMPLATE.format(
            actual=self.actual,
            limit=self.limit,
        )


def check_operators_limit(
    source: str,
    operators_limit: int | None,
    *,
    filename: str = "<student>",
) -> OperatorsLimitViolation | None:
    if operators_limit is None:
        return None
    actual = count_robot_operators(source, filename=filename)
    if actual <= operators_limit:
        return None
    return OperatorsLimitViolation(actual=actual, limit=operators_limit)
