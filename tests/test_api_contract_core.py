from io import BytesIO


def _evaluation_payload() -> dict:
    return {
        "project_id": "prj_a",
        "supplier_id": "sup_a",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {
            "include_doc_types": ["bid", "attachment"],
            "force_hitl": False,
        },
        "query_options": {
            "mode_hint": "hybrid",
            "top_k": 60,
        },
    }


def test_create_evaluation_returns_202_with_required_fields(client):
    resp = client.post(
        "/api/v1/evaluations",
        json=_evaluation_payload(),
        headers={"Idempotency-Key": "idem_core_eval_1"},
    )
    assert resp.status_code == 202

    body = resp.json()
    data = body["data"]
    assert body["success"] is True
    assert data["evaluation_id"].startswith("ev_")
    assert data["job_id"].startswith("job_")
    assert data["status"] == "queued"


def test_documents_upload_returns_202_with_next_link(client):
    files = {"file": ("test.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    data = {
        "project_id": "prj_u1",
        "supplier_id": "sup_u1",
        "doc_type": "bid",
    }
    resp = client.post(
        "/api/v1/documents/upload",
        data=data,
        files=files,
        headers={"Idempotency-Key": "idem_upload_1"},
    )
    assert resp.status_code == 202

    payload = resp.json()["data"]
    assert payload["document_id"].startswith("doc_")
    assert payload["job_id"].startswith("job_")
    assert payload["status"] == "queued"
    assert payload["next"].endswith(payload["job_id"])


def test_get_job_status_returns_job_payload(client):
    create = client.post(
        "/api/v1/evaluations",
        json=_evaluation_payload(),
        headers={"Idempotency-Key": "idem_core_eval_2"},
    )
    job_id = create.json()["data"]["job_id"]

    resp = client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    assert body["data"]["job_id"] == job_id
    assert body["data"]["status"] in {
        "queued",
        "running",
        "retrying",
        "succeeded",
        "failed",
        "needs_manual_decision",
        "dlq_pending",
        "dlq_recorded",
    }


def test_get_missing_job_returns_error_envelope(client):
    resp = client.get("/api/v1/jobs/job_missing")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "JOB_NOT_FOUND"
