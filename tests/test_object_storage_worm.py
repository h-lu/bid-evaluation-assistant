from __future__ import annotations

import json
from io import BytesIO

from app.store import store


def _upload_document(client, *, tenant_id: str, content: bytes) -> str:
    resp = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_obj", "supplier_id": "sup_obj", "doc_type": "bid"},
        files={"file": ("obj.pdf", BytesIO(content), "application/pdf")},
        headers={"Idempotency-Key": "idem_obj_upload_1", "x-tenant-id": tenant_id},
    )
    assert resp.status_code == 202
    return resp.json()["data"]["document_id"]


def test_upload_persists_object_storage(client):
    content = b"%PDF-1.4 object-storage"
    document_id = _upload_document(client, tenant_id="tenant_obj", content=content)
    doc = store.get_document_for_tenant(document_id=document_id, tenant_id="tenant_obj")
    assert doc is not None
    storage_uri = doc.get("storage_uri")
    assert isinstance(storage_uri, str) and storage_uri
    stored = store.object_storage.get_object(storage_uri=storage_uri)
    assert stored == content


def test_report_archived_to_object_storage(client):
    created = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_obj_eval_1", "x-tenant-id": "tenant_obj"},
        json={
            "project_id": "prj_obj",
            "supplier_id": "sup_obj",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
        },
    )
    assert created.status_code == 202
    evaluation_id = created.json()["data"]["evaluation_id"]
    report = store.get_evaluation_report_for_tenant(evaluation_id=evaluation_id, tenant_id="tenant_obj")
    assert report is not None
    report_uri = report.get("report_uri")
    assert isinstance(report_uri, str) and report_uri
    stored = store.object_storage.get_object(storage_uri=report_uri)
    payload = json.loads(stored.decode("utf-8"))
    assert payload["evaluation_id"] == evaluation_id


def test_legal_hold_blocks_object_storage_cleanup(client):
    document_id = _upload_document(client, tenant_id="tenant_obj", content=b"%PDF-1.4 hold")
    impose = client.post(
        "/api/v1/internal/legal-hold/impose",
        headers={"x-internal-debug": "true", "x-trace-id": "trace_hold_1", "x-tenant-id": "tenant_obj"},
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "regulatory_investigation",
            "imposed_by": "u_admin_1",
        },
    )
    assert impose.status_code == 200

    blocked = client.post(
        "/api/v1/internal/storage/cleanup",
        headers={"x-internal-debug": "true", "x-trace-id": "trace_hold_1", "x-tenant-id": "tenant_obj"},
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "retention_window_elapsed",
        },
    )
    assert blocked.status_code == 409

    hold_id = impose.json()["data"]["hold_id"]
    release = client.post(
        f"/api/v1/internal/legal-hold/{hold_id}/release",
        headers={"x-internal-debug": "true", "x-trace-id": "trace_hold_1", "x-tenant-id": "tenant_obj"},
        json={
            "reason": "case_closed",
            "reviewer_id": "u_approver_1",
            "reviewer_id_2": "u_approver_2",
        },
    )
    assert release.status_code == 200

    cleaned = client.post(
        "/api/v1/internal/storage/cleanup",
        headers={"x-internal-debug": "true", "x-trace-id": "trace_hold_1", "x-tenant-id": "tenant_obj"},
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "retention_window_elapsed",
        },
    )
    assert cleaned.status_code == 200
    assert cleaned.json()["data"]["deleted"] is True


def test_retention_blocks_object_storage_cleanup(client, monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_RETENTION_DAYS", "1")
    store.reset()
    document_id = _upload_document(client, tenant_id="tenant_obj", content=b"%PDF-1.4 retention")
    blocked = client.post(
        "/api/v1/internal/storage/cleanup",
        headers={"x-internal-debug": "true", "x-trace-id": "trace_retention_1", "x-tenant-id": "tenant_obj"},
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "retention_window_elapsed",
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "RETENTION_ACTIVE"


def test_cleanup_audit_log_includes_trace_id(client):
    """Audit log for storage cleanup must include trace_id (SSOT §2.2)."""
    content = b"%PDF-1.4 trace_test"
    document_id = _upload_document(client, tenant_id="tenant_trace", content=content)

    trace_id = "trace_cleanup_test_001"
    cleanup = client.post(
        "/api/v1/internal/storage/cleanup",
        headers={
            "x-internal-debug": "true",
            "x-trace-id": trace_id,
            "x-tenant-id": "tenant_trace",
        },
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "test_cleanup",
        },
    )
    assert cleanup.status_code == 200

    # Verify audit log contains trace_id
    audit_logs = [
        log for log in store.audit_logs
        if log.get("tenant_id") == "tenant_trace" and log.get("action") == "storage_cleanup_executed"
    ]
    assert any(log.get("trace_id") == trace_id for log in audit_logs)


def test_worm_mode_idempotent_put():
    """WORM mode should return same URI without overwriting (SSOT §2.2)."""
    from app.object_storage import LocalObjectStorage, ObjectStorageConfig

    config = ObjectStorageConfig(
        backend="local",
        bucket="test",
        root="/tmp/bea-test-worm-idem",
        prefix="",
        worm_mode=True,
        endpoint="",
        region="",
        access_key="",
        secret_key="",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = LocalObjectStorage(config=config)
    storage.reset()

    content1 = b"original content v1"
    content2 = b"modified content v2"

    # First put
    uri1 = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=content1,
    )

    # Second put with same key - should NOT overwrite
    uri2 = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=content2,
    )

    # Same URI returned
    assert uri1 == uri2

    # Original content preserved
    stored = storage.get_object(storage_uri=uri1)
    assert stored == content1
    assert stored != content2
