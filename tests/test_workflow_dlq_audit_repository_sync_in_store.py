from __future__ import annotations

from app.store import InMemoryStore


class CopyingWorkflowRepository:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}

    def append(self, *, checkpoint: dict) -> dict:
        item = dict(checkpoint)
        self.rows.setdefault(item["thread_id"], []).append(item)
        return dict(item)

    def list(self, *, thread_id: str, tenant_id: str, limit: int = 100) -> list[dict]:
        return [
            dict(x)
            for x in self.rows.get(thread_id, [])
            if x.get("tenant_id") == tenant_id
        ][:limit]


class CopyingDlqRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def upsert(self, *, item: dict) -> dict:
        row = dict(item)
        self.rows[row["dlq_id"]] = row
        return dict(row)

    def get(self, *, tenant_id: str, dlq_id: str) -> dict | None:
        row = self.rows.get(dlq_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def list(self, *, tenant_id: str) -> list[dict]:
        return [dict(x) for x in self.rows.values() if x.get("tenant_id") == tenant_id]


class CopyingAuditRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def append(self, *, log: dict) -> dict:
        row = dict(log)
        self.rows.append(row)
        return dict(row)

    def list_for_evaluation(self, *, tenant_id: str, evaluation_id: str) -> list[dict]:
        return [
            dict(x)
            for x in self.rows
            if x.get("tenant_id") == tenant_id and x.get("evaluation_id") == evaluation_id
        ]


def test_workflow_checkpoint_is_persisted_via_repository():
    store = InMemoryStore()
    store.workflow_repository = CopyingWorkflowRepository()

    cp = store.append_workflow_checkpoint(
        thread_id="thr_sync_1",
        job_id="job_sync_1",
        tenant_id="tenant_sync",
        node="job_started",
        status="running",
        payload={"k": "v"},
    )
    assert cp["checkpoint_id"].startswith("cp_")

    listed = store.list_workflow_checkpoints(thread_id="thr_sync_1", tenant_id="tenant_sync")
    assert len(listed) == 1


def test_dlq_status_mutation_is_persisted_via_repository():
    store = InMemoryStore()
    store.dlq_repository = CopyingDlqRepository()
    store.audit_repository = CopyingAuditRepository()

    item = store.seed_dlq_item(
        job_id="job_src_1",
        error_class="transient",
        error_code="RAG_UPSTREAM_UNAVAILABLE",
        tenant_id="tenant_sync",
    )
    result = store.requeue_dlq_item(dlq_id=item["dlq_id"], trace_id="trace_sync", tenant_id="tenant_sync")
    assert result["status"] == "queued"

    loaded = store.get_dlq_item(item["dlq_id"], tenant_id="tenant_sync")
    assert loaded is not None
    assert loaded["status"] == "requeued"
