from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.errors import ApiError


@dataclass
class IdempotencyRecord:
    fingerprint: str
    data: dict[str, Any]


class StoreAdminMixin:
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

    def create_upload_job(
        self,
        payload: dict[str, Any],
        *,
        file_bytes: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "tenant_default")
        file_sha256 = payload.get("file_sha256")

        # Check for duplicate by file_sha256
        if file_sha256:
            existing = self.find_document_by_file_sha256(
                tenant_id=tenant_id,
                file_sha256=file_sha256,
            )
            if existing:
                # Return existing document info instead of creating duplicate
                existing_job = self.jobs.get(existing["document_id"])
                return {
                    "document_id": existing["document_id"],
                    "job_id": existing_job.get("job_id") if existing_job else None,
                    "status": "duplicate",
                    "existing_status": existing.get("status"),
                    "next": f"/api/v1/documents/{existing['document_id']}",
                }

        document_id = f"doc_{uuid.uuid4().hex[:12]}"
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

    def find_document_by_file_sha256(
        self, *, tenant_id: str, file_sha256: str
    ) -> dict[str, Any] | None:
        """Find document by file SHA256 hash for deduplication."""
        for doc in self.documents.values():
            if doc.get("tenant_id") == tenant_id and doc.get("file_sha256") == file_sha256:
                return doc
        return None

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
            1 for item in self.dlq_items.values() if item.get("tenant_id") == tenant_id and item.get("status") == "open"
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
                error_info = {
                    "code": error_code,
                    "message": error["message"],
                    "retryable": True,
                    "class": "transient",
                    "occurred_at": self._utcnow_iso(),
                }
                retried_job["last_error"] = error_info
                # SSOT: append to errors array
                retried_job.setdefault("errors", []).append(error_info)
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
            error_info = {
                "code": error_code,
                "message": error["message"],
                "retryable": error["retryable"],
                "class": error["class"],
                "occurred_at": self._utcnow_iso(),
            }
            failed_job["last_error"] = error_info
            # SSOT: append to errors array
            failed_job.setdefault("errors", []).append(error_info)
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
                    existing_chunks = self.list_document_chunks_for_tenant(
                        document_id=document_id,
                        tenant_id=tenant_id,
                    )
                    if not existing_chunks:
                        parsed_chunks = self._parse_document_file(
                            document=document,
                            document_id=document_id,
                            tenant_id=tenant_id,
                            manifest=manifest,
                        )
                        if manifest is not None and parsed_chunks:
                            manifest["content_source"] = parsed_chunks[0].get("content_source", "unknown")
                        persisted_chunks = self._persist_document_chunks(
                            tenant_id=tenant_id,
                            document_id=document_id,
                            chunks=parsed_chunks,
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
                    # SSOT: vectors indexed -> document status = indexed
                    document["status"] = "indexed"
                    self._persist_document(document=document)
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
