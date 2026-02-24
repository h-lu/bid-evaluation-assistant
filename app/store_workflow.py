from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.errors import ApiError


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


class StoreWorkflowMixin:
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
                "errors": [],  # SSOT: errors array
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

    def get_workflow_state(self, *, evaluation_id: str, tenant_id: str) -> dict[str, Any] | None:
        """
        获取工作流状态对象（对齐 SSOT langgraph-agent-workflow-spec §2）。

        Returns:
            完整的工作流状态对象，包含 identity/trace/inputs/retrieval/scoring/review/output/runtime
        """
        report = self.get_evaluation_report_for_tenant(evaluation_id=evaluation_id, tenant_id=tenant_id)
        if report is None:
            return None

        thread_id = report.get("thread_id", "")
        job = self._find_job_by_evaluation_id(evaluation_id=evaluation_id, tenant_id=tenant_id)
        checkpoints = self.list_workflow_checkpoints(thread_id=thread_id, tenant_id=tenant_id) if thread_id else []

        # 从 checkpoints 提取各阶段信息
        retrieved_chunks = self._extract_retrieved_chunks(checkpoints)
        evidence_bundle = self._extract_evidence_bundle(checkpoints)
        query_bundle = self._extract_query_bundle(checkpoints)

        return {
            "identity": {
                "tenant_id": tenant_id,
                "project_id": report.get("project_id"),
                "evaluation_id": evaluation_id,
                "supplier_id": report.get("supplier_id"),
            },
            "trace": {
                "trace_id": report.get("trace_id"),
                "thread_id": thread_id,
                "checkpoint_id": checkpoints[-1].get("checkpoint_id") if checkpoints else None,
            },
            "inputs": {
                "query_bundle": query_bundle,
                "rule_pack_version": report.get("rule_pack_version"),
            },
            "retrieval": {
                "retrieved_chunks": retrieved_chunks,
                "evidence_bundle": evidence_bundle,
            },
            "scoring": {
                "criteria_scores": report.get("criteria_results", []),
                "total_score": report.get("total_score"),
                "confidence": report.get("confidence"),
                "citation_coverage": report.get("citation_coverage"),
            },
            "review": {
                "requires_human_review": report.get("needs_human_review"),
                "human_review_payload": report.get("interrupt"),
                "human_decision": None,
                "resume_token": report.get("interrupt", {}).get("resume_token") if report.get("interrupt") else None,
            },
            "output": {
                "report_payload": report,
                "status": job.get("status") if job else None,
            },
            "runtime": {
                "retry_count": job.get("retry_count", 0) if job else 0,
                "errors": self._collect_errors(job, checkpoints),
            },
        }

    def _find_job_by_evaluation_id(self, *, evaluation_id: str, tenant_id: str) -> dict[str, Any] | None:
        """通过 evaluation_id 查找对应的 job"""
        for job in self.jobs.values():
            if job.get("resource", {}).get("id") == evaluation_id:
                if job.get("tenant_id") == tenant_id:
                    return job
        return None

    def _extract_query_bundle(self, checkpoints: list[dict[str, Any]]) -> dict[str, Any] | None:
        """从 checkpoints 提取查询包"""
        for cp in checkpoints:
            if cp.get("node") == "load_context":
                return cp.get("payload", {}).get("query_bundle")
        return None

    def _extract_retrieved_chunks(self, checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """从 checkpoints 提取召回的 chunks"""
        for cp in checkpoints:
            if cp.get("node") == "retrieve_evidence":
                return cp.get("payload", {}).get("retrieved_chunks", [])
        return []

    def _extract_evidence_bundle(self, checkpoints: list[dict[str, Any]]) -> dict[str, Any] | None:
        """从 checkpoints 提取证据包"""
        for cp in checkpoints:
            if cp.get("node") == "retrieve_evidence":
                return cp.get("payload", {}).get("evidence_bundle")
        return None

    def _collect_errors(self, job: dict[str, Any] | None, checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """收集所有错误信息"""
        errors = []
        if job:
            # 从 job 的 errors 数组获取
            job_errors = job.get("errors", [])
            if job_errors:
                errors.extend(job_errors)
            # 兼容旧格式：从 last_error 获取
            elif job.get("last_error"):
                errors.append(job["last_error"])
        # 从 checkpoint 中收集错误
        for cp in checkpoints:
            if cp.get("status") == "error":
                error_info = cp.get("payload", {}).get("error")
                if error_info:
                    errors.append(error_info)
        return errors

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
            item for item in self.workflow_checkpoints[thread_id] if item.get("kind") != self.langgraph_checkpoint_kind
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
