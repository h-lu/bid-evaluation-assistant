from app.store import store


def test_resume_with_valid_token_returns_202(client):
    evaluation_id = "ev_resume_ok"
    token = "rt_valid_1"
    store.register_resume_token(evaluation_id=evaluation_id, resume_token=token)

    resp = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": token,
            "decision": "approve",
            "comment": "looks good",
            "editor": {"reviewer_id": "u_reviewer_1"},
        },
        headers={"Idempotency-Key": "idem_resume_1"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["evaluation_id"] == evaluation_id
    assert body["data"]["job_id"].startswith("job_")
    assert body["data"]["status"] == "queued"
    logs = store.list_audit_logs_for_evaluation(
        evaluation_id=evaluation_id,
        tenant_id="tenant_default",
    )
    assert len(logs) == 1
    assert logs[0]["action"] == "resume_submitted"
    assert logs[0]["reviewer_id"] == "u_reviewer_1"
    assert logs[0]["decision"] == "approve"


def test_resume_with_invalid_token_returns_409(client):
    evaluation_id = "ev_resume_bad"
    store.register_resume_token(evaluation_id=evaluation_id, resume_token="rt_other")

    resp = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": "rt_invalid",
            "decision": "approve",
            "comment": "nope",
            "editor": {"reviewer_id": "u_reviewer_2"},
        },
        headers={"Idempotency-Key": "idem_resume_2"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "WF_INTERRUPT_RESUME_INVALID"


def test_resume_requires_reviewer_identity(client):
    evaluation_id = "ev_resume_need_reviewer"
    token = "rt_need_reviewer"
    store.register_resume_token(evaluation_id=evaluation_id, resume_token=token)

    resp = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": token,
            "decision": "approve",
            "comment": "missing editor",
        },
        headers={"Idempotency-Key": "idem_resume_need_reviewer"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "WF_INTERRUPT_REVIEWER_REQUIRED"


def test_resume_token_is_single_use(client):
    evaluation_id = "ev_resume_once"
    token = "rt_once_1"
    store.register_resume_token(evaluation_id=evaluation_id, resume_token=token)

    first = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": token,
            "decision": "approve",
            "comment": "first use",
            "editor": {"reviewer_id": "u_reviewer_3"},
        },
        headers={"Idempotency-Key": "idem_resume_once_1"},
    )
    assert first.status_code == 202

    second = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": token,
            "decision": "approve",
            "comment": "second use",
            "editor": {"reviewer_id": "u_reviewer_4"},
        },
        headers={"Idempotency-Key": "idem_resume_once_2"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "WF_INTERRUPT_RESUME_INVALID"


def test_get_citation_source_returns_required_fields(client):
    chunk_id = "ck_demo_1"
    store.register_citation_source(
        chunk_id=chunk_id,
        source={
            "chunk_id": chunk_id,
            "document_id": "doc_123",
            "filename": "demo.pdf",
            "page": 8,
            "bbox": [120.2, 310.0, 520.8, 365.4],
            "text": "原文片段",
            "context": "上下文",
            "viewport_hint": {"scale": 1.0, "unit": "pdf_point"},
        },
    )

    resp = client.get(f"/api/v1/citations/{chunk_id}/source")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["document_id"] == "doc_123"
    assert data["page"] == 8
    assert data["bbox"] == [120.2, 310.0, 520.8, 365.4]
    assert data["text"]
    assert data["context"]


def test_get_missing_citation_returns_404(client):
    resp = client.get("/api/v1/citations/ck_missing/source")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CITATION_NOT_FOUND"
