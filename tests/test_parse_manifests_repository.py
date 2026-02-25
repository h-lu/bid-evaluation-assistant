from __future__ import annotations

import pytest

from app.repositories.parse_manifests import (
    InMemoryParseManifestsRepository,
    PostgresParseManifestsRepository,
)


def _manifest() -> dict:
    return {
        "job_id": "job_parse_repo_1",
        "run_id": "prun_1",
        "document_id": "doc_1",
        "tenant_id": "tenant_a",
        "selected_parser": "mineru",
        "parser_version": "v0",
        "fallback_chain": ["docling", "ocr"],
        "input_files": [{"name": "a.pdf"}],
        "started_at": None,
        "ended_at": None,
        "status": "queued",
        "error_code": None,
    }


def test_inmemory_parse_manifest_repository_scopes_by_tenant():
    data: dict[str, dict] = {}
    repo = InMemoryParseManifestsRepository(data)
    m = _manifest()
    repo.upsert(tenant_id=m["tenant_id"], manifest=m)
    assert repo.get(tenant_id="tenant_a", job_id="job_parse_repo_1") is not None
    assert repo.get(tenant_id="tenant_b", job_id="job_parse_repo_1") is None


def test_postgres_parse_manifest_repository_rejects_invalid_table_name():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresParseManifestsRepository(tx_runner=DummyRunner(), table_name="x;drop table y")


def test_postgres_parse_manifest_repository_upsert_and_get():
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
    repo = PostgresParseManifestsRepository(tx_runner=runner)
    created = repo.upsert(tenant_id="tenant_a", manifest=_manifest())
    assert created["tenant_id"] == "tenant_a"
    assert "INSERT INTO parse_manifests" in statements[0][0]

    current_row.append(
        (
            "job_parse_repo_1",
            "prun_1",
            "doc_1",
            "tenant_a",
            "mineru",
            "v0",
            ["docling", "ocr"],
            [{"name": "a.pdf"}],
            None,
            None,
            "queued",
            None,
        )
    )
    loaded = repo.get(tenant_id="tenant_a", job_id="job_parse_repo_1")
    assert loaded is not None
    assert loaded["job_id"] == "job_parse_repo_1"
    assert loaded["fallback_chain"] == ["docling", "ocr"]
