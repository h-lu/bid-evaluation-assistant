"""Comprehensive security regression tests.

Aligned with security-design.md §9 and §11 acceptance criteria:
  1. Cross-tenant access events = 0
  2. High-risk actions: no audit gaps
  3. Legal hold objects: no unauthorized deletion
  4. Security regression: all passing

Covers security-design.md §9 test requirements:
  1. Tenant isolation (API + retrieval)
  2. Permission bypass (approval chain)
  3. Log redaction
"""

from __future__ import annotations

from io import BytesIO

import pytest

# ---------------------------------------------------------------------------
# §4.1 Cross-tenant isolation: ALL public API endpoints
# ---------------------------------------------------------------------------


class TestCrossTenantIsolation:
    """Every resource created by tenant_a must be inaccessible to tenant_b."""

    def test_project_cross_tenant_blocked(self, client):
        created = client.post(
            "/api/v1/projects",
            json={"project_code": "proj_sec", "name": "proj_sec", "ruleset_version": "v1.0.0"},
            headers={"Idempotency-Key": "idem_sec_proj_1", "x-tenant-id": "tenant_a"},
        )
        project_id = created.json()["data"]["project_id"]

        denied = client.get(
            f"/api/v1/projects/{project_id}",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code in (403, 404)
        code = denied.json()["error"]["code"]
        assert code in ("TENANT_SCOPE_VIOLATION", "PROJECT_NOT_FOUND")

    def test_supplier_cross_tenant_blocked(self, client):
        created = client.post(
            "/api/v1/suppliers",
            json={"supplier_code": "sup_sec", "name": "sup_sec"},
            headers={"Idempotency-Key": "idem_sec_sup_1", "x-tenant-id": "tenant_a"},
        )
        supplier_id = created.json()["data"]["supplier_id"]

        denied = client.get(
            f"/api/v1/suppliers/{supplier_id}",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code in (403, 404)
        code = denied.json()["error"]["code"]
        assert code in ("TENANT_SCOPE_VIOLATION", "SUPPLIER_NOT_FOUND")

    def test_rule_pack_cross_tenant_blocked(self, client):
        created = client.post(
            "/api/v1/rules",
            json={
                "rule_pack_version": "v_sec_1.0.0",
                "name": "sec_rules",
                "rules": {},
            },
            headers={"Idempotency-Key": "idem_sec_rule_1", "x-tenant-id": "tenant_a"},
        )
        data = created.json()["data"]
        version = data.get("version") or data.get("rule_pack_version", "v_sec_1.0.0")

        denied = client.get(
            f"/api/v1/rules/{version}",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code in (403, 404)
        code = denied.json()["error"]["code"]
        assert code in ("TENANT_SCOPE_VIOLATION", "RULE_PACK_NOT_FOUND")

    def test_document_cross_tenant_blocked(self, client):
        upload = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_sec", "supplier_id": "sup_sec", "doc_type": "bid"},
            files={"file": ("sec.pdf", BytesIO(b"%PDF-1.4 sec"), "application/pdf")},
            headers={"Idempotency-Key": "idem_sec_doc_1", "x-tenant-id": "tenant_a"},
        )
        document_id = upload.json()["data"]["document_id"]

        denied = client.get(
            f"/api/v1/documents/{document_id}",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_document_raw_cross_tenant_blocked(self, client):
        upload = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_sec", "supplier_id": "sup_sec", "doc_type": "bid"},
            files={"file": ("sec2.pdf", BytesIO(b"%PDF-1.4 sec2"), "application/pdf")},
            headers={"Idempotency-Key": "idem_sec_doc_2", "x-tenant-id": "tenant_a"},
        )
        document_id = upload.json()["data"]["document_id"]

        denied = client.get(
            f"/api/v1/documents/{document_id}/raw",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_document_chunks_cross_tenant_blocked(self, client):
        upload = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_sec", "supplier_id": "sup_sec", "doc_type": "bid"},
            files={"file": ("sec3.pdf", BytesIO(b"%PDF-1.4 sec3"), "application/pdf")},
            headers={"Idempotency-Key": "idem_sec_doc_3", "x-tenant-id": "tenant_a"},
        )
        document_id = upload.json()["data"]["document_id"]

        denied = client.get(
            f"/api/v1/documents/{document_id}/chunks",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_evaluation_report_cross_tenant_blocked(self, client):
        ev = client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_sec",
                "supplier_id": "sup_sec",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": "idem_sec_eval_1", "x-tenant-id": "tenant_a"},
        )
        evaluation_id = ev.json()["data"]["evaluation_id"]

        denied = client.get(
            f"/api/v1/evaluations/{evaluation_id}/report",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_evaluation_audit_logs_cross_tenant_blocked(self, client):
        ev = client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_sec",
                "supplier_id": "sup_sec",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": "idem_sec_eval_2", "x-tenant-id": "tenant_a"},
        )
        evaluation_id = ev.json()["data"]["evaluation_id"]

        denied = client.get(
            f"/api/v1/evaluations/{evaluation_id}/audit-logs",
            headers={"x-tenant-id": "tenant_b"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_list_jobs_returns_only_own_tenant(self, client):
        client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_iso",
                "supplier_id": "sup_iso",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": "idem_sec_iso_a", "x-tenant-id": "tenant_iso_a"},
        )
        client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_iso",
                "supplier_id": "sup_iso",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": "idem_sec_iso_b", "x-tenant-id": "tenant_iso_b"},
        )

        resp_a = client.get("/api/v1/jobs", headers={"x-tenant-id": "tenant_iso_a"})
        resp_b = client.get("/api/v1/jobs", headers={"x-tenant-id": "tenant_iso_b"})
        items_a = resp_a.json()["data"]["items"]
        items_b = resp_b.json()["data"]["items"]
        assert len(items_a) >= 1
        assert len(items_b) >= 1
        job_ids_a = {j["job_id"] for j in items_a}
        job_ids_b = {j["job_id"] for j in items_b}
        assert job_ids_a.isdisjoint(job_ids_b)

    def test_dlq_requeue_cross_tenant_blocked(self, client):
        resp = client.post(
            "/api/v1/dlq/items/dlq_nonexistent/requeue",
            headers={
                "Idempotency-Key": "idem_sec_dlq_1",
                "x-tenant-id": "tenant_b",
            },
        )
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# §5 High-risk approval and tool audit
# ---------------------------------------------------------------------------


class TestHighRiskApproval:
    """Dual-approval and tool audit for high-risk actions."""

    def test_dlq_discard_requires_dual_approval(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_DUAL_APPROVAL_REQUIRED_ACTIONS", "dlq_discard")
        monkeypatch.setenv("SECURITY_APPROVAL_REQUIRED_ACTIONS", "dlq_discard")

        from fastapi.testclient import TestClient

        from app.main import create_app

        base = TestClient(create_app())
        _jwt_secret = "jwt_test_secret_key_32bytes_min_for_sha256"

        from datetime import UTC, datetime, timedelta

        import jwt as pyjwt

        now = datetime.now(UTC)
        token = pyjwt.encode(
            {
                "sub": "u_test",
                "tenant_id": "tenant_default",
                "exp": int((now + timedelta(minutes=30)).timestamp()),
                "iat": int(now.timestamp()),
                "iss": "test-issuer",
                "aud": "test-audience",
            },
            _jwt_secret,
            algorithm="HS256",
        )

        blocked = base.post(
            "/api/v1/dlq/items/dlq_test/discard",
            headers={"Idempotency-Key": "idem_sec_disc_1", "Authorization": f"Bearer {token}"},
            json={"reason": "test", "reviewer_id": "r1", "reviewer_id_2": ""},
        )
        assert blocked.status_code == 400
        assert blocked.json()["error"]["code"] == "APPROVAL_REQUIRED"

    def test_dlq_discard_dual_approval_rejects_same_reviewer(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_DUAL_APPROVAL_REQUIRED_ACTIONS", "dlq_discard")
        monkeypatch.setenv("SECURITY_APPROVAL_REQUIRED_ACTIONS", "dlq_discard")

        from fastapi.testclient import TestClient

        from app.main import create_app

        base = TestClient(create_app())
        _jwt_secret = "jwt_test_secret_key_32bytes_min_for_sha256"

        from datetime import UTC, datetime, timedelta

        import jwt as pyjwt

        now = datetime.now(UTC)
        token = pyjwt.encode(
            {
                "sub": "u_test",
                "tenant_id": "tenant_default",
                "exp": int((now + timedelta(minutes=30)).timestamp()),
                "iat": int(now.timestamp()),
                "iss": "test-issuer",
                "aud": "test-audience",
            },
            _jwt_secret,
            algorithm="HS256",
        )

        blocked = base.post(
            "/api/v1/dlq/items/dlq_test/discard",
            headers={"Idempotency-Key": "idem_sec_disc_2", "Authorization": f"Bearer {token}"},
            json={"reason": "test", "reviewer_id": "r1", "reviewer_id_2": "r1"},
        )
        assert blocked.status_code == 400
        assert blocked.json()["error"]["code"] == "APPROVAL_REQUIRED"

    def test_legal_hold_release_requires_approval(self, monkeypatch):
        monkeypatch.setenv("SECURITY_APPROVAL_REQUIRED_ACTIONS", "legal_hold_release")
        from fastapi.testclient import TestClient

        from app.main import create_app

        app = create_app()
        tc = TestClient(app)

        blocked = tc.post(
            "/api/v1/internal/legal-hold/hold_test/release",
            headers={"x-internal-debug": "true"},
            json={"reason": "test", "reviewer_id": "", "reviewer_id_2": ""},
        )
        assert blocked.status_code == 400
        assert blocked.json()["error"]["code"] == "APPROVAL_REQUIRED"


# ---------------------------------------------------------------------------
# §7 Log redaction
# ---------------------------------------------------------------------------


class TestLogRedaction:
    def test_sensitive_headers_are_redacted(self):
        from app.security import redact_sensitive

        headers = {
            "authorization": "Bearer sk-secret-token-value",
            "token": "my-secret-token",
            "secret": "my-api-secret",
            "content-type": "application/json",
            "x-tenant-id": "tenant_a",
        }
        redacted = redact_sensitive(headers)
        assert "sk-secret-token-value" not in str(redacted)
        assert "my-secret-token" not in str(redacted)
        assert "my-api-secret" not in str(redacted)
        assert redacted["content-type"] == "application/json"
        assert redacted["x-tenant-id"] == "tenant_a"


# ---------------------------------------------------------------------------
# §8 Audit integrity
# ---------------------------------------------------------------------------


class TestAuditIntegrity:
    def test_audit_hash_chain_is_valid(self, client):
        client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_audit",
                "supplier_id": "sup_audit",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": "idem_sec_audit_1", "x-tenant-id": "tenant_audit"},
        )

        resp = client.get(
            "/api/v1/internal/audit/integrity",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_audit"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is True


# ---------------------------------------------------------------------------
# §8.1 Legal hold protection
# ---------------------------------------------------------------------------


class TestLegalHoldProtection:
    def test_impose_and_verify_legal_hold(self, client):
        resp = client.post(
            "/api/v1/internal/legal-hold/impose",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_lh"},
            json={
                "object_type": "evaluation_report",
                "object_id": "ev_lh_001",
                "reason": "litigation hold",
                "imposed_by": "legal_counsel",
            },
        )
        assert resp.status_code == 200
        hold = resp.json()["data"]
        assert hold["status"] == "active"
        hold_id = hold["hold_id"]

        items_resp = client.get(
            "/api/v1/internal/legal-hold/items",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_lh"},
        )
        items = items_resp.json()["data"]["items"]
        assert any(i["hold_id"] == hold_id for i in items)

    def test_storage_cleanup_blocked_by_active_legal_hold(self, client):
        client.post(
            "/api/v1/internal/legal-hold/impose",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_lh2"},
            json={
                "object_type": "evaluation_report",
                "object_id": "ev_lh_002",
                "reason": "compliance hold",
                "imposed_by": "compliance_officer",
            },
        )

        cleanup = client.post(
            "/api/v1/internal/storage/cleanup",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_lh2"},
            json={
                "object_type": "evaluation_report",
                "object_id": "ev_lh_002",
                "reason": "routine cleanup",
            },
        )
        assert cleanup.status_code == 409
        assert cleanup.json()["error"]["code"] == "LEGAL_HOLD_ACTIVE"


# ---------------------------------------------------------------------------
# Internal endpoint access control
# ---------------------------------------------------------------------------


class TestInternalEndpointAccess:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/internal/jobs/j1/transition",
            "/api/v1/internal/jobs/j1/run",
            "/api/v1/internal/parse-manifests/j1",
            "/api/v1/internal/workflows/th1/checkpoints",
            "/api/v1/internal/tools/registry",
            "/api/v1/internal/ops/metrics/summary",
            "/api/v1/internal/audit/integrity",
            "/api/v1/internal/outbox/events",
        ],
    )
    def test_internal_endpoints_reject_without_debug_header(self, client, path):
        if "transition" in path or "run" in path:
            resp = client.post(path, json={"new_status": "running"})
        elif path.endswith("/run"):
            resp = client.post(path)
        else:
            resp = client.get(path)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


# ---------------------------------------------------------------------------
# SSOT alignment verification
# ---------------------------------------------------------------------------


class TestSSOTSecurityAlignment:
    """Verify security-design.md §11 acceptance criteria via gate."""

    def test_security_gate_thresholds_match_ssot(self):
        from app.security_gates import SECURITY_THRESHOLDS

        assert SECURITY_THRESHOLDS["tenant_scope_violations_max"] == 0
        assert SECURITY_THRESHOLDS["auth_bypass_findings_max"] == 0
        assert SECURITY_THRESHOLDS["high_risk_approval_coverage_min"] == 1.0
        assert SECURITY_THRESHOLDS["log_redaction_failures_max"] == 0
        assert SECURITY_THRESHOLDS["secret_scan_findings_max"] == 0

    def test_security_gate_passes_with_clean_metrics(self, client):
        resp = client.post(
            "/api/v1/internal/security-gates/evaluate",
            headers={"x-internal-debug": "true"},
            json={
                "dataset_id": "ds_sec_regression",
                "metrics": {
                    "tenant_scope_violations": 0,
                    "auth_bypass_findings": 0,
                    "high_risk_approval_coverage": 1.0,
                    "log_redaction_failures": 0,
                    "secret_scan_findings": 0,
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["passed"] is True
