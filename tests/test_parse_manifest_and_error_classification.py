import hashlib
from io import BytesIO

from app.store import store


def _upload_and_create_parse_job(client):
    file_bytes = b"%PDF-1.4 parse-manifest"
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_manifest", "supplier_id": "sup_manifest", "doc_type": "bid"},
        files={"file": ("manifest.pdf", BytesIO(file_bytes), "application/pdf")},
        headers={"Idempotency-Key": "idem_manifest_upload_1"},
    )
    assert upload.status_code == 202
    document_id = upload.json()["data"]["document_id"]

    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_manifest_parse_1"},
    )
    assert parse.status_code == 202
    return document_id, parse.json()["data"]["job_id"], file_bytes


def test_internal_parse_manifest_contains_input_hash_and_route(client):
    document_id, job_id, file_bytes = _upload_and_create_parse_job(client)

    resp = client.get(
        f"/api/v1/internal/parse-manifests/{job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_id"] == job_id
    assert data["document_id"] == document_id
    assert data["run_id"].startswith("prun_")
    assert data["selected_parser"] == "mineru"
    assert data["parser_version"] == "v0"
    assert data["fallback_chain"] == ["docling", "ocr"]
    assert data["status"] == "queued"
    assert data["error_code"] is None

    input_file = data["input_files"][0]
    assert input_file["name"] == "manifest.pdf"
    assert input_file["sha256"] == hashlib.sha256(file_bytes).hexdigest()


def test_parse_failure_is_classified_and_written_to_manifest_and_job(client):
    _, job_id, _ = _upload_and_create_parse_job(client)

    run = client.post(
        f"/api/v1/internal/jobs/{job_id}/run?force_fail=true&error_code=DOC_PARSE_SCHEMA_INVALID",
        headers={"x-internal-debug": "true"},
    )
    assert run.status_code == 200
    payload = run.json()["data"]
    assert payload["final_status"] == "failed"
    assert payload["dlq_id"].startswith("dlq_")

    job = store.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert job["last_error"]["code"] == "DOC_PARSE_SCHEMA_INVALID"
    assert job["last_error"]["class"] == "transient"
    assert job["last_error"]["retryable"] is True

    manifest_resp = client.get(
        f"/api/v1/internal/parse-manifests/{job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()["data"]
    assert manifest["status"] == "failed"
    assert manifest["error_code"] == "DOC_PARSE_SCHEMA_INVALID"


def test_parse_success_updates_manifest_status(client):
    _, job_id, _ = _upload_and_create_parse_job(client)

    run = client.post(
        f"/api/v1/internal/jobs/{job_id}/run",
        headers={"x-internal-debug": "true"},
    )
    assert run.status_code == 200
    assert run.json()["data"]["final_status"] == "succeeded"

    manifest_resp = client.get(
        f"/api/v1/internal/parse-manifests/{job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()["data"]
    assert manifest["status"] == "succeeded"
    assert manifest["error_code"] is None


def test_internal_parse_manifest_requires_internal_header(client):
    _, job_id, _ = _upload_and_create_parse_job(client)
    resp = client.get(f"/api/v1/internal/parse-manifests/{job_id}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
