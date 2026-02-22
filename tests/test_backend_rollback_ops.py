from __future__ import annotations

from app.ops.backend_rollback import switch_backends_to_sqlite, update_dotenv_for_sqlite


def test_switch_backends_to_sqlite_overrides_modes():
    env = {
        "BEA_STORE_BACKEND": "postgres",
        "BEA_QUEUE_BACKEND": "redis",
        "OTHER": "x",
    }
    updated = switch_backends_to_sqlite(env)
    assert updated["BEA_STORE_BACKEND"] == "sqlite"
    assert updated["BEA_QUEUE_BACKEND"] == "sqlite"
    assert updated["OTHER"] == "x"


def test_update_dotenv_for_sqlite_updates_and_appends():
    content = """# sample\nBEA_STORE_BACKEND=postgres\nX=1\n"""
    out = update_dotenv_for_sqlite(content)
    assert "BEA_STORE_BACKEND=sqlite" in out
    assert "BEA_QUEUE_BACKEND=sqlite" in out
    assert "X=1" in out
    assert out.endswith("\n")
