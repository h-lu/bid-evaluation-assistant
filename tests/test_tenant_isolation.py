from io import BytesIO


def _eval_payload() -> dict:
    return {
        "project_id": "prj_tenant",
        "supplier_id": "sup_tenant",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 10},
    }


def test_get_job_cross_tenant_is_blocked(client):
    created = client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_tenant_eval_1", "x-tenant-id": "tenant_a"},
    )
    job_id = created.json()["data"]["job_id"]

    denied = client.get(f"/api/v1/jobs/{job_id}", headers={"x-tenant-id": "tenant_b"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_list_jobs_only_returns_current_tenant(client):
    client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_tenant_eval_2", "x-tenant-id": "tenant_a"},
    )
    client.post(
        "/api/v1/evaluations",
        json=_eval_payload(),
        headers={"Idempotency-Key": "idem_tenant_eval_3", "x-tenant-id": "tenant_b"},
    )

    tenant_a_jobs = client.get("/api/v1/jobs", headers={"x-tenant-id": "tenant_a"})
    assert tenant_a_jobs.status_code == 200
    items = tenant_a_jobs.json()["data"]["items"]
    assert items
    assert all(item["resource"]["id"].startswith("ev_") for item in items)
    assert all(item["trace_id"] for item in items)


def test_parse_cross_tenant_is_blocked(client):
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_tenant", "supplier_id": "sup_tenant", "doc_type": "bid"},
        files={"file": ("tenant.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        headers={"Idempotency-Key": "idem_tenant_upload_1", "x-tenant-id": "tenant_a"},
    )
    document_id = upload.json()["data"]["document_id"]

    denied = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_tenant_parse_1", "x-tenant-id": "tenant_b"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"
