from io import BytesIO


def _create_parse_job(client) -> str:
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_worker", "supplier_id": "sup_worker", "doc_type": "bid"},
        files={"file": ("worker.pdf", BytesIO(b"%PDF-1.4 worker"), "application/pdf")},
        headers={"Idempotency-Key": "idem_worker_upload_1", "x-tenant-id": "tenant_worker"},
    )
    assert upload.status_code == 202
    document_id = upload.json()["data"]["document_id"]
    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_worker_parse_1", "x-tenant-id": "tenant_worker"},
    )
    assert parse.status_code == 202
    return parse.json()["data"]["job_id"]


def test_internal_worker_drain_once_consumes_queue_and_runs_jobs(client):
    job_id = _create_parse_job(client)
    relay = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_worker"},
    )
    assert relay.status_code == 200
    assert relay.json()["data"]["queued_count"] >= 1

    drain = client.post(
        "/api/v1/internal/worker/queues/jobs/drain-once?max_messages=10",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_worker"},
    )
    assert drain.status_code == 200
    data = drain.json()["data"]
    assert data["processed"] >= 1
    assert data["succeeded"] >= 1

    job = client.get(f"/api/v1/jobs/{job_id}", headers={"x-tenant-id": "tenant_worker"})
    assert job.status_code == 200
    assert job.json()["data"]["status"] == "succeeded"

    empty = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_worker"},
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["message"] is None


def test_internal_worker_drain_requires_internal_header(client):
    resp = client.post("/api/v1/internal/worker/queues/jobs/drain-once")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
