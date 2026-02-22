from __future__ import annotations

import pytest

from app.repositories.jobs import InMemoryJobsRepository, PostgresJobsRepository


def _job_dict() -> dict:
    return {
        "job_id": "job_repo_1",
        "job_type": "evaluation",
        "status": "queued",
        "retry_count": 0,
        "thread_id": "thr_repo_1",
        "trace_id": "trace_repo_1",
        "resource": {"type": "evaluation", "id": "ev_repo_1"},
        "payload": {"x": 1},
        "last_error": None,
    }


def test_inmemory_jobs_repository_scopes_by_tenant():
    jobs: dict[str, dict] = {}
    repo = InMemoryJobsRepository(jobs)
    repo.create(job={**_job_dict(), "tenant_id": "tenant_a"})

    assert repo.get(tenant_id="tenant_a", job_id="job_repo_1") is not None
    assert repo.get(tenant_id="tenant_b", job_id="job_repo_1") is None


def test_postgres_jobs_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresJobsRepository(tx_runner=DummyRunner(), table_name="jobs;drop table jobs")


def test_postgres_jobs_repository_create_and_get_with_fake_runner():
    statements: list[tuple[str, tuple | None]] = []
    current_row: list[tuple] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append((query, params))
            if query.strip().lower().startswith("select"):
                self._row = current_row[0] if current_row else None
            else:
                self._row = None

        def fetchone(self):
            return self._row

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    class FakeRunner:
        def __init__(self):
            self.tenants: list[str] = []

        def run_in_tx(self, *, tenant_id: str, fn):
            self.tenants.append(tenant_id)
            return fn(FakeConnection())

    runner = FakeRunner()
    repo = PostgresJobsRepository(tx_runner=runner, table_name="jobs")
    created = repo.create(tenant_id="tenant_a", job=_job_dict())
    assert created["tenant_id"] == "tenant_a"
    assert runner.tenants[0] == "tenant_a"
    insert_sql, insert_params = statements[0]
    assert "INSERT INTO jobs" in insert_sql
    assert insert_params is not None
    assert insert_params[1] == "tenant_a"

    current_row.append(
        (
            "job_repo_1",
            "tenant_a",
            "evaluation",
            "queued",
            0,
            "thr_repo_1",
            "trace_repo_1",
            {"type": "evaluation", "id": "ev_repo_1"},
            {"x": 1},
            None,
        )
    )
    loaded = repo.get(tenant_id="tenant_a", job_id="job_repo_1")
    assert loaded is not None
    assert loaded["job_id"] == "job_repo_1"
    assert loaded["tenant_id"] == "tenant_a"
    select_sql, select_params = statements[-1]
    assert "WHERE tenant_id = %s AND job_id = %s" in select_sql
    assert select_params == ("tenant_a", "job_repo_1")
