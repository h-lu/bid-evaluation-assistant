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


def test_store_factory_rejects_non_postgres_when_true_stack_required(monkeypatch):
    monkeypatch.setenv("BEA_REQUIRE_TRUESTACK", "true")
    monkeypatch.setenv("BEA_STORE_BACKEND", "sqlite")
    try:
        create_store_from_env()
    except RuntimeError as exc:
        assert "BEA_STORE_BACKEND" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when true stack is required")


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
    shared: dict[str, object] = {"jobs": {}}

    class FakeCursor:
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None) -> None:
            normalized = " ".join(query.strip().split()).lower()
            if normalized.startswith("create table if not exists") or normalized.startswith("alter table"):
                return
            if normalized.startswith("set local app.current_tenant =") or normalized.startswith(
                "select set_config('app.current_tenant',"
            ):
                return
            if normalized.startswith("select payload::text from"):
                payload = self._state.get("payload")
                self._row = (payload,) if payload is not None else None
                return
            if normalized.startswith("select job_id, tenant_id, job_type"):
                if not params:
                    raise AssertionError("expected tenant_id and job_id")
                tenant_id, job_id = params
                jobs = self._state.get("jobs", {})
                assert isinstance(jobs, dict)
                row = jobs.get(str(job_id))
                if isinstance(row, tuple) and row[1] == tenant_id:
                    self._row = row
                else:
                    self._row = None
                return
            if normalized.startswith("insert into") and "bea_store_state" in normalized:
                if not params:
                    raise AssertionError("expected payload parameter")
                self._state["payload"] = str(params[0])
                return
            if normalized.startswith("insert into") and "insert into jobs" in normalized:
                if not params:
                    raise AssertionError("expected jobs insert parameters")
                jobs = self._state.setdefault("jobs", {})
                assert isinstance(jobs, dict)
                jobs[str(params[0])] = params
                return
            if normalized.startswith("insert into") and "insert into evaluation_reports" in normalized:
                if not params:
                    raise AssertionError("expected evaluation_reports insert parameters")
                reports = self._state.setdefault("evaluation_reports", {})
                assert isinstance(reports, dict)
                reports[str(params[0])] = params
                return
            raise AssertionError(f"unexpected SQL: {query}")

        def fetchone(self):
            return self._row

    class FakeConnection:
        def __init__(self, state: dict[str, object]) -> None:
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
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state
            self.dsns: list[str] = []

        def connect(self, dsn: str) -> FakeConnection:
            self.dsns.append(dsn)
            return FakeConnection(self._state)

    fake_psycopg = FakePsycopg(shared)
    monkeypatch.setenv("BEA_STORE_BACKEND", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://test-user:test-pass@localhost:5432/bea")
    monkeypatch.setattr("app.store._import_psycopg", lambda: fake_psycopg)
    monkeypatch.setattr("app.db.postgres._import_psycopg", lambda: fake_psycopg)

    store = create_store_from_env()
    assert isinstance(store, PostgresBackedStore)
    payload = _evaluation_payload()
    created = store.create_evaluation_job(payload)
    assert created["job_id"].startswith("job_")

    store_reloaded = create_store_from_env()
    reloaded_job = store_reloaded.get_job_for_tenant(job_id=created["job_id"], tenant_id="tenant_store")
    assert reloaded_job is not None
    assert fake_psycopg.dsns


def test_store_factory_postgres_reports_missing_psycopg(monkeypatch):
    monkeypatch.setenv("BEA_STORE_BACKEND", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://missing-driver")

    def _raise_missing():
        raise ImportError("No module named psycopg")

    monkeypatch.setattr("app.store._import_psycopg", _raise_missing)
    try:
        create_store_from_env()
    except (RuntimeError, ImportError) as exc:
        assert "psycopg" in str(exc)
    else:
        raise AssertionError("expected error when psycopg is missing")


def test_store_factory_passes_postgres_apply_rls_flag(monkeypatch):
    captured: dict[str, object] = {}

    class FakeStore:
        def __init__(self, *, dsn: str, table_name: str, apply_rls: bool = False) -> None:
            captured["dsn"] = dsn
            captured["table_name"] = table_name
            captured["apply_rls"] = apply_rls

    monkeypatch.setenv("BEA_STORE_BACKEND", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://with-rls")
    monkeypatch.setenv("BEA_STORE_POSTGRES_TABLE", "bea_store_state")
    monkeypatch.setenv("POSTGRES_APPLY_RLS", "true")
    monkeypatch.setattr("app.store.PostgresBackedStore", FakeStore)

    store = create_store_from_env()
    assert isinstance(store, FakeStore)
    assert captured["dsn"] == "postgresql://with-rls"
    assert captured["table_name"] == "bea_store_state"
    assert captured["apply_rls"] is True


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


def test_postgres_store_uses_parse_manifest_repository_sql(monkeypatch):
    shared: dict[str, object] = {"parse_rows": {}}
    statements: list[str] = []

    class FakeCursor:
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None) -> None:
            normalized = " ".join(query.strip().split()).lower()
            statements.append(normalized)
            if normalized.startswith("create table if not exists") or normalized.startswith("alter table"):
                return
            if normalized.startswith("set local app.current_tenant =") or normalized.startswith(
                "select set_config('app.current_tenant',"
            ):
                return
            if normalized.startswith("select payload::text from"):
                self._row = None
                return
            if normalized.startswith("insert into") and "parse_manifests" in normalized:
                if not params:
                    raise AssertionError("expected parse manifest parameters")
                rows = self._state.setdefault("parse_rows", {})
                assert isinstance(rows, dict)
                rows[str(params[0])] = params
                return
            if normalized.startswith("select job_id, run_id, document_id, tenant_id") and "parse_manifests" in normalized:
                if not params:
                    raise AssertionError("expected tenant_id and job_id")
                tenant_id, job_id = params
                rows = self._state.get("parse_rows", {})
                assert isinstance(rows, dict)
                row = rows.get(str(job_id))
                if isinstance(row, tuple) and row[3] == tenant_id:
                    self._row = row
                else:
                    self._row = None
                return
            raise AssertionError(f"unexpected SQL: {query}")

        def fetchone(self):
            return self._row

    class FakeConnection:
        def __init__(self, state: dict[str, object]) -> None:
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
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state

        def connect(self, dsn: str) -> FakeConnection:
            return FakeConnection(self._state)

    fake_psycopg = FakePsycopg(shared)
    monkeypatch.setattr("app.store._import_psycopg", lambda: fake_psycopg)
    monkeypatch.setattr("app.db.postgres._import_psycopg", lambda: fake_psycopg)

    store = PostgresBackedStore(dsn="postgresql://test")

    manifest = {
        "run_id": "prun_store_pg_1",
        "job_id": "job_store_pg_1",
        "document_id": "doc_store_pg_1",
        "tenant_id": "tenant_store",
        "selected_parser": "mineru",
        "parser_version": "v0",
        "fallback_chain": ["docling", "ocr"],
        "input_files": [{"name": "a.pdf", "sha256": "abc", "size": 12}],
        "started_at": "2026-02-22T00:00:00+00:00",
        "ended_at": None,
        "status": "queued",
        "error_code": None,
    }

    store._persist_parse_manifest(manifest=manifest)
    loaded = store.get_parse_manifest_for_tenant(job_id="job_store_pg_1", tenant_id="tenant_store")

    assert loaded is not None
    assert loaded["job_id"] == "job_store_pg_1"
    assert any("insert into parse_manifests" in sql for sql in statements)
    assert any("from parse_manifests" in sql for sql in statements)


def test_postgres_store_run_job_once_persists_status_between_transitions(monkeypatch):
    shared: dict[str, object] = {"jobs": {}, "evaluation_reports": {}, "checkpoints": {}}
    statements: list[str] = []

    class FakeCursor:
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query: str, params=None) -> None:
            normalized = " ".join(query.strip().split()).lower()
            statements.append(normalized)
            if normalized.startswith("create table if not exists") or normalized.startswith("alter table"):
                return
            if normalized.startswith("set local app.current_tenant =") or normalized.startswith(
                "select set_config('app.current_tenant',"
            ):
                return
            if normalized.startswith("select payload::text from"):
                self._row = None
                return
            if normalized.startswith("insert into") and "bea_store_state" in normalized:
                return
            if normalized.startswith("insert into") and "insert into jobs" in normalized:
                if not params:
                    raise AssertionError("expected jobs insert parameters")
                rows = self._state.setdefault("jobs", {})
                assert isinstance(rows, dict)
                rows[str(params[0])] = params
                return
            if normalized.startswith("select job_id, tenant_id, job_type") and "from jobs" in normalized:
                if not params:
                    raise AssertionError("expected tenant_id and job_id")
                tenant_id, job_id = params
                rows = self._state.get("jobs", {})
                assert isinstance(rows, dict)
                row = rows.get(str(job_id))
                if isinstance(row, tuple) and row[1] == tenant_id:
                    self._row = row
                else:
                    self._row = None
                return
            if normalized.startswith("insert into") and "insert into evaluation_reports" in normalized:
                if not params:
                    raise AssertionError("expected evaluation reports parameters")
                rows = self._state.setdefault("evaluation_reports", {})
                assert isinstance(rows, dict)
                rows[str(params[0])] = params
                return
            if normalized.startswith("insert into") and "insert into workflow_checkpoints" in normalized:
                if not params:
                    raise AssertionError("expected checkpoint parameters")
                rows = self._state.setdefault("checkpoints", {})
                assert isinstance(rows, dict)
                rows[str(params[0])] = params
                return
            raise AssertionError(f"unexpected SQL: {query}")

        def fetchone(self):
            return self._row

    class FakeConnection:
        def __init__(self, state: dict[str, object]) -> None:
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
        def __init__(self, state: dict[str, object]) -> None:
            self._state = state

        def connect(self, dsn: str) -> FakeConnection:
            return FakeConnection(self._state)

    fake_psycopg = FakePsycopg(shared)
    monkeypatch.setattr("app.store._import_psycopg", lambda: fake_psycopg)
    monkeypatch.setattr("app.db.postgres._import_psycopg", lambda: fake_psycopg)

    store = PostgresBackedStore(dsn="postgresql://test")
    created = store.create_evaluation_job(_evaluation_payload())
    result = store.run_job_once(job_id=created["job_id"], tenant_id="tenant_store")

    assert result["final_status"] == "succeeded"
    job_row = shared["jobs"][created["job_id"]]
    assert isinstance(job_row, tuple)
    assert job_row[3] == "succeeded"
    insert_jobs = [sql for sql in statements if "insert into jobs" in sql]
    assert len(insert_jobs) >= 2
