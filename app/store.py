from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.errors import ApiError


@dataclass
class IdempotencyRecord:
    fingerprint: str
    data: dict[str, Any]


class InMemoryStore:
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
        self.evaluation_reports: dict[str, dict[str, Any]] = {}
        self.parse_manifests: dict[str, dict[str, Any]] = {}
        self.resume_tokens: dict[str, str] = {}
        self.citation_sources: dict[str, dict[str, Any]] = {}
        self.dlq_items: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        self.idempotency_records.clear()
        self.jobs.clear()
        self.documents.clear()
        self.evaluation_reports.clear()
        self.parse_manifests.clear()
        self.resume_tokens.clear()
        self.citation_sources.clear()
        self.dlq_items.clear()

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
            "total_score": 88.5,
            "confidence": 0.78,
            "risk_level": "medium",
            "criteria_results": [
                {
                    "criteria_id": "delivery",
                    "score": 18.0,
                    "max_score": 20.0,
                    "hard_pass": True,
                    "reason": "delivery period satisfies baseline",
                    "citations": ["ck_eval_stub_1"],
                    "confidence": 0.81,
                }
            ],
            "citations": ["ck_eval_stub_1"],
            "needs_human_review": False,
            "trace_id": payload.get("trace_id") or "",
            "tenant_id": tenant_id,
        }
        return {
            "evaluation_id": evaluation_id,
            "job_id": job_id,
            "status": "queued",
        }

    def create_upload_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        job_id = f"job_{uuid.uuid4().hex[:12]}"
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
        self.jobs[job_id] = {
            "job_id": job_id,
            "job_type": "upload",
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
        return {
            "document_id": document_id,
            "job_id": job_id,
            "status": "queued",
            "next": f"/api/v1/jobs/{job_id}",
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
        return {
            "document_id": document_id,
            "job_id": job_id,
            "status": "queued",
        }

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
            "risk_level": report["risk_level"],
            "criteria_results": report["criteria_results"],
            "citations": report["citations"],
            "needs_human_review": report["needs_human_review"],
            "trace_id": report["trace_id"],
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

    def register_resume_token(self, *, evaluation_id: str, resume_token: str) -> None:
        self.resume_tokens[evaluation_id] = resume_token

    def validate_resume_token(self, *, evaluation_id: str, resume_token: str) -> bool:
        return self.resume_tokens.get(evaluation_id) == resume_token

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
        return {
            "evaluation_id": evaluation_id,
            "job_id": job_id,
            "status": "queued",
        }

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

    def run_job_once(
        self,
        *,
        job_id: str,
        tenant_id: str,
        force_fail: bool = False,
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
            return {
                "job_id": job_id,
                "final_status": "failed",
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
        return {
            "job_id": job_id,
            "final_status": "succeeded",
            "dlq_id": None,
        }


store = InMemoryStore()
