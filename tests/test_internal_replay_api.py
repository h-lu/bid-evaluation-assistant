def _eval_payload() -> dict:
    return {
        "project_id": "prj_replay",
        "supplier_id": "sup_replay",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 10},
    }


def test_internal_transition_updates_status(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_replay_1"},
    )
    job_id = created.json()["data"]["job_id"]

    resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/transition",
        json={"new_status": "running"},
        headers={"x-internal-debug": "true"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "running"


def test_internal_transition_requires_internal_header(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_replay_2"},
    )
    job_id = created.json()["data"]["job_id"]
    resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/transition",
        json={"new_status": "running"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_internal_transition_blocks_invalid_transition(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_replay_3"},
    )
    job_id = created.json()["data"]["job_id"]
    resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/transition",
        json={"new_status": "failed"},
        headers={"x-internal-debug": "true"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "WF_STATE_TRANSITION_INVALID"
