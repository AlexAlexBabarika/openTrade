"""AST-level allow-list for user scripts.

Runs *before* `compile()` so well-known sandbox escapes
(`().__class__.__bases__[0].__subclasses__()`, format-string tricks,
`__import__` lookups) are rejected without ever entering the bytecode VM.
"""

from __future__ import annotations

import ast
import hashlib


ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "math",
        "statistics",
        "dataclasses",
        "itertools",
        "functools",
        "collections",
        "typing",
        "datetime",
    }
)

FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "breakpoint",
        "help",
        "exit",
        "quit",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "__builtins__",
    }
)


class ScriptValidationError(ValueError):
    """Raised when a user script contains a disallowed construct."""


def _root_module(name: str) -> str:
    return name.split(".", 1)[0]


class _Validator(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[str] = []

    def _err(self, node: ast.AST, msg: str) -> None:
        line = getattr(node, "lineno", "?")
        self.errors.append(f"line {line}: {msg}")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if _root_module(alias.name) not in ALLOWED_IMPORTS:
                self._err(node, f"import '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        if not mod or _root_module(mod) not in ALLOWED_IMPORTS:
            self._err(node, f"import from '{mod}' is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in FORBIDDEN_NAMES:
            self._err(node, f"use of '{node.id}' is not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Reject any "private" attribute access. Beyond the classic dunder
        # escapes (``__class__``…), this also blocks single-underscore
        # internals such as a bar view's ``_series``, which would otherwise
        # leak future bars past the look-ahead guard.
        if node.attr.startswith("_"):
            self._err(node, f"access to attribute '{node.attr}' is not allowed")
        self.generic_visit(node)


def validate(code: str) -> None:
    """Parse and validate a user script.

    Raises:
        ScriptValidationError: code contains a forbidden construct or fails
            to parse as Python.
    """
    try:
        tree = ast.parse(code, filename="<script>", mode="exec")
    except SyntaxError as e:
        raise ScriptValidationError(f"syntax error: {e}") from e

    v = _Validator()
    v.visit(tree)
    if v.errors:
        raise ScriptValidationError("; ".join(v.errors))


def _strip_docstrings(tree: ast.Module) -> None:
    """Drop leading string-expression statements from the module and every
    function/class body, so docstring edits don't perturb the hash."""
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)


def ast_hash(code: str) -> str:
    """A whitespace/comment/docstring-stable sha256 of strategy source.

    Stable across reformatting, comments, and docstrings; changes on any other
    source edit. Use this for run identity, not the source hash.
    """
    try:
        tree = ast.parse(code, filename="<script>", mode="exec")
    except SyntaxError as e:
        raise ScriptValidationError(f"syntax error: {e}") from e
    _strip_docstrings(tree)
    dumped = ast.dump(tree, include_attributes=False)
    return hashlib.sha256(dumped.encode()).hexdigest()
