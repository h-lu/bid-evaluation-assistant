from __future__ import annotations

import pytest

from app.repositories.documents import InMemoryDocumentsRepository, PostgresDocumentsRepository


def _document() -> dict:
    return {
        "document_id": "doc_repo_1",
        "tenant_id": "tenant_a",
        "project_id": "prj_a",
        "supplier_id": "sup_a",
        "doc_type": "bid",
        "filename": "bid.pdf",
        "file_sha256": "abc",
        "file_size": 12,
        "status": "uploaded",
    }


def _chunk() -> dict:
    return {
        "chunk_id": "ck_repo_1",
        "chunk_hash": "hash_repo_1",
        "document_id": "doc_repo_1",
        "pages": [1],
        "positions": [{"page": 1, "bbox": [0, 0, 1, 1], "start": 0, "end": 10}],
        "section": "Sec",
        "heading_path": ["H1"],
        "chunk_type": "text",
        "parser": "mineru",
        "parser_version": "v0",
        "text": "hello",
    }


def test_inmemory_documents_repository_scopes_by_tenant():
    documents: dict[str, dict] = {}
    chunks: dict[str, list[dict]] = {}
    repo = InMemoryDocumentsRepository(documents, chunks)
    repo.upsert(document=_document())
    repo.replace_chunks(tenant_id="tenant_a", document_id="doc_repo_1", chunks=[_chunk()])

    assert repo.get(tenant_id="tenant_a", document_id="doc_repo_1") is not None
    assert repo.get(tenant_id="tenant_b", document_id="doc_repo_1") is None
    assert len(repo.list_chunks(tenant_id="tenant_a", document_id="doc_repo_1")) == 1
    assert repo.list_chunks(tenant_id="tenant_b", document_id="doc_repo_1") == []


def test_postgres_documents_repository_rejects_invalid_table_names():
    class DummyRunner:
        def run_in_tx(self, *, tenant_id: str, fn):
            return fn(None)

    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PostgresDocumentsRepository(tx_runner=DummyRunner(), documents_table="documents;drop table documents")


def test_postgres_documents_repository_upsert_get_replace_and_list():
    statements: list[tuple[str, tuple | None]] = []
    current_doc_row: list[tuple] = []
    current_chunk_rows: list[list[tuple]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None):
            statements.append((query, params))
            lower = query.strip().lower()
            if lower.startswith("select document_id"):
                self._one = current_doc_row[0] if current_doc_row else None
                self._many = []
                return
            if lower.startswith("select chunk_id"):
                self._many = current_chunk_rows[0] if current_chunk_rows else []
                self._one = None
                return
            self._one = None
            self._many = []

        def fetchone(self):
            return self._one

        def fetchall(self):
            return self._many

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
    repo = PostgresDocumentsRepository(tx_runner=runner)
    doc = repo.upsert(tenant_id="tenant_a", document=_document())
    assert doc["tenant_id"] == "tenant_a"
    assert runner.tenants[0] == "tenant_a"
    assert "INSERT INTO documents" in statements[0][0]

    current_doc_row.append(("doc_repo_1", "tenant_a", "prj_a", "sup_a", "bid", "bid.pdf", "abc", 12, "uploaded", None))
    loaded = repo.get(tenant_id="tenant_a", document_id="doc_repo_1")
    assert loaded is not None
    assert loaded["document_id"] == "doc_repo_1"

    replaced = repo.replace_chunks(tenant_id="tenant_a", document_id="doc_repo_1", chunks=[_chunk()])
    assert len(replaced) == 1
    assert any("DELETE FROM document_chunks" in x[0] for x in statements)
    assert any("INSERT INTO document_chunks" in x[0] for x in statements)

    current_chunk_rows.append(
        [
            (
                "ck_repo_1",
                "doc_repo_1",
                "hash_repo_1",
                [1],
                [{"page": 1, "bbox": [0, 0, 1, 1], "start": 0, "end": 10}],
                "Sec",
                ["H1"],
                "text",
                "mineru",
                "v0",
                "hello",
            )
        ]
    )
    listed = repo.list_chunks(tenant_id="tenant_a", document_id="doc_repo_1")
    assert len(listed) == 1
    assert listed[0]["chunk_id"] == "ck_repo_1"
    assert listed[0]["chunk_hash"] == "hash_repo_1"
