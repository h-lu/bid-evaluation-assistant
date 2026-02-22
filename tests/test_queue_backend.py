from __future__ import annotations

from pathlib import Path

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

    nack = q.nack(tenant_id="tenant_a", message_id=msg.message_id, requeue=True)
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


def test_sqlite_queue_persists_pending_messages_between_instances(tmp_path: Path):
    db_path = tmp_path / "queue.sqlite3"
    env = {
        "BEA_QUEUE_BACKEND": "sqlite",
        "BEA_QUEUE_SQLITE_PATH": str(db_path),
    }
    queue1 = create_queue_from_env(env)
    queue1.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_persist_1"})
    queue1.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_persist_2"})

    queue2 = create_queue_from_env(env)
    first = queue2.dequeue(tenant_id="tenant_a", queue_name="jobs")
    second = queue2.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert first is not None
    assert second is not None
    assert first.payload["job_id"] == "job_persist_1"
    assert second.payload["job_id"] == "job_persist_2"


def test_sqlite_queue_nack_requeue_and_ack_lifecycle(tmp_path: Path):
    db_path = tmp_path / "queue_lifecycle.sqlite3"
    env = {
        "BEA_QUEUE_BACKEND": "sqlite",
        "BEA_QUEUE_SQLITE_PATH": str(db_path),
    }
    queue = create_queue_from_env(env)
    sent = queue.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_retry"})
    got = queue.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert got is not None
    assert got.message_id == sent.message_id

    nacked = queue.nack(tenant_id="tenant_a", message_id=got.message_id, requeue=True)
    assert nacked is not None
    assert nacked.attempt == 1

    replay = queue.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert replay is not None
    assert replay.message_id == got.message_id
    assert replay.attempt == 1
    queue.ack(tenant_id="tenant_a", message_id=replay.message_id)

    queue_reloaded = create_queue_from_env(env)
    assert queue_reloaded.pending_count(tenant_id="tenant_a", queue_name="jobs") == 0


def test_queue_factory_supports_sqlite_backend(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BEA_QUEUE_BACKEND", "sqlite")
    monkeypatch.setenv("BEA_QUEUE_SQLITE_PATH", str(tmp_path / "queue_factory.sqlite3"))
    queue = create_queue_from_env()
    assert queue.__class__.__name__ == "SqliteQueueBackend"


def test_queue_ack_and_nack_require_same_tenant():
    q = InMemoryQueueBackend()
    sent = q.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": "job_tenant"})
    got = q.dequeue(tenant_id="tenant_a", queue_name="jobs")
    assert got is not None

    try:
        q.ack(tenant_id="tenant_b", message_id=sent.message_id)
    except RuntimeError as exc:
        assert "tenant mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for cross-tenant ack")

    try:
        q.nack(tenant_id="tenant_b", message_id=sent.message_id, requeue=True)
    except RuntimeError as exc:
        assert "tenant mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for cross-tenant nack")
