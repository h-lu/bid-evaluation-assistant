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
        },
        headers={"Idempotency-Key": "idem_resume_1"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["evaluation_id"] == evaluation_id
    assert body["data"]["job_id"].startswith("job_")
    assert body["data"]["status"] == "queued"


def test_resume_with_invalid_token_returns_409(client):
    evaluation_id = "ev_resume_bad"
    store.register_resume_token(evaluation_id=evaluation_id, resume_token="rt_other")

    resp = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        json={
            "resume_token": "rt_invalid",
            "decision": "approve",
            "comment": "nope",
        },
        headers={"Idempotency-Key": "idem_resume_2"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "WF_INTERRUPT_RESUME_INVALID"


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
