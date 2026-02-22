def _eval_payload(force_hitl: bool) -> dict:
    return {
        "project_id": "prj_audit",
        "supplier_id": "sup_audit",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": force_hitl},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
    }


def _create_and_resume_one(client, tenant: str = "tenant_a") -> str:
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(force_hitl=True),
        headers={"Idempotency-Key": f"idem_audit_eval_{tenant}", "x-tenant-id": tenant},
    )
    evaluation_id = created.json()["data"]["evaluation_id"]

    report = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": tenant},
    )
    resume_token = report.json()["data"]["interrupt"]["resume_token"]

    resume = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        headers={"Idempotency-Key": f"idem_audit_resume_{tenant}", "x-tenant-id": tenant},
        json={
            "resume_token": resume_token,
            "decision": "approve",
            "comment": "audit trail test",
            "editor": {"reviewer_id": "u_audit"},
        },
    )
    assert resume.status_code == 202
    return evaluation_id


def test_list_evaluation_audit_logs_returns_resume_entries(client):
    evaluation_id = _create_and_resume_one(client, tenant="tenant_a")

    resp = client.get(
        f"/api/v1/evaluations/{evaluation_id}/audit-logs",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["evaluation_id"] == evaluation_id
    assert data["total"] >= 1
    assert data["items"][0]["action"] == "resume_submitted"


def test_list_evaluation_audit_logs_cross_tenant_is_blocked(client):
    evaluation_id = _create_and_resume_one(client, tenant="tenant_a")
    denied = client.get(
        f"/api/v1/evaluations/{evaluation_id}/audit-logs",
        headers={"x-tenant-id": "tenant_b"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_list_evaluation_audit_logs_missing_returns_404(client):
    resp = client.get("/api/v1/evaluations/ev_missing/audit-logs")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "EVALUATION_REPORT_NOT_FOUND"
