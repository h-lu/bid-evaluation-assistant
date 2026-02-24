from __future__ import annotations

import uuid
from typing import Any

from app.errors import ApiError


class StoreOpsMixin:
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
