def _eval_payload() -> dict:
    return {
        "project_id": "prj_report",
        "supplier_id": "sup_report",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
    }


def test_get_evaluation_report_returns_scoring_payload(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_report_1", "x-tenant-id": "tenant_a"},
    )
    evaluation_id = created.json()["data"]["evaluation_id"]

    resp = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["evaluation_id"] == evaluation_id
    assert data["supplier_id"] == "sup_report"
    assert isinstance(data["total_score"], float)
    assert 0 <= data["confidence"] <= 1
    assert 0 <= data["citation_coverage"] <= 1
    assert data["criteria_results"]
    assert all(item["citations"] for item in data["criteria_results"])
    assert data["citations"]
    assert data["interrupt"] is None


def test_get_evaluation_report_missing_returns_404(client):
    resp = client.get("/api/v1/evaluations/ev_missing/report")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "EVALUATION_REPORT_NOT_FOUND"


def test_get_evaluation_report_cross_tenant_is_blocked(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_report_2", "x-tenant-id": "tenant_a"},
    )
    evaluation_id = created.json()["data"]["evaluation_id"]

    denied = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_b"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_report_force_hitl_includes_interrupt_payload(client):
    payload = _eval_payload()
    payload["evaluation_scope"]["force_hitl"] = True
    created = client.post(
        "/api/v1/evaluations",
        json=payload,
        headers={"Idempotency-Key": "idem_report_hitl_1", "x-tenant-id": "tenant_a"},
    )
    evaluation_id = created.json()["data"]["evaluation_id"]

    resp = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["needs_human_review"] is True
    interrupt = data["interrupt"]
    assert interrupt["type"] == "human_review"
    assert interrupt["evaluation_id"] == evaluation_id
    assert "resume_token" in interrupt and interrupt["resume_token"].startswith("rt_")
