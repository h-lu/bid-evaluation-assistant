from io import BytesIO


def _create_parse_job(client) -> str:
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_cp", "supplier_id": "sup_cp", "doc_type": "bid"},
        files={"file": ("cp.pdf", BytesIO(b"%PDF-1.4 cp"), "application/pdf")},
        headers={"Idempotency-Key": "idem_cp_upload_1", "x-tenant-id": "tenant_a"},
    )
    assert upload.status_code == 202
    document_id = upload.json()["data"]["document_id"]
    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_cp_parse_1", "x-tenant-id": "tenant_a"},
    )
    assert parse.status_code == 202
    return parse.json()["data"]["job_id"]


def _create_hitl_evaluation(client) -> tuple[str, str, str]:
    created = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_cp_eval_1", "x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_cp",
            "supplier_id": "sup_cp",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": True},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
        },
    )
    assert created.status_code == 202
    evaluation_id = created.json()["data"]["evaluation_id"]
    job_id = created.json()["data"]["job_id"]
    report = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert report.status_code == 200
    token = report.json()["data"]["interrupt"]["resume_token"]
    return evaluation_id, job_id, token


def test_workflow_checkpoints_record_job_run(client):
    job_id = _create_parse_job(client)
    job = client.get(f"/api/v1/jobs/{job_id}", headers={"x-tenant-id": "tenant_a"})
    assert job.status_code == 200
    thread_id = job.json()["data"]["thread_id"]
    assert thread_id.startswith("thr_")

    run = client.post(
        f"/api/v1/internal/jobs/{job_id}/run",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert run.status_code == 200

    checkpoints = client.get(
        f"/api/v1/internal/workflows/{thread_id}/checkpoints",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert checkpoints.status_code == 200
    items = checkpoints.json()["data"]["items"]
    assert len(items) >= 2
    assert items[0]["status"] == "running"
    assert items[-1]["status"] == "succeeded"
    assert all(x["thread_id"] == thread_id for x in items)
    assert all(x["job_id"] == job_id for x in items)


def test_workflow_checkpoints_require_internal_header(client):
    job_id = _create_parse_job(client)
    job = client.get(f"/api/v1/jobs/{job_id}", headers={"x-tenant-id": "tenant_a"})
    thread_id = job.json()["data"]["thread_id"]
    resp = client.get(f"/api/v1/internal/workflows/{thread_id}/checkpoints")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_resume_job_reuses_evaluation_thread_id(client):
    evaluation_id, eval_job_id, resume_token = _create_hitl_evaluation(client)
    eval_job = client.get(f"/api/v1/jobs/{eval_job_id}", headers={"x-tenant-id": "tenant_a"})
    assert eval_job.status_code == 200
    thread_id = eval_job.json()["data"]["thread_id"]

    resume = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        headers={"Idempotency-Key": "idem_cp_resume_1", "x-tenant-id": "tenant_a"},
        json={
            "resume_token": resume_token,
            "decision": "approve",
            "comment": "ok",
            "editor": {"reviewer_id": "u_cp"},
            "edited_scores": [],
        },
    )
    assert resume.status_code == 202
    resume_job_id = resume.json()["data"]["job_id"]

    resume_job = client.get(f"/api/v1/jobs/{resume_job_id}", headers={"x-tenant-id": "tenant_a"})
    assert resume_job.status_code == 200
    assert resume_job.json()["data"]["thread_id"] == thread_id
