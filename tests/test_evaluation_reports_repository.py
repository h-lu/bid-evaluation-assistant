from __future__ import annotations

import pytest

from app.repositories.evaluation_reports import (
    InMemoryEvaluationReportsRepository,
    PostgresEvaluationReportsRepository,
)


def _report() -> dict:
    return {
        "evaluation_id": "ev_repo_1",
        "supplier_id": "sup_1",
        "total_score": 88.5,
        "confidence": 0.78,
        "citation_coverage": 1.0,
        "risk_level": "medium",
        "criteria_results": [{"criteria_id": "delivery", "citations": ["ck_1"]}],
        "citations": ["ck_1"],
        "needs_human_review": False,
        "trace_id": "trace_1",
        "tenant_id": "tenant_a",
        "thread_id": "thr_1",
        "interrupt": None,
    }


def test_inmemory_evaluation_reports_repository_scopes_by_tenant():
    reports: dict[str, dict] = {}
    repo = InMemoryEvaluationReportsRepository(reports)
    repo.upsert(report=_report())

    assert repo.get(tenant_id="tenant_a", evaluation_id="ev_repo_1") is not None
    assert repo.get(tenant_id="tenant_b", evaluation_id="ev_repo_1") is None


def test_postgres_evaluation_reports_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresEvaluationReportsRepository(tx_runner=DummyRunner(), table_name="x;drop table y")


def test_postgres_evaluation_reports_repository_upsert_and_get():
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

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    class FakeRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(FakeConn())

    repo = PostgresEvaluationReportsRepository(tx_runner=FakeRunner())
    created = repo.upsert(tenant_id="tenant_a", report=_report())
    assert created["tenant_id"] == "tenant_a"
    assert "INSERT INTO evaluation_reports" in statements[0][0]

    current_row.append(({"evaluation_id": "ev_repo_1", "tenant_id": "tenant_a", "interrupt": None},))
    loaded = repo.get(tenant_id="tenant_a", evaluation_id="ev_repo_1")
    assert loaded is not None
    assert loaded["evaluation_id"] == "ev_repo_1"
