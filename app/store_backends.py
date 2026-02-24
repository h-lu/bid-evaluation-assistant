from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.postgres import PostgresTxRunner
from app.db.rls import PostgresRlsManager
from app.repositories.audit_logs import InMemoryAuditLogsRepository, PostgresAuditLogsRepository
from app.repositories.dlq_items import InMemoryDlqItemsRepository, PostgresDlqItemsRepository
from app.repositories.documents import InMemoryDocumentsRepository, PostgresDocumentsRepository
from app.repositories.evaluation_reports import InMemoryEvaluationReportsRepository, PostgresEvaluationReportsRepository
from app.repositories.jobs import InMemoryJobsRepository, PostgresJobsRepository
from app.repositories.parse_manifests import InMemoryParseManifestsRepository, PostgresParseManifestsRepository
from app.repositories.projects import InMemoryProjectsRepository, PostgresProjectsRepository
from app.repositories.rule_packs import InMemoryRulePacksRepository, PostgresRulePacksRepository
from app.repositories.suppliers import InMemorySuppliersRepository, PostgresSuppliersRepository
from app.repositories.workflow_checkpoints import (
    InMemoryWorkflowCheckpointsRepository,
    PostgresWorkflowCheckpointsRepository,
)
from app.store import InMemoryStore


@dataclass
class IdempotencyRecord:
    fingerprint: str
    data: dict[str, Any]


class SqliteBackedStore(InMemoryStore):
    """Persistent store backend for P1 that snapshots state to SQLite."""

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize_database()
        self._load_state()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _initialize_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_state (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _state_snapshot(self) -> dict[str, Any]:
        idempotency_records = []
        for (scope, key), record in self.idempotency_records.items():
            idempotency_records.append(
                {
                    "scope": scope,
                    "key": key,
                    "fingerprint": record.fingerprint,
                    "data": record.data,
                }
            )
        return {
            "schema_version": 1,
            "idempotency_records": idempotency_records,
            "jobs": self.jobs,
            "documents": self.documents,
            "document_chunks": self.document_chunks,
            "projects": self.projects,
            "suppliers": self.suppliers,
            "rule_packs": self.rule_packs,
            "evaluation_reports": self.evaluation_reports,
            "parse_manifests": self.parse_manifests,
            "resume_tokens": self.resume_tokens,
            "audit_logs": self.audit_logs,
            "domain_events_outbox": self.domain_events_outbox,
            "outbox_delivery_records": self.outbox_delivery_records,
            "workflow_checkpoints": self.workflow_checkpoints,
            "citation_sources": self.citation_sources,
            "dlq_items": self.dlq_items,
            "legal_hold_objects": self.legal_hold_objects,
            "release_rollout_policies": self.release_rollout_policies,
            "release_replay_runs": self.release_replay_runs,
            "release_readiness_assessments": self.release_readiness_assessments,
            "counterexample_samples": self.counterexample_samples,
            "gold_candidate_samples": self.gold_candidate_samples,
            "dataset_version": self.dataset_version,
            "strategy_version_counter": self.strategy_version_counter,
            "strategy_config": self.strategy_config,
            "parser_retrieval_metrics": self.parser_retrieval_metrics,
        }

    def _restore_state(self, payload: dict[str, Any]) -> None:
        self.idempotency_records = {}
        for row in payload.get("idempotency_records", []):
            if not isinstance(row, dict):
                continue
            scope = row.get("scope")
            key = row.get("key")
            fingerprint = row.get("fingerprint")
            data = row.get("data")
            if not isinstance(scope, str) or not isinstance(key, str) or not isinstance(fingerprint, str):
                continue
            if not isinstance(data, dict):
                continue
            self.idempotency_records[(scope, key)] = IdempotencyRecord(
                fingerprint=fingerprint,
                data=data,
            )
        self.jobs = payload.get("jobs", {}) if isinstance(payload.get("jobs"), dict) else {}
        self.documents = payload.get("documents", {}) if isinstance(payload.get("documents"), dict) else {}
        self.document_chunks = (
            payload.get("document_chunks", {}) if isinstance(payload.get("document_chunks"), dict) else {}
        )
        self.projects = payload.get("projects", {}) if isinstance(payload.get("projects"), dict) else {}
        self.suppliers = payload.get("suppliers", {}) if isinstance(payload.get("suppliers"), dict) else {}
        self.rule_packs = payload.get("rule_packs", {}) if isinstance(payload.get("rule_packs"), dict) else {}
        self.evaluation_reports = (
            payload.get("evaluation_reports", {}) if isinstance(payload.get("evaluation_reports"), dict) else {}
        )
        self.parse_manifests = (
            payload.get("parse_manifests", {}) if isinstance(payload.get("parse_manifests"), dict) else {}
        )
        self.resume_tokens = payload.get("resume_tokens", {}) if isinstance(payload.get("resume_tokens"), dict) else {}
        self.audit_logs = payload.get("audit_logs", []) if isinstance(payload.get("audit_logs"), list) else []
        self.domain_events_outbox = (
            payload.get("domain_events_outbox", {}) if isinstance(payload.get("domain_events_outbox"), dict) else {}
        )
        self.outbox_delivery_records = (
            payload.get("outbox_delivery_records", {})
            if isinstance(payload.get("outbox_delivery_records"), dict)
            else {}
        )
        self.workflow_checkpoints = (
            payload.get("workflow_checkpoints", {}) if isinstance(payload.get("workflow_checkpoints"), dict) else {}
        )
        self.citation_sources = (
            payload.get("citation_sources", {}) if isinstance(payload.get("citation_sources"), dict) else {}
        )
        self.dlq_items = payload.get("dlq_items", {}) if isinstance(payload.get("dlq_items"), dict) else {}
        self.legal_hold_objects = (
            payload.get("legal_hold_objects", {}) if isinstance(payload.get("legal_hold_objects"), dict) else {}
        )
        self.release_rollout_policies = (
            payload.get("release_rollout_policies", {})
            if isinstance(payload.get("release_rollout_policies"), dict)
            else {}
        )
        self.release_replay_runs = (
            payload.get("release_replay_runs", {}) if isinstance(payload.get("release_replay_runs"), dict) else {}
        )
        self.release_readiness_assessments = (
            payload.get("release_readiness_assessments", {})
            if isinstance(payload.get("release_readiness_assessments"), dict)
            else {}
        )
        self.counterexample_samples = (
            payload.get("counterexample_samples", {}) if isinstance(payload.get("counterexample_samples"), dict) else {}
        )
        self.gold_candidate_samples = (
            payload.get("gold_candidate_samples", {}) if isinstance(payload.get("gold_candidate_samples"), dict) else {}
        )
        dataset_version = payload.get("dataset_version", "v1.0.0")
        self.dataset_version = dataset_version if isinstance(dataset_version, str) else "v1.0.0"
        strategy_version_counter = payload.get("strategy_version_counter", 0)
        self.strategy_version_counter = (
            int(strategy_version_counter)
            if isinstance(strategy_version_counter, int | float | str) and str(strategy_version_counter).isdigit()
            else 0
        )
        strategy_config = payload.get("strategy_config")
        if isinstance(strategy_config, dict):
            self.strategy_config = strategy_config
        metrics = payload.get("parser_retrieval_metrics")
        if isinstance(metrics, dict):
            merged = dict(self.parser_retrieval_metrics)
            for key, value in metrics.items():
                if key in merged and isinstance(value, int):
                    merged[key] = value
            self.parser_retrieval_metrics = merged
        self._bind_repositories()

    def _save_state(self) -> None:
        snapshot = self._state_snapshot()
        blob = json.dumps(snapshot, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                    INSERT INTO store_state(id, payload)
                    VALUES (1, ?)
                    ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                    """,
                (blob,),
            )
            conn.commit()

    def _load_state(self) -> None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM store_state WHERE id = 1").fetchone()
        if row is None:
            return
        payload_raw = row[0]
        if not isinstance(payload_raw, str):
            return
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        self._restore_state(payload)

    def reset(self) -> None:
        super().reset()
        self._save_state()

    def run_idempotent(
        self,
        *,
        endpoint: str,
        tenant_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        execute: callable,
    ) -> dict[str, Any]:
        data = super().run_idempotent(
            endpoint=endpoint,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            payload=payload,
            execute=execute,
        )
        self._save_state()
        return data

    def execute_release_pipeline(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().execute_release_pipeline(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            dataset_version=dataset_version,
            replay_passed=replay_passed,
            gate_results=gate_results,
        )
        self._save_state()
        return data

    def create_evaluation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_evaluation_job(payload)
        self._save_state()
        return data

    def create_upload_job(
        self,
        payload: dict[str, Any],
        *,
        file_bytes: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        data = super().create_upload_job(payload, file_bytes=file_bytes, content_type=content_type)
        self._save_state()
        return data

    def create_parse_job(self, *, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_parse_job(document_id=document_id, payload=payload)
        self._save_state()
        return data

    def transition_job_status(
        self,
        *,
        job_id: str,
        new_status: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = super().transition_job_status(job_id=job_id, new_status=new_status, tenant_id=tenant_id)
        self._save_state()
        return data

    def register_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str = "tenant_default",
        reasons: list[str] | None = None,
    ) -> None:
        super().register_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
            reasons=reasons,
        )
        self._save_state()

    def consume_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str,
    ) -> bool:
        data = super().consume_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def create_resume_job(self, *, evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_resume_job(evaluation_id=evaluation_id, payload=payload)
        self._save_state()
        return data

    def append_outbox_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().append_outbox_event(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        self._save_state()
        return data

    def mark_outbox_event_published(self, *, tenant_id: str, event_id: str) -> dict[str, Any]:
        data = super().mark_outbox_event_published(tenant_id=tenant_id, event_id=event_id)
        self._save_state()
        return data

    def mark_outbox_delivered(
        self,
        *,
        tenant_id: str,
        event_id: str,
        consumer_name: str,
        message_id: str,
    ) -> dict[str, Any]:
        data = super().mark_outbox_delivered(
            tenant_id=tenant_id,
            event_id=event_id,
            consumer_name=consumer_name,
            message_id=message_id,
        )
        self._save_state()
        return data

    def register_citation_source(self, *, chunk_id: str, source: dict[str, Any]) -> None:
        super().register_citation_source(chunk_id=chunk_id, source=source)
        self._save_state()

    def seed_dlq_item(
        self,
        *,
        job_id: str,
        error_class: str,
        error_code: str,
        tenant_id: str = "tenant_default",
    ) -> dict[str, Any]:
        data = super().seed_dlq_item(
            job_id=job_id,
            error_class=error_class,
            error_code=error_code,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def requeue_dlq_item(self, *, dlq_id: str, trace_id: str | None, tenant_id: str) -> dict[str, Any]:
        data = super().requeue_dlq_item(dlq_id=dlq_id, trace_id=trace_id, tenant_id=tenant_id)
        self._save_state()
        return data

    def discard_dlq_item(
        self,
        *,
        dlq_id: str,
        reason: str,
        reviewer_id: str,
        reviewer_id_2: str,
        tenant_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        data = super().discard_dlq_item(
            dlq_id=dlq_id,
            reason=reason,
            reviewer_id=reviewer_id,
            reviewer_id_2=reviewer_id_2,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def impose_legal_hold(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        reason: str,
        imposed_by: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().impose_legal_hold(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            imposed_by=imposed_by,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def release_legal_hold(
        self,
        *,
        hold_id: str,
        tenant_id: str,
        reason: str,
        reviewer_id: str,
        reviewer_id_2: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().release_legal_hold(
            hold_id=hold_id,
            tenant_id=tenant_id,
            reason=reason,
            reviewer_id=reviewer_id,
            reviewer_id_2=reviewer_id_2,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def execute_storage_cleanup(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        reason: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().execute_storage_cleanup(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def cancel_job(self, *, job_id: str, tenant_id: str) -> dict[str, Any]:
        data = super().cancel_job(job_id=job_id, tenant_id=tenant_id)
        self._save_state()
        return data

    def upsert_rollout_policy(
        self,
        *,
        release_id: str,
        tenant_whitelist: list[str],
        enabled_project_sizes: list[str],
        high_risk_hitl_enforced: bool,
        tenant_id: str,
    ) -> dict[str, Any]:
        data = super().upsert_rollout_policy(
            release_id=release_id,
            tenant_whitelist=tenant_whitelist,
            enabled_project_sizes=enabled_project_sizes,
            high_risk_hitl_enforced=high_risk_hitl_enforced,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def execute_rollback(
        self,
        *,
        release_id: str,
        consecutive_threshold: int,
        breaches: list[dict[str, Any]],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().execute_rollback(
            release_id=release_id,
            consecutive_threshold=consecutive_threshold,
            breaches=breaches,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def run_release_replay_e2e(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        project_id: str,
        supplier_id: str,
        doc_type: str = "bid",
        force_hitl: bool = True,
        decision: str = "approve",
    ) -> dict[str, Any]:
        data = super().run_release_replay_e2e(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            project_id=project_id,
            supplier_id=supplier_id,
            doc_type=doc_type,
            force_hitl=force_hitl,
            decision=decision,
        )
        self._save_state()
        return data

    def evaluate_release_readiness(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().evaluate_release_readiness(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            dataset_version=dataset_version,
            replay_passed=replay_passed,
            gate_results=gate_results,
        )
        self._save_state()
        return data

    def execute_release_pipeline(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().execute_release_pipeline(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            dataset_version=dataset_version,
            replay_passed=replay_passed,
            gate_results=gate_results,
        )
        self._save_state()
        return data

    def run_data_feedback(
        self,
        *,
        release_id: str,
        dlq_ids: list[str],
        version_bump: str,
        include_manual_override_candidates: bool,
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().run_data_feedback(
            release_id=release_id,
            dlq_ids=dlq_ids,
            version_bump=version_bump,
            include_manual_override_candidates=include_manual_override_candidates,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def apply_strategy_tuning(
        self,
        *,
        release_id: str,
        selector: dict[str, Any],
        score_calibration: dict[str, Any],
        tool_policy: dict[str, Any],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().apply_strategy_tuning(
            release_id=release_id,
            selector=selector,
            score_calibration=score_calibration,
            tool_policy=tool_policy,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def run_job_once(
        self,
        *,
        job_id: str,
        tenant_id: str,
        force_fail: bool = False,
        transient_fail: bool = False,
        force_error_code: str | None = None,
    ) -> dict[str, Any]:
        data = super().run_job_once(
            job_id=job_id,
            tenant_id=tenant_id,
            force_fail=force_fail,
            transient_fail=transient_fail,
            force_error_code=force_error_code,
        )
        self._save_state()
        return data


class PostgresBackedStore(InMemoryStore):
    """Persistent store backend for P1 that snapshots state to PostgreSQL."""

    def __init__(
        self,
        *,
        dsn: str,
        table_name: str = "bea_store_state",
        apply_rls: bool = False,
    ) -> None:
        super().__init__()
        if not os.environ.get("WORKFLOW_CHECKPOINT_BACKEND", "").strip():
            self.workflow_checkpoint_backend = "postgres"
        if not dsn.strip():
            raise ValueError("POSTGRES_DSN must be provided for postgres store backend")
        self._dsn = dsn.strip()
        self._table_name = table_name.strip() or "bea_store_state"
        self._lock = threading.RLock()
        self._initialize_database()
        self._tx_runner = PostgresTxRunner(self._dsn)
        self._jobs_pg_repo = PostgresJobsRepository(tx_runner=self._tx_runner, table_name="jobs")
        self._documents_pg_repo = PostgresDocumentsRepository(
            tx_runner=self._tx_runner,
            documents_table="documents",
            chunks_table="document_chunks",
        )
        self._projects_pg_repo = PostgresProjectsRepository(
            tx_runner=self._tx_runner,
            table_name="projects",
        )
        self._suppliers_pg_repo = PostgresSuppliersRepository(
            tx_runner=self._tx_runner,
            table_name="suppliers",
        )
        self._rule_packs_pg_repo = PostgresRulePacksRepository(
            tx_runner=self._tx_runner,
            table_name="rule_packs",
        )
        self._evaluation_reports_pg_repo = PostgresEvaluationReportsRepository(
            tx_runner=self._tx_runner,
            table_name="evaluation_reports",
        )
        self._parse_manifests_pg_repo = PostgresParseManifestsRepository(
            tx_runner=self._tx_runner,
            table_name="parse_manifests",
        )
        self._audit_pg_repo = PostgresAuditLogsRepository(
            tx_runner=self._tx_runner,
            table_name="audit_logs",
        )
        self._dlq_pg_repo = PostgresDlqItemsRepository(
            tx_runner=self._tx_runner,
            table_name="dlq_items",
        )
        self._workflow_pg_repo = PostgresWorkflowCheckpointsRepository(
            tx_runner=self._tx_runner,
            table_name="workflow_checkpoints",
        )
        self.projects_repository = self._projects_pg_repo
        self.suppliers_repository = self._suppliers_pg_repo
        self.rule_packs_repository = self._rule_packs_pg_repo
        if apply_rls:
            PostgresRlsManager(self._dsn).apply()
        self._load_state()

    def _connect(self) -> Any:
        from app.store import _import_psycopg
        psycopg = _import_psycopg()
        return psycopg.connect(self._dsn)

    def _initialize_database(self) -> None:
        create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                  id SMALLINT PRIMARY KEY,
                  payload JSONB NOT NULL
                )
                """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                      job_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      job_type TEXT NOT NULL,
                      status TEXT NOT NULL,
                      retry_count INTEGER NOT NULL DEFAULT 0,
                      thread_id TEXT NOT NULL,
                      trace_id TEXT,
                      resource JSONB NOT NULL,
                      payload JSONB NOT NULL,
                      last_error JSONB
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                      document_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      project_id TEXT,
                      supplier_id TEXT,
                      doc_type TEXT,
                      filename TEXT,
                      file_sha256 TEXT,
                      file_size BIGINT,
                      status TEXT NOT NULL,
                      storage_uri TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                      project_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      project_code TEXT NOT NULL,
                      name TEXT NOT NULL,
                      ruleset_version TEXT,
                      status TEXT NOT NULL,
                      created_at TEXT,
                      updated_at TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS suppliers (
                      supplier_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      supplier_code TEXT NOT NULL,
                      name TEXT NOT NULL,
                      qualification_json JSONB,
                      risk_flags_json JSONB,
                      status TEXT NOT NULL,
                      created_at TEXT,
                      updated_at TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rule_packs (
                      rule_pack_version TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      name TEXT NOT NULL,
                      status TEXT NOT NULL,
                      payload JSONB NOT NULL,
                      created_at TEXT,
                      updated_at TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_chunks (
                      chunk_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      document_id TEXT NOT NULL,
                      chunk_hash TEXT,
                      pages JSONB NOT NULL,
                      positions JSONB NOT NULL,
                      section TEXT,
                      heading_path JSONB NOT NULL,
                      chunk_type TEXT,
                      parser TEXT,
                      parser_version TEXT,
                      text TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE document_chunks
                    ADD COLUMN IF NOT EXISTS chunk_hash TEXT
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_reports (
                      evaluation_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      supplier_id TEXT,
                      total_score DOUBLE PRECISION,
                      confidence DOUBLE PRECISION,
                      citation_coverage DOUBLE PRECISION,
                      risk_level TEXT,
                      needs_human_review BOOLEAN NOT NULL DEFAULT FALSE,
                      trace_id TEXT,
                      thread_id TEXT,
                      interrupt JSONB,
                      payload JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS parse_manifests (
                      job_id TEXT PRIMARY KEY,
                      run_id TEXT NOT NULL,
                      document_id TEXT NOT NULL,
                      tenant_id TEXT NOT NULL,
                      selected_parser TEXT NOT NULL,
                      parser_version TEXT NOT NULL,
                      fallback_chain JSONB NOT NULL,
                      input_files JSONB NOT NULL,
                      started_at TEXT,
                      ended_at TEXT,
                      status TEXT NOT NULL,
                      error_code TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                      audit_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      evaluation_id TEXT,
                      action TEXT NOT NULL,
                      occurred_at TEXT,
                      payload JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dlq_items (
                      dlq_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      status TEXT NOT NULL,
                      payload JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                      checkpoint_id TEXT PRIMARY KEY,
                      tenant_id TEXT NOT NULL,
                      thread_id TEXT NOT NULL,
                      seq INTEGER NOT NULL,
                      payload JSONB NOT NULL
                    )
                    """
                )
            conn.commit()

    def _persist_job(self, *, job: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_job(job=job)
        tenant_id = str(saved.get("tenant_id") or "tenant_default")
        self._jobs_pg_repo.upsert(tenant_id=tenant_id, job=saved)
        return saved

    def get_job_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        loaded = self._jobs_pg_repo.get(tenant_id=tenant_id, job_id=job_id)
        if loaded is not None:
            self.jobs[job_id] = loaded
            return loaded
        return super().get_job_for_tenant(job_id=job_id, tenant_id=tenant_id)

    def _persist_document(self, *, document: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_document(document=document)
        tenant_id = str(saved.get("tenant_id") or "tenant_default")
        self._documents_pg_repo.upsert(tenant_id=tenant_id, document=saved)
        return saved

    def _persist_document_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        saved = super()._persist_document_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=chunks,
        )
        self._documents_pg_repo.replace_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=saved,
        )
        return saved

    def _persist_evaluation_report(self, *, report: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_evaluation_report(report=report)
        tenant_id = str(saved.get("tenant_id") or "tenant_default")
        self._evaluation_reports_pg_repo.upsert(tenant_id=tenant_id, report=saved)
        return saved

    def _persist_parse_manifest(self, *, manifest: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_parse_manifest(manifest=manifest)
        tenant_id = str(saved.get("tenant_id") or "tenant_default")
        self._parse_manifests_pg_repo.upsert(tenant_id=tenant_id, manifest=saved)
        return saved

    def _append_audit_log(self, *, log: dict[str, Any]) -> dict[str, Any]:
        saved = super()._append_audit_log(log=log)
        self._audit_pg_repo.append(log=saved)
        return saved

    def _persist_dlq_item(self, *, item: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_dlq_item(item=item)
        self._dlq_pg_repo.upsert(item=saved)
        return saved

    def _persist_workflow_checkpoint(self, *, checkpoint: dict[str, Any]) -> dict[str, Any]:
        saved = super()._persist_workflow_checkpoint(checkpoint=checkpoint)
        self._workflow_pg_repo.append(checkpoint=saved)
        return saved

    def get_document_for_tenant(self, *, document_id: str, tenant_id: str) -> dict[str, Any] | None:
        loaded = self._documents_pg_repo.get(tenant_id=tenant_id, document_id=document_id)
        if loaded is not None:
            self.documents[document_id] = loaded
            return loaded
        return super().get_document_for_tenant(document_id=document_id, tenant_id=tenant_id)

    def list_document_chunks_for_tenant(self, *, document_id: str, tenant_id: str) -> list[dict[str, Any]]:
        loaded = self._documents_pg_repo.list_chunks(tenant_id=tenant_id, document_id=document_id)
        if loaded:
            self.document_chunks[document_id] = loaded
            return loaded
        return super().list_document_chunks_for_tenant(document_id=document_id, tenant_id=tenant_id)

    def get_parse_manifest_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        loaded = self._parse_manifests_pg_repo.get(tenant_id=tenant_id, job_id=job_id)
        if loaded is not None:
            self.parse_manifests[job_id] = loaded
            return loaded
        return super().get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)

    def get_evaluation_report_for_tenant(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        loaded = self._evaluation_reports_pg_repo.get_any(evaluation_id=evaluation_id)
        if loaded is not None:
            self._assert_tenant_scope(loaded.get("tenant_id", "tenant_default"), tenant_id)
            self.evaluation_reports[evaluation_id] = loaded
            # Resolve citations to full objects per SSOT spec
            raw_citations = loaded.get("citations", [])
            if raw_citations and isinstance(raw_citations[0], str):
                resolved_citations = self._resolve_citations_batch(raw_citations, include_quote=True)
            else:
                resolved_citations = raw_citations
            # Resolve criteria_results citations (without quote per SSOT)
            raw_criteria = loaded.get("criteria_results", [])
            resolved_criteria = []
            for item in raw_criteria:
                item_copy = dict(item)
                item_citations = item_copy.get("citations", [])
                if item_citations and isinstance(item_citations[0], str):
                    item_copy["citations"] = self._resolve_citations_batch(item_citations, include_quote=False)
                item_copy.pop("weight", None)
                item_copy.pop("citations_count", None)
                resolved_criteria.append(item_copy)
            return {
                "evaluation_id": loaded["evaluation_id"],
                "supplier_id": loaded["supplier_id"],
                "total_score": loaded["total_score"],
                "confidence": loaded["confidence"],
                "citation_coverage": loaded.get("citation_coverage", 0.0),
                "risk_level": loaded["risk_level"],
                "criteria_results": resolved_criteria,
                "citations": resolved_citations,
                "needs_human_review": loaded["needs_human_review"],
                "trace_id": loaded["trace_id"],
                "interrupt": loaded.get("interrupt"),
                "report_uri": loaded.get("report_uri"),
            }
        return super().get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
        )

    def list_audit_logs_for_evaluation(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        loaded = self._audit_pg_repo.list_for_evaluation(
            tenant_id=tenant_id,
            evaluation_id=evaluation_id,
        )
        # Keep list identity stable so repository bindings remain valid across calls.
        self.audit_logs.clear()
        self.audit_logs.extend(dict(x) for x in loaded)
        return loaded

    def list_dlq_items(self, *, tenant_id: str) -> list[dict[str, Any]]:
        loaded = self._dlq_pg_repo.list(tenant_id=tenant_id)
        if loaded:
            for row in loaded:
                dlq_id = str(row.get("dlq_id", ""))
                if dlq_id:
                    self.dlq_items[dlq_id] = row
            return loaded
        return super().list_dlq_items(tenant_id=tenant_id)

    def get_dlq_item(self, dlq_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        loaded = self._dlq_pg_repo.get(tenant_id=tenant_id, dlq_id=dlq_id)
        if loaded is not None:
            self.dlq_items[dlq_id] = loaded
            return loaded
        return super().get_dlq_item(dlq_id, tenant_id=tenant_id)

    def list_workflow_checkpoints(
        self,
        *,
        thread_id: str,
        tenant_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        loaded = self._workflow_pg_repo.list(
            thread_id=thread_id,
            tenant_id=tenant_id,
            limit=limit,
        )
        if loaded:
            self.workflow_checkpoints[thread_id] = [dict(x) for x in loaded]
            return loaded
        return super().list_workflow_checkpoints(thread_id=thread_id, tenant_id=tenant_id, limit=limit)

    def _state_snapshot(self) -> dict[str, Any]:
        idempotency_records = []
        for (scope, key), record in self.idempotency_records.items():
            idempotency_records.append(
                {
                    "scope": scope,
                    "key": key,
                    "fingerprint": record.fingerprint,
                    "data": record.data,
                }
            )
        return {
            "schema_version": 1,
            "idempotency_records": idempotency_records,
            "jobs": self.jobs,
            "documents": self.documents,
            "document_chunks": self.document_chunks,
            "projects": self.projects,
            "suppliers": self.suppliers,
            "rule_packs": self.rule_packs,
            "evaluation_reports": self.evaluation_reports,
            "parse_manifests": self.parse_manifests,
            "resume_tokens": self.resume_tokens,
            "audit_logs": self.audit_logs,
            "domain_events_outbox": self.domain_events_outbox,
            "outbox_delivery_records": self.outbox_delivery_records,
            "workflow_checkpoints": self.workflow_checkpoints,
            "citation_sources": self.citation_sources,
            "dlq_items": self.dlq_items,
            "legal_hold_objects": self.legal_hold_objects,
            "release_rollout_policies": self.release_rollout_policies,
            "release_replay_runs": self.release_replay_runs,
            "release_readiness_assessments": self.release_readiness_assessments,
            "counterexample_samples": self.counterexample_samples,
            "gold_candidate_samples": self.gold_candidate_samples,
            "dataset_version": self.dataset_version,
            "strategy_version_counter": self.strategy_version_counter,
            "strategy_config": self.strategy_config,
            "parser_retrieval_metrics": self.parser_retrieval_metrics,
        }

    def _restore_state(self, payload: dict[str, Any]) -> None:
        self.idempotency_records = {}
        for row in payload.get("idempotency_records", []):
            if not isinstance(row, dict):
                continue
            scope = row.get("scope")
            key = row.get("key")
            fingerprint = row.get("fingerprint")
            data = row.get("data")
            if not isinstance(scope, str) or not isinstance(key, str) or not isinstance(fingerprint, str):
                continue
            if not isinstance(data, dict):
                continue
            self.idempotency_records[(scope, key)] = IdempotencyRecord(
                fingerprint=fingerprint,
                data=data,
            )
        self.jobs = payload.get("jobs", {}) if isinstance(payload.get("jobs"), dict) else {}
        self.documents = payload.get("documents", {}) if isinstance(payload.get("documents"), dict) else {}
        self.document_chunks = (
            payload.get("document_chunks", {}) if isinstance(payload.get("document_chunks"), dict) else {}
        )
        self.projects = payload.get("projects", {}) if isinstance(payload.get("projects"), dict) else {}
        self.suppliers = payload.get("suppliers", {}) if isinstance(payload.get("suppliers"), dict) else {}
        self.rule_packs = payload.get("rule_packs", {}) if isinstance(payload.get("rule_packs"), dict) else {}
        self.evaluation_reports = (
            payload.get("evaluation_reports", {}) if isinstance(payload.get("evaluation_reports"), dict) else {}
        )
        self.parse_manifests = (
            payload.get("parse_manifests", {}) if isinstance(payload.get("parse_manifests"), dict) else {}
        )
        self.resume_tokens = payload.get("resume_tokens", {}) if isinstance(payload.get("resume_tokens"), dict) else {}
        self.audit_logs = payload.get("audit_logs", []) if isinstance(payload.get("audit_logs"), list) else []
        self.domain_events_outbox = (
            payload.get("domain_events_outbox", {}) if isinstance(payload.get("domain_events_outbox"), dict) else {}
        )
        self.outbox_delivery_records = (
            payload.get("outbox_delivery_records", {})
            if isinstance(payload.get("outbox_delivery_records"), dict)
            else {}
        )
        self.workflow_checkpoints = (
            payload.get("workflow_checkpoints", {}) if isinstance(payload.get("workflow_checkpoints"), dict) else {}
        )
        self.citation_sources = (
            payload.get("citation_sources", {}) if isinstance(payload.get("citation_sources"), dict) else {}
        )
        self.dlq_items = payload.get("dlq_items", {}) if isinstance(payload.get("dlq_items"), dict) else {}
        self.legal_hold_objects = (
            payload.get("legal_hold_objects", {}) if isinstance(payload.get("legal_hold_objects"), dict) else {}
        )
        self.release_rollout_policies = (
            payload.get("release_rollout_policies", {})
            if isinstance(payload.get("release_rollout_policies"), dict)
            else {}
        )
        self.release_replay_runs = (
            payload.get("release_replay_runs", {}) if isinstance(payload.get("release_replay_runs"), dict) else {}
        )
        self.release_readiness_assessments = (
            payload.get("release_readiness_assessments", {})
            if isinstance(payload.get("release_readiness_assessments"), dict)
            else {}
        )
        self.counterexample_samples = (
            payload.get("counterexample_samples", {}) if isinstance(payload.get("counterexample_samples"), dict) else {}
        )
        self.gold_candidate_samples = (
            payload.get("gold_candidate_samples", {}) if isinstance(payload.get("gold_candidate_samples"), dict) else {}
        )
        dataset_version = payload.get("dataset_version", "v1.0.0")
        self.dataset_version = dataset_version if isinstance(dataset_version, str) else "v1.0.0"
        strategy_version_counter = payload.get("strategy_version_counter", 0)
        self.strategy_version_counter = (
            int(strategy_version_counter)
            if isinstance(strategy_version_counter, int | float | str) and str(strategy_version_counter).isdigit()
            else 0
        )
        strategy_config = payload.get("strategy_config")
        if isinstance(strategy_config, dict):
            self.strategy_config = strategy_config
        metrics = payload.get("parser_retrieval_metrics")
        if isinstance(metrics, dict):
            merged = dict(self.parser_retrieval_metrics)
            for key, value in metrics.items():
                if key in merged and isinstance(value, int):
                    merged[key] = value
            self.parser_retrieval_metrics = merged
        self._bind_repositories()

    def _save_state(self) -> None:
        snapshot = self._state_snapshot()
        blob = json.dumps(snapshot, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        upsert_sql = f"""
                    INSERT INTO {self._table_name}(id, payload)
                    VALUES (1, %s::jsonb)
                    ON CONFLICT(id) DO UPDATE SET payload = EXCLUDED.payload
                    """
        with self._lock, self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(upsert_sql, (blob,))
            conn.commit()

    def _load_state(self) -> None:
        select_sql = f"SELECT payload::text FROM {self._table_name} WHERE id = 1"
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(select_sql)
            row = cur.fetchone()
        if row is None:
            return
        payload_raw = row[0]
        if not isinstance(payload_raw, str):
            return
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        self._restore_state(payload)

    def reset(self) -> None:
        with self._lock, self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        TRUNCATE TABLE
                          jobs,
                          documents,
                          document_chunks,
                          evaluation_reports,
                          parse_manifests,
                          audit_logs,
                          dlq_items,
                          workflow_checkpoints
                        """
                )
            conn.commit()
        super().reset()
        self._save_state()

    def run_idempotent(
        self,
        *,
        endpoint: str,
        tenant_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        execute: callable,
    ) -> dict[str, Any]:
        data = super().run_idempotent(
            endpoint=endpoint,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            payload=payload,
            execute=execute,
        )
        self._save_state()
        return data

    def create_evaluation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_evaluation_job(payload)
        self._save_state()
        return data

    def create_upload_job(
        self,
        payload: dict[str, Any],
        *,
        file_bytes: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        data = super().create_upload_job(payload, file_bytes=file_bytes, content_type=content_type)
        self._save_state()
        return data

    def create_parse_job(self, *, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_parse_job(document_id=document_id, payload=payload)
        self._save_state()
        return data

    def transition_job_status(
        self,
        *,
        job_id: str,
        new_status: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = super().transition_job_status(job_id=job_id, new_status=new_status, tenant_id=tenant_id)
        self._save_state()
        return data

    def register_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str = "tenant_default",
        reasons: list[str] | None = None,
    ) -> None:
        super().register_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
            reasons=reasons,
        )
        self._save_state()

    def consume_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str,
    ) -> bool:
        data = super().consume_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def create_resume_job(self, *, evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_resume_job(evaluation_id=evaluation_id, payload=payload)
        self._save_state()
        return data

    def append_outbox_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().append_outbox_event(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        self._save_state()
        return data

    def mark_outbox_event_published(self, *, tenant_id: str, event_id: str) -> dict[str, Any]:
        data = super().mark_outbox_event_published(tenant_id=tenant_id, event_id=event_id)
        self._save_state()
        return data

    def mark_outbox_delivered(
        self,
        *,
        tenant_id: str,
        event_id: str,
        consumer_name: str,
        message_id: str,
    ) -> dict[str, Any]:
        data = super().mark_outbox_delivered(
            tenant_id=tenant_id,
            event_id=event_id,
            consumer_name=consumer_name,
            message_id=message_id,
        )
        self._save_state()
        return data

    def register_citation_source(self, *, chunk_id: str, source: dict[str, Any]) -> None:
        super().register_citation_source(chunk_id=chunk_id, source=source)
        self._save_state()

    def seed_dlq_item(
        self,
        *,
        job_id: str,
        error_class: str,
        error_code: str,
        tenant_id: str = "tenant_default",
    ) -> dict[str, Any]:
        data = super().seed_dlq_item(
            job_id=job_id,
            error_class=error_class,
            error_code=error_code,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def requeue_dlq_item(self, *, dlq_id: str, trace_id: str | None, tenant_id: str) -> dict[str, Any]:
        data = super().requeue_dlq_item(dlq_id=dlq_id, trace_id=trace_id, tenant_id=tenant_id)
        self._save_state()
        return data

    def discard_dlq_item(
        self,
        *,
        dlq_id: str,
        reason: str,
        reviewer_id: str,
        reviewer_id_2: str,
        tenant_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        data = super().discard_dlq_item(
            dlq_id=dlq_id,
            reason=reason,
            reviewer_id=reviewer_id,
            reviewer_id_2=reviewer_id_2,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def impose_legal_hold(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        reason: str,
        imposed_by: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().impose_legal_hold(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            imposed_by=imposed_by,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def release_legal_hold(
        self,
        *,
        hold_id: str,
        tenant_id: str,
        reason: str,
        reviewer_id: str,
        reviewer_id_2: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().release_legal_hold(
            hold_id=hold_id,
            tenant_id=tenant_id,
            reason=reason,
            reviewer_id=reviewer_id,
            reviewer_id_2=reviewer_id_2,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def execute_storage_cleanup(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        reason: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().execute_storage_cleanup(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def cancel_job(self, *, job_id: str, tenant_id: str) -> dict[str, Any]:
        data = super().cancel_job(job_id=job_id, tenant_id=tenant_id)
        self._save_state()
        return data

    def upsert_rollout_policy(
        self,
        *,
        release_id: str,
        tenant_whitelist: list[str],
        enabled_project_sizes: list[str],
        high_risk_hitl_enforced: bool,
        tenant_id: str,
    ) -> dict[str, Any]:
        data = super().upsert_rollout_policy(
            release_id=release_id,
            tenant_whitelist=tenant_whitelist,
            enabled_project_sizes=enabled_project_sizes,
            high_risk_hitl_enforced=high_risk_hitl_enforced,
            tenant_id=tenant_id,
        )
        self._save_state()
        return data

    def execute_rollback(
        self,
        *,
        release_id: str,
        consecutive_threshold: int,
        breaches: list[dict[str, Any]],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().execute_rollback(
            release_id=release_id,
            consecutive_threshold=consecutive_threshold,
            breaches=breaches,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def run_release_replay_e2e(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        project_id: str,
        supplier_id: str,
        doc_type: str = "bid",
        force_hitl: bool = True,
        decision: str = "approve",
    ) -> dict[str, Any]:
        data = super().run_release_replay_e2e(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            project_id=project_id,
            supplier_id=supplier_id,
            doc_type=doc_type,
            force_hitl=force_hitl,
            decision=decision,
        )
        self._save_state()
        return data

    def evaluate_release_readiness(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().evaluate_release_readiness(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            dataset_version=dataset_version,
            replay_passed=replay_passed,
            gate_results=gate_results,
        )
        self._save_state()
        return data

    def run_data_feedback(
        self,
        *,
        release_id: str,
        dlq_ids: list[str],
        version_bump: str,
        include_manual_override_candidates: bool,
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().run_data_feedback(
            release_id=release_id,
            dlq_ids=dlq_ids,
            version_bump=version_bump,
            include_manual_override_candidates=include_manual_override_candidates,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def apply_strategy_tuning(
        self,
        *,
        release_id: str,
        selector: dict[str, Any],
        score_calibration: dict[str, Any],
        tool_policy: dict[str, Any],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        data = super().apply_strategy_tuning(
            release_id=release_id,
            selector=selector,
            score_calibration=score_calibration,
            tool_policy=tool_policy,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        self._save_state()
        return data

    def run_job_once(
        self,
        *,
        job_id: str,
        tenant_id: str,
        force_fail: bool = False,
        transient_fail: bool = False,
        force_error_code: str | None = None,
    ) -> dict[str, Any]:
        data = super().run_job_once(
            job_id=job_id,
            tenant_id=tenant_id,
            force_fail=force_fail,
            transient_fail=transient_fail,
            force_error_code=force_error_code,
        )
        self._save_state()
        return data
