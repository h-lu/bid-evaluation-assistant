from io import BytesIO

from app.main import queue_backend
from app.store import store


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


def test_internal_worker_drain_requeues_with_backoff_delay(client, monkeypatch):
    job_id = _create_parse_job(client)
    enqueue = client.post(
        "/api/v1/internal/queue/jobs/enqueue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_worker"},
        json={"job_id": job_id, "job_type": "parse"},
    )
    assert enqueue.status_code == 200

    store.worker_retry_backoff_base_ms = 1500
    store.worker_retry_backoff_max_ms = 30000

    captured: dict[str, int] = {}
    real_nack = queue_backend.nack

    def _capture_nack(*, tenant_id: str, message_id: str, requeue: bool = True, delay_ms: int = 0):
        captured["delay_ms"] = delay_ms
        return real_nack(tenant_id=tenant_id, message_id=message_id, requeue=requeue, delay_ms=delay_ms)

    monkeypatch.setattr(queue_backend, "nack", _capture_nack)

    drain = client.post(
        "/api/v1/internal/worker/queues/jobs/drain-once?max_messages=1&transient_fail=true",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_worker"},
    )
    assert drain.status_code == 200
    assert drain.json()["data"]["retrying"] == 1
    assert captured.get("delay_ms", 0) >= 1500

    job = client.get(f"/api/v1/jobs/{job_id}", headers={"x-tenant-id": "tenant_worker"})
    assert job.status_code == 200
    assert job.json()["data"]["status"] == "retrying"
