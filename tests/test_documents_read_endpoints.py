from io import BytesIO


def _upload_doc(client, tenant_id: str = "tenant_a", key: str = "idem_doc_read_upload") -> str:
    resp = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_doc", "supplier_id": "sup_doc", "doc_type": "bid"},
        files={"file": ("doc-read.pdf", BytesIO(b"%PDF-1.4 doc read"), "application/pdf")},
        headers={"Idempotency-Key": key, "x-tenant-id": tenant_id},
    )
    assert resp.status_code == 202
    return resp.json()["data"]["document_id"]


def test_get_document_returns_metadata(client):
    document_id = _upload_doc(client)
    resp = client.get(f"/api/v1/documents/{document_id}", headers={"x-tenant-id": "tenant_a"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["document_id"] == document_id
    assert data["project_id"] == "prj_doc"
    assert data["supplier_id"] == "sup_doc"
    assert data["doc_type"] == "bid"
    assert data["filename"] == "doc-read.pdf"


def test_get_document_chunks_returns_items_after_parse_success(client):
    document_id = _upload_doc(client, key="idem_doc_read_upload_2")
    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_doc_read_parse_1", "x-tenant-id": "tenant_a"},
    )
    job_id = parse.json()["data"]["job_id"]

    run = client.post(
        f"/api/v1/internal/jobs/{job_id}/run",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert run.status_code == 200

    chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert chunks.status_code == 200
    data = chunks.json()["data"]
    assert data["document_id"] == document_id
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["chunk_id"].startswith("ck_")
    assert item["chunk_hash"]
    assert item["document_id"] == document_id
    assert item["page"] >= 1
    assert len(item["bbox"]) == 4
    assert item["pages"]
    assert item["positions"]
    assert item["chunk_type"] == "text"
    assert item["parser"] == "mineru"


def test_get_document_cross_tenant_is_blocked(client):
    document_id = _upload_doc(client, tenant_id="tenant_a", key="idem_doc_read_upload_3")
    denied = client.get(f"/api/v1/documents/{document_id}", headers={"x-tenant-id": "tenant_b"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_get_document_chunks_cross_tenant_is_blocked(client):
    document_id = _upload_doc(client, tenant_id="tenant_a", key="idem_doc_read_upload_4")
    denied = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers={"x-tenant-id": "tenant_b"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"
