def _eval_payload() -> dict:
    return {
        "project_id": "prj_cancel",
        "supplier_id": "sup_cancel",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {
            "include_doc_types": ["bid"],
            "force_hitl": False,
        },
        "query_options": {
            "mode_hint": "hybrid",
            "top_k": 30,
        },
    }


def test_cancel_job_returns_202_and_failed_status(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_cancel_create_1"},
    )
    job_id = created.json()["data"]["job_id"]

    resp = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={"Idempotency-Key": "idem_cancel_1"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["job_id"] == job_id
    assert data["status"] == "failed"
    assert data["error_code"] == "JOB_CANCELLED"


def test_cancel_job_requires_idempotency_key(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_cancel_create_2"},
    )
    job_id = created.json()["data"]["job_id"]
    resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_MISSING"


def test_cancel_terminal_job_returns_conflict(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_cancel_create_3"},
    )
    job_id = created.json()["data"]["job_id"]

    # Simulate completion first
    client.get(f"/api/v1/jobs/{job_id}")
    from app.store import store

    store.transition_job_status(job_id=job_id, new_status="running")
    store.transition_job_status(job_id=job_id, new_status="succeeded")

    resp = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={"Idempotency-Key": "idem_cancel_3"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "JOB_CANCEL_CONFLICT"
