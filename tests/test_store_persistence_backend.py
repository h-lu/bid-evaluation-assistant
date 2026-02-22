from __future__ import annotations

from pathlib import Path

from app.store import InMemoryStore, PostgresBackedStore, SqliteBackedStore, create_store_from_env


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


def test_store_factory_requires_postgres_dsn(monkeypatch):
    monkeypatch.setenv("BEA_STORE_BACKEND", "postgres")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    try:
        create_store_from_env()
    except ValueError as exc:
        assert "POSTGRES_DSN" in str(exc)
    else:
        raise AssertionError("expected ValueError when POSTGRES_DSN is missing")


def test_store_factory_uses_postgres_backend_with_fake_driver(monkeypatch):
    shared: dict[str, str] = {}

    class FakeCursor:
        def __init__(self, state: dict[str, str]) -> None:
            self._state = state
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None) -> None:
            normalized = " ".join(query.strip().split()).lower()
            if normalized.startswith("create table if not exists"):
                return
            if normalized.startswith("select payload::text from"):
                payload = self._state.get("payload")
                self._row = (payload,) if payload is not None else None
                return
            if normalized.startswith("insert into"):
                if not params:
                    raise AssertionError("expected payload parameter")
                self._state["payload"] = str(params[0])
                return
            raise AssertionError(f"unexpected SQL: {query}")

        def fetchone(self):
            return self._row

    class FakeConnection:
        def __init__(self, state: dict[str, str]) -> None:
            self._state = state

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor(self._state)

        def commit(self) -> None:
            return None

    class FakePsycopg:
        def __init__(self, state: dict[str, str]) -> None:
            self._state = state
            self.dsns: list[str] = []

        def connect(self, dsn: str) -> FakeConnection:
            self.dsns.append(dsn)
            return FakeConnection(self._state)

    fake_psycopg = FakePsycopg(shared)
    monkeypatch.setenv("BEA_STORE_BACKEND", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://test-user:test-pass@localhost:5432/bea")
    monkeypatch.setattr("app.store._import_psycopg", lambda: fake_psycopg)

    store = create_store_from_env()
    assert isinstance(store, PostgresBackedStore)
    payload = _evaluation_payload()
    created = store.create_evaluation_job(payload)
    assert created["job_id"].startswith("job_")

    store_reloaded = create_store_from_env()
    reloaded_job = store_reloaded.get_job_for_tenant(job_id=created["job_id"], tenant_id="tenant_store")
    assert reloaded_job is not None
    assert fake_psycopg.dsns


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


def test_sqlite_store_persists_release_replay_and_readiness(tmp_path: Path):
    db_path = tmp_path / "release.sqlite3"
    store1 = SqliteBackedStore(str(db_path))
    replay = store1.run_release_replay_e2e(
        release_id="rel_store_001",
        tenant_id="tenant_store",
        trace_id="trace_store",
        project_id="prj_store",
        supplier_id="sup_store",
        doc_type="bid",
        force_hitl=True,
        decision="approve",
    )
    readiness = store1.evaluate_release_readiness(
        release_id="rel_store_001",
        tenant_id="tenant_store",
        trace_id="trace_store",
        replay_passed=True,
        gate_results={
            "quality": True,
            "performance": True,
            "security": True,
            "cost": True,
            "rollout": True,
            "rollback": True,
            "ops": True,
        },
    )

    store2 = SqliteBackedStore(str(db_path))
    persisted_replay = store2.release_replay_runs.get(replay["replay_run_id"])
    assert persisted_replay is not None
    assert persisted_replay["release_id"] == "rel_store_001"
    persisted_readiness = store2.release_readiness_assessments.get(readiness["assessment_id"])
    assert persisted_readiness is not None
    assert persisted_readiness["admitted"] is True
