from __future__ import annotations

import ast
import io
import keyword
import token
import tokenize
from collections import deque
from dataclasses import dataclass, field

from .i18n import t

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

OPERATORS_LIMIT_MESSAGE_TEMPLATE = t("limit.operators")

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


CUSTOM_FUNCTION_CALL_COUNT_MESSAGE_TEMPLATE = t("limit.custom_function_calls")
REQUIRED_KEYWORDS_MESSAGE_TEMPLATE = t("limit.required_keywords")
BANNED_KEYWORDS_MESSAGE_TEMPLATE = t("limit.banned_keywords")
IF_LIMIT_MESSAGE_TEMPLATE = t("limit.if_keyword")
WHILE_LIMIT_MESSAGE_TEMPLATE = t("limit.while_keyword")


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


def _top_level_function_defs(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def _reachable_user_function_names(
    tree: ast.Module, function_defs: dict[str, ast.FunctionDef]
) -> set[str]:
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

    return reachable


def _qualifying_user_function_names(
    function_defs: dict[str, ast.FunctionDef], reachable: set[str]
) -> set[str]:
    return {
        name
        for name in reachable
        if _body_contains_robot_operator_excluding_nested_defs(
            function_defs[name].body
        )
    }


def _count_qualifying_calls_in_body(
    body: list[ast.stmt], qualifying_function_names: set[str]
) -> int:
    return sum(
        1
        for node in _walk_nodes_skip_nested_scopes(body)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in qualifying_function_names
    )


def count_custom_function_calls_with_robot_commands(
    source: str, *, filename: str = DEFAULT_STUDENT_FILENAME
) -> int:
    tree = ast.parse(source, filename=filename)
    function_defs = _top_level_function_defs(tree)
    if not function_defs:
        return 0

    reachable = _reachable_user_function_names(tree, function_defs)
    qualifying_function_names = _qualifying_user_function_names(
        function_defs, reachable
    )
    if not qualifying_function_names:
        return 0

    actual = _count_qualifying_calls_in_body(tree.body, qualifying_function_names)
    for name in reachable:
        actual += _count_qualifying_calls_in_body(
            function_defs[name].body,
            qualifying_function_names,
        )
    return actual


@dataclass(frozen=True)
class CustomFunctionCallCountViolation:
    actual: int
    required: int

    @property
    def message(self) -> str:
        return CUSTOM_FUNCTION_CALL_COUNT_MESSAGE_TEMPLATE.format(
            actual=self.actual,
            required=self.required,
        )


def check_custom_function_call_count(
    source: str,
    custom_function_call_count: int | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> CustomFunctionCallCountViolation | None:
    if custom_function_call_count is None:
        return None
    actual = count_custom_function_calls_with_robot_commands(
        source, filename=filename
    )
    if actual >= custom_function_call_count:
        return None
    return CustomFunctionCallCountViolation(
        actual=actual,
        required=custom_function_call_count,
    )


def extract_python_keywords(
    source: str, *, filename: str = DEFAULT_STUDENT_FILENAME
) -> frozenset[str]:
    del filename  # Reserved for parity with other static checks.
    keywords: set[str] = set()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok in tokens:
        if tok.type != token.NAME:
            continue
        if keyword.iskeyword(tok.string):
            keywords.add(tok.string)
    return frozenset(keywords)


def count_python_keyword_token_occurrences(
    source: str, keyword_name: str, *, filename: str = DEFAULT_STUDENT_FILENAME
) -> int:
    """Count real keyword tokens (same tokenizer rules as ``extract_python_keywords``)."""
    del filename
    count = 0
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok in tokens:
        if tok.type != token.NAME:
            continue
        if tok.string == keyword_name and keyword.iskeyword(tok.string):
            count += 1
    return count


@dataclass(frozen=True)
class PythonKeywordLimitViolation:
    actual: int
    limit: int
    _message_template: str = field(repr=False)

    @property
    def message(self) -> str:
        return self._message_template.format(
            actual=self.actual,
            limit=self.limit,
        )


def _check_python_keyword_token_limit(
    source: str,
    limit: int | None,
    *,
    keyword_token: str,
    filename: str,
    message_template: str,
) -> PythonKeywordLimitViolation | None:
    if limit is None:
        return None
    actual = count_python_keyword_token_occurrences(
        source, keyword_token, filename=filename
    )
    if actual <= limit:
        return None
    return PythonKeywordLimitViolation(
        actual=actual,
        limit=limit,
        _message_template=message_template,
    )


def check_if_limit(
    source: str,
    if_limit: int | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> PythonKeywordLimitViolation | None:
    return _check_python_keyword_token_limit(
        source,
        if_limit,
        keyword_token="if",
        filename=filename,
        message_template=IF_LIMIT_MESSAGE_TEMPLATE,
    )


def check_while_limit(
    source: str,
    while_limit: int | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> PythonKeywordLimitViolation | None:
    return _check_python_keyword_token_limit(
        source,
        while_limit,
        keyword_token="while",
        filename=filename,
        message_template=WHILE_LIMIT_MESSAGE_TEMPLATE,
    )


@dataclass(frozen=True)
class RequiredKeywordsViolation:
    missing_keywords: tuple[str, ...]

    @property
    def message(self) -> str:
        return REQUIRED_KEYWORDS_MESSAGE_TEMPLATE.format(
            keywords=", ".join(self.missing_keywords)
        )


def check_required_keywords(
    source: str,
    required_keywords: tuple[str, ...] | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> RequiredKeywordsViolation | None:
    if not required_keywords:
        return None
    used_keywords = extract_python_keywords(source, filename=filename)
    missing_keywords = tuple(
        keyword_name
        for keyword_name in required_keywords
        if keyword_name not in used_keywords
    )
    if not missing_keywords:
        return None
    return RequiredKeywordsViolation(missing_keywords=missing_keywords)


@dataclass(frozen=True)
class BannedKeywordsViolation:
    used_keywords: tuple[str, ...]

    @property
    def message(self) -> str:
        return BANNED_KEYWORDS_MESSAGE_TEMPLATE.format(
            keywords=", ".join(self.used_keywords)
        )


def check_banned_keywords(
    source: str,
    banned_keywords: tuple[str, ...] | None,
    *,
    filename: str = DEFAULT_STUDENT_FILENAME,
) -> BannedKeywordsViolation | None:
    if not banned_keywords:
        return None
    used_keywords = extract_python_keywords(source, filename=filename)
    matched_keywords = tuple(
        keyword_name for keyword_name in banned_keywords if keyword_name in used_keywords
    )
    if not matched_keywords:
        return None
    return BannedKeywordsViolation(used_keywords=matched_keywords)
