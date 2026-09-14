"""The alembic revision graph must stay linear with a single head.

002b/002c were spliced in by editing 003's down_revision; a future revision
that still says `down_revision = "002_claude_data"` would create a second
head and break `alembic upgrade head` in CI and on deploy. Needs alembic
(registry/requirements.txt); skipped where it is not installed.
"""
from pathlib import Path

import pytest

REGISTRY = Path(__file__).resolve().parent


def test_revision_graph_is_linear_with_one_head():
    pytest.importorskip("alembic.config")  # "alembic" alone resolves to the local registry/alembic/ directory
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(REGISTRY / "alembic.ini"))
    cfg.set_main_option("script_location", str(REGISTRY / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"multiple heads: {heads}"
    walked = [rev.revision for rev in script.walk_revisions()]
    files = [p for p in (REGISTRY / "alembic" / "versions").glob("*.py") if p.name != "__init__.py"]
    assert len(walked) == len(files), f"{len(files)} revision files but the chain from head visits {len(walked)}"
    assert "002b_cme_bootstrap" in walked and "002c_legacy_tables_bootstrap" in walked
