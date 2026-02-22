from app.store import store


def _eval_payload() -> dict:
    return {
        "project_id": "prj_internal",
        "supplier_id": "sup_internal",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 10},
    }


def test_internal_outbox_list_and_publish(client):
    create = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_internal_1", "x-tenant-id": "tenant_a"},
        json=_eval_payload(),
    )
    assert create.status_code == 202
    created_job_id = create.json()["data"]["job_id"]

    listed = client.get(
        "/api/v1/internal/outbox/events",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert items
    job_events = [x for x in items if x["aggregate_id"] == created_job_id]
    assert job_events
    event_id = job_events[-1]["event_id"]
    assert job_events[-1]["status"] == "pending"

    publish = client.post(
        f"/api/v1/internal/outbox/events/{event_id}/publish",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert publish.status_code == 200
    assert publish.json()["data"]["status"] == "published"


def test_internal_outbox_requires_internal_header(client):
    resp = client.get("/api/v1/internal/outbox/events")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_internal_queue_enqueue_and_dequeue_with_tenant_scope(client):
    enqueue = client.post(
        "/api/v1/internal/queue/jobs/enqueue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
        json={"job_id": "job_queue_1"},
    )
    assert enqueue.status_code == 200
    msg_id = enqueue.json()["data"]["message_id"]

    dequeue_same_tenant = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert dequeue_same_tenant.status_code == 200
    message = dequeue_same_tenant.json()["data"]["message"]
    assert message is not None
    assert message["message_id"] == msg_id
    assert message["payload"]["job_id"] == "job_queue_1"

    dequeue_other_tenant = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_b"},
    )
    assert dequeue_other_tenant.status_code == 200
    assert dequeue_other_tenant.json()["data"]["message"] is None


def test_internal_queue_requires_internal_header(client):
    resp = client.post("/api/v1/internal/queue/jobs/enqueue", json={"job_id": "x"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_internal_outbox_relay_enqueues_queue_messages(client):
    create = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_internal_relay_1", "x-tenant-id": "tenant_a"},
        json=_eval_payload(),
    )
    assert create.status_code == 202
    created_job_id = create.json()["data"]["job_id"]

    relay = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert relay.status_code == 200
    assert relay.json()["data"]["published_count"] >= 1

    dequeue = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert dequeue.status_code == 200
    message = dequeue.json()["data"]["message"]
    assert message is not None
    assert message["payload"]["job_id"] == created_job_id
    assert message["payload"]["tenant_id"] == "tenant_a"
    assert message["payload"]["trace_id"]
    assert message["payload"]["job_type"] == "evaluation"

    listed = client.get(
        "/api/v1/internal/outbox/events?status=published",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert listed.status_code == 200
    assert any(x["aggregate_id"] == created_job_id for x in listed.json()["data"]["items"])


def test_internal_outbox_relay_is_idempotent_for_published_events(client):
    create = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_internal_relay_2", "x-tenant-id": "tenant_a"},
        json=_eval_payload(),
    )
    assert create.status_code == 202

    first = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert first.status_code == 200
    assert first.json()["data"]["published_count"] >= 1

    second = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert second.status_code == 200
    assert second.json()["data"]["published_count"] == 0


def test_internal_queue_ack_and_nack_flow(client):
    enqueue = client.post(
        "/api/v1/internal/queue/jobs/enqueue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
        json={"job_id": "job_ack_nack"},
    )
    assert enqueue.status_code == 200

    first = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert first.status_code == 200
    message = first.json()["data"]["message"]
    assert message is not None
    message_id = message["message_id"]

    nack = client.post(
        "/api/v1/internal/queue/jobs/nack",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
        json={"message_id": message_id, "requeue": True},
    )
    assert nack.status_code == 200
    nacked_message = nack.json()["data"]["message"]
    assert nacked_message is not None
    assert nacked_message["attempt"] == 1

    second = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert second.status_code == 200
    replay = second.json()["data"]["message"]
    assert replay is not None
    assert replay["message_id"] == message_id
    assert replay["attempt"] == 1

    ack = client.post(
        "/api/v1/internal/queue/jobs/ack",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
        json={"message_id": message_id},
    )
    assert ack.status_code == 200
    assert ack.json()["data"]["acked"] is True

    empty = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["message"] is None


def test_internal_queue_ack_nack_blocks_cross_tenant(client):
    enqueue = client.post(
        "/api/v1/internal/queue/jobs/enqueue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
        json={"job_id": "job_cross_tenant"},
    )
    assert enqueue.status_code == 200

    first = client.post(
        "/api/v1/internal/queue/jobs/dequeue",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert first.status_code == 200
    message = first.json()["data"]["message"]
    assert message is not None
    message_id = message["message_id"]

    cross_ack = client.post(
        "/api/v1/internal/queue/jobs/ack",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_b"},
        json={"message_id": message_id},
    )
    assert cross_ack.status_code == 403
    assert cross_ack.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    cross_nack = client.post(
        "/api/v1/internal/queue/jobs/nack",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_b"},
        json={"message_id": message_id, "requeue": True},
    )
    assert cross_nack.status_code == 403
    assert cross_nack.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

def test_internal_outbox_relay_is_idempotent_per_event_and_consumer(client):
    create = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_internal_relay_consumer_1", "x-tenant-id": "tenant_a"},
        json=_eval_payload(),
    )
    assert create.status_code == 202

    pending = client.get(
        "/api/v1/internal/outbox/events?status=pending",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert pending.status_code == 200
    event_id = pending.json()["data"]["items"][0]["event_id"]

    first = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50&consumer_name=worker-a",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert first.status_code == 200
    assert first.json()["data"]["published_count"] >= 1

    # Simulate replay window where event appears pending again; same consumer must not duplicate side effects.
    store.domain_events_outbox[event_id]["status"] = "pending"
    store.domain_events_outbox[event_id]["published_at"] = None

    second_same_consumer = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50&consumer_name=worker-a",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert second_same_consumer.status_code == 200
    assert second_same_consumer.json()["data"]["published_count"] == 0

    store.domain_events_outbox[event_id]["status"] = "pending"
    store.domain_events_outbox[event_id]["published_at"] = None

    third_other_consumer = client.post(
        "/api/v1/internal/outbox/relay?queue_name=jobs&limit=50&consumer_name=worker-b",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert third_other_consumer.status_code == 200
    assert third_other_consumer.json()["data"]["published_count"] >= 1
