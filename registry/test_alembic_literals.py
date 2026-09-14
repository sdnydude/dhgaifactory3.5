"""Guard the alembic chain against a failure class a clean replay found on 2026-09-13.

No database needed; runs in CI's ``pytest registry/`` and locally.

Every string literal passed to ``op.execute`` (directly or via a module-level
constant / dict of constants) must have no SQLAlchemy ``text()`` bind
parameters. Alembic wraps plain strings in ``text()``, so JSON like
``{"stagger_ms":40}`` becomes a bind parameter named ``40`` and the migration
fails on a fresh database (006 on master did exactly that).
"""
import ast
from pathlib import Path

import pytest
from sqlalchemy import text

VERSIONS = Path(__file__).resolve().parent / "alembic" / "versions"


def _string_literals(tree: ast.Module):
    """Yield (lineno, sql) for every str literal that can reach op.execute."""
    consts: dict[str, list[tuple[int, str]]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            val = node.value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                consts[name] = [(val.lineno, val.value)]
            elif isinstance(val, ast.Dict):
                consts[name] = [(v.lineno, v.value) for v in val.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "execute" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield arg.lineno, arg.value
            elif isinstance(arg, ast.Name) and arg.id in consts:
                yield from consts[arg.id]
            elif isinstance(arg, ast.JoinedStr):
                pytest.fail(f"line {arg.lineno}: op.execute(f-string) cannot be checked statically; build the SQL with sa.text().bindparams()")


@pytest.mark.parametrize("path", sorted(VERSIONS.glob("*.py")), ids=lambda p: p.name)
def test_op_execute_literals_have_no_bind_parameters(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    offenders = []
    for lineno, sql in _string_literals(tree):
        binds = list(text(sql)._bindparams)
        if binds:
            offenders.append(f"{path.name}:{lineno} binds {binds}")
    assert not offenders, "escape ':' as '\\:' inside the SQL literal (see 006_add_frontend_design_specs.py):\n" + "\n".join(offenders)
