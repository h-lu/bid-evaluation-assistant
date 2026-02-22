from __future__ import annotations

from app.store import InMemoryStore


class CopyingEvaluationReportsRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def upsert(self, *, report: dict) -> dict:
        item = dict(report)
        self.rows[str(item["evaluation_id"])] = item
        return dict(item)

    def get(self, *, tenant_id: str, evaluation_id: str) -> dict | None:
        row = self.rows.get(evaluation_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)


def test_resume_updates_evaluation_report_via_repository():
    store = InMemoryStore()
    store.evaluation_reports_repository = CopyingEvaluationReportsRepository()

    created = store.create_evaluation_job(
        {
            "project_id": "prj_sync",
            "supplier_id": "sup_sync",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": True},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
            "tenant_id": "tenant_sync",
            "trace_id": "trace_sync",
        }
    )
    report_before = store.get_evaluation_report_for_tenant(
        evaluation_id=created["evaluation_id"], tenant_id="tenant_sync"
    )
    assert report_before is not None
    assert report_before["needs_human_review"] is True

    resumed = store.create_resume_job(
        evaluation_id=created["evaluation_id"],
        payload={
            "tenant_id": "tenant_sync",
            "decision": "approve",
            "comment": "ok",
            "editor": {"reviewer_id": "u_sync"},
            "trace_id": "trace_sync",
        },
    )
    assert resumed["status"] == "queued"

    report_after = store.get_evaluation_report_for_tenant(
        evaluation_id=created["evaluation_id"], tenant_id="tenant_sync"
    )
    assert report_after is not None
    assert report_after["needs_human_review"] is False
    assert report_after["interrupt"] is None
