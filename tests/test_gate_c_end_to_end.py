from io import BytesIO

from app.store import store


def _evaluation_payload(force_hitl: bool) -> dict:
    return {
        "project_id": "prj_e2e",
        "supplier_id": "sup_e2e",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": force_hitl},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
    }


def test_gate_c_minimal_end_to_end_chain(client):
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
        files={"file": ("e2e.pdf", BytesIO(b"%PDF-1.4 e2e"), "application/pdf")},
        headers={"Idempotency-Key": "idem_e2e_upload_1", "x-tenant-id": "tenant_a"},
    )
    assert upload.status_code == 202
    document_id = upload.json()["data"]["document_id"]

    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_e2e_parse_1", "x-tenant-id": "tenant_a"},
    )
    assert parse.status_code == 202
    parse_job_id = parse.json()["data"]["job_id"]

    run_parse = client.post(
        f"/api/v1/internal/jobs/{parse_job_id}/run",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_a"},
    )
    assert run_parse.status_code == 200
    assert run_parse.json()["data"]["final_status"] == "succeeded"

    chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert chunks.status_code == 200
    chunk_items = chunks.json()["data"]["items"]
    assert chunk_items

    retr = client.post(
        "/api/v1/retrieval/preview",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_e2e",
            "supplier_id": "sup_e2e",
            "query": "chunk generated",
            "query_type": "fact",
            "must_include_terms": ["chunk"],
        },
    )
    assert retr.status_code == 200
    retr_data = retr.json()["data"]
    assert retr_data["total"] >= 1

    created_eval = client.post(
        "/api/v1/evaluations",
        json=_evaluation_payload(force_hitl=True),
        headers={"Idempotency-Key": "idem_e2e_eval_1", "x-tenant-id": "tenant_a"},
    )
    assert created_eval.status_code == 202
    evaluation_id = created_eval.json()["data"]["evaluation_id"]

    report_before = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert report_before.status_code == 200
    before = report_before.json()["data"]
    assert before["needs_human_review"] is True
    resume_token = before["interrupt"]["resume_token"]

    resume = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        headers={"Idempotency-Key": "idem_e2e_resume_1", "x-tenant-id": "tenant_a"},
        json={
            "resume_token": resume_token,
            "decision": "approve",
            "comment": "approved in e2e",
            "editor": {"reviewer_id": "u_e2e_reviewer"},
        },
    )
    assert resume.status_code == 202

    report_after = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers={"x-tenant-id": "tenant_a"},
    )
    assert report_after.status_code == 200
    after = report_after.json()["data"]
    assert after["needs_human_review"] is False
    assert after["interrupt"] is None

    logs = store.list_audit_logs_for_evaluation(evaluation_id=evaluation_id, tenant_id="tenant_a")
    assert any(x["action"] == "resume_submitted" for x in logs)
