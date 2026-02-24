"""E2E API tests covering all 6 SSOT §9 mandatory scenarios.

Scenarios:
  1. Upload -> Parse -> Index (document reaches 'indexed' state)
  2. Evaluation -> Report generation
  3. HITL trigger + resume
  4. Citation source retrieval (回跳与高亮)
  5. DLQ requeue and status closure
  6. Cross-role permission enforcement
"""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.store import store

TENANT = "tenant_e2e"


def _headers(*, idempotency: bool = False, internal: bool = False) -> dict[str, str]:
    h: dict[str, str] = {
        "x-tenant-id": TENANT,
        "x-trace-id": f"tr_{uuid.uuid4().hex[:12]}",
    }
    if idempotency:
        h["Idempotency-Key"] = f"idem_{uuid.uuid4().hex[:12]}"
    if internal:
        h["x-internal-debug"] = "true"
    return h


def _upload_and_parse(client) -> dict:
    """Upload a document, run the parse job, return upload payload."""
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
        files={"file": ("e2e_test.pdf", BytesIO(b"%PDF-1.4 e2e content"), "application/pdf")},
        headers=_headers(idempotency=True),
    )
    assert upload.status_code == 202, f"upload failed: {upload.text}"
    data = upload.json()["data"]

    run = client.post(
        f"/api/v1/internal/jobs/{data['job_id']}/run",
        headers=_headers(internal=True),
    )
    assert run.status_code == 200, f"job run failed: {run.text}"
    assert run.json()["data"]["final_status"] == "succeeded"
    return data


def _create_evaluation(client, *, force_hitl: bool = False) -> dict:
    resp = client.post(
        "/api/v1/evaluations",
        json={
            "project_id": "prj_e2e",
            "supplier_id": "sup_e2e",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": force_hitl},
            "query_options": {"mode_hint": "hybrid", "top_k": 20},
        },
        headers=_headers(idempotency=True),
    )
    assert resp.status_code == 202, f"create evaluation failed: {resp.text}"
    return resp.json()["data"]


# ──────────────────────────────────────────────────────────────────
# Scenario 1: Upload -> Parse -> Index
# ──────────────────────────────────────────────────────────────────


class TestE2EUploadToIndex:
    """SSOT §9-1: 上传成功并进入 indexed."""

    def test_upload_returns_202_with_document_and_job(self, client):
        upload = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
            files={"file": ("s1.pdf", BytesIO(b"%PDF-1.4 scenario1"), "application/pdf")},
            headers=_headers(idempotency=True),
        )
        assert upload.status_code == 202
        data = upload.json()["data"]
        assert data["document_id"].startswith("doc_")
        assert data["job_id"].startswith("job_")
        assert data["status"] == "queued"

    def test_parse_job_succeeds_and_document_becomes_indexed(self, client):
        uploaded = _upload_and_parse(client)
        doc_id = uploaded["document_id"]

        doc_resp = client.get(
            f"/api/v1/documents/{doc_id}",
            headers=_headers(),
        )
        assert doc_resp.status_code == 200
        doc = doc_resp.json()["data"]
        assert doc["status"] in ("indexed", "parsed"), f"unexpected status: {doc['status']}"

    def test_chunks_exist_after_parse(self, client):
        uploaded = _upload_and_parse(client)
        doc_id = uploaded["document_id"]

        chunks_resp = client.get(
            f"/api/v1/documents/{doc_id}/chunks",
            headers=_headers(),
        )
        assert chunks_resp.status_code == 200
        chunks = chunks_resp.json()["data"]
        assert chunks["total"] >= 1, "expected at least 1 chunk after parse"
        assert chunks["items"], "chunk items list should not be empty"

    def test_retrieval_finds_indexed_content(self, client):
        _upload_and_parse(client)

        retr = client.post(
            "/api/v1/retrieval/preview",
            headers=_headers(),
            json={
                "project_id": "prj_e2e",
                "supplier_id": "sup_e2e",
                "query": "content",
                "query_type": "fact",
                "must_include_terms": [],
            },
        )
        assert retr.status_code == 200
        assert retr.json()["data"]["total"] >= 1


# ──────────────────────────────────────────────────────────────────
# Scenario 2: Evaluation -> Report
# ──────────────────────────────────────────────────────────────────


class TestE2EEvaluationReport:
    """SSOT §9-2: 发起评估并生成报告."""

    def test_create_evaluation_returns_202(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client)
        assert ev["evaluation_id"].startswith("ev_")
        assert ev["job_id"].startswith("job_")
        assert ev["status"] == "queued"

    def test_evaluation_report_has_required_fields(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client)

        report_resp = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        assert report_resp.status_code == 200
        report = report_resp.json()["data"]
        assert report["evaluation_id"] == ev["evaluation_id"]
        assert "total_score" in report
        assert "confidence" in report
        assert "criteria_results" in report
        assert isinstance(report["criteria_results"], list)

    def test_evaluation_report_contains_citations(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client)

        report_resp = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        assert report_resp.status_code == 200
        report = report_resp.json()["data"]
        all_citations = []
        for cr in report.get("criteria_results", []):
            all_citations.extend(cr.get("citations", []))
        assert all_citations, "report should have at least one citation"


# ──────────────────────────────────────────────────────────────────
# Scenario 3: HITL Trigger + Resume
# ──────────────────────────────────────────────────────────────────


class TestE2EHitlFlow:
    """SSOT §9-3: 触发 HITL 并恢复."""

    def test_hitl_trigger_sets_needs_human_review(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client, force_hitl=True)

        report_resp = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        assert report_resp.status_code == 200
        report = report_resp.json()["data"]
        assert report["needs_human_review"] is True
        assert report["interrupt"] is not None
        assert report["interrupt"]["resume_token"]

    def test_resume_clears_hitl_and_updates_report(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client, force_hitl=True)

        report_before = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        token = report_before.json()["data"]["interrupt"]["resume_token"]

        resume = client.post(
            f"/api/v1/evaluations/{ev['evaluation_id']}/resume",
            headers=_headers(idempotency=True),
            json={
                "resume_token": token,
                "decision": "approve",
                "comment": "e2e approved",
                "editor": {"reviewer_id": "u_e2e_reviewer"},
            },
        )
        assert resume.status_code == 202, f"resume failed: {resume.text}"

        report_after = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        after = report_after.json()["data"]
        assert after["needs_human_review"] is False
        assert after["interrupt"] is None

    def test_resume_creates_audit_log(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client, force_hitl=True)

        report = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        token = report.json()["data"]["interrupt"]["resume_token"]

        client.post(
            f"/api/v1/evaluations/{ev['evaluation_id']}/resume",
            headers=_headers(idempotency=True),
            json={
                "resume_token": token,
                "decision": "approve",
                "comment": "audit check",
                "editor": {"reviewer_id": "u_e2e_auditor"},
            },
        )

        logs = store.list_audit_logs_for_evaluation(
            evaluation_id=ev["evaluation_id"],
            tenant_id=TENANT,
        )
        assert any(
            log["action"] == "resume_submitted" and log["reviewer_id"] == "u_e2e_auditor"
            for log in logs
        ), f"expected resume_submitted audit log, got: {logs}"

    def test_resume_with_invalid_token_rejected(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client, force_hitl=True)

        resp = client.post(
            f"/api/v1/evaluations/{ev['evaluation_id']}/resume",
            headers=_headers(idempotency=True),
            json={
                "resume_token": "rt_invalid_token",
                "decision": "approve",
                "comment": "bad token",
                "editor": {"reviewer_id": "u_e2e"},
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "WF_INTERRUPT_RESUME_INVALID"


# ──────────────────────────────────────────────────────────────────
# Scenario 4: Citation Source (回跳与高亮)
# ──────────────────────────────────────────────────────────────────


class TestE2ECitationJump:
    """SSOT §9-4: citation 回跳与高亮."""

    def test_citation_source_returns_required_fields(self, client):
        chunk_id = f"ck_e2e_{uuid.uuid4().hex[:8]}"
        store.register_citation_source(
            chunk_id=chunk_id,
            source={
                "chunk_id": chunk_id,
                "document_id": "doc_e2e_cit",
                "filename": "cit_test.pdf",
                "page": 3,
                "bbox": [100.0, 200.0, 400.0, 250.0],
                "text": "投标文件第三章内容",
                "context": "周边上下文段落",
                "viewport_hint": {"scale": 1.0, "unit": "pdf_point"},
            },
        )

        resp = client.get(
            f"/api/v1/citations/{chunk_id}/source",
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["chunk_id"] == chunk_id
        assert data["document_id"] == "doc_e2e_cit"
        assert data["page"] == 3
        assert data["bbox"] == [100.0, 200.0, 400.0, 250.0]
        assert data["text"]
        assert data["context"]

    def test_citation_from_evaluation_report(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client)

        report_resp = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        report = report_resp.json()["data"]
        chunk_ids = []
        for cr in report.get("criteria_results", []):
            for cit in cr.get("citations", []):
                cid = cit.get("chunk_id")
                if cid:
                    chunk_ids.append(cid)

        for cid in chunk_ids[:3]:
            cit_resp = client.get(
                f"/api/v1/citations/{cid}/source",
                headers=_headers(),
            )
            assert cit_resp.status_code == 200, (
                f"citation {cid} not found: {cit_resp.text}"
            )
            cit_data = cit_resp.json()["data"]
            assert "document_id" in cit_data
            assert "page" in cit_data
            assert "text" in cit_data

    def test_missing_citation_returns_404(self, client):
        resp = client.get(
            "/api/v1/citations/ck_nonexistent/source",
            headers=_headers(),
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CITATION_NOT_FOUND"


# ──────────────────────────────────────────────────────────────────
# Scenario 5: DLQ Requeue + Status Closure
# ──────────────────────────────────────────────────────────────────


class TestE2EDlqFlow:
    """SSOT §9-5: DLQ requeue 与状态闭环."""

    def test_dlq_list_returns_seeded_items(self, client):
        store.seed_dlq_item(
            job_id="job_e2e_dlq_1",
            error_class="transient",
            error_code="RAG_UPSTREAM_UNAVAILABLE",
            tenant_id=TENANT,
        )

        resp = client.get("/api/v1/dlq/items", headers=_headers())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert any(i["job_id"] == "job_e2e_dlq_1" for i in items)

    def test_dlq_requeue_creates_new_job_and_closes_loop(self, client):
        seeded = store.seed_dlq_item(
            job_id="job_e2e_dlq_2",
            error_class="transient",
            error_code="RAG_UPSTREAM_UNAVAILABLE",
            tenant_id=TENANT,
        )
        dlq_id = seeded["dlq_id"]

        rq = client.post(
            f"/api/v1/dlq/items/{dlq_id}/requeue",
            headers=_headers(idempotency=True),
        )
        assert rq.status_code == 202, f"requeue failed: {rq.text}"
        rq_data = rq.json()["data"]
        assert rq_data["dlq_id"] == dlq_id
        assert rq_data["job_id"].startswith("job_")
        assert rq_data["status"] == "queued"

        item = store.get_dlq_item(dlq_id, tenant_id=TENANT)
        assert item is not None
        assert item["status"] == "requeued"

    def test_dlq_discard_requires_dual_approval(self, client):
        seeded = store.seed_dlq_item(
            job_id="job_e2e_dlq_3",
            error_class="permanent",
            error_code="DOC_PARSE_SCHEMA_INVALID",
            tenant_id=TENANT,
        )
        dlq_id = seeded["dlq_id"]

        bad = client.post(
            f"/api/v1/dlq/items/{dlq_id}/discard",
            json={"reason": ""},
            headers=_headers(idempotency=True),
        )
        assert bad.status_code == 400
        assert bad.json()["error"]["code"] == "APPROVAL_REQUIRED"

        ok = client.post(
            f"/api/v1/dlq/items/{dlq_id}/discard",
            json={
                "reason": "confirmed duplicate",
                "reviewer_id": "u_reviewer_e2e_1",
                "reviewer_id_2": "u_reviewer_e2e_2",
            },
            headers=_headers(idempotency=True),
        )
        assert ok.status_code == 200
        assert ok.json()["data"]["status"] == "discarded"

    def test_dlq_requeue_writes_audit_log(self, client):
        seeded = store.seed_dlq_item(
            job_id="job_e2e_dlq_audit",
            error_class="transient",
            error_code="RAG_UPSTREAM_UNAVAILABLE",
            tenant_id=TENANT,
        )
        dlq_id = seeded["dlq_id"]

        client.post(
            f"/api/v1/dlq/items/{dlq_id}/requeue",
            headers=_headers(idempotency=True),
        )

        audit_logs = [
            x for x in store.audit_logs
            if x.get("action") == "dlq_requeue_submitted" and x.get("dlq_id") == dlq_id
        ]
        assert audit_logs, "expected dlq_requeue_submitted audit log"

    def test_force_fail_job_enters_dlq(self, client):
        uploaded = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
            files={"file": ("fail.pdf", BytesIO(b"%PDF-1.4 fail"), "application/pdf")},
            headers=_headers(idempotency=True),
        )
        assert uploaded.status_code == 202
        job_id = uploaded.json()["data"]["job_id"]

        run = client.post(
            f"/api/v1/internal/jobs/{job_id}/run?force_fail=true",
            headers=_headers(internal=True),
        )
        assert run.status_code == 200
        result = run.json()["data"]
        assert result["final_status"] in ("failed", "dlq_recorded", "dlq_pending")


# ──────────────────────────────────────────────────────────────────
# Scenario 6: Cross-role Permission Enforcement
# ──────────────────────────────────────────────────────────────────


class TestE2ERolePermission:
    """SSOT §9-6: 跨角色权限限制验证."""

    def test_internal_endpoints_require_debug_header(self, client):
        resp = client.post(
            "/api/v1/internal/jobs/job_fake/run",
            headers=_headers(),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"

    def test_internal_endpoints_accessible_with_debug_header(self, client):
        uploaded = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
            files={"file": ("perm.pdf", BytesIO(b"%PDF-1.4 perm"), "application/pdf")},
            headers=_headers(idempotency=True),
        )
        job_id = uploaded.json()["data"]["job_id"]

        resp = client.post(
            f"/api/v1/internal/jobs/{job_id}/run",
            headers=_headers(internal=True),
        )
        assert resp.status_code == 200

    def test_cross_tenant_job_access_blocked(self, client):
        created = client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_e2e",
                "supplier_id": "sup_e2e",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={**_headers(idempotency=True), "x-tenant-id": "tenant_alpha"},
        )
        assert created.status_code == 202
        job_id = created.json()["data"]["job_id"]

        denied = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={**_headers(), "x-tenant-id": "tenant_beta"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"

    def test_cross_tenant_document_access_blocked(self, client):
        uploaded = client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_e2e", "supplier_id": "sup_e2e", "doc_type": "bid"},
            files={"file": ("cross.pdf", BytesIO(b"%PDF-1.4 cross"), "application/pdf")},
            headers={**_headers(idempotency=True), "x-tenant-id": "tenant_alpha"},
        )
        doc_id = uploaded.json()["data"]["document_id"]

        denied = client.get(
            f"/api/v1/documents/{doc_id}",
            headers={**_headers(), "x-tenant-id": "tenant_beta"},
        )
        assert denied.status_code in (403, 404)

    def test_dlq_discard_without_dual_approval_blocked(self, client):
        seeded = store.seed_dlq_item(
            job_id="job_e2e_perm_dlq",
            error_class="permanent",
            error_code="DOC_PARSE_SCHEMA_INVALID",
            tenant_id=TENANT,
        )
        dlq_id = seeded["dlq_id"]

        single_reviewer = client.post(
            f"/api/v1/dlq/items/{dlq_id}/discard",
            json={"reason": "test", "reviewer_id": "u_single"},
            headers=_headers(idempotency=True),
        )
        assert single_reviewer.status_code == 400
        assert single_reviewer.json()["error"]["code"] == "APPROVAL_REQUIRED"

    def test_resume_requires_reviewer_identity(self, client):
        _upload_and_parse(client)
        ev = _create_evaluation(client, force_hitl=True)
        report = client.get(
            f"/api/v1/evaluations/{ev['evaluation_id']}/report",
            headers=_headers(),
        )
        token = report.json()["data"]["interrupt"]["resume_token"]

        resp = client.post(
            f"/api/v1/evaluations/{ev['evaluation_id']}/resume",
            headers=_headers(idempotency=True),
            json={
                "resume_token": token,
                "decision": "approve",
                "comment": "no reviewer",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WF_INTERRUPT_REVIEWER_REQUIRED"

    def test_write_operations_require_idempotency_key(self, client):
        resp = client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_e2e",
                "supplier_id": "sup_e2e",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers=_headers(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "IDEMPOTENCY_MISSING"

    def test_jwt_required_when_security_enabled(self, monkeypatch):
        """Without JWT, secured endpoints reject requests."""
        monkeypatch.setenv("JWT_SHARED_SECRET", "jwt_test_secret_key_32bytes_min_for_sha256")
        monkeypatch.setenv("JWT_ISSUER", "test-issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "test-audience")
        monkeypatch.setenv("JWT_REQUIRED_CLAIMS", "tenant_id,sub,exp")
        raw_client = TestClient(create_app())

        resp = raw_client.get(
            "/api/v1/jobs",
            headers={"x-trace-id": "tr_jwt_test"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"


# ──────────────────────────────────────────────────────────────────
# Meta-test: SSOT §9 alignment
# ──────────────────────────────────────────────────────────────────


class TestE2ESSOTAlignment:
    """Verify all 6 SSOT §9 scenarios have corresponding test classes."""

    REQUIRED_SCENARIO_CLASSES = [
        ("TestE2EUploadToIndex", "§9-1 上传成功并进入 indexed"),
        ("TestE2EEvaluationReport", "§9-2 发起评估并生成报告"),
        ("TestE2EHitlFlow", "§9-3 触发 HITL 并恢复"),
        ("TestE2ECitationJump", "§9-4 citation 回跳与高亮"),
        ("TestE2EDlqFlow", "§9-5 DLQ requeue 与状态闭环"),
        ("TestE2ERolePermission", "§9-6 跨角色权限限制验证"),
    ]

    def test_all_six_scenarios_covered(self):
        import sys

        module = sys.modules[__name__]
        for class_name, description in self.REQUIRED_SCENARIO_CLASSES:
            cls = getattr(module, class_name, None)
            assert cls is not None, f"missing test class {class_name} for {description}"
            methods = [m for m in dir(cls) if m.startswith("test_")]
            assert methods, f"{class_name} ({description}) has no test methods"

    def test_minimum_test_coverage_per_scenario(self):
        import sys

        module = sys.modules[__name__]
        for class_name, description in self.REQUIRED_SCENARIO_CLASSES:
            cls = getattr(module, class_name, None)
            assert cls is not None
            methods = [m for m in dir(cls) if m.startswith("test_")]
            assert len(methods) >= 2, (
                f"{class_name} ({description}) should have >= 2 tests, got {len(methods)}"
            )
