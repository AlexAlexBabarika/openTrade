import pytest

from backend.scripts.ast_guard import ScriptValidationError, ast_hash

_BASE = "def on_bar(ctx):\n    x = 1 + 2\n    return x\n"


def test_stable_across_whitespace_and_comments():
    reformatted = "def on_bar(ctx):\n\n    # a comment\n    x = 1 +   2\n    return x\n"
    assert ast_hash(_BASE) == ast_hash(reformatted)


def test_stable_across_docstring_changes():
    with_doc = 'def on_bar(ctx):\n    "explains things"\n    x = 1 + 2\n    return x\n'
    assert ast_hash(_BASE) == ast_hash(with_doc)


def test_changes_on_constant_change():
    changed = "def on_bar(ctx):\n    x = 1 + 3\n    return x\n"
    assert ast_hash(_BASE) != ast_hash(changed)


def test_rejects_unparseable_code():
    with pytest.raises(ScriptValidationError):
        ast_hash("def on_bar(:\n")
