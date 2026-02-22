from __future__ import annotations

from app.queue_backend import InMemoryQueueBackend, create_queue_from_env


def test_queue_backend_keeps_tenant_isolation():
    q = InMemoryQueueBackend()
    q.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_a"})
    q.enqueue(tenant_id="tenant_b", queue_name="jobs", payload={"job_id": "job_b"})

    msg_a = q.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert msg_a is not None
    assert msg_a.payload["job_id"] == "job_a"

    msg_b = q.dequeue(tenant_id="tenant_b", queue_name="jobs")
    assert msg_b is not None
    assert msg_b.payload["job_id"] == "job_b"


def test_queue_nack_requeues_with_attempt_increment():
    q = InMemoryQueueBackend()
    enqueued = q.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_1"})
    msg = q.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert msg is not None
    assert msg.message_id == enqueued.message_id

    nack = q.nack(message_id=msg.message_id, requeue=True)
    assert nack is not None
    assert nack.attempt == 1
    assert q.pending_count(tenant_id="tenant_a", queue_name="jobs") == 1

    replay = q.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert replay is not None
    assert replay.message_id == msg.message_id
    assert replay.attempt == 1


def test_queue_factory_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("BEA_QUEUE_BACKEND", raising=False)
    q = create_queue_from_env()
    assert isinstance(q, InMemoryQueueBackend)


def test_queue_factory_rejects_unsupported_backend(monkeypatch):
    monkeypatch.setenv("BEA_QUEUE_BACKEND", "redis")
    try:
        create_queue_from_env()
    except RuntimeError as exc:
        assert "unsupported queue backend" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for unsupported queue backend")
