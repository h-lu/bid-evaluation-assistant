from io import BytesIO

from app.store import store


def _create_parse_job(client) -> str:
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_run", "supplier_id": "sup_run", "doc_type": "bid"},
        files={"file": ("run.pdf", BytesIO(b"%PDF-1.4 run"), "application/pdf")},
        headers={"Idempotency-Key": "idem_run_upload_1"},
    )
    document_id = upload.json()["data"]["document_id"]
    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_run_parse_1"},
    )
    return parse.json()["data"]["job_id"]


def test_internal_run_job_success_path(client):
    job_id = _create_parse_job(client)
    resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/run",
        headers={"x-internal-debug": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_id"] == job_id
    assert data["final_status"] == "succeeded"
    assert data["dlq_id"] is None

    job = store.get_job(job_id)
    assert job is not None
    assert job["status"] == "succeeded"


def test_internal_run_job_failure_paths_to_dlq_then_failed(client):
    job_id = _create_parse_job(client)
    resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/run?force_fail=true",
        headers={"x-internal-debug": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_id"] == job_id
    assert data["final_status"] == "failed"
    assert data["dlq_id"].startswith("dlq_")

    job = store.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    dlq = store.get_dlq_item(data["dlq_id"], tenant_id="tenant_default")
    assert dlq is not None


def test_internal_run_requires_internal_header(client):
    job_id = _create_parse_job(client)
    resp = client.post(f"/api/v1/internal/jobs/{job_id}/run")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_internal_run_transient_fail_once_then_success(client):
    job_id = _create_parse_job(client)

    fail_resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/run?transient_fail=true",
        headers={"x-internal-debug": "true"},
    )
    assert fail_resp.status_code == 200
    fail_data = fail_resp.json()["data"]
    assert fail_data["final_status"] == "retrying"
    assert fail_data["dlq_id"] is None
    assert fail_data["retry_count"] == 1

    success_resp = client.post(
        f"/api/v1/internal/jobs/{job_id}/run",
        headers={"x-internal-debug": "true"},
    )
    assert success_resp.status_code == 200
    success_data = success_resp.json()["data"]
    assert success_data["final_status"] == "succeeded"
    assert success_data["dlq_id"] is None
    assert success_data["retry_count"] == 1


def test_internal_run_transient_fail_fourth_time_goes_dlq(client):
    job_id = _create_parse_job(client)
    headers = {"x-internal-debug": "true"}

    for expected_retry in (1, 2, 3):
        resp = client.post(
            f"/api/v1/internal/jobs/{job_id}/run?transient_fail=true",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["final_status"] == "retrying"
        assert data["dlq_id"] is None
        assert data["retry_count"] == expected_retry

    fourth = client.post(
        f"/api/v1/internal/jobs/{job_id}/run?transient_fail=true",
        headers=headers,
    )
    assert fourth.status_code == 200
    data = fourth.json()["data"]
    assert data["final_status"] == "failed"
    assert data["retry_count"] == 3
    assert data["dlq_id"].startswith("dlq_")

    job = store.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
