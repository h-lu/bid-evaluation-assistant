from io import BytesIO


def _create_jobs(client):
    client.post(
        "/api/v1/evaluations",
        json={
            "project_id": "prj_jobs",
            "supplier_id": "sup_jobs",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
        },
        headers={"Idempotency-Key": "idem_jobs_eval_1"},
    )
    files = {"file": ("jobs.pdf", BytesIO(b"%PDF-1.4 jobs"), "application/pdf")}
    client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_jobs", "supplier_id": "sup_jobs", "doc_type": "bid"},
        files=files,
        headers={"Idempotency-Key": "idem_jobs_upload_1"},
    )


def test_list_jobs_returns_items_and_total(client):
    _create_jobs(client)
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


def test_list_jobs_filters_by_type(client):
    _create_jobs(client)
    resp = client.get("/api/v1/jobs?type=evaluation")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert items
    assert all(item["job_type"] == "evaluation" for item in items)


def test_list_jobs_supports_cursor_and_limit(client):
    _create_jobs(client)
    first = client.get("/api/v1/jobs?limit=1")
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert len(first_data["items"]) == 1
    assert first_data["next_cursor"] is not None

    second = client.get(f"/api/v1/jobs?limit=1&cursor={first_data['next_cursor']}")
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert len(second_data["items"]) >= 1
