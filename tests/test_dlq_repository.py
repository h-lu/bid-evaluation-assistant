from __future__ import annotations

import pytest

from app.repositories.dlq_items import InMemoryDlqItemsRepository, PostgresDlqItemsRepository


def _item() -> dict:
    return {
        "dlq_id": "dlq_repo_1",
        "job_id": "job_repo_1",
        "tenant_id": "tenant_a",
        "error_class": "transient",
        "error_code": "RAG_UPSTREAM_UNAVAILABLE",
        "status": "open",
    }


def test_inmemory_dlq_repository_upsert_get_and_list():
    data: dict[str, dict] = {}
    repo = InMemoryDlqItemsRepository(data)
    repo.upsert(item=_item())
    got = repo.get(tenant_id="tenant_a", dlq_id="dlq_repo_1")
    assert got is not None
    assert got["status"] == "open"
    assert repo.get(tenant_id="tenant_b", dlq_id="dlq_repo_1") is None
    listed = repo.list(tenant_id="tenant_a")
    assert len(listed) == 1


def test_postgres_dlq_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresDlqItemsRepository(tx_runner=DummyRunner(), table_name="x;drop table y")


def test_postgres_dlq_repository_upsert_get_and_list():
    statements: list[tuple[str, tuple | None]] = []
    current_row: list[tuple] = []
    current_rows: list[tuple] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append((query, params))
            text = query.strip().lower()
            if text.startswith("select") and "limit 1" in text:
                self._row = current_row[0] if current_row else None
                self._rows = []
            elif text.startswith("select"):
                self._row = None
                self._rows = list(current_rows)
            else:
                self._row = None
                self._rows = []

        def fetchone(self):
            return self._row

        def fetchall(self):
            return self._rows

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    class FakeRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(FakeConn())

    repo = PostgresDlqItemsRepository(tx_runner=FakeRunner())
    repo.upsert(item=_item())
    assert "INSERT INTO dlq_items" in statements[0][0]

    current_row.append(({"dlq_id": "dlq_repo_1", "tenant_id": "tenant_a", "status": "open"},))
    got = repo.get(tenant_id="tenant_a", dlq_id="dlq_repo_1")
    assert got is not None
    assert got["dlq_id"] == "dlq_repo_1"

    current_rows.append(({"dlq_id": "dlq_repo_1", "tenant_id": "tenant_a", "status": "open"},))
    listed = repo.list(tenant_id="tenant_a")
    assert len(listed) == 1
