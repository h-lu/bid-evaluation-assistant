from __future__ import annotations


def _headers() -> dict[str, str]:
    return {"x-internal-debug": "true", "x-trace-id": "trace_legal_hold_1", "x-tenant-id": "tenant_legal_hold"}


def test_legal_hold_lifecycle_and_cleanup_guard(client):
    impose = client.post(
        "/api/v1/internal/legal-hold/impose",
        headers=_headers(),
        json={
            "object_type": "document",
            "object_id": "doc_legal_1",
            "reason": "regulatory_investigation",
            "imposed_by": "u_admin_1",
        },
    )
    assert impose.status_code == 200
    hold_id = impose.json()["data"]["hold_id"]

    list_resp = client.get("/api/v1/internal/legal-hold/items", headers=_headers())
    assert list_resp.status_code == 200
    assert any(x["hold_id"] == hold_id and x["status"] == "active" for x in list_resp.json()["data"]["items"])

    blocked_cleanup = client.post(
        "/api/v1/internal/storage/cleanup",
        headers=_headers(),
        json={
            "object_type": "document",
            "object_id": "doc_legal_1",
            "reason": "retention_window_elapsed",
        },
    )
    assert blocked_cleanup.status_code == 409
    assert blocked_cleanup.json()["error"]["code"] == "LEGAL_HOLD_ACTIVE"

    release_missing = client.post(
        f"/api/v1/internal/legal-hold/{hold_id}/release",
        headers=_headers(),
        json={
            "reason": "case_closed",
            "reviewer_id": "u_approver_1",
        },
    )
    assert release_missing.status_code == 400
    assert release_missing.json()["error"]["code"] == "APPROVAL_REQUIRED"

    release_ok = client.post(
        f"/api/v1/internal/legal-hold/{hold_id}/release",
        headers=_headers(),
        json={
            "reason": "case_closed",
            "reviewer_id": "u_approver_1",
            "reviewer_id_2": "u_approver_2",
        },
    )
    assert release_ok.status_code == 200
    assert release_ok.json()["data"]["status"] == "released"

    cleanup_ok = client.post(
        "/api/v1/internal/storage/cleanup",
        headers=_headers(),
        json={
            "object_type": "document",
            "object_id": "doc_legal_1",
            "reason": "retention_window_elapsed",
        },
    )
    assert cleanup_ok.status_code == 200
    assert cleanup_ok.json()["data"]["cleaned"] is True
