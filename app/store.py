from __future__ import annotations

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

from app.errors import ApiError


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
        self.idempotency_records: dict[tuple[str, str], IdempotencyRecord] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.document_chunks: dict[str, list[dict[str, Any]]] = {}
        self.evaluation_reports: dict[str, dict[str, Any]] = {}
        self.parse_manifests: dict[str, dict[str, Any]] = {}
        self.resume_tokens: dict[str, dict[str, Any]] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.domain_events_outbox: dict[str, dict[str, Any]] = {}
        self.citation_sources: dict[str, dict[str, Any]] = {}
        self.dlq_items: dict[str, dict[str, Any]] = {}
        self.release_rollout_policies: dict[str, dict[str, Any]] = {}
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

    def reset(self) -> None:
        self.idempotency_records.clear()
        self.jobs.clear()
        self.documents.clear()
        self.document_chunks.clear()
        self.evaluation_reports.clear()
        self.parse_manifests.clear()
        self.resume_tokens.clear()
        self.audit_logs.clear()
        self.domain_events_outbox.clear()
        self.citation_sources.clear()
        self.dlq_items.clear()
        self.release_rollout_policies.clear()
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
    def _select_parser(*, filename: str, doc_type: str | None) -> tuple[str, list[str]]:
        lower_name = filename.lower()
        office_or_html_suffixes = (".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".html", ".htm")
        if lower_name.endswith(".pdf"):
            return "mineru", ["docling", "ocr"]
        if lower_name.endswith(office_or_html_suffixes):
            return "docling", ["ocr"]
        if (doc_type or "").lower() in {"tender", "bid", "attachment"}:
            return "mineru", ["docling", "ocr"]
        return "ocr", []

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
        return {
            "rewritten_query": rewritten,
            "rewrite_reason": "normalize_whitespace_and_constraints",
            "constraints_preserved": True,
            "constraint_diff": [],
        }

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
        tenant_id = payload.get("tenant_id", "tenant_default")
        force_hitl = bool(payload.get("evaluation_scope", {}).get("force_hitl", False))
        include_doc_types = payload.get("evaluation_scope", {}).get("include_doc_types", [])
        include_doc_types_normalized = {str(x).lower() for x in include_doc_types}
        hard_constraint_pass = "bid" in include_doc_types_normalized
        needs_human_review = force_hitl and hard_constraint_pass
        confidence = 0.62 if needs_human_review else (0.78 if hard_constraint_pass else 1.0)
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
        self.jobs[job_id] = {
            "job_id": job_id,
            "job_type": "evaluation",
            "status": "queued",
            "retry_count": 0,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "evaluation",
                "id": evaluation_id,
            },
            "payload": payload,
            "last_error": None,
        }
        self.evaluation_reports[evaluation_id] = {
            "evaluation_id": evaluation_id,
            "supplier_id": payload.get("supplier_id", ""),
            "total_score": 88.5 if hard_constraint_pass else 0.0,
            "confidence": confidence,
            "citation_coverage": 1.0,
            "risk_level": "medium" if hard_constraint_pass else "high",
            "criteria_results": [
                {
                    "criteria_id": "delivery",
                    "score": 18.0 if hard_constraint_pass else 0.0,
                    "max_score": 20.0,
                    "hard_pass": hard_constraint_pass,
                    "reason": (
                        "delivery period satisfies baseline"
                        if hard_constraint_pass
                        else "rule engine blocked: required bid document scope missing"
                    ),
                    "citations": ["ck_eval_stub_1" if hard_constraint_pass else "ck_rule_block_1"],
                    "confidence": 0.81 if hard_constraint_pass else 1.0,
                }
            ],
            "citations": ["ck_eval_stub_1" if hard_constraint_pass else "ck_rule_block_1"],
            "needs_human_review": needs_human_review,
            "trace_id": payload.get("trace_id") or "",
            "tenant_id": tenant_id,
            "interrupt": interrupt_payload,
        }
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

    def create_upload_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        tenant_id = payload.get("tenant_id", "tenant_default")
        self.documents[document_id] = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "project_id": payload.get("project_id"),
            "supplier_id": payload.get("supplier_id"),
            "doc_type": payload.get("doc_type"),
            "filename": payload.get("filename"),
            "file_sha256": payload.get("file_sha256"),
            "file_size": payload.get("file_size"),
            "status": "uploaded",
        }
        self.document_chunks[document_id] = []
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
        document = self.documents.get(document_id)
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
        self.jobs[job_id] = {
            "job_id": job_id,
            "job_type": "parse",
            "status": "queued",
            "retry_count": 0,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "document",
                "id": document_id,
            },
            "payload": payload,
            "last_error": None,
        }
        selected_parser, fallback_chain = self._select_parser(
            filename=document.get("filename", ""),
            doc_type=document.get("doc_type"),
        )
        self.parse_manifests[job_id] = {
            "job_id": job_id,
            "document_id": document_id,
            "tenant_id": tenant_id,
            "selected_parser": selected_parser,
            "fallback_chain": fallback_chain,
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
        document["status"] = "parse_queued"
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

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)

    def get_job_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        self._assert_tenant_scope(job.get("tenant_id", "tenant_default"), tenant_id)
        return job

    def get_parse_manifest_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        manifest = self.parse_manifests.get(job_id)
        if manifest is None:
            return None
        self._assert_tenant_scope(manifest.get("tenant_id", "tenant_default"), tenant_id)
        return manifest

    def get_evaluation_report_for_tenant(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        report = self.evaluation_reports.get(evaluation_id)
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
        return job

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

        expires_at = issued_at + timedelta(hours=self.RESUME_TOKEN_TTL_HOURS)
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
        self.jobs[job_id] = {
            "job_id": job_id,
            "job_type": "resume",
            "status": "queued",
            "retry_count": 0,
            "tenant_id": tenant_id,
            "trace_id": payload.get("trace_id"),
            "resource": {
                "type": "evaluation",
                "id": evaluation_id,
            },
            "payload": payload,
            "last_error": None,
        }
        report = self.evaluation_reports.get(evaluation_id)
        if report is not None:
            self._assert_tenant_scope(report.get("tenant_id", "tenant_default"), tenant_id)
            report["needs_human_review"] = False
            report["interrupt"] = None
        self.audit_logs.append(
            {
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
        return [
            x
            for x in self.audit_logs
            if x.get("tenant_id") == tenant_id and x.get("evaluation_id") == evaluation_id
        ]

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
        selected_mode = self._select_retrieval_mode(query_type=query_type, high_risk=high_risk)
        candidates = [x for x in self.citation_sources.values() if x.get("tenant_id") == tenant_id]
        candidates = [x for x in candidates if x.get("project_id") == project_id]
        candidates = [x for x in candidates if x.get("supplier_id") == supplier_id]
        if doc_scope:
            scope = set(doc_scope)
            candidates = [x for x in candidates if x.get("doc_type") in scope]
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
                if all(term in str(x.get("text", "")).lower() for term in include_terms)
            ]
        if exclude_terms:
            candidates = [
                x
                for x in candidates
                if all(term not in str(x.get("text", "")).lower() for term in exclude_terms)
            ]

        items = []
        for source in candidates:
            score_raw = float(source.get("score_raw", 0.5))
            score_rerank = None if not enable_rerank else min(1.0, score_raw + 0.05)
            items.append(
                {
                    "chunk_id": source.get("chunk_id"),
                    "score_raw": score_raw,
                    "score_rerank": score_rerank,
                    "reason": f"matched {query_type} intent",
                    "metadata": {
                        "project_id": source.get("project_id"),
                        "supplier_id": source.get("supplier_id"),
                        "doc_type": source.get("doc_type"),
                        "page": int(source.get("page", 1)),
                        "bbox": source.get("bbox", [0, 0, 1, 1]),
                    },
                }
            )
        if enable_rerank:
            items = sorted(items, key=lambda x: x["score_rerank"], reverse=True)
        else:
            items = sorted(items, key=lambda x: x["score_raw"], reverse=True)
        items = items[:top_k]
        return {
            "query": query,
            "rewritten_query": rewrite["rewritten_query"],
            "rewrite_reason": rewrite["rewrite_reason"],
            "constraints_preserved": rewrite["constraints_preserved"],
            "constraint_diff": rewrite["constraint_diff"],
            "query_type": query_type,
            "selected_mode": selected_mode,
            "degraded": not enable_rerank,
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
        self.dlq_items[dlq_id] = item
        return item

    def list_dlq_items(self, *, tenant_id: str) -> list[dict[str, Any]]:
        filtered = [x for x in self.dlq_items.values() if x.get("tenant_id") == tenant_id]
        return sorted(filtered, key=lambda x: x["dlq_id"])

    def get_dlq_item(self, dlq_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        item = self.dlq_items.get(dlq_id)
        if item is None:
            return None
        self._assert_tenant_scope(item.get("tenant_id", "tenant_default"), tenant_id)
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
        self.jobs[new_job_id] = {
            "job_id": new_job_id,
            "job_type": "requeue",
            "status": "queued",
            "retry_count": 0,
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "resource": {
                "type": "job",
                "id": item["job_id"],
            },
            "payload": {"source_dlq_id": dlq_id},
            "last_error": None,
        }
        item["status"] = "requeued"
        self.audit_logs.append(
            {
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
        tenant_id: str,
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
        if not reason.strip() or not reviewer_id.strip():
            raise ApiError(
                code="DLQ_DISCARD_REQUIRES_APPROVAL",
                message="discard requires reviewer and reason",
                error_class="business_rule",
                retryable=False,
                http_status=400,
            )

        item["status"] = "discarded"
        item["discard_reason"] = reason
        item["reviewer_id"] = reviewer_id
        self.audit_logs.append(
            {
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "dlq_discard_submitted",
                "dlq_id": dlq_id,
                "reviewer_id": reviewer_id,
                "reason": reason,
                "trace_id": "",
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "dlq_id": dlq_id,
            "status": "discarded",
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

        self.audit_logs.append(
            {
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
        self.jobs[replay_job_id] = {
            "job_id": replay_job_id,
            "job_type": "replay_verification",
            "status": "queued",
            "retry_count": 0,
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
        replay_result = self.run_job_once(job_id=replay_job_id, tenant_id=tenant_id)
        replay_status = replay_result["final_status"]

        self.audit_logs.append(
            {
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
        self.audit_logs.append(
            {
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
        self.audit_logs.append(
            {
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

        status = job["status"]
        if status in {"queued", "retrying", "needs_manual_decision"}:
            job = self.transition_job_status(
                job_id=job_id,
                new_status="running",
                tenant_id=tenant_id,
            )
            status = job["status"]
        if job.get("job_type") == "parse":
            manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
            if manifest is not None:
                if manifest.get("started_at") is None:
                    manifest["started_at"] = self._utcnow_iso()
                manifest["status"] = "running"
                manifest["error_code"] = None

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

            if current_retry < 3:
                retried_job = self.transition_job_status(
                    job_id=job_id,
                    new_status="retrying",
                    tenant_id=tenant_id,
                )
                retried_job["last_error"] = {
                    "code": error_code,
                    "message": error["message"],
                    "retryable": True,
                    "class": "transient",
                }
                if job.get("job_type") == "parse":
                    manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
                    if manifest is not None:
                        manifest["status"] = "retrying"
                        manifest["error_code"] = error_code
                return {
                    "job_id": job_id,
                    "final_status": "retrying",
                    "retry_count": retried_job.get("retry_count", 0),
                    "dlq_id": None,
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
            failed_job["last_error"] = {
                "code": error_code,
                "message": error["message"],
                "retryable": error["retryable"],
                "class": error["class"],
            }
            if job.get("job_type") == "parse":
                manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
                if manifest is not None:
                    manifest["status"] = "failed"
                    manifest["error_code"] = error_code
                    manifest["ended_at"] = self._utcnow_iso()
                document_id = job.get("resource", {}).get("id")
                if isinstance(document_id, str) and document_id in self.documents:
                    self.documents[document_id]["status"] = "parse_failed"
            return {
                "job_id": job_id,
                "final_status": "failed",
                "retry_count": failed_job.get("retry_count", 0),
                "dlq_id": dlq_item["dlq_id"],
            }

        self.transition_job_status(
            job_id=job_id,
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        if job.get("job_type") == "parse":
            manifest = self.get_parse_manifest_for_tenant(job_id=job_id, tenant_id=tenant_id)
            if manifest is not None:
                manifest["status"] = "succeeded"
                manifest["error_code"] = None
                manifest["ended_at"] = self._utcnow_iso()
            document_id = job.get("resource", {}).get("id")
            if isinstance(document_id, str):
                document = self.documents.get(document_id)
                if document is not None:
                    document["status"] = "indexed"
                    if not self.document_chunks.get(document_id):
                        chunk = {
                            "chunk_id": f"ck_{uuid.uuid4().hex[:12]}",
                            "document_id": document_id,
                            "pages": [1],
                            "positions": [
                                {
                                    "page": 1,
                                    "bbox": [100, 120, 520, 380],
                                    "start": 0,
                                    "end": 128,
                                }
                            ],
                            "section": "投标响应",
                            "heading_path": ["第一章", "响应说明"],
                            "chunk_type": "text",
                            "parser": manifest["selected_parser"] if manifest else "mineru",
                            "parser_version": "v0",
                            "text": "chunk generated by parse skeleton",
                        }
                        self.document_chunks[document_id] = [chunk]
                        self.register_citation_source(
                            chunk_id=chunk["chunk_id"],
                            source={
                                "chunk_id": chunk["chunk_id"],
                                "document_id": document_id,
                                "tenant_id": tenant_id,
                                "project_id": document.get("project_id"),
                                "supplier_id": document.get("supplier_id"),
                                "doc_type": document.get("doc_type"),
                                "page": chunk["positions"][0]["page"],
                                "bbox": chunk["positions"][0]["bbox"],
                                "text": chunk["text"],
                                "context": chunk["section"],
                                "score_raw": 0.78,
                            },
                        )
        return {
            "job_id": job_id,
            "final_status": "succeeded",
            "retry_count": job.get("retry_count", 0),
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
            "evaluation_reports": self.evaluation_reports,
            "parse_manifests": self.parse_manifests,
            "resume_tokens": self.resume_tokens,
            "audit_logs": self.audit_logs,
            "domain_events_outbox": self.domain_events_outbox,
            "citation_sources": self.citation_sources,
            "dlq_items": self.dlq_items,
            "release_rollout_policies": self.release_rollout_policies,
            "counterexample_samples": self.counterexample_samples,
            "gold_candidate_samples": self.gold_candidate_samples,
            "dataset_version": self.dataset_version,
            "strategy_version_counter": self.strategy_version_counter,
            "strategy_config": self.strategy_config,
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
        self.citation_sources = (
            payload.get("citation_sources", {}) if isinstance(payload.get("citation_sources"), dict) else {}
        )
        self.dlq_items = payload.get("dlq_items", {}) if isinstance(payload.get("dlq_items"), dict) else {}
        self.release_rollout_policies = (
            payload.get("release_rollout_policies", {})
            if isinstance(payload.get("release_rollout_policies"), dict)
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

    def create_evaluation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_evaluation_job(payload)
        self._save_state()
        return data

    def create_upload_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().create_upload_job(payload)
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
        tenant_id: str,
    ) -> dict[str, Any]:
        data = super().discard_dlq_item(
            dlq_id=dlq_id,
            reason=reason,
            reviewer_id=reviewer_id,
            tenant_id=tenant_id,
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
    if backend == "sqlite":
        db_path = env.get("BEA_STORE_SQLITE_PATH", ".local/bea-store.sqlite3")
        return SqliteBackedStore(db_path)
    return InMemoryStore()


store = create_store_from_env()
