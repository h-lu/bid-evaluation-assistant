from __future__ import annotations

import pytest

from app.repositories.audit_logs import InMemoryAuditLogsRepository, PostgresAuditLogsRepository


def _log() -> dict:
    return {
        "audit_id": "audit_repo_1",
        "tenant_id": "tenant_a",
        "evaluation_id": "ev_repo_1",
        "action": "resume_submitted",
        "trace_id": "trace_repo_1",
        "occurred_at": "2026-02-22T00:00:00+00:00",
    }


def test_inmemory_audit_repository_append_and_list_for_evaluation():
    data: list[dict] = []
    repo = InMemoryAuditLogsRepository(data)
    repo.append(log=_log())
    rows = repo.list_for_evaluation(tenant_id="tenant_a", evaluation_id="ev_repo_1")
    assert len(rows) == 1
    assert rows[0]["audit_id"] == "audit_repo_1"
    assert repo.list_for_evaluation(tenant_id="tenant_b", evaluation_id="ev_repo_1") == []


def test_postgres_audit_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresAuditLogsRepository(tx_runner=DummyRunner(), table_name="x;drop table y")


def test_postgres_audit_repository_append_and_list_for_evaluation():
    statements: list[tuple[str, tuple | None]] = []
    rows: list[tuple] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append((query, params))
            if query.strip().lower().startswith("select"):
                self._rows = list(rows)
            else:
                self._rows = []

        def fetchall(self):
            return self._rows

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    class FakeRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(FakeConn())

    repo = PostgresAuditLogsRepository(tx_runner=FakeRunner())
    repo.append(log=_log())
    assert "INSERT INTO audit_logs" in statements[0][0]

    rows.append(({"audit_id": "audit_repo_1", "tenant_id": "tenant_a", "evaluation_id": "ev_repo_1"},))
    loaded = repo.list_for_evaluation(tenant_id="tenant_a", evaluation_id="ev_repo_1")
    assert loaded[0]["audit_id"] == "audit_repo_1"
