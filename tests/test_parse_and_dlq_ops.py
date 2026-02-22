from io import BytesIO

from app.store import store


def _upload_one_document(client, key: str = "idem_u_for_parse") -> str:
    files = {"file": ("parse-me.pdf", BytesIO(b"%PDF-1.4 parse"), "application/pdf")}
    data = {"project_id": "prj_p1", "supplier_id": "sup_p1", "doc_type": "bid"}
    resp = client.post(
        "/api/v1/documents/upload",
        data=data,
        files=files,
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 202
    return resp.json()["data"]["document_id"]


def test_parse_document_returns_202_with_job_id(client):
    document_id = _upload_one_document(client)
    resp = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_parse_1"},
    )
    assert resp.status_code == 202
    payload = resp.json()["data"]
    assert payload["document_id"] == document_id
    assert payload["job_id"].startswith("job_")
    assert payload["status"] == "queued"


def test_upload_auto_enqueues_parse_job_and_manifest(client):
    files = {"file": ("auto-parse.pdf", BytesIO(b"%PDF-1.4 auto parse"), "application/pdf")}
    data = {"project_id": "prj_auto", "supplier_id": "sup_auto", "doc_type": "bid"}
    upload = client.post(
        "/api/v1/documents/upload",
        data=data,
        files=files,
        headers={"Idempotency-Key": "idem_upload_auto_parse_1"},
    )
    assert upload.status_code == 202

    payload = upload.json()["data"]
    document_id = payload["document_id"]
    parse_job_id = payload["job_id"]
    assert payload["next"].endswith(parse_job_id)

    job = client.get(f"/api/v1/jobs/{parse_job_id}")
    assert job.status_code == 200
    assert job.json()["data"]["job_type"] == "parse"

    manifest = client.get(
        f"/api/v1/internal/parse-manifests/{parse_job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert manifest.status_code == 200
    manifest_data = manifest.json()["data"]
    assert manifest_data["document_id"] == document_id
    assert manifest_data["status"] == "queued"

    doc = client.get(f"/api/v1/documents/{document_id}")
    assert doc.status_code == 200
    assert doc.json()["data"]["status"] == "parse_queued"


def test_parse_document_missing_idempotency_key_returns_400(client):
    document_id = _upload_one_document(client, key="idem_u_for_parse2")
    resp = client.post(f"/api/v1/documents/{document_id}/parse")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_MISSING"


def test_dlq_list_and_requeue_flow(client):
    seeded = store.seed_dlq_item(
        job_id="job_failed_1",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
    )
    item_id = seeded["dlq_id"]

    list_resp = client.get("/api/v1/dlq/items")
    assert list_resp.status_code == 200
    assert any(x["dlq_id"] == item_id for x in list_resp.json()["data"]["items"])

    rq_resp = client.post(
        f"/api/v1/dlq/items/{item_id}/requeue",
        headers={"Idempotency-Key": "idem_dlq_requeue_1"},
    )
    assert rq_resp.status_code == 202
    rq_data = rq_resp.json()["data"]
    assert rq_data["dlq_id"] == item_id
    assert rq_data["job_id"].startswith("job_")
    assert rq_data["status"] == "queued"

    post_item = store.get_dlq_item(item_id, tenant_id="tenant_default")
    assert post_item is not None
    assert post_item["status"] == "requeued"


def test_dlq_discard_requires_approval(client):
    seeded = store.seed_dlq_item(
        job_id="job_failed_2",
        error_class="permanent",
        error_code="DOC_PARSE_SCHEMA_INVALID",
    )
    item_id = seeded["dlq_id"]

    bad = client.post(
        f"/api/v1/dlq/items/{item_id}/discard",
        json={"reason": ""},
        headers={"Idempotency-Key": "idem_dlq_discard_1"},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "DLQ_DISCARD_REQUIRES_APPROVAL"

    ok = client.post(
        f"/api/v1/dlq/items/{item_id}/discard",
        json={
            "reason": "manual replacement completed",
            "reviewer_id": "u_reviewer_1",
        },
        headers={"Idempotency-Key": "idem_dlq_discard_2"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["status"] == "discarded"


def test_dlq_write_endpoints_require_idempotency_key(client):
    seeded = store.seed_dlq_item(
        job_id="job_failed_3",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
    )
    item_id = seeded["dlq_id"]

    requeue = client.post(f"/api/v1/dlq/items/{item_id}/requeue")
    assert requeue.status_code == 400
    assert requeue.json()["error"]["code"] == "IDEMPOTENCY_MISSING"

    discard = client.post(
        f"/api/v1/dlq/items/{item_id}/discard",
        json={"reason": "manual", "reviewer_id": "u_1"},
    )
    assert discard.status_code == 400
    assert discard.json()["error"]["code"] == "IDEMPOTENCY_MISSING"


def test_dlq_requeue_is_idempotent_with_same_key(client):
    seeded = store.seed_dlq_item(
        job_id="job_failed_4",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
    )
    item_id = seeded["dlq_id"]
    headers = {"Idempotency-Key": "idem_dlq_requeue_same"}

    first = client.post(f"/api/v1/dlq/items/{item_id}/requeue", headers=headers)
    second = client.post(f"/api/v1/dlq/items/{item_id}/requeue", headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"] == second.json()["data"]


def test_dlq_requeue_and_discard_write_audit_logs(client):
    seeded_requeue = store.seed_dlq_item(
        job_id="job_failed_audit_1",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
    )
    requeue_id = seeded_requeue["dlq_id"]
    requeue_resp = client.post(
        f"/api/v1/dlq/items/{requeue_id}/requeue",
        headers={"Idempotency-Key": "idem_dlq_audit_requeue"},
    )
    assert requeue_resp.status_code == 202
    requeue_logs = [x for x in store.audit_logs if x.get("action") == "dlq_requeue_submitted"]
    assert any(x.get("dlq_id") == requeue_id for x in requeue_logs)

    seeded_discard = store.seed_dlq_item(
        job_id="job_failed_audit_2",
        error_class="permanent",
        error_code="DOC_PARSE_SCHEMA_INVALID",
    )
    discard_id = seeded_discard["dlq_id"]
    discard_resp = client.post(
        f"/api/v1/dlq/items/{discard_id}/discard",
        json={"reason": "operator verified", "reviewer_id": "u_reviewer_9"},
        headers={"Idempotency-Key": "idem_dlq_audit_discard"},
    )
    assert discard_resp.status_code == 200
    discard_logs = [x for x in store.audit_logs if x.get("action") == "dlq_discard_submitted"]
    assert any(
        x.get("dlq_id") == discard_id and x.get("reviewer_id") == "u_reviewer_9"
        for x in discard_logs
    )
