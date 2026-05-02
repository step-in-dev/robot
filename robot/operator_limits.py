from __future__ import annotations

import ast
from collections import deque
from dataclasses import dataclass

DEFAULT_STUDENT_FILENAME = "<student>"

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
    "Использовано команд Робота: {actual}. Разрешено не более {limit}"
)

_SKIP_NESTED_SCOPE_TYPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
)


def _is_counted_operator_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Name)
        and node.func.id in COUNTED_OPERATOR_NAMES
    )


def _walk_nodes_skip_nested_scopes(body: list[ast.stmt]):
    """Depth-first over *body*, skipping nested class/function/lambda subtrees."""
    stack: list[ast.AST] = []
    for stmt in reversed(body):
        stack.append(stmt)
    while stack:
        node = stack.pop()
        if isinstance(node, _SKIP_NESTED_SCOPE_TYPES):
            continue
        yield node
        for child in reversed(list(ast.iter_child_nodes(node))):
            stack.append(child)


def count_robot_operators(
    source: str, *, filename: str = DEFAULT_STUDENT_FILENAME
) -> int:
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
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> OperatorsLimitViolation | None:
    if operators_limit is None:
        return None
    actual = count_robot_operators(source, filename=filename)
    if actual <= operators_limit:
        return None
    return OperatorsLimitViolation(actual=actual, limit=operators_limit)


MIN_USED_USER_FUNCTIONS_MESSAGE_TEMPLATE = (
    "Использовано пользовательских функций: {actual}. Требуется не менее {required}"
)


def _body_contains_robot_operator_excluding_nested_defs(body: list[ast.stmt]) -> bool:
    """True if a counted robot call appears in *body*, not inside a nested scope."""
    for node in _walk_nodes_skip_nested_scopes(body):
        if isinstance(node, ast.Call) and _is_counted_operator_call(node):
            return True
    return False


def _name_call_ids_skip_nested_scopes(body: list[ast.stmt]) -> set[str]:
    return {
        node.func.id
        for node in _walk_nodes_skip_nested_scopes(body)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def _module_level_name_call_ids(body: list[ast.stmt]) -> set[str]:
    """``f()`` names at module level, excluding calls inside top-level ``def``/``class``."""
    return _name_call_ids_skip_nested_scopes(body)


def count_used_user_functions_with_robot_commands(
    source: str, *, filename: str = DEFAULT_STUDENT_FILENAME
) -> int:
    tree = ast.parse(source, filename=filename)
    function_defs = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    if not function_defs:
        return 0

    roots = _module_level_name_call_ids(tree.body) & function_defs.keys()
    reachable: set[str] = set()
    queue: deque[str] = deque(roots)

    while queue:
        name = queue.popleft()
        if name in reachable:
            continue
        if name not in function_defs:
            continue
        reachable.add(name)
        for callee in _name_call_ids_skip_nested_scopes(function_defs[name].body):
            if callee in function_defs and callee not in reachable:
                queue.append(callee)

    return sum(
        1
        for name in reachable
        if _body_contains_robot_operator_excluding_nested_defs(
            function_defs[name].body
        )
    )


@dataclass(frozen=True)
class MinUsedUserFunctionsViolation:
    actual: int
    required: int

    @property
    def message(self) -> str:
        return MIN_USED_USER_FUNCTIONS_MESSAGE_TEMPLATE.format(
            actual=self.actual,
            required=self.required,
        )


def check_min_used_user_functions(
    source: str,
    min_used_user_functions: int | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> MinUsedUserFunctionsViolation | None:
    if min_used_user_functions is None:
        return None
    actual = count_used_user_functions_with_robot_commands(
        source, filename=filename
    )
    if actual >= min_used_user_functions:
        return None
    return MinUsedUserFunctionsViolation(
        actual=actual,
        required=min_used_user_functions,
    )
