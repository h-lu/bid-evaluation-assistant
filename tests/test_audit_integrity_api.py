from __future__ import annotations

from app.store import store


def _headers() -> dict[str, str]:
    return {"x-internal-debug": "true", "x-trace-id": "trace_audit_integrity", "x-tenant-id": "tenant_default"}


def test_audit_integrity_verification_detects_tamper(client):
    seeded = store.seed_dlq_item(
        job_id="job_audit_integrity_1",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
        tenant_id="tenant_default",
    )
    item_id = seeded["dlq_id"]
    discard = client.post(
        f"/api/v1/dlq/items/{item_id}/discard",
        headers={"Idempotency-Key": "idem_audit_integrity_discard", "x-trace-id": "trace_audit_discard"},
        json={
            "reason": "manual_verified",
            "reviewer_id": "u_audit_1",
            "reviewer_id_2": "u_audit_2",
        },
    )
    assert discard.status_code == 200

    verify_ok = client.get("/api/v1/internal/audit/integrity", headers=_headers())
    assert verify_ok.status_code == 200
    assert verify_ok.json()["data"]["valid"] is True

    store.audit_logs[-1]["action"] = "tampered_action"
    verify_bad = client.get("/api/v1/internal/audit/integrity", headers=_headers())
    assert verify_bad.status_code == 409
    assert verify_bad.json()["error"]["code"] == "AUDIT_INTEGRITY_BROKEN"
