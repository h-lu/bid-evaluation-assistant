from __future__ import annotations

from pathlib import Path

from app.store import InMemoryStore, SqliteBackedStore, create_store_from_env


def _evaluation_payload() -> dict:
    return {
        "project_id": "prj_store",
        "supplier_id": "sup_store",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
        "tenant_id": "tenant_store",
        "trace_id": "trace_store",
    }


def test_sqlite_store_persists_jobs_and_idempotency_across_instances(tmp_path: Path):
    db_path = tmp_path / "store.sqlite3"
    store1 = SqliteBackedStore(str(db_path))

    payload = _evaluation_payload()
    created = store1.run_idempotent(
        endpoint="POST:/api/v1/evaluations",
        tenant_id="tenant_store",
        idempotency_key="idem_store_1",
        payload=payload,
        execute=lambda: store1.create_evaluation_job(payload),
    )
    assert created["job_id"].startswith("job_")

    store2 = SqliteBackedStore(str(db_path))
    reloaded_job = store2.get_job_for_tenant(job_id=created["job_id"], tenant_id="tenant_store")
    assert reloaded_job is not None
    assert reloaded_job["job_id"] == created["job_id"]

    replay = store2.run_idempotent(
        endpoint="POST:/api/v1/evaluations",
        tenant_id="tenant_store",
        idempotency_key="idem_store_1",
        payload=payload,
        execute=lambda: {"unexpected": True},
    )
    assert replay["job_id"] == created["job_id"]


def test_store_factory_defaults_to_in_memory(monkeypatch):
    monkeypatch.delenv("BEA_STORE_BACKEND", raising=False)
    monkeypatch.delenv("BEA_STORE_SQLITE_PATH", raising=False)
    store = create_store_from_env()
    assert isinstance(store, InMemoryStore)


def test_store_factory_uses_sqlite_backend_when_configured(monkeypatch, tmp_path: Path):
    sqlite_path = tmp_path / "factory.sqlite3"
    monkeypatch.setenv("BEA_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("BEA_STORE_SQLITE_PATH", str(sqlite_path))

    store = create_store_from_env()
    assert isinstance(store, SqliteBackedStore)

    payload = _evaluation_payload()
    created = store.create_evaluation_job(payload)
    assert created["job_id"].startswith("job_")

    store_reloaded = create_store_from_env()
    reloaded_job = store_reloaded.get_job_for_tenant(job_id=created["job_id"], tenant_id="tenant_store")
    assert reloaded_job is not None


def test_sqlite_store_persists_workflow_checkpoints(tmp_path: Path):
    db_path = tmp_path / "checkpoints.sqlite3"
    store1 = SqliteBackedStore(str(db_path))
    created = store1.create_evaluation_job(_evaluation_payload())
    job = store1.get_job_for_tenant(job_id=created["job_id"], tenant_id="tenant_store")
    assert job is not None
    thread_id = job["thread_id"]

    run = store1.run_job_once(job_id=created["job_id"], tenant_id="tenant_store")
    assert run["final_status"] == "succeeded"
    checkpoints = store1.list_workflow_checkpoints(thread_id=thread_id, tenant_id="tenant_store")
    assert checkpoints

    store2 = SqliteBackedStore(str(db_path))
    reloaded_checkpoints = store2.list_workflow_checkpoints(thread_id=thread_id, tenant_id="tenant_store")
    assert reloaded_checkpoints
    assert reloaded_checkpoints[-1]["status"] == "succeeded"
