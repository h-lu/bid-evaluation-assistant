from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.errors import ApiError
from app.llm_provider import is_real_llm_available  # noqa: F401 - re-exported
from app.mock_llm import (  # noqa: F401
    MOCK_LLM_ENABLED,  # noqa: F401 - re-exported
    mock_retrieve_evidence,
    mock_score_criteria,
)
from app.object_storage import build_report_filename, create_object_storage_from_env
from app.parser_adapters import (
    ParseRoute,
    build_default_parser_registry,
    disabled_parsers_from_env,
    select_parse_route,
)
from app.repositories.audit_logs import InMemoryAuditLogsRepository
from app.repositories.dlq_items import InMemoryDlqItemsRepository
from app.repositories.documents import InMemoryDocumentsRepository
from app.repositories.evaluation_reports import InMemoryEvaluationReportsRepository
from app.repositories.jobs import InMemoryJobsRepository
from app.repositories.parse_manifests import InMemoryParseManifestsRepository
from app.repositories.projects import InMemoryProjectsRepository
from app.repositories.rule_packs import InMemoryRulePacksRepository
from app.repositories.suppliers import InMemorySuppliersRepository
from app.repositories.workflow_checkpoints import InMemoryWorkflowCheckpointsRepository
from app.runtime_profile import true_stack_required
from app.store_admin import StoreAdminMixin
from app.store_eval import StoreEvalMixin
from app.store_ops import StoreOpsMixin
from app.store_parse import StoreParseMixin
from app.store_release import StoreReleaseMixin
from app.store_retrieval import StoreRetrievalMixin
from app.store_workflow import StoreWorkflowMixin


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value, ensure_ascii=True)
        return value
    except TypeError:
        return str(value)


@dataclass
class IdempotencyRecord:
    fingerprint: str
    data: dict[str, Any]


class InMemoryStore(
    StoreParseMixin,
    StoreEvalMixin,
    StoreRetrievalMixin,
    StoreReleaseMixin,
    StoreAdminMixin,
    StoreWorkflowMixin,
    StoreOpsMixin,
):
    RESUME_TOKEN_TTL_HOURS = 24

    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        "queued": {"running"},
        "running": {"retrying", "succeeded", "needs_manual_decision", "dlq_pending"},
        "retrying": {"running", "dlq_pending"},
        "needs_manual_decision": {"running", "succeeded"},
        "dlq_pending": {"dlq_recorded"},
        "dlq_recorded": {"failed"},
        "succeeded": set(),
        "failed": set(),
    }

    def __init__(self) -> None:
        self.resume_token_ttl_hours = self._env_int(
            "RESUME_TOKEN_TTL_HOURS",
            default=self.RESUME_TOKEN_TTL_HOURS,
            minimum=1,
        )
        self.worker_max_retries = self._env_int("WORKER_MAX_RETRIES", default=3, minimum=0)
        self.worker_retry_backoff_base_ms = self._env_int(
            "WORKER_RETRY_BACKOFF_BASE_MS",
            default=1000,
            minimum=0,
        )
        self.worker_retry_backoff_max_ms = self._env_int(
            "WORKER_RETRY_BACKOFF_MAX_MS",
            default=30000,
            minimum=0,
        )
        self.workflow_checkpoint_backend = (
            os.environ.get("WORKFLOW_CHECKPOINT_BACKEND", "memory").strip().lower() or "memory"
        )
        self.obs_metrics_namespace = os.environ.get("OBS_METRICS_NAMESPACE", "bea").strip() or "bea"
        self.otel_exporter_otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        self.obs_alert_webhook = os.environ.get("OBS_ALERT_WEBHOOK", "").strip()
        self.release_canary_ratio = self._env_float("RELEASE_CANARY_RATIO", default=0.1, minimum=0.0, maximum=1.0)
        self.release_canary_duration_min = self._env_int("RELEASE_CANARY_DURATION_MIN", default=30, minimum=1)
        self.rollback_max_minutes = self._env_int("ROLLBACK_MAX_MINUTES", default=30, minimum=1)
        self.p6_readiness_required = self._env_bool("P6_READINESS_REQUIRED", default=True)
        self.object_storage = create_object_storage_from_env(os.environ)
        self.idempotency_records: dict[tuple[str, str], IdempotencyRecord] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.document_chunks: dict[str, list[dict[str, Any]]] = {}
        self.projects: dict[str, dict[str, Any]] = {}
        self.suppliers: dict[str, dict[str, Any]] = {}
        self.rule_packs: dict[str, dict[str, Any]] = {}
        self.evaluation_reports: dict[str, dict[str, Any]] = {}
        self.parse_manifests: dict[str, dict[str, Any]] = {}
        self.resume_tokens: dict[str, dict[str, Any]] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.domain_events_outbox: dict[str, dict[str, Any]] = {}
        self.outbox_delivery_records: dict[str, dict[str, Any]] = {}
        self.workflow_checkpoints: dict[str, list[dict[str, Any]]] = {}
        self.langgraph_checkpoint_kind = "langgraph_state"
        self.citation_sources: dict[str, dict[str, Any]] = {}
        self.dlq_items: dict[str, dict[str, Any]] = {}
        self.legal_hold_objects: dict[str, dict[str, Any]] = {}
        self.release_rollout_policies: dict[str, dict[str, Any]] = {}
        self.release_replay_runs: dict[str, dict[str, Any]] = {}
        self.release_readiness_assessments: dict[str, dict[str, Any]] = {}
        self.counterexample_samples: dict[str, dict[str, Any]] = {}
        self.gold_candidate_samples: dict[str, dict[str, Any]] = {}
        self.dataset_version: str = "v1.0.0"
        self.strategy_version_counter: int = 0
        self.strategy_config: dict[str, Any] = {
            "selector": {"risk_mix_threshold": 0.7, "relation_mode": "global"},
            "score_calibration": {"confidence_scale": 1.0, "score_bias": 0.0},
            "tool_policy": {
                "require_double_approval_actions": ["dlq_discard"],
                "allowed_tools": ["retrieval", "evaluation", "dlq"],
            },
        }
        self.parser_retrieval_metrics: dict[str, int] = {
            "parse_runs_total": 0,
            "parse_fallback_used_total": 0,
            "parse_index_write_total": 0,
            "parse_index_fail_total": 0,
            "retrieval_queries_total": 0,
            "retrieval_lightrag_calls_total": 0,
            "retrieval_lightrag_fail_total": 0,
            "rerank_degraded_total": 0,
        }
        self._bind_repositories()

    @staticmethod
    def _env_int(name: str, *, default: int, minimum: int = 0) -> int:
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            return default
        return max(minimum, value)

    @staticmethod
    def _env_float(name: str, *, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            return default
        return max(minimum, min(maximum, value))

    @staticmethod
    def _env_bool(name: str, *, default: bool) -> bool:
        raw = os.environ.get(name, "").strip().lower()
        if not raw:
            return default
        return raw in {"1", "true", "yes", "on"}

    def _bind_repositories(self) -> None:
        self.jobs_repository = InMemoryJobsRepository(self.jobs)
        self.documents_repository = InMemoryDocumentsRepository(self.documents, self.document_chunks)
        self.parse_manifests_repository = InMemoryParseManifestsRepository(self.parse_manifests)
        self.projects_repository = InMemoryProjectsRepository(self.projects)
        self.suppliers_repository = InMemorySuppliersRepository(self.suppliers)
        self.rule_packs_repository = InMemoryRulePacksRepository(self.rule_packs)
        self.evaluation_reports_repository = InMemoryEvaluationReportsRepository(self.evaluation_reports)
        self.audit_repository = InMemoryAuditLogsRepository(self.audit_logs)
        self.dlq_repository = InMemoryDlqItemsRepository(self.dlq_items)
        self.workflow_repository = InMemoryWorkflowCheckpointsRepository(self.workflow_checkpoints)
        self._parser_registry = build_default_parser_registry(
            disabled_parsers=disabled_parsers_from_env(),
            env=os.environ,
        )

    def reset(self) -> None:
        self.object_storage = create_object_storage_from_env(os.environ)
        reset_fn = getattr(self.object_storage, "reset", None)
        if callable(reset_fn):
            reset_fn()
        self.idempotency_records.clear()
        self.jobs.clear()
        self.documents.clear()
        self.document_chunks.clear()
        self.projects.clear()
        self.suppliers.clear()
        self.rule_packs.clear()
        self.evaluation_reports.clear()
        self.parse_manifests.clear()
        self.resume_tokens.clear()
        self.audit_logs.clear()
        self.domain_events_outbox.clear()
        self.outbox_delivery_records.clear()
        self.workflow_checkpoints.clear()
        self.citation_sources.clear()
        self.dlq_items.clear()
        self.legal_hold_objects.clear()
        self.release_rollout_policies.clear()
        self.release_replay_runs.clear()
        self.release_readiness_assessments.clear()
        self.counterexample_samples.clear()
        self.gold_candidate_samples.clear()
        self.dataset_version = "v1.0.0"
        self.strategy_version_counter = 0
        self.strategy_config = {
            "selector": {"risk_mix_threshold": 0.7, "relation_mode": "global"},
            "score_calibration": {"confidence_scale": 1.0, "score_bias": 0.0},
            "tool_policy": {
                "require_double_approval_actions": ["dlq_discard"],
                "allowed_tools": ["retrieval", "evaluation", "dlq"],
            },
        }
        self.parser_retrieval_metrics = {
            "parse_runs_total": 0,
            "parse_fallback_used_total": 0,
            "parse_index_write_total": 0,
            "parse_index_fail_total": 0,
            "retrieval_queries_total": 0,
            "retrieval_lightrag_calls_total": 0,
            "retrieval_lightrag_fail_total": 0,
            "rerank_degraded_total": 0,
        }

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def _assert_tenant_scope(entity_tenant_id: str, tenant_id: str) -> None:
        if entity_tenant_id != tenant_id:
            raise ApiError(
                code="TENANT_SCOPE_VIOLATION",
                message="tenant mismatch",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _new_thread_id(prefix: str) -> str:
        return f"thr_{prefix}_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def _retry_jitter_ms(*, job_id: str, retry_count: int) -> int:
        seed = f"{job_id}:{retry_count}".encode()
        digest = hashlib.sha256(seed).digest()
        return int.from_bytes(digest[:2], byteorder="big") % 301

    def _retry_backoff_ms(self, *, job_id: str, retry_count: int) -> int:
        normalized_retry = max(1, int(retry_count))
        base = max(0, int(self.worker_retry_backoff_base_ms))
        max_backoff = max(base, int(self.worker_retry_backoff_max_ms))
        exponential = base * (2 ** (normalized_retry - 1))
        return min(max_backoff, exponential) + self._retry_jitter_ms(
            job_id=job_id,
            retry_count=normalized_retry,
        )

    def _persist_job(self, *, job: dict[str, Any]) -> dict[str, Any]:
        return self.jobs_repository.create(job=job)

    def _persist_document(self, *, document: dict[str, Any]) -> dict[str, Any]:
        return self.documents_repository.upsert(document=document)

    def _persist_document_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        deduped = self._dedupe_chunks(document_id=document_id, chunks=chunks)
        return self.documents_repository.replace_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=deduped,
        )

    def _persist_parse_manifest(self, *, manifest: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(manifest.get("tenant_id") or "tenant_default")
        return self.parse_manifests_repository.upsert(tenant_id=tenant_id, manifest=manifest)

    def _persist_evaluation_report(self, *, report: dict[str, Any]) -> dict[str, Any]:
        archived = self._archive_report_to_object_storage(report=report)
        return self.evaluation_reports_repository.upsert(report=archived)

    def _archive_report_to_object_storage(self, *, report: dict[str, Any]) -> dict[str, Any]:
        item = dict(report)
        evaluation_id = str(item.get("evaluation_id") or "")
        tenant_id = str(item.get("tenant_id") or "tenant_default")
        if not evaluation_id:
            return item
        filename = build_report_filename(report_payload=item)
        payload = dict(item)
        payload.pop("report_uri", None)
        blob = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        storage_uri = self.object_storage.put_object(
            tenant_id=tenant_id,
            object_type="report",
            object_id=evaluation_id,
            filename=filename,
            content_bytes=blob,
            content_type="application/json",
        )
        active_hold = self._find_active_legal_hold(
            tenant_id=tenant_id,
            object_type="report",
            object_id=evaluation_id,
        )
        if active_hold is not None:
            active_hold["storage_uri"] = storage_uri
            self.object_storage.apply_legal_hold(storage_uri=storage_uri)
        item["report_uri"] = storage_uri
        return item

    @staticmethod
    def _compute_audit_hash(*, log: dict[str, Any], prev_hash: str) -> str:
        material = {key: value for key, value in log.items() if key not in {"audit_hash", "prev_hash"}}
        material["prev_hash"] = prev_hash
        blob = json.dumps(material, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _append_audit_log(self, *, log: dict[str, Any]) -> dict[str, Any]:
        entry = dict(log)
        if not entry.get("audit_id"):
            entry["audit_id"] = f"audit_{uuid.uuid4().hex[:12]}"
        if not entry.get("occurred_at"):
            entry["occurred_at"] = self._utcnow_iso()
        prev_hash = ""
        if self.audit_logs:
            prev_hash = str(self.audit_logs[-1].get("audit_hash") or "")
        entry["prev_hash"] = prev_hash
        entry["audit_hash"] = self._compute_audit_hash(log=entry, prev_hash=prev_hash)
        return self.audit_repository.append(log=entry)

    def _persist_dlq_item(self, *, item: dict[str, Any]) -> dict[str, Any]:
        return self.dlq_repository.upsert(item=item)

    def _persist_workflow_checkpoint(self, *, checkpoint: dict[str, Any]) -> dict[str, Any]:
        return self.workflow_repository.append(checkpoint=checkpoint)

    def verify_audit_integrity(self, *, tenant_id: str | None = None) -> dict[str, Any]:
        rows = self.audit_logs
        if tenant_id:
            rows = [x for x in rows if str(x.get("tenant_id") or "") == tenant_id]
        prev_hash = ""
        for idx, row in enumerate(rows):
            stored_prev = str(row.get("prev_hash") or "")
            if stored_prev != prev_hash:
                return {
                    "valid": False,
                    "checked_count": idx + 1,
                    "reason": "prev_hash_mismatch",
                    "audit_id": row.get("audit_id"),
                }
            expected = self._compute_audit_hash(log=row, prev_hash=stored_prev)
            actual = str(row.get("audit_hash") or "")
            if actual != expected:
                return {
                    "valid": False,
                    "checked_count": idx + 1,
                    "reason": "audit_hash_mismatch",
                    "audit_id": row.get("audit_id"),
                }
            prev_hash = actual
        return {
            "valid": True,
            "checked_count": len(rows),
            "last_hash": prev_hash,
        }


def create_store_from_env(environ: Mapping[str, str] | None = None) -> InMemoryStore:
    import app.store as _this_module

    env = os.environ if environ is None else environ
    backend = env.get("BEA_STORE_BACKEND", "memory").strip().lower()
    if true_stack_required(env) and backend != "postgres":
        raise RuntimeError("BEA_STORE_BACKEND must be postgres when BEA_REQUIRE_TRUESTACK=true")
    if backend == "sqlite":
        SqliteBackedStore = _this_module.SqliteBackedStore  # noqa: N806
        db_path = env.get("BEA_STORE_SQLITE_PATH", ".local/bea-store.sqlite3")
        return SqliteBackedStore(db_path)
    if backend == "postgres":
        PostgresBackedStore = _this_module.PostgresBackedStore  # noqa: N806
        dsn = env.get("POSTGRES_DSN", "").strip()
        if not dsn:
            raise ValueError("POSTGRES_DSN must be set when BEA_STORE_BACKEND=postgres")
        table_name = env.get("BEA_STORE_POSTGRES_TABLE", "bea_store_state")
        apply_rls = env.get("POSTGRES_APPLY_RLS", "false").strip().lower() in {"1", "true", "yes", "on"}
        return PostgresBackedStore(dsn=dsn, table_name=table_name, apply_rls=apply_rls)
    return InMemoryStore()


def _import_psycopg() -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg is required for BEA_STORE_BACKEND=postgres; install psycopg[binary]") from exc
    return psycopg


# Re-export backend classes for backward compatibility
def __getattr__(name: str) -> Any:
    if name == "SqliteBackedStore":
        from app.store_backends import SqliteBackedStore

        return SqliteBackedStore
    if name == "PostgresBackedStore":
        from app.store_backends import PostgresBackedStore

        return PostgresBackedStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


store = create_store_from_env()
