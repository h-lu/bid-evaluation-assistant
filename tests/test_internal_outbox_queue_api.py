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
