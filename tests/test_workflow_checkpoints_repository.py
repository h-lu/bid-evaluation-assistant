from __future__ import annotations

import pytest

from app.repositories.workflow_checkpoints import (
    InMemoryWorkflowCheckpointsRepository,
    PostgresWorkflowCheckpointsRepository,
)


def _checkpoint() -> dict:
    return {
        "checkpoint_id": "cp_repo_1",
        "thread_id": "thr_repo_1",
        "job_id": "job_repo_1",
        "seq": 1,
        "node": "job_started",
        "status": "running",
        "payload": {"job_type": "parse"},
        "tenant_id": "tenant_a",
        "created_at": "2026-02-22T00:00:00+00:00",
    }


def test_inmemory_workflow_repository_append_and_list_scoped():
    data: dict[str, list[dict]] = {}
    repo = InMemoryWorkflowCheckpointsRepository(data)
    repo.append(checkpoint=_checkpoint())
    rows = repo.list(thread_id="thr_repo_1", tenant_id="tenant_a", limit=20)
    assert len(rows) == 1
    assert rows[0]["checkpoint_id"] == "cp_repo_1"
    assert repo.list(thread_id="thr_repo_1", tenant_id="tenant_b", limit=20) == []


def test_postgres_workflow_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresWorkflowCheckpointsRepository(tx_runner=DummyRunner(), table_name="x;drop table y")


def test_postgres_workflow_repository_append_and_list():
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

    repo = PostgresWorkflowCheckpointsRepository(tx_runner=FakeRunner())
    repo.append(checkpoint=_checkpoint())
    assert "INSERT INTO workflow_checkpoints" in statements[0][0]

    rows.append(({"checkpoint_id": "cp_repo_1", "thread_id": "thr_repo_1", "tenant_id": "tenant_a", "seq": 1},))
    loaded = repo.list(thread_id="thr_repo_1", tenant_id="tenant_a", limit=10)
    assert loaded[0]["checkpoint_id"] == "cp_repo_1"
