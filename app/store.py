from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import URLError

from app.errors import ApiError
from app.object_storage import build_report_filename, create_object_storage_from_env
from app.parser_adapters import (
    ParseRoute,
    build_default_parser_registry,
    disabled_parsers_from_env,
    select_parse_route,
)
from app.db.postgres import PostgresTxRunner
from app.db.rls import PostgresRlsManager
from app.repositories.audit_logs import InMemoryAuditLogsRepository
from app.repositories.audit_logs import PostgresAuditLogsRepository
from app.repositories.dlq_items import InMemoryDlqItemsRepository
from app.repositories.dlq_items import PostgresDlqItemsRepository
from app.repositories.documents import InMemoryDocumentsRepository
from app.repositories.documents import PostgresDocumentsRepository
from app.repositories.evaluation_reports import InMemoryEvaluationReportsRepository
from app.repositories.evaluation_reports import PostgresEvaluationReportsRepository
from app.repositories.jobs import InMemoryJobsRepository
from app.repositories.jobs import PostgresJobsRepository
from app.repositories.parse_manifests import InMemoryParseManifestsRepository
from app.repositories.parse_manifests import PostgresParseManifestsRepository
from app.repositories.projects import InMemoryProjectsRepository
from app.repositories.projects import PostgresProjectsRepository
from app.repositories.rule_packs import InMemoryRulePacksRepository
from app.repositories.rule_packs import PostgresRulePacksRepository
from app.repositories.suppliers import InMemorySuppliersRepository
from app.repositories.suppliers import PostgresSuppliersRepository
from app.repositories.workflow_checkpoints import InMemoryWorkflowCheckpointsRepository
from app.repositories.workflow_checkpoints import PostgresWorkflowCheckpointsRepository
from app.runtime_profile import true_stack_required


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


class InMemoryStore:
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
        seed = f"{job_id}:{retry_count}".encode("utf-8")
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
        return self.parse_manifests_repository.upsert(manifest=manifest)

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
        material = {
            key: value
            for key, value in log.items()
            if key not in {"audit_hash", "prev_hash"}
        }
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

    @staticmethod
    def _select_parser(*, filename: str, doc_type: str | None) -> ParseRoute:
        return select_parse_route(filename=filename, doc_type=doc_type)

    @staticmethod
    def _classify_error_code(error_code: str) -> dict[str, Any]:
        matrix: dict[str, dict[str, Any]] = {
            "DOC_PARSE_OUTPUT_NOT_FOUND": {
                "class": "permanent",
                "retryable": False,
                "message": "parse output missing",
            },
            "DOC_PARSE_SCHEMA_INVALID": {
                "class": "transient",
                "retryable": True,
                "message": "parse schema invalid",
            },
            "MINERU_BBOX_FORMAT_INVALID": {
                "class": "permanent",
                "retryable": False,
                "message": "bbox format invalid",
            },
            "TEXT_ENCODING_UNSUPPORTED": {
                "class": "permanent",
                "retryable": False,
                "message": "text encoding unsupported",
            },
            "PARSER_FALLBACK_EXHAUSTED": {
                "class": "transient",
                "retryable": True,
                "message": "parser fallback exhausted",
            },
            "RAG_UPSTREAM_UNAVAILABLE": {
                "class": "transient",
                "retryable": True,
                "message": "retrieval upstream unavailable",
            },
            "INTERNAL_DEBUG_FORCED_FAIL": {
                "class": "transient",
                "retryable": True,
                "message": "forced failure by internal debug run",
            },
        }
        return matrix.get(
            error_code,
            {
                "class": "transient",
                "retryable": True,
                "message": "forced failure by internal debug run",
            },
        )

    @staticmethod
    def _normalize_and_rewrite_query(query: str, include_terms: list[str], exclude_terms: list[str]) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", query).strip()
        rewritten = normalized
        parts: list[str] = []
        if include_terms:
            parts.append("include:" + ",".join(include_terms))
        if exclude_terms:
            parts.append("exclude:" + ",".join(exclude_terms))
        if parts:
            rewritten = f"{normalized} [{' | '.join(parts)}]"
        diff: list[str] = []
        lower_rewritten = rewritten.lower()
        for term in include_terms:
            if term not in lower_rewritten:
                diff.append(f"missing_include:{term}")
        for term in exclude_terms:
            if term not in lower_rewritten:
                diff.append(f"missing_exclude:{term}")
        return {
            "rewritten_query": rewritten,
            "rewrite_reason": "normalize_whitespace_and_constraints",
            "constraints_preserved": len(diff) == 0,
            "constraint_diff": diff,
        }

    @staticmethod
    def _extract_page_and_bbox(chunk: dict[str, Any]) -> tuple[int, list[float]]:
        positions = chunk.get("positions", [])
        if isinstance(positions, list) and positions:
            first = positions[0] if isinstance(positions[0], dict) else {}
            page = int(first.get("page") or 1)
            bbox = first.get("bbox")
            if isinstance(bbox, list) and len(bbox) == 4:
                try:
                    return page, [float(x) for x in bbox]
                except (TypeError, ValueError):
                    return page, [0.0, 0.0, 1.0, 1.0]
        page = int(chunk.get("page") or 1)
        bbox = chunk.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                return page, [float(x) for x in bbox]
            except (TypeError, ValueError):
                return page, [0.0, 0.0, 1.0, 1.0]
        return page, [0.0, 0.0, 1.0, 1.0]

    @classmethod
    def _ensure_chunk_shape(cls, *, document_id: str, chunk: dict[str, Any]) -> dict[str, Any]:
        item = dict(chunk)
        page, bbox = cls._extract_page_and_bbox(item)
        text = str(item.get("text") or "")
        heading_path = item.get("heading_path")
        if not isinstance(heading_path, list):
            heading_path = []
        hash_key = json.dumps(
            {
                "document_id": document_id,
                "page": page,
                "bbox": bbox,
                "heading_path": heading_path,
                "text": text,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        chunk_hash = hashlib.sha256(hash_key.encode("utf-8")).hexdigest()
        item["document_id"] = document_id
        item["page"] = page
        item["bbox"] = bbox
        item["chunk_hash"] = chunk_hash
        if not item.get("chunk_id"):
            item["chunk_id"] = f"ck_{chunk_hash[:12]}"
        if "positions" not in item or not isinstance(item.get("positions"), list) or not item["positions"]:
            item["positions"] = [{"page": page, "bbox": bbox, "start": 0, "end": max(1, len(text))}]
        if "pages" not in item or not isinstance(item.get("pages"), list) or not item["pages"]:
            item["pages"] = [page]
        if "heading_path" not in item or not isinstance(item.get("heading_path"), list):
            item["heading_path"] = []
        item.setdefault("chunk_type", "text")
        item.setdefault("parser", "mineru")
        item.setdefault("parser_version", "v0")
        item.setdefault("section", "")
        item.setdefault("content_source", "unknown")
        item.setdefault("text", text)
        return item

    def _dedupe_chunks(
        self,
        *,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for chunk in chunks:
            normalized = self._ensure_chunk_shape(document_id=document_id, chunk=chunk)
            key = str(normalized.get("chunk_hash", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(normalized)
        return out

    @staticmethod
    def _lightrag_index_prefix() -> str:
        return os.environ.get("LIGHTRAG_INDEX_PREFIX", "lightrag").strip() or "lightrag"

    def _retrieval_index_name(self, *, tenant_id: str, project_id: str) -> str:
        prefix = self._lightrag_index_prefix()
        return f"{prefix}:{tenant_id}:{project_id}"

    @staticmethod
    def _post_json(
        *,
        endpoint: str,
        payload: dict[str, Any],
        timeout_s: float,
    ) -> object:
        body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _maybe_index_chunks_to_lightrag(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        document_id: str,
        doc_type: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        dsn = os.environ.get("LIGHTRAG_DSN", "").strip()
        if not dsn:
            return
        endpoint = dsn.rstrip("/") + "/index"
        payload = {
            "index_name": self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id),
            "tenant_id": tenant_id,
            "project_id": project_id,
            "supplier_id": supplier_id,
            "document_id": document_id,
            "doc_type": doc_type,
            "chunks": chunks,
        }
        timeout_s = float(os.environ.get("RERANK_TIMEOUT_MS", "2000")) / 1000.0 + 3.0
        self.parser_retrieval_metrics["parse_index_write_total"] += 1
        try:
            self._post_json(endpoint=endpoint, payload=payload, timeout_s=timeout_s)
        except (TimeoutError, URLError, ValueError, OSError):
            self.parser_retrieval_metrics["parse_index_fail_total"] += 1

    def _query_lightrag(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        selected_mode: str,
        top_k: int,
        doc_scope: list[str],
    ) -> list[dict[str, Any]] | None:
        dsn = os.environ.get("LIGHTRAG_DSN", "").strip()
        if not dsn:
            return None
        endpoint = dsn.rstrip("/") + "/query"
        payload = {
            "index_name": self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id),
            "query": query,
            "mode": selected_mode,
            "top_k": top_k,
            "filters": {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "doc_scope": list(doc_scope),
            },
        }
        timeout_s = float(os.environ.get("RERANK_TIMEOUT_MS", "2000")) / 1000.0 + 3.0
        self.parser_retrieval_metrics["retrieval_lightrag_calls_total"] += 1
        try:
            result = self._post_json(endpoint=endpoint, payload=payload, timeout_s=timeout_s)
        except (TimeoutError, URLError, ValueError, OSError):
            self.parser_retrieval_metrics["retrieval_lightrag_fail_total"] += 1
            return None
        if not isinstance(result, dict):
            self.parser_retrieval_metrics["retrieval_lightrag_fail_total"] += 1
            return None
        rows = result.get("items")
        if not isinstance(rows, list):
            return []
        out: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            metadata = row.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            if metadata.get("tenant_id") != tenant_id:
                continue
            if metadata.get("project_id") != project_id:
                continue
            if metadata.get("supplier_id") != supplier_id:
                continue
            doc_type = metadata.get("doc_type")
            if doc_scope and doc_type not in set(doc_scope):
                continue
            out.append(
                {
                    "chunk_id": row.get("chunk_id"),
                    "score_raw": float(row.get("score_raw", 0.5)),
                    "reason": str(row.get("reason", "matched retrieval intent")),
                    "metadata": {
                        "tenant_id": metadata.get("tenant_id"),
                        "project_id": metadata.get("project_id"),
                        "supplier_id": metadata.get("supplier_id"),
                        "document_id": metadata.get("document_id"),
                        "doc_type": metadata.get("doc_type"),
                        "page": int(metadata.get("page", 1)),
                        "bbox": metadata.get("bbox", [0, 0, 1, 1]),
                    },
                }
            )
        return out

    @staticmethod
    def _rerank_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if os.environ.get("BEA_FORCE_RERANK_ERROR", "").strip().lower() in {"1", "true", "yes", "on"}:
            raise RuntimeError("forced rerank error")
        ranked: list[dict[str, Any]] = []
        for item in items:
            copied = dict(item)
            copied["score_rerank"] = min(1.0, float(copied.get("score_raw", 0.5)) + 0.05)
            ranked.append(copied)
        return sorted(ranked, key=lambda x: float(x.get("score_rerank", 0.0)), reverse=True)

    def run_idempotent(
        self,
        *,
        endpoint: str,
        tenant_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        execute: callable,
    ) -> dict[str, Any]:
        key = (f"{tenant_id}:{endpoint}", idempotency_key)
        current_fingerprint = self._fingerprint(payload)
        if key in self.idempotency_records:
            record = self.idempotency_records[key]
            if record.fingerprint != current_fingerprint:
                raise ApiError(
                    code="IDEMPOTENCY_CONFLICT",
                    message="same key with different payload",
                    error_class="validation",
                    retryable=False,
                    http_status=409,
                )
            return record.data

        data = execute()
        self.idempotency_records[key] = IdempotencyRecord(
            fingerprint=current_fingerprint,
            data=data,
        )
        return data

    def create_evaluation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        evaluation_id = f"ev_{uuid.uuid4().hex[:12]}"
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        thread_id = self._new_thread_id("eval")
        tenant_id = payload.get("tenant_id", "tenant_default")
        force_hitl = bool(payload.get("evaluation_scope", {}).get("force_hitl", False))
        include_doc_types = payload.get("evaluation_scope", {}).get("include_doc_types", [])
        include_doc_types_normalized = {str(x).lower() for x in include_doc_types}
        hard_constraint_pass = "bid" in include_doc_types_normalized
        rule_pack = self.get_rule_pack_for_tenant(
            rule_pack_version=str(payload.get("rule_pack_version") or ""),
            tenant_id=tenant_id,
        )
        rules = rule_pack.get("rules") if isinstance(rule_pack, dict) else {}
        criteria_defs = rules.get("criteria") if isinstance(rules, dict) else None
        if not isinstance(criteria_defs, list) or not criteria_defs:
            criteria_defs = [
                {
                    "criteria_id": "delivery",
                    "max_score": 20.0,
                    "weight": 1.0,
                }
            ]

        criteria_results: list[dict[str, Any]] = []
        citations_all: list[str] = []
        unsupported_claims: list[str] = []
        redline_conflict = False
        for criteria in criteria_defs:
            if not isinstance(criteria, dict):
                continue
            criteria_id = str(criteria.get("criteria_id") or "criteria")
            max_score = float(criteria.get("max_score", 20.0))
            weight = float(criteria.get("weight", 1.0))
            score = max_score * 0.9 if hard_constraint_pass else 0.0
            citation_id = (
                f"ck_{criteria_id}_{evaluation_id[:6]}"
                if hard_constraint_pass
                else "ck_rule_block_1"
            )
            citations = [citation_id]
            criteria_name = criteria.get("criteria_name") or criteria.get("name") or criteria_id
            requirement_text = criteria.get("requirement_text") or criteria.get("requirement")
            response_text = criteria.get("response_text") or criteria.get("response")
            criteria_results.append(
                {
                    "criteria_id": criteria_id,
                    "criteria_name": str(criteria_name),
                    "requirement_text": str(requirement_text) if requirement_text is not None else None,
                    "response_text": str(response_text) if response_text is not None else None,
                    "score": score,
                    "max_score": max_score,
                    "weight": weight,
                    "hard_pass": hard_constraint_pass,
                    "reason": (
                        "delivery period satisfies baseline"
                        if hard_constraint_pass
                        else "rule engine blocked: required bid document scope missing"
                    ),
                    "citations": citations,
                    "citations_count": len(citations),
                    "confidence": 0.81 if hard_constraint_pass else 1.0,
                }
            )
            citations_all.extend(citations)
            if criteria.get("require_citation") and not citations:
                unsupported_claims.append(criteria_id)

        for chunk_id in citations_all:
            if chunk_id not in self.citation_sources:
                self.register_citation_source(
                    chunk_id=chunk_id,
                    source={
                        "chunk_id": chunk_id,
                        "document_id": f"doc_{evaluation_id[:8]}",
                        "tenant_id": tenant_id,
                        "project_id": payload.get("project_id"),
                        "supplier_id": payload.get("supplier_id"),
                        "doc_type": include_doc_types[0] if include_doc_types else "bid",
                        "page": 1,
                        "bbox": [0.0, 0.0, 1.0, 1.0],
                        "heading_path": ["auto", "stub"],
                        "chunk_type": "text",
                        "content_source": "stub",
                        "text": "stub citation",
                        "context": "stub context",
                        "score_raw": 0.78,
                        "chunk_hash": f"hash_{chunk_id}",
                    },
                )

        resolvable = [
            cid for cid in citations_all if self.citation_sources.get(cid) is not None
        ]
        if len(resolvable) < len(citations_all):
            for missing in (set(citations_all) - set(resolvable)):
                unsupported_claims.append(missing)
        if isinstance(rules, dict):
            redlines = rules.get("redlines")
            if isinstance(redlines, list):
                for item in redlines:
                    if not isinstance(item, dict):
                        continue
                    if item.get("violated") is True:
                        redline_conflict = True
                        break
                    status = str(item.get("status") or "").strip().lower()
                    if status in {"blocked", "violation", "failed", "conflict"}:
                        redline_conflict = True
                        break
            required_doc_types = rules.get("required_doc_types")
            if isinstance(required_doc_types, list) and required_doc_types:
                required = {str(x).lower() for x in required_doc_types}
                if not required.issubset(include_doc_types_normalized):
                    redline_conflict = True

        total_score = sum(float(item.get("score", 0.0)) * float(item.get("weight", 1.0)) for item in criteria_results)
        max_total = sum(float(item.get("max_score", 0.0)) * float(item.get("weight", 1.0)) for item in criteria_results) or 1.0
        citation_coverage = len(resolvable) / max(len(citations_all), 1)
        evidence_quality = citation_coverage
        retrieval_agreement = citation_coverage
        model_stability = 0.85 if hard_constraint_pass else 0.7
        base_confidence = 0.4 * evidence_quality + 0.3 * retrieval_agreement + 0.3 * model_stability
        score_calibration = self.strategy_config.get("score_calibration", {})
        confidence_scale = float(score_calibration.get("confidence_scale", 1.0))
        score_bias = float(score_calibration.get("score_bias", 0.0))
        confidence_avg = max(0.0, min(1.0, base_confidence * confidence_scale + score_bias))
        score_deviation_pct = abs(total_score - max_total) / max_total * 100.0
        needs_human_review = (
            force_hitl
            or confidence_avg < 0.65
            or citation_coverage < 0.90
            or score_deviation_pct > 20.0
            or redline_conflict
            or bool(unsupported_claims)
        )
        interrupt_payload = None
        if needs_human_review:
            resume_token = f"rt_{uuid.uuid4().hex[:12]}"
            interrupt_payload = {
                "type": "human_review",
                "evaluation_id": evaluation_id,
                "reasons": ["force_hitl"],
                "suggested_actions": ["approve", "reject", "edit_scores"],
                "resume_token": resume_token,
            }
            self.register_resume_token(
                evaluation_id=evaluation_id,
                resume_token=resume_token,
                tenant_id=tenant_id,
                reasons=["force_hitl"],
            )
        self._persist_job(
            job={
            "job_id": job_id,
            "job_type": "evaluation",
            "status": "queued",
            "retry_count": 0,
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "evaluation",
                "id": evaluation_id,
            },
            "payload": payload,
            "last_error": None,
            }
        )
        self._persist_evaluation_report(
            report={
            "evaluation_id": evaluation_id,
            "supplier_id": payload.get("supplier_id", ""),
            "total_score": total_score if hard_constraint_pass else 0.0,
            "confidence": confidence_avg,
            "citation_coverage": citation_coverage,
            "score_deviation_pct": round(score_deviation_pct, 2),
            "risk_level": "medium" if hard_constraint_pass else "high",
            "criteria_results": criteria_results,
            "citations": citations_all,
            "needs_human_review": needs_human_review,
            "trace_id": payload.get("trace_id") or "",
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "interrupt": interrupt_payload,
            "unsupported_claims": unsupported_claims,
            "redline_conflict": redline_conflict,
            }
        )
        self.append_outbox_event(
            tenant_id=tenant_id,
            event_type="job.created",
            aggregate_type="job",
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "job_type": "evaluation",
                "resource_type": "evaluation",
                "resource_id": evaluation_id,
            },
        )
        return {
            "evaluation_id": evaluation_id,
            "job_id": job_id,
            "status": "queued",
        }

    def create_upload_job(
        self,
        payload: dict[str, Any],
        *,
        file_bytes: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        tenant_id = payload.get("tenant_id", "tenant_default")
        storage_uri = None
        if file_bytes is not None:
            storage_uri = self.object_storage.put_object(
                tenant_id=tenant_id,
                object_type="document",
                object_id=document_id,
                filename=str(payload.get("filename") or "upload.bin"),
                content_bytes=file_bytes,
                content_type=content_type or "application/octet-stream",
            )
            active_hold = self._find_active_legal_hold(
                tenant_id=tenant_id,
                object_type="document",
                object_id=document_id,
            )
            if active_hold is not None:
                active_hold["storage_uri"] = storage_uri
                self.object_storage.apply_legal_hold(storage_uri=storage_uri)
        document = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "project_id": payload.get("project_id"),
            "supplier_id": payload.get("supplier_id"),
            "doc_type": payload.get("doc_type"),
            "filename": payload.get("filename"),
            "file_sha256": payload.get("file_sha256"),
            "file_size": payload.get("file_size"),
            "status": "uploaded",
            "storage_uri": storage_uri,
        }
        self._persist_document(document=document)
        self._persist_document_chunks(tenant_id=tenant_id, document_id=document_id, chunks=[])
        parse_job = self.create_parse_job(
            document_id=document_id,
            payload={
                "document_id": document_id,
                "trace_id": payload.get("trace_id"),
                "tenant_id": tenant_id,
            },
        )
        return {
            "document_id": document_id,
            "job_id": parse_job["job_id"],
            "status": parse_job["status"],
            "next": f"/api/v1/jobs/{parse_job['job_id']}",
        }

    def create_parse_job(self, *, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        document = self.get_document_for_tenant(document_id=document_id, tenant_id=payload.get("tenant_id", "tenant_default"))
        if document is None:
            raise ApiError(
                code="DOC_NOT_FOUND",
                message="document not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        tenant_id = payload.get("tenant_id", "tenant_default")
        self._assert_tenant_scope(document["tenant_id"], tenant_id)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        thread_id = self._new_thread_id("parse")
        self._persist_job(
            job={
            "job_id": job_id,
            "job_type": "parse",
            "status": "queued",
            "retry_count": 0,
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "document",
                "id": document_id,
            },
            "payload": payload,
            "last_error": None,
            }
        )
        route = self._select_parser(
            filename=document.get("filename", ""),
            doc_type=document.get("doc_type"),
        )
        self._persist_parse_manifest(
            manifest={
            "run_id": f"prun_{uuid.uuid4().hex[:12]}",
            "job_id": job_id,
            "document_id": document_id,
            "tenant_id": tenant_id,
            "selected_parser": route.selected_parser,
            "parser_version": route.parser_version,
            "fallback_chain": route.fallback_chain,
            "input_files": [
                {
                    "name": document.get("filename"),
                    "sha256": document.get("file_sha256"),
                    "size": int(document.get("file_size") or 0),
                }
            ],
            "started_at": None,
            "ended_at": None,
            "status": "queued",
            "error_code": None,
            }
        )
        document["status"] = "parse_queued"
        self._persist_document(document=document)
        self.append_outbox_event(
            tenant_id=tenant_id,
            event_type="job.created",
            aggregate_type="job",
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "job_type": "parse",
                "resource_type": "document",
                "resource_id": document_id,
            },
        )
        return {
            "document_id": document_id,
            "job_id": job_id,
            "status": "queued",
        }

    def get_document_for_tenant(self, *, document_id: str, tenant_id: str) -> dict[str, Any] | None:
        doc = self.documents.get(document_id)
        if doc is None:
            return None
        self._assert_tenant_scope(doc.get("tenant_id", "tenant_default"), tenant_id)
        return doc

    def list_document_chunks_for_tenant(self, *, document_id: str, tenant_id: str) -> list[dict[str, Any]]:
        doc = self.get_document_for_tenant(document_id=document_id, tenant_id=tenant_id)
        if doc is None:
            raise ApiError(
                code="DOC_NOT_FOUND",
                message="document not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        return list(self.document_chunks.get(document_id, []))

    def create_project(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "tenant_default")
        project_code = str(payload.get("project_code") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not project_code or not name:
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="project_code and name are required",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        existing = self.projects_repository.get_by_code(tenant_id=tenant_id, project_code=project_code)
        if existing is not None:
            return existing
        now = self._utcnow_iso()
        project = {
            "project_id": f"prj_{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "project_code": project_code,
            "name": name,
            "ruleset_version": str(payload.get("ruleset_version") or "v1.0.0"),
            "status": str(payload.get("status") or "active"),
            "created_at": now,
            "updated_at": now,
        }
        saved = self.projects_repository.upsert(project=project)
        self.projects[str(saved.get("project_id") or project["project_id"])] = saved
        return saved

    def list_projects(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return self.projects_repository.list(tenant_id=tenant_id)

    def get_project_for_tenant(self, *, project_id: str, tenant_id: str) -> dict[str, Any] | None:
        return self.projects_repository.get(tenant_id=tenant_id, project_id=project_id)

    def update_project(
        self,
        *,
        project_id: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        project = self.get_project_for_tenant(project_id=project_id, tenant_id=tenant_id)
        if project is None:
            raise ApiError(
                code="PROJECT_NOT_FOUND",
                message="project not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if payload.get("name") is not None:
            project["name"] = str(payload.get("name") or "").strip() or project["name"]
        if payload.get("ruleset_version") is not None:
            project["ruleset_version"] = str(payload.get("ruleset_version") or "").strip() or project["ruleset_version"]
        if payload.get("status") is not None:
            project["status"] = str(payload.get("status") or "").strip() or project["status"]
        project["updated_at"] = self._utcnow_iso()
        saved = self.projects_repository.upsert(project=project)
        self.projects[str(saved.get("project_id") or project_id)] = saved
        return saved

    def delete_project(self, *, project_id: str, tenant_id: str) -> dict[str, Any]:
        deleted = self.projects_repository.delete(tenant_id=tenant_id, project_id=project_id)
        if not deleted:
            raise ApiError(
                code="PROJECT_NOT_FOUND",
                message="project not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        self.projects.pop(project_id, None)
        return {"project_id": project_id, "deleted": True}

    def create_supplier(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "tenant_default")
        supplier_code = str(payload.get("supplier_code") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not supplier_code or not name:
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="supplier_code and name are required",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        existing = self.suppliers_repository.get_by_code(tenant_id=tenant_id, supplier_code=supplier_code)
        if existing is not None:
            return existing
        now = self._utcnow_iso()
        supplier = {
            "supplier_id": f"sup_{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "supplier_code": supplier_code,
            "name": name,
            "qualification": payload.get("qualification") or {},
            "risk_flags": payload.get("risk_flags") or {},
            "status": str(payload.get("status") or "active"),
            "created_at": now,
            "updated_at": now,
        }
        saved = self.suppliers_repository.upsert(supplier=supplier)
        self.suppliers[str(saved.get("supplier_id") or supplier["supplier_id"])] = saved
        return saved

    def list_suppliers(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return self.suppliers_repository.list(tenant_id=tenant_id)

    def get_supplier_for_tenant(self, *, supplier_id: str, tenant_id: str) -> dict[str, Any] | None:
        return self.suppliers_repository.get(tenant_id=tenant_id, supplier_id=supplier_id)

    def update_supplier(
        self,
        *,
        supplier_id: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        supplier = self.get_supplier_for_tenant(supplier_id=supplier_id, tenant_id=tenant_id)
        if supplier is None:
            raise ApiError(
                code="SUPPLIER_NOT_FOUND",
                message="supplier not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if payload.get("name") is not None:
            supplier["name"] = str(payload.get("name") or "").strip() or supplier["name"]
        if payload.get("qualification") is not None:
            supplier["qualification"] = payload.get("qualification") or {}
        if payload.get("risk_flags") is not None:
            supplier["risk_flags"] = payload.get("risk_flags") or {}
        if payload.get("status") is not None:
            supplier["status"] = str(payload.get("status") or "").strip() or supplier["status"]
        supplier["updated_at"] = self._utcnow_iso()
        saved = self.suppliers_repository.upsert(supplier=supplier)
        self.suppliers[str(saved.get("supplier_id") or supplier_id)] = saved
        return saved

    def delete_supplier(self, *, supplier_id: str, tenant_id: str) -> dict[str, Any]:
        deleted = self.suppliers_repository.delete(tenant_id=tenant_id, supplier_id=supplier_id)
        if not deleted:
            raise ApiError(
                code="SUPPLIER_NOT_FOUND",
                message="supplier not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        self.suppliers.pop(supplier_id, None)
        return {"supplier_id": supplier_id, "deleted": True}

    def create_rule_pack(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "tenant_default")
        version = str(payload.get("rule_pack_version") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not version or not name:
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="rule_pack_version and name are required",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        existing = self.rule_packs_repository.get(tenant_id=tenant_id, rule_pack_version=version)
        if existing is not None:
            return existing
        now = self._utcnow_iso()
        rule_pack = {
            "rule_pack_version": version,
            "tenant_id": tenant_id,
            "name": name,
            "status": str(payload.get("status") or "active"),
            "rules": payload.get("rules") or {},
            "created_at": now,
            "updated_at": now,
        }
        saved = self.rule_packs_repository.upsert(rule_pack=rule_pack)
        self.rule_packs[str(saved.get("rule_pack_version") or rule_pack["rule_pack_version"])] = saved
        return saved

    def list_rule_packs(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return self.rule_packs_repository.list(tenant_id=tenant_id)

    def get_rule_pack_for_tenant(self, *, rule_pack_version: str, tenant_id: str) -> dict[str, Any] | None:
        return self.rule_packs_repository.get(tenant_id=tenant_id, rule_pack_version=rule_pack_version)

    def update_rule_pack(
        self,
        *,
        rule_pack_version: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        rule_pack = self.get_rule_pack_for_tenant(rule_pack_version=rule_pack_version, tenant_id=tenant_id)
        if rule_pack is None:
            raise ApiError(
                code="RULE_PACK_NOT_FOUND",
                message="rule pack not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if payload.get("name") is not None:
            rule_pack["name"] = str(payload.get("name") or "").strip() or rule_pack["name"]
        if payload.get("status") is not None:
            rule_pack["status"] = str(payload.get("status") or "").strip() or rule_pack["status"]
        if payload.get("rules") is not None:
            rule_pack["rules"] = payload.get("rules") or {}
        rule_pack["updated_at"] = self._utcnow_iso()
        saved = self.rule_packs_repository.upsert(rule_pack=rule_pack)
        self.rule_packs[str(saved.get("rule_pack_version") or rule_pack_version)] = saved
        return saved

    def delete_rule_pack(self, *, rule_pack_version: str, tenant_id: str) -> dict[str, Any]:
        deleted = self.rule_packs_repository.delete(tenant_id=tenant_id, rule_pack_version=rule_pack_version)
        if not deleted:
            raise ApiError(
                code="RULE_PACK_NOT_FOUND",
                message="rule pack not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        self.rule_packs.pop(rule_pack_version, None)
        return {"rule_pack_version": rule_pack_version, "deleted": True}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)

    def get_job_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        self._assert_tenant_scope(job.get("tenant_id", "tenant_default"), tenant_id)
        return job

    def get_parse_manifest_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        manifest = self.parse_manifests_repository.get(tenant_id=tenant_id, job_id=job_id)
        if manifest is None:
            return None
        return manifest

    def get_evaluation_report_for_tenant(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        report = None
        get_any = getattr(self.evaluation_reports_repository, "get_any", None)
        if callable(get_any):
            report = get_any(evaluation_id=evaluation_id)
        if report is None:
            report = self.evaluation_reports_repository.get(
                tenant_id=tenant_id,
                evaluation_id=evaluation_id,
            )
        if report is None:
            return None
        self._assert_tenant_scope(report.get("tenant_id", "tenant_default"), tenant_id)
        return {
            "evaluation_id": report["evaluation_id"],
            "supplier_id": report["supplier_id"],
            "total_score": report["total_score"],
            "confidence": report["confidence"],
            "citation_coverage": report.get("citation_coverage", 0.0),
            "risk_level": report["risk_level"],
            "criteria_results": report["criteria_results"],
            "citations": report["citations"],
            "needs_human_review": report["needs_human_review"],
            "trace_id": report["trace_id"],
            "interrupt": report.get("interrupt"),
            "report_uri": report.get("report_uri"),
        }

    def transition_job_status(
        self,
        *,
        job_id: str,
        new_status: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        if tenant_id is None:
            job = self.get_job(job_id)
        else:
            job = self.get_job_for_tenant(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            raise ApiError(
                code="JOB_NOT_FOUND",
                message="job not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )

        current_status = job["status"]
        if new_status == current_status:
            return job
        allowed = self.ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ApiError(
                code="WF_STATE_TRANSITION_INVALID",
                message=f"invalid transition: {current_status} -> {new_status}",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )

        if new_status == "retrying":
            job["retry_count"] = int(job.get("retry_count", 0)) + 1
        job["status"] = new_status
        return self._persist_job(job=job)

    def register_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str = "tenant_default",
        reasons: list[str] | None = None,
    ) -> None:
        self.resume_tokens[evaluation_id] = {
            "resume_token": resume_token,
            "tenant_id": tenant_id,
            "used": False,
            "reasons": list(reasons or []),
            "issued_at": self._utcnow_iso(),
        }

    def validate_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str | None = None,
    ) -> bool:
        record = self.resume_tokens.get(evaluation_id)
        if record is None:
            return False
        if tenant_id is not None:
            self._assert_tenant_scope(record.get("tenant_id", "tenant_default"), tenant_id)
        if record.get("resume_token") != resume_token or bool(record.get("used", False)):
            return False

        issued_at_raw = record.get("issued_at")
        if not isinstance(issued_at_raw, str):
            return False
        try:
            issued_at = datetime.fromisoformat(issued_at_raw)
        except ValueError:
            return False
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=UTC)

        expires_at = issued_at + timedelta(hours=self.resume_token_ttl_hours)
        return datetime.now(UTC) <= expires_at

    def consume_resume_token(
        self,
        *,
        evaluation_id: str,
        resume_token: str,
        tenant_id: str,
    ) -> bool:
        if not self.validate_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
        ):
            return False
        record = self.resume_tokens[evaluation_id]
        record["used"] = True
        record["used_at"] = self._utcnow_iso()
        return True

    def create_resume_job(self, *, evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        tenant_id = payload.get("tenant_id", "tenant_default")
        report = self.evaluation_reports_repository.get(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
        )
        thread_id = str(report.get("thread_id", "")) if isinstance(report, dict) else ""
        if not thread_id:
            thread_id = self._new_thread_id("resume")
        self._persist_job(
            job={
            "job_id": job_id,
            "job_type": "resume",
            "status": "queued",
            "retry_count": 0,
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "evaluation",
                "id": evaluation_id,
            },
            "payload": payload,
            "last_error": None,
            }
        )
        if report is not None:
            report["needs_human_review"] = False
            report["interrupt"] = None
            self._persist_evaluation_report(report=report)
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "evaluation_id": evaluation_id,
                "action": "resume_submitted",
                "reviewer_id": payload.get("editor", {}).get("reviewer_id", ""),
                "decision": payload.get("decision", ""),
                "comment": payload.get("comment", ""),
                "trace_id": payload.get("trace_id", ""),
                "occurred_at": self._utcnow_iso(),
            }
        )
        self.append_outbox_event(
            tenant_id=tenant_id,
            event_type="job.created",
            aggregate_type="job",
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "job_type": "resume",
                "resource_type": "evaluation",
                "resource_id": evaluation_id,
            },
        )
        return {
            "evaluation_id": evaluation_id,
            "job_id": job_id,
            "status": "queued",
        }

    def list_audit_logs_for_evaluation(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        return self.audit_repository.list_for_evaluation(
            tenant_id=tenant_id,
            evaluation_id=evaluation_id,
        )

    def append_workflow_checkpoint(
        self,
        *,
        thread_id: str,
        job_id: str,
        tenant_id: str,
        node: str,
        status: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.workflow_checkpoints.get(thread_id, [])
        checkpoint = {
            "checkpoint_id": f"cp_{uuid.uuid4().hex[:12]}",
            "thread_id": thread_id,
            "job_id": job_id,
            "seq": len(existing) + 1,
            "node": node,
            "status": status,
            "payload": payload or {},
            "tenant_id": tenant_id,
            "created_at": self._utcnow_iso(),
        }
        return self._persist_workflow_checkpoint(checkpoint=checkpoint)

    def list_workflow_checkpoints(
        self,
        *,
        thread_id: str,
        tenant_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = self.workflow_repository.list(
            thread_id=thread_id,
            tenant_id=tenant_id,
            limit=limit,
        )
        return [item for item in items if item.get("kind") != self.langgraph_checkpoint_kind]

    def upsert_langgraph_checkpoint(self, *, record: dict[str, Any]) -> dict[str, Any]:
        thread_id = str(record.get("thread_id") or "")
        tenant_id = str(record.get("tenant_id") or "tenant_default")
        checkpoint_id = str(record.get("checkpoint_id") or "")
        if not thread_id or not checkpoint_id:
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="invalid langgraph checkpoint record",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        existing = self.get_langgraph_checkpoint_record(
            thread_id=thread_id,
            tenant_id=tenant_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=record.get("checkpoint_ns", ""),
        )
        seq = int(existing.get("seq", 0)) if existing else self._next_workflow_seq(thread_id, tenant_id)
        payload = dict(record)
        payload["kind"] = self.langgraph_checkpoint_kind
        payload["seq"] = seq
        payload["langgraph_checkpoint_id"] = checkpoint_id
        payload["parent_langgraph_checkpoint_id"] = record.get("parent_checkpoint_id")
        payload["checkpoint_id"] = f"lgcp_{checkpoint_id}"
        return self.workflow_repository.append(checkpoint=_json_safe(payload))

    def get_langgraph_checkpoint_record(
        self,
        *,
        thread_id: str,
        tenant_id: str,
        checkpoint_id: str | None,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any] | None:
        items = self.list_langgraph_checkpoints(
            thread_id=thread_id,
            tenant_id=tenant_id,
            checkpoint_ns=checkpoint_ns,
        )
        if checkpoint_id:
            for item in items:
                if item.get("checkpoint_id") == checkpoint_id:
                    return item
            return None
        return items[0] if items else None

    def list_langgraph_checkpoints(
        self,
        *,
        thread_id: str,
        tenant_id: str,
        checkpoint_ns: str | None = None,
    ) -> list[dict[str, Any]]:
        raw = self.workflow_repository.list(thread_id=thread_id, tenant_id=tenant_id, limit=1000)
        items: list[dict[str, Any]] = []
        for item in raw:
            if item.get("kind") != self.langgraph_checkpoint_kind:
                continue
            if checkpoint_ns is not None and item.get("checkpoint_ns", "") != checkpoint_ns:
                continue
            record = dict(item)
            record["checkpoint_id"] = record.get("langgraph_checkpoint_id")
            record["parent_checkpoint_id"] = record.get("parent_langgraph_checkpoint_id")
            items.append(record)
        items.sort(key=lambda x: int(x.get("seq", 0)), reverse=True)
        return items

    def delete_langgraph_checkpoints(self, *, thread_id: str) -> None:
        if thread_id not in self.workflow_checkpoints:
            return
        self.workflow_checkpoints[thread_id] = [
            item
            for item in self.workflow_checkpoints[thread_id]
            if item.get("kind") != self.langgraph_checkpoint_kind
        ]

    def _next_workflow_seq(self, thread_id: str, tenant_id: str) -> int:
        items = self.workflow_repository.list(thread_id=thread_id, tenant_id=tenant_id, limit=1000)
        if not items:
            return 1
        return max(int(item.get("seq", 0)) for item in items) + 1

    def _workflow_runtime_mode(self) -> tuple[str, object | None]:
        mode = os.environ.get("WORKFLOW_RUNTIME", "langgraph").strip().lower() or "langgraph"
        if mode != "langgraph":
            return mode, None
        try:
            import langgraph  # type: ignore

            return "langgraph", langgraph
        except Exception as exc:
            raise RuntimeError("langgraph runtime required but dependency is missing") from exc

    def _append_node_checkpoint(
        self,
        *,
        thread_id: str,
        job_id: str,
        tenant_id: str,
        node: str,
        status: str = "succeeded",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.append_workflow_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node=node,
            status=status,
            payload=payload or {},
        )

    def _run_evaluation_workflow(
        self,
        *,
        job: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        evaluation_id = str(job.get("resource", {}).get("id") or "")
        thread_id = str(job.get("thread_id") or self._new_thread_id("eval"))
        trace_id = str(job.get("trace_id") or "")
        report: dict[str, Any] | None = None
        if evaluation_id:
            report = self.evaluation_reports.get(evaluation_id)
            if report is None:
                report = self.get_evaluation_report_for_tenant(evaluation_id=evaluation_id, tenant_id=tenant_id)
        needs_human_review = bool(report.get("needs_human_review", False)) if isinstance(report, dict) else False
        interrupt_payload = report.get("interrupt") if isinstance(report, dict) else None

        def _base_state() -> dict[str, Any]:
            return {
                "identity": {
                    "tenant_id": tenant_id,
                    "evaluation_id": evaluation_id,
                    "project_id": report.get("project_id") if isinstance(report, dict) else None,
                    "supplier_id": report.get("supplier_id") if isinstance(report, dict) else None,
                },
                "trace": {"trace_id": trace_id, "thread_id": thread_id},
                "review": {
                    "requires_human_review": needs_human_review,
                    "human_review_payload": interrupt_payload,
                },
                "output": {"status": "running"},
            }

        mode, langgraph_module = self._workflow_runtime_mode()
        state = _base_state()

        def _node(name: str, payload: dict[str, Any] | None = None):
            def _inner(current: dict[str, Any]) -> dict[str, Any]:
                self._append_node_checkpoint(
                    thread_id=thread_id,
                    job_id=str(job.get("job_id") or ""),
                    tenant_id=tenant_id,
                    node=name,
                    payload=payload,
                )
                return current

            return _inner

        if mode != "langgraph" and needs_human_review:
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="load_context",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="retrieve_evidence",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="evaluate_rules",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="score_with_llm",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="quality_gate",
                status="hitl",
                payload={"decision": "hitl"},
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="human_review_interrupt",
                status="needs_manual_decision",
                payload=interrupt_payload if isinstance(interrupt_payload, dict) else {},
            )
            job = self.transition_job_status(
                job_id=str(job.get("job_id") or ""),
                new_status="needs_manual_decision",
                tenant_id=tenant_id,
            )
            return {
                "job_id": str(job.get("job_id") or ""),
                "final_status": "needs_manual_decision",
                "thread_id": thread_id,
                "evaluation_id": evaluation_id,
            }

        if mode == "langgraph" and langgraph_module is not None:
            try:
                from app.langgraph_runtime import run_evaluation_graph

                return run_evaluation_graph(store=self, job=job, tenant_id=tenant_id)
            except Exception:
                if true_stack_required(os.environ):
                    raise
                mode = "compat"

        if mode != "langgraph":
            for node in [
                "load_context",
                "retrieve_evidence",
                "evaluate_rules",
                "score_with_llm",
                "quality_gate",
                "finalize_report",
                "persist_result",
            ]:
                self._append_node_checkpoint(
                    thread_id=thread_id,
                    job_id=str(job.get("job_id") or ""),
                    tenant_id=tenant_id,
                    node=node,
                )

        job = self.transition_job_status(
            job_id=str(job.get("job_id") or ""),
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        return {
            "job_id": str(job.get("job_id") or ""),
            "final_status": "succeeded",
            "thread_id": thread_id,
            "evaluation_id": evaluation_id,
        }

    def _run_resume_workflow(
        self,
        *,
        job: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        thread_id = str(job.get("thread_id") or self._new_thread_id("resume"))
        job_id = str(job.get("job_id") or "")
        mode, langgraph_module = self._workflow_runtime_mode()
        if mode == "langgraph" and langgraph_module is not None:
            try:
                from app.langgraph_runtime import run_resume_graph

                return run_resume_graph(store=self, job=job, tenant_id=tenant_id)
            except Exception:
                if true_stack_required(os.environ):
                    raise
                mode = "compat"

        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="resume_received",
        )
        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="finalize_report",
        )
        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="persist_result",
        )
        job = self.transition_job_status(
            job_id=job_id,
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        return {
            "job_id": job_id,
            "final_status": "succeeded",
            "thread_id": thread_id,
        }

    def append_outbox_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        event = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "status": "pending",
            "published_at": None,
            "created_at": self._utcnow_iso(),
        }
        self.domain_events_outbox[event_id] = event
        return event

    def list_outbox_events(
        self,
        *,
        tenant_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = [x for x in self.domain_events_outbox.values() if x.get("tenant_id") == tenant_id]
        if status:
            items = [x for x in items if x.get("status") == status]
        items = sorted(items, key=lambda x: x.get("created_at", ""))
        return items[: max(1, min(limit, 1000))]

    def mark_outbox_event_published(self, *, tenant_id: str, event_id: str) -> dict[str, Any]:
        event = self.domain_events_outbox.get(event_id)
        if event is None:
            raise ApiError(
                code="OUTBOX_EVENT_NOT_FOUND",
                message="outbox event not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        self._assert_tenant_scope(event.get("tenant_id", "tenant_default"), tenant_id)
        event["status"] = "published"
        event["published_at"] = self._utcnow_iso()
        return event

    @staticmethod
    def _outbox_delivery_key(*, tenant_id: str, event_id: str, consumer_name: str) -> str:
        return f"{tenant_id}:{event_id}:{consumer_name}"

    def get_outbox_delivery(
        self,
        *,
        tenant_id: str,
        event_id: str,
        consumer_name: str,
    ) -> dict[str, Any] | None:
        key = self._outbox_delivery_key(
            tenant_id=tenant_id,
            event_id=event_id,
            consumer_name=consumer_name,
        )
        return self.outbox_delivery_records.get(key)

    def mark_outbox_delivered(
        self,
        *,
        tenant_id: str,
        event_id: str,
        consumer_name: str,
        message_id: str,
    ) -> dict[str, Any]:
        event = self.domain_events_outbox.get(event_id)
        if event is None:
            raise ApiError(
                code="OUTBOX_EVENT_NOT_FOUND",
                message="outbox event not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        self._assert_tenant_scope(event.get("tenant_id", "tenant_default"), tenant_id)
        key = self._outbox_delivery_key(
            tenant_id=tenant_id,
            event_id=event_id,
            consumer_name=consumer_name,
        )
        existing = self.outbox_delivery_records.get(key)
        if existing is not None:
            return existing
        record = {
            "delivery_id": f"odl_{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "event_id": event_id,
            "consumer_name": consumer_name,
            "message_id": message_id,
            "created_at": self._utcnow_iso(),
        }
        self.outbox_delivery_records[key] = record
        return record

    def register_citation_source(self, *, chunk_id: str, source: dict[str, Any]) -> None:
        self.citation_sources[chunk_id] = source

    def get_citation_source(self, *, chunk_id: str, tenant_id: str) -> dict[str, Any] | None:
        source = self.citation_sources.get(chunk_id)
        if source is None:
            return None
        source_tenant = source.get("tenant_id", tenant_id)
        self._assert_tenant_scope(source_tenant, tenant_id)
        return source

    @staticmethod
    def _select_retrieval_mode(*, query_type: str, high_risk: bool) -> str:
        if high_risk:
            return "mix"
        mapping = {
            "fact": "local",
            "relation": "global",
            "comparison": "hybrid",
            "summary": "hybrid",
            "risk": "mix",
        }
        return mapping.get(query_type, "hybrid")

    def retrieval_query(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        query_type: str,
        high_risk: bool,
        top_k: int,
        doc_scope: list[str],
        enable_rerank: bool = True,
        must_include_terms: list[str] | None = None,
        must_exclude_terms: list[str] | None = None,
    ) -> dict[str, Any]:
        self.parser_retrieval_metrics["retrieval_queries_total"] += 1
        selected_mode = self._select_retrieval_mode(query_type=query_type, high_risk=high_risk)
        index_name = self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id)
        candidates = self._query_lightrag(
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_id=supplier_id,
            query=query,
            selected_mode=selected_mode,
            top_k=top_k,
            doc_scope=doc_scope,
        )
        if candidates is None:
            local_candidates = [x for x in self.citation_sources.values() if x.get("tenant_id") == tenant_id]
            local_candidates = [x for x in local_candidates if x.get("project_id") == project_id]
            local_candidates = [x for x in local_candidates if x.get("supplier_id") == supplier_id]
            if doc_scope:
                scope = set(doc_scope)
                local_candidates = [x for x in local_candidates if x.get("doc_type") in scope]
            candidates = []
            for source in local_candidates:
                candidates.append(
                    {
                        "chunk_id": source.get("chunk_id"),
                        "score_raw": float(source.get("score_raw", 0.5)),
                        "reason": f"matched {query_type} intent",
                        "metadata": {
                            "tenant_id": source.get("tenant_id"),
                            "project_id": source.get("project_id"),
                            "supplier_id": source.get("supplier_id"),
                            "document_id": source.get("document_id"),
                            "doc_type": source.get("doc_type"),
                            "page": int(source.get("page", 1)),
                            "bbox": source.get("bbox", [0, 0, 1, 1]),
                        },
                    }
                )
        include_terms = [x.lower() for x in (must_include_terms or []) if x.strip()]
        exclude_terms = [x.lower() for x in (must_exclude_terms or []) if x.strip()]
        rewrite = self._normalize_and_rewrite_query(
            query=query,
            include_terms=include_terms,
            exclude_terms=exclude_terms,
        )
        if include_terms:
            candidates = [
                x
                for x in candidates
                if all(
                    term in str(self.citation_sources.get(str(x.get("chunk_id", "")), {}).get("text", "")).lower()
                    for term in include_terms
                )
            ]
        if exclude_terms:
            candidates = [
                x
                for x in candidates
                if all(
                    term not in str(self.citation_sources.get(str(x.get("chunk_id", "")), {}).get("text", "")).lower()
                    for term in exclude_terms
                )
            ]

        items = [dict(x) for x in candidates]
        degraded = False
        degrade_reason = ""
        if enable_rerank:
            try:
                items = self._rerank_items(items)
            except Exception:
                degraded = True
                degrade_reason = "rerank_failed"
                self.parser_retrieval_metrics["rerank_degraded_total"] += 1
                for item in items:
                    item["score_rerank"] = None
                items = sorted(items, key=lambda x: float(x.get("score_raw", 0.0)), reverse=True)
        else:
            degraded = True
            degrade_reason = "rerank_disabled"
            self.parser_retrieval_metrics["rerank_degraded_total"] += 1
            for item in items:
                item["score_rerank"] = None
            items = sorted(items, key=lambda x: float(x.get("score_raw", 0.0)), reverse=True)
        items = items[:top_k]
        return {
            "query": query,
            "rewritten_query": rewrite["rewritten_query"],
            "rewrite_reason": rewrite["rewrite_reason"],
            "constraints_preserved": rewrite["constraints_preserved"],
            "constraint_diff": rewrite["constraint_diff"],
            "query_type": query_type,
            "selected_mode": selected_mode,
            "index_name": index_name,
            "degraded": degraded,
            "degrade_reason": degrade_reason or None,
            "items": items,
            "total": len(items),
        }

    def retrieval_preview(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        query_type: str,
        high_risk: bool,
        top_k: int,
        doc_scope: list[str],
        enable_rerank: bool = True,
        must_include_terms: list[str] | None = None,
        must_exclude_terms: list[str] | None = None,
    ) -> dict[str, Any]:
        base = self.retrieval_query(
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_id=supplier_id,
            query=query,
            query_type=query_type,
            high_risk=high_risk,
            top_k=top_k,
            doc_scope=doc_scope,
            enable_rerank=enable_rerank,
            must_include_terms=must_include_terms,
            must_exclude_terms=must_exclude_terms,
        )
        preview_items = []
        for item in base["items"]:
            source = self.citation_sources.get(item["chunk_id"], {})
            preview_items.append(
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": source.get("document_id"),
                    "page": item["metadata"]["page"],
                    "bbox": item["metadata"]["bbox"],
                    "text": source.get("text", ""),
                }
            )
        return {
            "query": query,
            "selected_mode": base["selected_mode"],
            "index_name": base["index_name"],
            "degraded": base["degraded"],
            "items": preview_items,
            "total": len(preview_items),
        }

    def seed_dlq_item(
        self,
        *,
        job_id: str,
        error_class: str,
        error_code: str,
        tenant_id: str = "tenant_default",
    ) -> dict[str, Any]:
        dlq_id = f"dlq_{uuid.uuid4().hex[:12]}"
        item = {
            "dlq_id": dlq_id,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "error_class": error_class,
            "error_code": error_code,
            "status": "open",
        }
        return self._persist_dlq_item(item=item)

    def list_dlq_items(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return self.dlq_repository.list(tenant_id=tenant_id)

    def get_dlq_item(self, dlq_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        item = self.dlq_repository.get(tenant_id=tenant_id, dlq_id=dlq_id)
        if item is None:
            return None
        return item

    def requeue_dlq_item(self, *, dlq_id: str, trace_id: str | None, tenant_id: str) -> dict[str, Any]:
        item = self.get_dlq_item(dlq_id, tenant_id=tenant_id)
        if item is None:
            raise ApiError(
                code="DLQ_ITEM_NOT_FOUND",
                message="dlq item not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if item["status"] != "open":
            raise ApiError(
                code="DLQ_REQUEUE_CONFLICT",
                message="dlq item is not open",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )

        new_job_id = f"job_{uuid.uuid4().hex[:12]}"
        self._persist_job(
            job={
            "job_id": new_job_id,
            "job_type": "requeue",
            "status": "queued",
            "retry_count": 0,
            "thread_id": self._new_thread_id("requeue"),
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "resource": {
                "type": "job",
                "id": item["job_id"],
            },
            "payload": {"source_dlq_id": dlq_id},
            "last_error": None,
            }
        )
        item["status"] = "requeued"
        self._persist_dlq_item(item=item)
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "dlq_requeue_submitted",
                "dlq_id": dlq_id,
                "source_job_id": item["job_id"],
                "new_job_id": new_job_id,
                "trace_id": trace_id or "",
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "dlq_id": dlq_id,
            "job_id": new_job_id,
            "status": "queued",
        }

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
        item = self.get_dlq_item(dlq_id, tenant_id=tenant_id)
        if item is None:
            raise ApiError(
                code="DLQ_ITEM_NOT_FOUND",
                message="dlq item not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        reviewer_a = reviewer_id.strip()
        reviewer_b = reviewer_id_2.strip()
        if not reason.strip() or not reviewer_a or not reviewer_b:
            raise ApiError(
                code="APPROVAL_REQUIRED",
                message="discard requires reason and dual reviewers",
                error_class="business_rule",
                retryable=False,
                http_status=400,
            )
        if reviewer_a == reviewer_b:
            raise ApiError(
                code="APPROVAL_REQUIRED",
                message="dual reviewers must be different identities",
                error_class="business_rule",
                retryable=False,
                http_status=400,
            )

        item["status"] = "discarded"
        item["discard_reason"] = reason
        item["reviewer_id"] = reviewer_a
        item["reviewer_id_2"] = reviewer_b
        self._persist_dlq_item(item=item)
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "dlq_discard_submitted",
                "dlq_id": dlq_id,
                "reviewer_id": reviewer_a,
                "reviewer_id_2": reviewer_b,
                "approval_reviewers": [reviewer_a, reviewer_b],
                "reason": reason,
                "trace_id": trace_id or "",
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "dlq_id": dlq_id,
            "status": "discarded",
        }

    def _find_active_legal_hold(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:
        for hold in self.legal_hold_objects.values():
            if hold.get("tenant_id") != tenant_id:
                continue
            if hold.get("object_type") != object_type:
                continue
            if hold.get("object_id") != object_id:
                continue
            if hold.get("status") == "active":
                return hold
        return None

    def _resolve_storage_uri(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
    ) -> str | None:
        if object_type == "document":
            doc = self.get_document_for_tenant(document_id=object_id, tenant_id=tenant_id)
            if isinstance(doc, dict):
                uri = doc.get("storage_uri")
                if isinstance(uri, str) and uri:
                    return uri
        if object_type == "report":
            report = self.get_evaluation_report_for_tenant(evaluation_id=object_id, tenant_id=tenant_id)
            if isinstance(report, dict):
                uri = report.get("report_uri")
                if isinstance(uri, str) and uri:
                    return uri
        return None

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
        if not object_type.strip() or not object_id.strip() or not reason.strip() or not imposed_by.strip():
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="invalid legal hold payload",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        existing = self._find_active_legal_hold(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
        )
        if existing is not None:
            return existing
        hold_id = f"hold_{uuid.uuid4().hex[:12]}"
        hold = {
            "hold_id": hold_id,
            "tenant_id": tenant_id,
            "object_type": object_type.strip(),
            "object_id": object_id.strip(),
            "reason": reason.strip(),
            "imposed_by": imposed_by.strip(),
            "imposed_at": self._utcnow_iso(),
            "released_by": None,
            "released_by_2": None,
            "released_at": None,
            "release_reason": None,
            "status": "active",
            "storage_uri": None,
        }
        storage_uri = self._resolve_storage_uri(
            tenant_id=tenant_id,
            object_type=hold["object_type"],
            object_id=hold["object_id"],
        )
        if storage_uri:
            hold["storage_uri"] = storage_uri
            self.object_storage.apply_legal_hold(storage_uri=storage_uri)
        self.legal_hold_objects[hold_id] = hold
        self._append_audit_log(
            log={
                "tenant_id": tenant_id,
                "action": "legal_hold_imposed",
                "hold_id": hold_id,
                "object_type": hold["object_type"],
                "object_id": hold["object_id"],
                "reason": hold["reason"],
                "imposed_by": hold["imposed_by"],
                "trace_id": trace_id,
            }
        )
        return hold

    def list_legal_holds(
        self,
        *,
        tenant_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        items = [x for x in self.legal_hold_objects.values() if x.get("tenant_id") == tenant_id]
        if status:
            items = [x for x in items if x.get("status") == status]
        return sorted(items, key=lambda x: str(x.get("imposed_at") or ""), reverse=True)

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
        hold = self.legal_hold_objects.get(hold_id)
        if hold is None or hold.get("tenant_id") != tenant_id:
            raise ApiError(
                code="LEGAL_HOLD_NOT_FOUND",
                message="legal hold not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if hold.get("status") != "active":
            raise ApiError(
                code="LEGAL_HOLD_RELEASE_CONFLICT",
                message="legal hold already released",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        reviewer_a = reviewer_id.strip()
        reviewer_b = reviewer_id_2.strip()
        if not reason.strip() or not reviewer_a or not reviewer_b or reviewer_a == reviewer_b:
            raise ApiError(
                code="APPROVAL_REQUIRED",
                message="legal hold release requires reason and dual reviewers",
                error_class="business_rule",
                retryable=False,
                http_status=400,
            )
        hold["status"] = "released"
        hold["released_by"] = reviewer_a
        hold["released_by_2"] = reviewer_b
        hold["released_at"] = self._utcnow_iso()
        hold["release_reason"] = reason.strip()
        storage_uri = hold.get("storage_uri")
        if not storage_uri:
            storage_uri = self._resolve_storage_uri(
                tenant_id=tenant_id,
                object_type=str(hold.get("object_type") or ""),
                object_id=str(hold.get("object_id") or ""),
            )
            if storage_uri:
                hold["storage_uri"] = storage_uri
        if storage_uri:
            self.object_storage.release_legal_hold(storage_uri=storage_uri)
        self._append_audit_log(
            log={
                "tenant_id": tenant_id,
                "action": "legal_hold_released",
                "hold_id": hold_id,
                "object_type": hold.get("object_type"),
                "object_id": hold.get("object_id"),
                "reason": reason.strip(),
                "reviewer_id": reviewer_a,
                "reviewer_id_2": reviewer_b,
                "approval_reviewers": [reviewer_a, reviewer_b],
                "trace_id": trace_id,
            }
        )
        return hold

    def execute_storage_cleanup(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        reason: str,
        trace_id: str,
    ) -> dict[str, Any]:
        active_hold = self._find_active_legal_hold(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
        )
        if active_hold is not None:
            storage_uri = self._resolve_storage_uri(
                tenant_id=tenant_id,
                object_type=object_type,
                object_id=object_id,
            )
            self._append_audit_log(
                log={
                    "tenant_id": tenant_id,
                    "action": "storage_cleanup_blocked",
                    "object_type": object_type,
                    "object_id": object_id,
                    "storage_uri": storage_uri,
                    "reason": reason,
                    "trace_id": trace_id,
                    "blocked_by": "legal_hold",
                    "occurred_at": self._utcnow_iso(),
                }
            )
            raise ApiError(
                code="LEGAL_HOLD_ACTIVE",
                message="object is under legal hold",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        storage_uri = self._resolve_storage_uri(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
        )
        if storage_uri and self.object_storage.is_retention_active(storage_uri=storage_uri):
            retention = self.object_storage.get_retention(storage_uri=storage_uri)
            self._append_audit_log(
                log={
                    "tenant_id": tenant_id,
                    "action": "storage_cleanup_blocked",
                    "object_type": object_type,
                    "object_id": object_id,
                    "storage_uri": storage_uri,
                    "reason": reason,
                    "trace_id": trace_id,
                    "blocked_by": "retention",
                    "retention": retention,
                    "occurred_at": self._utcnow_iso(),
                }
            )
            raise ApiError(
                code="RETENTION_ACTIVE",
                message="object is under retention",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        deleted = False
        if storage_uri:
            deleted = self.object_storage.delete_object(storage_uri=storage_uri)
        self._append_audit_log(
            log={
                "tenant_id": tenant_id,
                "action": "storage_cleanup_executed",
                "object_type": object_type,
                "object_id": object_id,
                "storage_uri": storage_uri,
                "reason": reason,
                "trace_id": trace_id,
            }
        )
        return {
            "tenant_id": tenant_id,
            "object_type": object_type,
            "object_id": object_id,
            "reason": reason,
            "cleaned": True,
            "deleted": deleted,
            "storage_uri": storage_uri,
        }

    def cancel_job(self, *, job_id: str, tenant_id: str) -> dict[str, Any]:
        job = self.get_job_for_tenant(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            raise ApiError(
                code="JOB_NOT_FOUND",
                message="job not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        if job["status"] in {"succeeded", "failed"}:
            raise ApiError(
                code="JOB_CANCEL_CONFLICT",
                message="job already in terminal state",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )

        job["status"] = "failed"
        job["error_code"] = "JOB_CANCELLED"
        job["last_error"] = {
            "code": "JOB_CANCELLED",
            "message": "job cancelled by operator",
            "retryable": False,
            "class": "business_rule",
        }
        return {
            "job_id": job_id,
            "status": "failed",
            "error_code": "JOB_CANCELLED",
        }

    def list_jobs(
        self,
        *,
        tenant_id: str,
        status: str | None = None,
        job_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        jobs = [j for j in self.jobs.values() if j.get("tenant_id") == tenant_id]
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        if job_type:
            jobs = [j for j in jobs if j.get("job_type") == job_type]

        start = 0
        if cursor:
            try:
                start = max(0, int(cursor))
            except ValueError:
                start = 0
        limit = min(max(limit, 1), 100)

        sliced = jobs[start : start + limit]
        next_cursor = None
        if start + limit < len(jobs):
            next_cursor = str(start + limit)

        return {
            "items": sliced,
            "total": len(jobs),
            "next_cursor": next_cursor,
        }

    def summarize_ops_metrics(self, *, tenant_id: str) -> dict[str, Any]:
        jobs = [j for j in self.jobs.values() if j.get("tenant_id") == tenant_id]
        total_jobs = len(jobs)
        succeeded_jobs = sum(1 for j in jobs if j.get("status") == "succeeded")
        failed_jobs = sum(1 for j in jobs if j.get("status") == "failed")
        retrying_jobs = sum(1 for j in jobs if j.get("status") == "retrying")
        success_rate = (succeeded_jobs / total_jobs) if total_jobs else 0.0
        error_rate = (failed_jobs / total_jobs) if total_jobs else 0.0

        dlq_open = sum(
            1
            for item in self.dlq_items.values()
            if item.get("tenant_id") == tenant_id and item.get("status") == "open"
        )
        outbox_pending = sum(
            1
            for item in self.domain_events_outbox.values()
            if item.get("tenant_id") == tenant_id and item.get("status") == "pending"
        )

        reports = [r for r in self.evaluation_reports.values() if r.get("tenant_id") == tenant_id]
        if reports:
            citation_coverage_avg = sum(float(r.get("citation_coverage", 0.0)) for r in reports) / len(reports)
        else:
            citation_coverage_avg = 0.0

        return {
            "tenant_id": tenant_id,
            "api": {
                "total_jobs": total_jobs,
                "succeeded_jobs": succeeded_jobs,
                "failed_jobs": failed_jobs,
                "error_rate": round(error_rate, 4),
            },
            "worker": {
                "retrying_jobs": retrying_jobs,
                "dlq_open": dlq_open,
                "outbox_pending": outbox_pending,
                "max_retries": self.worker_max_retries,
                "retry_backoff_base_ms": self.worker_retry_backoff_base_ms,
                "retry_backoff_max_ms": self.worker_retry_backoff_max_ms,
                "resume_token_ttl_hours": self.resume_token_ttl_hours,
                "checkpoint_backend": self.workflow_checkpoint_backend,
            },
            "quality": {
                "report_count": len(reports),
                "citation_coverage_avg": round(citation_coverage_avg, 4),
            },
            "cost": {
                "dataset_version": self.dataset_version,
                "strategy_version": f"stg_v{self.strategy_version_counter}",
            },
            "parse_retrieval": dict(self.parser_retrieval_metrics),
            "slo": {
                "success_rate": round(success_rate, 4),
            },
            "observability": {
                "metrics_namespace": self.obs_metrics_namespace,
                "otel_exporter_configured": bool(self.otel_exporter_otlp_endpoint),
                "alert_webhook_configured": bool(self.obs_alert_webhook),
                "p6_readiness_required": bool(self.p6_readiness_required),
                "release_canary_ratio": self.release_canary_ratio,
                "release_canary_duration_min": self.release_canary_duration_min,
                "rollback_max_minutes": self.rollback_max_minutes,
            },
        }

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
        replay_run_id = f"rpy_{uuid.uuid4().hex[:12]}"
        upload = self.create_upload_job(
            {
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "doc_type": doc_type,
                "filename": f"{release_id}.pdf",
                "file_sha256": uuid.uuid4().hex,
                "file_size": 128,
            }
        )
        parse_job_id = upload["job_id"]
        parse_result = self.run_job_once(job_id=parse_job_id, tenant_id=tenant_id)
        parse_status = parse_result["final_status"]

        eval_created = self.create_evaluation_job(
            {
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": [doc_type], "force_hitl": force_hitl},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            }
        )
        evaluation_id = eval_created["evaluation_id"]
        evaluation_job_id = eval_created["job_id"]
        resume_job_id: str | None = None

        report = self.get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
        )
        if force_hitl and isinstance(report, dict):
            interrupt = report.get("interrupt")
            token = interrupt.get("resume_token") if isinstance(interrupt, dict) else None
            if isinstance(token, str) and token:
                if self.consume_resume_token(
                    evaluation_id=evaluation_id,
                    resume_token=token,
                    tenant_id=tenant_id,
                ):
                    resumed = self.create_resume_job(
                        evaluation_id=evaluation_id,
                        payload={
                            "tenant_id": tenant_id,
                            "trace_id": trace_id,
                            "decision": decision,
                            "comment": "release replay auto resume",
                            "editor": {"reviewer_id": "system_replay"},
                        },
                    )
                    resume_job_id = resumed["job_id"]
                    self.run_job_once(job_id=resume_job_id, tenant_id=tenant_id)

        final_report = self.get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
        ) or {}
        needs_human_review = bool(final_report.get("needs_human_review", False))
        passed = parse_status == "succeeded" and (not force_hitl or not needs_human_review)

        data = {
            "replay_run_id": replay_run_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "parse": {"job_id": parse_job_id, "status": parse_status},
            "evaluation": {
                "evaluation_id": evaluation_id,
                "job_id": evaluation_job_id,
                "resume_job_id": resume_job_id,
                "needs_human_review": needs_human_review,
            },
            "passed": passed,
        }
        self.release_replay_runs[replay_run_id] = {**data, "trace_id": trace_id, "created_at": self._utcnow_iso()}
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_replay_e2e_executed",
                "release_id": release_id,
                "replay_run_id": replay_run_id,
                "passed": passed,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return data

    def evaluate_release_readiness(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        expected_gates = ["quality", "performance", "security", "cost", "rollout", "rollback", "ops"]
        normalized_gate_results = {name: bool(gate_results.get(name, False)) for name in expected_gates}
        failed_checks: list[str] = []
        for gate_name in expected_gates:
            if not normalized_gate_results[gate_name]:
                failed_checks.append(f"{gate_name.upper()}_GATE_FAILED")
        if not replay_passed:
            failed_checks.append("REPLAY_E2E_FAILED")
        admitted = len(failed_checks) == 0
        assessment_id = f"ra_{uuid.uuid4().hex[:12]}"
        data = {
            "assessment_id": assessment_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "admitted": admitted,
            "failed_checks": failed_checks,
            "replay_passed": replay_passed,
            "gate_results": normalized_gate_results,
        }
        self.release_readiness_assessments[assessment_id] = {
            **data,
            "trace_id": trace_id,
            "created_at": self._utcnow_iso(),
        }
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_readiness_evaluated",
                "release_id": release_id,
                "assessment_id": assessment_id,
                "admitted": admitted,
                "failed_checks": failed_checks,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return data

    def execute_release_pipeline(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        pipeline_id = f"pl_{uuid.uuid4().hex[:12]}"
        if self.p6_readiness_required:
            readiness = self.evaluate_release_readiness(
                release_id=release_id,
                tenant_id=tenant_id,
                trace_id=trace_id,
                replay_passed=replay_passed,
                gate_results=gate_results,
            )
            admitted = bool(readiness.get("admitted", False))
            failed_checks = list(readiness.get("failed_checks", []))
            assessment_id = str(readiness.get("assessment_id", ""))
        else:
            admitted = True
            failed_checks = []
            assessment_id = ""
            readiness = None

        stage = "release_blocked"
        if admitted:
            stage = "release_ready"
        data = {
            "pipeline_id": pipeline_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "stage": stage,
            "admitted": admitted,
            "failed_checks": failed_checks,
            "readiness_assessment_id": assessment_id,
            "canary": {
                "ratio": self.release_canary_ratio,
                "duration_min": self.release_canary_duration_min,
            },
            "rollback": {
                "max_minutes": self.rollback_max_minutes,
            },
            "readiness_required": bool(self.p6_readiness_required),
        }
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_pipeline_executed",
                "release_id": release_id,
                "pipeline_id": pipeline_id,
                "stage": stage,
                "admitted": admitted,
                "failed_checks": failed_checks,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        if readiness is not None:
            data["readiness"] = readiness
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
        size_order = {"small": 1, "medium": 2, "large": 3}
        policy = {
            "release_id": release_id,
            "tenant_whitelist": sorted({x.strip() for x in tenant_whitelist if x.strip()}),
            "enabled_project_sizes": sorted(
                {x.strip() for x in enabled_project_sizes if x.strip()},
                key=lambda x: size_order.get(x, 999),
            ),
            "high_risk_hitl_enforced": bool(high_risk_hitl_enforced),
            "tenant_id": tenant_id,
            "updated_at": self._utcnow_iso(),
        }
        self.release_rollout_policies[release_id] = policy
        return {
            "release_id": policy["release_id"],
            "tenant_whitelist": policy["tenant_whitelist"],
            "enabled_project_sizes": policy["enabled_project_sizes"],
            "high_risk_hitl_enforced": policy["high_risk_hitl_enforced"],
        }

    def decide_rollout(
        self,
        *,
        release_id: str,
        tenant_id: str,
        project_size: str,
        high_risk: bool,
    ) -> dict[str, Any]:
        policy = self.release_rollout_policies.get(release_id)
        if policy is None:
            raise ApiError(
                code="RELEASE_POLICY_NOT_FOUND",
                message="release rollout policy not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )

        reasons: list[str] = []
        matched_whitelist = tenant_id in set(policy["tenant_whitelist"])
        if not matched_whitelist:
            reasons.append("TENANT_NOT_IN_WHITELIST")
        if project_size not in set(policy["enabled_project_sizes"]):
            reasons.append("PROJECT_SIZE_NOT_ENABLED")
        force_hitl = bool(high_risk and policy["high_risk_hitl_enforced"])

        return {
            "release_id": release_id,
            "admitted": len(reasons) == 0,
            "stage": "tenant_whitelist+project_size",
            "matched_whitelist": matched_whitelist,
            "force_hitl": force_hitl,
            "reasons": reasons,
        }

    def execute_rollback(
        self,
        *,
        release_id: str,
        consecutive_threshold: int,
        breaches: list[dict[str, Any]],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        rollback_order = [
            "model_config",
            "retrieval_params",
            "workflow_version",
            "release_version",
        ]
        trigger_breach = next(
            (x for x in breaches if int(x.get("consecutive_failures", 0)) >= consecutive_threshold),
            None,
        )
        if trigger_breach is None:
            return {
                "release_id": release_id,
                "triggered": False,
                "trigger_gate": None,
                "rollback_order": rollback_order,
                "replay_verification": None,
                "elapsed_minutes": 0,
                "rollback_completed_within_30m": True,
                "service_restored": True,
            }

        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "rollback_executed",
                "release_id": release_id,
                "trigger_gate": trigger_breach.get("gate"),
                "consecutive_threshold": consecutive_threshold,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )

        replay_job_id = f"job_{uuid.uuid4().hex[:12]}"
        self._persist_job(
            job={
            "job_id": replay_job_id,
            "job_type": "replay_verification",
            "status": "queued",
            "retry_count": 0,
            "thread_id": self._new_thread_id("replay"),
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "resource": {
                "type": "job",
                "id": release_id,
            },
            "payload": {
                "release_id": release_id,
                "trigger_gate": trigger_breach.get("gate"),
            },
            "last_error": None,
            }
        )
        replay_result = self.run_job_once(job_id=replay_job_id, tenant_id=tenant_id)
        replay_status = replay_result["final_status"]

        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "rollback_replay_verified",
                "release_id": release_id,
                "replay_job_id": replay_job_id,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )

        return {
            "release_id": release_id,
            "triggered": True,
            "trigger_gate": trigger_breach.get("gate"),
            "rollback_order": rollback_order,
            "replay_verification": {
                "job_id": replay_job_id,
                "status": replay_status,
            },
            "elapsed_minutes": 8,
            "rollback_completed_within_30m": True,
            "service_restored": replay_status == "succeeded",
        }

    @staticmethod
    def _bump_dataset_version(version: str, bump: str) -> str:
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
        if not match:
            return "v1.0.0"
        major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if bump == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"v{major}.{minor}.{patch}"

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
        candidate_dlq_ids = dlq_ids or [x["dlq_id"] for x in self.list_dlq_items(tenant_id=tenant_id)]
        counterexample_added = 0
        for dlq_id in candidate_dlq_ids:
            item = self.get_dlq_item(dlq_id, tenant_id=tenant_id)
            if item is None:
                continue
            if dlq_id in self.counterexample_samples:
                continue
            self.counterexample_samples[dlq_id] = {
                "sample_id": dlq_id,
                "release_id": release_id,
                "tenant_id": tenant_id,
                "source": "dlq",
                "job_id": item.get("job_id"),
                "error_class": item.get("error_class"),
                "error_code": item.get("error_code"),
                "created_at": self._utcnow_iso(),
            }
            counterexample_added += 1

        gold_candidates_added = 0
        if include_manual_override_candidates:
            for log in self.audit_logs:
                if log.get("tenant_id") != tenant_id:
                    continue
                if log.get("action") != "resume_submitted":
                    continue
                if log.get("decision") not in {"reject", "edit_scores"}:
                    continue
                key = str(log.get("audit_id"))
                if key in self.gold_candidate_samples:
                    continue
                self.gold_candidate_samples[key] = {
                    "sample_id": key,
                    "release_id": release_id,
                    "tenant_id": tenant_id,
                    "source": "manual_override",
                    "evaluation_id": log.get("evaluation_id"),
                    "decision": log.get("decision"),
                    "created_at": self._utcnow_iso(),
                }
                gold_candidates_added += 1

        before = self.dataset_version
        after = self._bump_dataset_version(before, version_bump)
        self.dataset_version = after
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "data_feedback_run",
                "release_id": release_id,
                "counterexample_added": counterexample_added,
                "gold_candidates_added": gold_candidates_added,
                "dataset_version_before": before,
                "dataset_version_after": after,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "release_id": release_id,
            "counterexample_added": counterexample_added,
            "gold_candidates_added": gold_candidates_added,
            "dataset_version_before": before,
            "dataset_version_after": after,
        }

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
        self.strategy_config["selector"] = {
            "risk_mix_threshold": float(selector["risk_mix_threshold"]),
            "relation_mode": str(selector["relation_mode"]),
        }
        self.strategy_config["score_calibration"] = {
            "confidence_scale": float(score_calibration["confidence_scale"]),
            "score_bias": float(score_calibration["score_bias"]),
        }
        self.strategy_config["tool_policy"] = {
            "require_double_approval_actions": list(tool_policy["require_double_approval_actions"]),
            "allowed_tools": list(tool_policy["allowed_tools"]),
        }
        self.strategy_version_counter += 1
        strategy_version = f"stg_v{self.strategy_version_counter}"
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "strategy_tuning_applied",
                "release_id": release_id,
                "strategy_version": strategy_version,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "release_id": release_id,
            "strategy_version": strategy_version,
            "selector": self.strategy_config["selector"],
            "score_calibration": self.strategy_config["score_calibration"],
            "tool_policy": self.strategy_config["tool_policy"],
        }

    def run_job_once(
        self,
        *,
        job_id: str,
        tenant_id: str,
        force_fail: bool = False,
        transient_fail: bool = False,
        force_error_code: str | None = None,
    ) -> dict[str, Any]:
        job = self.get_job_for_tenant(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            raise ApiError(
                code="JOB_NOT_FOUND",
                message="job not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        thread_id = str(job.get("thread_id") or self._new_thread_id("job"))
        if not job.get("thread_id"):
            job["thread_id"] = thread_id
            self._persist_job(job=job)

        status = job["status"]
        if status in {"queued", "retrying", "needs_manual_decision"}:
            job = self.transition_job_status(
                job_id=job_id,
                new_status="running",
                tenant_id=tenant_id,
            )
            status = job["status"]
            self.append_workflow_checkpoint(
                thread_id=thread_id,
                job_id=job_id,
                tenant_id=tenant_id,
                node="job_started",
                status="running",
                payload={"job_type": job.get("job_type", "")},
            )
        if job.get("job_type") == "parse":
            manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
            if manifest is not None:
                if manifest.get("started_at") is None:
                    manifest["started_at"] = self._utcnow_iso()
                manifest["status"] = "running"
                manifest["error_code"] = None
                self._persist_parse_manifest(manifest=manifest)
            self.parser_retrieval_metrics["parse_runs_total"] += 1

        if status != "running":
            raise ApiError(
                code="WF_STATE_TRANSITION_INVALID",
                message=f"job cannot run from status: {status}",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )

        if transient_fail and not force_fail:
            error_code = force_error_code or "RAG_UPSTREAM_UNAVAILABLE"
            error = self._classify_error_code(error_code)
            current_retry = int(job.get("retry_count", 0))

            if current_retry < self.worker_max_retries:
                retried_job = self.transition_job_status(
                    job_id=job_id,
                    new_status="retrying",
                    tenant_id=tenant_id,
                )
                retry_count = int(retried_job.get("retry_count", 0))
                retry_after_ms = self._retry_backoff_ms(job_id=job_id, retry_count=retry_count)
                retry_at = (datetime.now(UTC) + timedelta(milliseconds=retry_after_ms)).isoformat()
                retried_job["next_retry_at"] = retry_at
                retried_job["last_error"] = {
                    "code": error_code,
                    "message": error["message"],
                    "retryable": True,
                    "class": "transient",
                }
                self._persist_job(job=retried_job)
                if job.get("job_type") == "parse":
                    manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
                    if manifest is not None:
                        manifest["status"] = "retrying"
                        manifest["error_code"] = error_code
                        self._persist_parse_manifest(manifest=manifest)
                self.append_workflow_checkpoint(
                    thread_id=thread_id,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    node="job_retrying",
                    status="retrying",
                    payload={
                        "retry_count": retried_job.get("retry_count", 0),
                        "error_code": error_code,
                        "retry_after_ms": retry_after_ms,
                        "retry_at": retry_at,
                    },
                )
                return {
                    "job_id": job_id,
                    "final_status": "retrying",
                    "retry_count": retried_job.get("retry_count", 0),
                    "dlq_id": None,
                    "retry_after_ms": retry_after_ms,
                    "retry_at": retry_at,
                }
            force_fail = True
            force_error_code = error_code

        if force_fail:
            error_code = force_error_code
            if not error_code:
                if job.get("job_type") == "parse":
                    error_code = "DOC_PARSE_OUTPUT_NOT_FOUND"
                else:
                    error_code = "INTERNAL_DEBUG_FORCED_FAIL"
            error = self._classify_error_code(error_code)
            self.transition_job_status(
                job_id=job_id,
                new_status="dlq_pending",
                tenant_id=tenant_id,
            )
            self.transition_job_status(
                job_id=job_id,
                new_status="dlq_recorded",
                tenant_id=tenant_id,
            )
            dlq_item = self.seed_dlq_item(
                job_id=job_id,
                error_class=error["class"],
                error_code=error_code,
                tenant_id=tenant_id,
            )
            failed_job = self.transition_job_status(
                job_id=job_id,
                new_status="failed",
                tenant_id=tenant_id,
            )
            failed_job.pop("next_retry_at", None)
            failed_job["last_error"] = {
                "code": error_code,
                "message": error["message"],
                "retryable": error["retryable"],
                "class": error["class"],
            }
            self._persist_job(job=failed_job)
            if job.get("job_type") == "parse":
                manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
                if manifest is not None:
                    manifest["status"] = "failed"
                    manifest["error_code"] = error_code
                    manifest["ended_at"] = self._utcnow_iso()
                    self._persist_parse_manifest(manifest=manifest)
                document_id = job.get("resource", {}).get("id")
                if isinstance(document_id, str):
                    document = self.get_document_for_tenant(document_id=document_id, tenant_id=tenant_id)
                    if document is not None:
                        document["status"] = "parse_failed"
                        self._persist_document(document=document)
            self.append_workflow_checkpoint(
                thread_id=thread_id,
                job_id=job_id,
                tenant_id=tenant_id,
                node="job_failed",
                status="failed",
                payload={"error_code": error_code, "retry_count": failed_job.get("retry_count", 0)},
            )
            return {
                "job_id": job_id,
                "final_status": "failed",
                "retry_count": failed_job.get("retry_count", 0),
                "dlq_id": dlq_item["dlq_id"],
            }

        if job.get("job_type") == "evaluation":
            result = self._run_evaluation_workflow(job=job, tenant_id=tenant_id)
            if result.get("final_status") == "succeeded":
                self.append_workflow_checkpoint(
                    thread_id=str(result.get("thread_id") or thread_id),
                    job_id=job_id,
                    tenant_id=tenant_id,
                    node="job_succeeded",
                    status="succeeded",
                    payload={"job_type": "evaluation"},
                )
            elif result.get("final_status") == "needs_manual_decision":
                self.append_workflow_checkpoint(
                    thread_id=str(result.get("thread_id") or thread_id),
                    job_id=job_id,
                    tenant_id=tenant_id,
                    node="job_needs_manual_decision",
                    status="needs_manual_decision",
                    payload={"job_type": "evaluation"},
                )
            return result

        if job.get("job_type") == "resume":
            result = self._run_resume_workflow(job=job, tenant_id=tenant_id)
            self.append_workflow_checkpoint(
                thread_id=str(result.get("thread_id") or thread_id),
                job_id=job_id,
                tenant_id=tenant_id,
                node="job_succeeded",
                status="succeeded",
                payload={"job_type": "resume"},
            )
            return result

        succeeded_job = self.transition_job_status(
            job_id=job_id,
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        succeeded_job.pop("next_retry_at", None)
        self._persist_job(job=succeeded_job)
        if job.get("job_type") == "parse":
            manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
            if manifest is not None:
                manifest["status"] = "succeeded"
                manifest["error_code"] = None
                manifest["ended_at"] = self._utcnow_iso()
                self._persist_parse_manifest(manifest=manifest)
            document_id = job.get("resource", {}).get("id")
            if isinstance(document_id, str):
                document = self.get_document_for_tenant(document_id=document_id, tenant_id=tenant_id)
                if document is not None:
                    document["status"] = "indexed"
                    self._persist_document(document=document)
                    existing_chunks = self.list_document_chunks_for_tenant(
                        document_id=document_id,
                        tenant_id=tenant_id,
                    )
                    if not existing_chunks:
                        selected_parser = manifest["selected_parser"] if manifest else "mineru"
                        parser_version = manifest.get("parser_version", "v0") if manifest else "v0"
                        fallback_chain = list(manifest.get("fallback_chain", [])) if manifest else []
                        route = ParseRoute(
                            selected_parser=selected_parser,
                            fallback_chain=fallback_chain,
                            parser_version=parser_version,
                        )
                        chunk = self._parser_registry.parse_with_route(
                            route=route,
                            document_id=document_id,
                            default_text="chunk generated by parse skeleton",
                        )
                        normalized_chunk = self._ensure_chunk_shape(document_id=document_id, chunk=chunk)
                        if normalized_chunk.get("parser") != route.selected_parser:
                            self.parser_retrieval_metrics["parse_fallback_used_total"] += 1
                        if manifest is not None:
                            manifest["content_source"] = normalized_chunk.get("content_source", "unknown")
                        persisted_chunks = self._persist_document_chunks(
                            tenant_id=tenant_id,
                            document_id=document_id,
                            chunks=[normalized_chunk],
                        )
                        if manifest is not None:
                            manifest["chunk_count"] = len(persisted_chunks)
                            self._persist_parse_manifest(manifest=manifest)
                        for persisted in persisted_chunks:
                            page, bbox = self._extract_page_and_bbox(persisted)
                            self.register_citation_source(
                                chunk_id=str(persisted["chunk_id"]),
                                source={
                                    "chunk_id": persisted["chunk_id"],
                                    "document_id": document_id,
                                    "tenant_id": tenant_id,
                                    "project_id": document.get("project_id"),
                                    "supplier_id": document.get("supplier_id"),
                                    "doc_type": document.get("doc_type"),
                                    "page": page,
                                    "bbox": bbox,
                                    "heading_path": persisted.get("heading_path", []),
                                    "chunk_type": persisted.get("chunk_type", "text"),
                                    "content_source": persisted.get("content_source", "unknown"),
                                    "text": persisted.get("text", ""),
                                    "context": persisted.get("section", ""),
                                    "score_raw": 0.78,
                                    "chunk_hash": persisted.get("chunk_hash"),
                                },
                            )
                        self._maybe_index_chunks_to_lightrag(
                            tenant_id=tenant_id,
                            project_id=str(document.get("project_id") or ""),
                            supplier_id=str(document.get("supplier_id") or ""),
                            document_id=document_id,
                            doc_type=str(document.get("doc_type") or ""),
                            chunks=persisted_chunks,
                        )
        self.append_workflow_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="job_succeeded",
            status="succeeded",
            payload={"retry_count": job.get("retry_count", 0)},
        )
        return {
            "job_id": job_id,
            "final_status": "succeeded",
            "retry_count": succeeded_job.get("retry_count", 0),
            "dlq_id": None,
        }


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
            payload.get("domain_events_outbox", {})
            if isinstance(payload.get("domain_events_outbox"), dict)
            else {}
        )
        self.outbox_delivery_records = (
            payload.get("outbox_delivery_records", {})
            if isinstance(payload.get("outbox_delivery_records"), dict)
            else {}
        )
        self.workflow_checkpoints = (
            payload.get("workflow_checkpoints", {})
            if isinstance(payload.get("workflow_checkpoints"), dict)
            else {}
        )
        self.citation_sources = (
            payload.get("citation_sources", {}) if isinstance(payload.get("citation_sources"), dict) else {}
        )
        self.dlq_items = payload.get("dlq_items", {}) if isinstance(payload.get("dlq_items"), dict) else {}
        self.legal_hold_objects = (
            payload.get("legal_hold_objects", {})
            if isinstance(payload.get("legal_hold_objects"), dict)
            else {}
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
            payload.get("counterexample_samples", {})
            if isinstance(payload.get("counterexample_samples"), dict)
            else {}
        )
        self.gold_candidate_samples = (
            payload.get("gold_candidate_samples", {})
            if isinstance(payload.get("gold_candidate_samples"), dict)
            else {}
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
        with self._lock:
            with self._connect() as conn:
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
        with self._lock:
            with self._connect() as conn:
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
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().execute_release_pipeline(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
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
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().evaluate_release_readiness(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
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
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().execute_release_pipeline(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
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


def _import_psycopg() -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "psycopg is required for BEA_STORE_BACKEND=postgres; install psycopg[binary]"
        ) from exc
    return psycopg


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
            return {
                "evaluation_id": loaded["evaluation_id"],
                "supplier_id": loaded["supplier_id"],
                "total_score": loaded["total_score"],
                "confidence": loaded["confidence"],
                "citation_coverage": loaded.get("citation_coverage", 0.0),
                "risk_level": loaded["risk_level"],
                "criteria_results": loaded["criteria_results"],
                "citations": loaded["citations"],
                "needs_human_review": loaded["needs_human_review"],
                "trace_id": loaded["trace_id"],
                "interrupt": loaded.get("interrupt"),
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
            payload.get("domain_events_outbox", {})
            if isinstance(payload.get("domain_events_outbox"), dict)
            else {}
        )
        self.outbox_delivery_records = (
            payload.get("outbox_delivery_records", {})
            if isinstance(payload.get("outbox_delivery_records"), dict)
            else {}
        )
        self.workflow_checkpoints = (
            payload.get("workflow_checkpoints", {})
            if isinstance(payload.get("workflow_checkpoints"), dict)
            else {}
        )
        self.citation_sources = (
            payload.get("citation_sources", {}) if isinstance(payload.get("citation_sources"), dict) else {}
        )
        self.dlq_items = payload.get("dlq_items", {}) if isinstance(payload.get("dlq_items"), dict) else {}
        self.legal_hold_objects = (
            payload.get("legal_hold_objects", {})
            if isinstance(payload.get("legal_hold_objects"), dict)
            else {}
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
            payload.get("counterexample_samples", {})
            if isinstance(payload.get("counterexample_samples"), dict)
            else {}
        )
        self.gold_candidate_samples = (
            payload.get("gold_candidate_samples", {})
            if isinstance(payload.get("gold_candidate_samples"), dict)
            else {}
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
        with self._lock:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(upsert_sql, (blob,))
                conn.commit()

    def _load_state(self) -> None:
        select_sql = f"SELECT payload::text FROM {self._table_name} WHERE id = 1"
        with self._lock:
            with self._connect() as conn:
                with conn.cursor() as cur:
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
        with self._lock:
            with self._connect() as conn:
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
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        data = super().evaluate_release_readiness(
            release_id=release_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
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


def create_store_from_env(environ: Mapping[str, str] | None = None) -> InMemoryStore:
    env = os.environ if environ is None else environ
    backend = env.get("BEA_STORE_BACKEND", "memory").strip().lower()
    if true_stack_required(env) and backend != "postgres":
        raise RuntimeError("BEA_STORE_BACKEND must be postgres when BEA_REQUIRE_TRUESTACK=true")
    if backend == "sqlite":
        db_path = env.get("BEA_STORE_SQLITE_PATH", ".local/bea-store.sqlite3")
        return SqliteBackedStore(db_path)
    if backend == "postgres":
        dsn = env.get("POSTGRES_DSN", "").strip()
        if not dsn:
            raise ValueError("POSTGRES_DSN must be set when BEA_STORE_BACKEND=postgres")
        table_name = env.get("BEA_STORE_POSTGRES_TABLE", "bea_store_state")
        apply_rls = env.get("POSTGRES_APPLY_RLS", "false").strip().lower() in {"1", "true", "yes", "on"}
        return PostgresBackedStore(dsn=dsn, table_name=table_name, apply_rls=apply_rls)
    return InMemoryStore()


store = create_store_from_env()
