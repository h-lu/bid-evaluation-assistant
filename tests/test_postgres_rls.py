from __future__ import annotations

import pytest

from app.db.rls import PostgresRlsManager


def test_postgres_rls_manager_requires_dsn():
    with pytest.raises(ValueError, match="POSTGRES_DSN"):
        PostgresRlsManager("")


def test_postgres_rls_manager_rejects_invalid_table_name():
    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresRlsManager("postgresql://x", tables=["jobs", "x;drop table y"])


def test_postgres_rls_manager_applies_rls_statements(monkeypatch):
    statements: list[str] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append(" ".join(query.strip().split()))

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
            self.dsns: list[str] = []
            self.connection = FakeConnection()

        def connect(self, dsn: str):
            self.dsns.append(dsn)
            return self.connection

    fake = FakePsycopg()
    monkeypatch.setattr("app.db.rls._import_psycopg", lambda: fake)

    manager = PostgresRlsManager("postgresql://user:pass@localhost:5432/bea", tables=["jobs", "dlq_items"])
    applied = manager.apply()

    assert applied == ["jobs", "dlq_items"]
    assert fake.dsns == ["postgresql://user:pass@localhost:5432/bea"]
    assert any("ALTER TABLE jobs ENABLE ROW LEVEL SECURITY" in x for x in statements)
    assert any("FORCE ROW LEVEL SECURITY" in x for x in statements)
    assert any("CREATE POLICY jobs_tenant_isolation" in x for x in statements)
    assert any("CREATE POLICY dlq_items_tenant_isolation" in x for x in statements)
    assert fake.connection.committed is True
