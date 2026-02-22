from io import BytesIO


def _seed_tenant_a_activity(client):
    created = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_obs_eval_1", "x-tenant-id": "tenant_obs_a"},
        json={
            "project_id": "prj_obs",
            "supplier_id": "sup_obs",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
        },
    )
    assert created.status_code == 202

    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_obs", "supplier_id": "sup_obs", "doc_type": "bid"},
        files={"file": ("obs.pdf", BytesIO(b"%PDF-1.4 obs"), "application/pdf")},
        headers={"Idempotency-Key": "idem_obs_upload_1", "x-tenant-id": "tenant_obs_a"},
    )
    assert upload.status_code == 202
    parse_job_id = upload.json()["data"]["job_id"]
    run_fail = client.post(
        f"/api/v1/internal/jobs/{parse_job_id}/run?force_fail=true&error_code=DOC_PARSE_SCHEMA_INVALID",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_obs_a"},
    )
    assert run_fail.status_code == 200


def test_internal_ops_metrics_summary_returns_tenant_scoped_metrics(client):
    _seed_tenant_a_activity(client)

    resp = client.get(
        "/api/v1/internal/ops/metrics/summary?queue_name=jobs",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_obs_a"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tenant_id"] == "tenant_obs_a"
    assert "api" in data and "worker" in data and "quality" in data and "cost" in data
    assert data["api"]["total_jobs"] >= 2
    assert data["worker"]["dlq_open"] >= 1
    assert data["worker"]["queue_pending"] >= 0
    assert data["cost"]["dataset_version"].startswith("v")


def test_internal_ops_metrics_summary_requires_internal_header(client):
    resp = client.get("/api/v1/internal/ops/metrics/summary")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_internal_ops_metrics_summary_is_tenant_isolated(client):
    _seed_tenant_a_activity(client)
    resp = client.get(
        "/api/v1/internal/ops/metrics/summary?queue_name=jobs",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_obs_b"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tenant_id"] == "tenant_obs_b"
    assert data["api"]["total_jobs"] == 0
    assert data["worker"]["dlq_open"] == 0
