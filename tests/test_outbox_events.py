from __future__ import annotations

from pathlib import Path

from app.store import InMemoryStore, SqliteBackedStore


def _payload() -> dict:
    return {
        "project_id": "prj_outbox",
        "supplier_id": "sup_outbox",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
        "tenant_id": "tenant_outbox",
        "trace_id": "trace_outbox",
    }


def test_create_evaluation_adds_outbox_event():
    store = InMemoryStore()
    created = store.create_evaluation_job(_payload())
    events = store.list_outbox_events(tenant_id="tenant_outbox")
    assert events
    latest = events[-1]
    assert latest["event_type"] == "job.created"
    assert latest["aggregate_id"] == created["job_id"]
    assert latest["status"] == "pending"


def test_mark_outbox_event_published():
    store = InMemoryStore()
    store.create_evaluation_job(_payload())
    event = store.list_outbox_events(tenant_id="tenant_outbox")[-1]
    published = store.mark_outbox_event_published(tenant_id="tenant_outbox", event_id=event["event_id"])
    assert published["status"] == "published"
    assert published["published_at"] is not None


def test_sqlite_store_persists_outbox_events(tmp_path: Path):
    db_path = tmp_path / "outbox.sqlite3"
    store1 = SqliteBackedStore(str(db_path))
    created = store1.create_evaluation_job(_payload())
    event = store1.list_outbox_events(tenant_id="tenant_outbox")[-1]
    assert event["aggregate_id"] == created["job_id"]

    store2 = SqliteBackedStore(str(db_path))
    reloaded_events = store2.list_outbox_events(tenant_id="tenant_outbox")
    assert reloaded_events
    assert reloaded_events[-1]["aggregate_id"] == created["job_id"]
