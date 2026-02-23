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
