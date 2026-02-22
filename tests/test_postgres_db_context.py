from __future__ import annotations

import pytest

from app.db.postgres import PostgresTxRunner


def test_postgres_tx_runner_requires_dsn():
    with pytest.raises(ValueError, match="POSTGRES_DSN"):
        PostgresTxRunner("")


def test_postgres_tx_runner_requires_tenant_id():
    runner = PostgresTxRunner("postgresql://user:pass@localhost:5432/bea")
    with pytest.raises(ValueError, match="tenant_id"):
        runner.run_in_tx(tenant_id="", fn=lambda _conn: None)


def test_postgres_tx_runner_sets_tenant_and_commits(monkeypatch):
    statements: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append((query, params))

    class FakeConnection:
        def __init__(self):
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

    class FakePsycopg:
        def __init__(self):
            self.connection = FakeConnection()
            self.dsn_calls: list[str] = []

        def connect(self, dsn: str):
            self.dsn_calls.append(dsn)
            return self.connection

    fake_driver = FakePsycopg()
    monkeypatch.setattr("app.db.postgres._import_psycopg", lambda: fake_driver)

    runner = PostgresTxRunner("postgresql://user:pass@localhost:5432/bea")
    result = runner.run_in_tx(tenant_id="tenant_a", fn=lambda _conn: {"ok": True})

    assert result == {"ok": True}
    assert fake_driver.dsn_calls == ["postgresql://user:pass@localhost:5432/bea"]
    assert statements[0][0] == "SELECT set_config('app.current_tenant', %s, true)"
    assert statements[0][1] == ("tenant_a",)
    assert fake_driver.connection.committed is True
