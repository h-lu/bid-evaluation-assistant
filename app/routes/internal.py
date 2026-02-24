from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Body, Header, Query, Request

from app.cost_gates import evaluate_cost_gate
from app.errors import ApiError
from app.performance_gates import evaluate_performance_gate
from app.quality_gates import evaluate_quality_gate
from app.routes._deps import (
    append_tool_audit_log,
    require_approval,
    tenant_id_from_request,
    trace_id_from_request,
)
from app.schemas import (
    CostGateEvaluateRequest,
    DataFeedbackRunRequest,
    InternalTransitionRequest,
    LegalHoldImposeRequest,
    LegalHoldReleaseRequest,
    PerformanceGateEvaluateRequest,
    QualityGateEvaluateRequest,
    RollbackExecuteRequest,
    RolloutDecisionRequest,
    RolloutPlanRequest,
    SecurityGateEvaluateRequest,
    StorageCleanupRequest,
    StrategyTuningApplyRequest,
    success_envelope,
)
from app.security_gates import evaluate_security_gate
from app.store import store
from app.tools_registry import execute_tool, require_tool

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


def _require_internal_debug(x_internal_debug: str | None) -> None:
    if x_internal_debug != "true":
        raise ApiError(
            code="AUTH_FORBIDDEN",
            message="internal endpoint forbidden",
            error_class="security_sensitive",
            retryable=False,
            http_status=403,
        )


def _job_type_from_event_type(event_type: str) -> str:
    if event_type.endswith(".job.created"):
        return event_type.split(".", maxsplit=1)[0]
    if event_type.endswith(".created"):
        return event_type.rsplit(".", maxsplit=1)[0]
    return "unknown"


# ---------------------------------------------------------------------------
# Jobs internal
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/transition")
def internal_transition_job(
    job_id: str,
    payload: InternalTransitionRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    updated = store.transition_job_status(
        job_id=job_id,
        new_status=payload.new_status,
        tenant_id=tenant_id_from_request(request),
    )
    return success_envelope(
        {
            "job_id": updated["job_id"],
            "status": updated["status"],
            "retry_count": updated.get("retry_count", 0),
        },
        trace_id_from_request(request),
    )


@router.post("/jobs/{job_id}/run")
def internal_run_job(
    job_id: str,
    request: Request,
    force_fail: bool = Query(default=False),
    transient_fail: bool = Query(default=False),
    error_code: str | None = Query(default=None),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    result = store.run_job_once(
        job_id=job_id,
        tenant_id=tenant_id_from_request(request),
        force_fail=force_fail,
        transient_fail=transient_fail,
        force_error_code=error_code,
    )
    return success_envelope(result, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Parse manifests
# ---------------------------------------------------------------------------


@router.get("/parse-manifests/{job_id}")
def internal_get_parse_manifest(
    job_id: str,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    manifest = store.get_parse_manifest_for_tenant(
        job_id=job_id,
        tenant_id=tenant_id_from_request(request),
    )
    if manifest is None:
        raise ApiError(
            code="DOC_PARSE_OUTPUT_NOT_FOUND",
            message="parse manifest not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(manifest, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@router.get("/workflows/{thread_id}/checkpoints")
def internal_list_workflow_checkpoints(
    thread_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    items = store.list_workflow_checkpoints(
        thread_id=thread_id,
        tenant_id=tenant_id_from_request(request),
        limit=limit,
    )
    return success_envelope(
        {"thread_id": thread_id, "items": items, "total": len(items)},
        trace_id_from_request(request),
    )


# ---------------------------------------------------------------------------
# Quality / Performance / Security / Cost gates
# ---------------------------------------------------------------------------


@router.post("/quality-gates/evaluate")
def internal_evaluate_quality_gate(
    payload: QualityGateEvaluateRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = evaluate_quality_gate(
        dataset_id=payload.dataset_id,
        ragas=payload.metrics.ragas.model_dump(mode="json"),
        deepeval=payload.metrics.deepeval.model_dump(mode="json"),
        citation=payload.metrics.citation.model_dump(mode="json"),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/performance-gates/evaluate")
def internal_evaluate_performance_gate(
    payload: PerformanceGateEvaluateRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = evaluate_performance_gate(
        dataset_id=payload.dataset_id,
        metrics=payload.metrics.model_dump(mode="json"),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/security-gates/evaluate")
def internal_evaluate_security_gate(
    payload: SecurityGateEvaluateRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = evaluate_security_gate(
        dataset_id=payload.dataset_id,
        metrics=payload.metrics.model_dump(mode="json"),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/cost-gates/evaluate")
def internal_evaluate_cost_gate(
    payload: CostGateEvaluateRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = evaluate_cost_gate(
        dataset_id=payload.dataset_id,
        metrics=payload.metrics.model_dump(mode="json"),
    )
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Release management
# ---------------------------------------------------------------------------


@router.post("/release/rollout/plan")
def internal_plan_release_rollout(
    payload: RolloutPlanRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.upsert_rollout_policy(
        release_id=payload.release_id,
        tenant_whitelist=list(payload.tenant_whitelist),
        enabled_project_sizes=list(payload.enabled_project_sizes),
        high_risk_hitl_enforced=payload.high_risk_hitl_enforced,
        tenant_id=tenant_id_from_request(request),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/release/rollout/decision")
def internal_decide_release_rollout(
    payload: RolloutDecisionRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.decide_rollout(
        release_id=payload.release_id,
        tenant_id=payload.tenant_id,
        project_size=payload.project_size,
        high_risk=payload.high_risk,
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/release/rollback/execute")
def internal_execute_release_rollback(
    payload: RollbackExecuteRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.execute_rollback(
        release_id=payload.release_id,
        consecutive_threshold=payload.consecutive_threshold,
        breaches=[x.model_dump(mode="json") for x in payload.breaches],
        tenant_id=tenant_id_from_request(request),
        trace_id=trace_id_from_request(request),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/release/replay/e2e")
def internal_run_release_replay_e2e(
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    release_id = str(payload.get("release_id") or "").strip()
    project_id = str(payload.get("project_id") or "").strip()
    supplier_id = str(payload.get("supplier_id") or "").strip()
    if not release_id or not project_id or not supplier_id:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="release_id, project_id and supplier_id are required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    doc_type = str(payload.get("doc_type") or "bid").strip() or "bid"
    force_hitl = bool(payload.get("force_hitl", True))
    decision = str(payload.get("decision") or "approve").strip() or "approve"
    data = store.run_release_replay_e2e(
        release_id=release_id,
        tenant_id=tenant_id_from_request(request),
        trace_id=trace_id_from_request(request),
        project_id=project_id,
        supplier_id=supplier_id,
        doc_type=doc_type,
        force_hitl=force_hitl,
        decision=decision,
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/release/readiness/evaluate")
def internal_evaluate_release_readiness(
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    release_id = str(payload.get("release_id") or "").strip()
    if not release_id:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="release_id is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    if "replay_passed" not in payload:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="replay_passed is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    replay_passed = bool(payload.get("replay_passed"))
    dataset_version = str(payload.get("dataset_version") or "").strip() or None
    gate_results_obj = payload.get("gate_results", {})
    gate_results: dict[str, Any] = gate_results_obj if isinstance(gate_results_obj, dict) else {}
    data = store.evaluate_release_readiness(
        release_id=release_id,
        tenant_id=tenant_id_from_request(request),
        trace_id=trace_id_from_request(request),
        dataset_version=dataset_version,
        replay_passed=replay_passed,
        gate_results=gate_results,
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/release/pipeline/execute")
def internal_execute_release_pipeline(
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    release_id = str(payload.get("release_id") or "").strip()
    if not release_id:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="release_id is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    replay_passed = bool(payload.get("replay_passed", False))
    dataset_version = str(payload.get("dataset_version") or "").strip() or None
    gate_results_obj = payload.get("gate_results", {})
    gate_results: dict[str, Any] = gate_results_obj if isinstance(gate_results_obj, dict) else {}
    data = store.execute_release_pipeline(
        release_id=release_id,
        tenant_id=tenant_id_from_request(request),
        trace_id=trace_id_from_request(request),
        dataset_version=dataset_version,
        replay_passed=replay_passed,
        gate_results=gate_results,
    )
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Tools registry
# ---------------------------------------------------------------------------


@router.get("/tools/registry")
def internal_list_tool_registry(
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    from app.tools_registry import list_tool_specs

    return success_envelope({"items": list_tool_specs()}, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Ops metrics & data feedback & strategy tuning
# ---------------------------------------------------------------------------


@router.get("/ops/metrics/summary")
def internal_get_ops_metrics_summary(
    request: Request,
    queue_name: str = Query(default="jobs"),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    summary = store.summarize_ops_metrics(tenant_id=tenant_id)
    queue_backend = request.app.state.queue_backend
    summary["worker"]["queue_name"] = queue_name
    summary["worker"]["queue_pending"] = queue_backend.pending_count(
        tenant_id=tenant_id,
        queue_name=queue_name,
    )
    return success_envelope(summary, trace_id_from_request(request))


@router.post("/ops/data-feedback/run")
def internal_run_data_feedback(
    payload: DataFeedbackRunRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.run_data_feedback(
        release_id=payload.release_id,
        dlq_ids=list(payload.dlq_ids),
        version_bump=payload.version_bump,
        include_manual_override_candidates=payload.include_manual_override_candidates,
        tenant_id=tenant_id_from_request(request),
        trace_id=trace_id_from_request(request),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/ops/strategy-tuning/apply")
def internal_apply_strategy_tuning(
    payload: StrategyTuningApplyRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    x_reviewer_id: str | None = Header(default=None, alias="x-reviewer-id"),
    x_reviewer_id_2: str | None = Header(default=None, alias="x-reviewer-id-2"),
    x_approval_reason: str | None = Header(default=None, alias="x-approval-reason"),
):
    _require_internal_debug(x_internal_debug)
    require_approval(
        action="strategy_tuning_apply",
        request=request,
        reviewer_id=x_reviewer_id or "",
        reviewer_id_2=x_reviewer_id_2 or "",
        reason=x_approval_reason or "",
    )
    tool_spec = require_tool("strategy_tuning_apply")
    req_payload = {
        "release_id": payload.release_id,
        "selector": payload.selector.model_dump(mode="json"),
        "score_calibration": payload.score_calibration.model_dump(mode="json"),
        "tool_policy": payload.tool_policy.model_dump(mode="json"),
    }
    started = time.monotonic()
    try:
        data = execute_tool(
            tool_spec,
            input_payload=req_payload,
            invoke=lambda: store.apply_strategy_tuning(
                release_id=payload.release_id,
                selector=payload.selector.model_dump(mode="json"),
                score_calibration=payload.score_calibration.model_dump(mode="json"),
                tool_policy=payload.tool_policy.model_dump(mode="json"),
                tenant_id=tenant_id_from_request(request),
                trace_id=trace_id_from_request(request),
            ),
        )
    except ApiError as exc:
        append_tool_audit_log(
            request=request,
            tool_name=tool_spec.name,
            risk_level=tool_spec.risk_level,
            input_payload=req_payload,
            result_summary=exc.code,
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise
    except Exception:
        append_tool_audit_log(
            request=request,
            tool_name=tool_spec.name,
            risk_level=tool_spec.risk_level,
            input_payload=req_payload,
            result_summary="unexpected_error",
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise
    append_tool_audit_log(
        request=request,
        tool_name=tool_spec.name,
        risk_level=tool_spec.risk_level,
        input_payload=req_payload,
        result_summary="strategy_applied",
        status="success",
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Audit integrity
# ---------------------------------------------------------------------------


@router.get("/audit/integrity")
def internal_verify_audit_integrity(
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    result = store.verify_audit_integrity(tenant_id=tenant_id_from_request(request))
    if not result.get("valid", False):
        raise ApiError(
            code="AUDIT_INTEGRITY_BROKEN",
            message="audit log integrity check failed",
            error_class="security_sensitive",
            retryable=False,
            http_status=409,
        )
    return success_envelope(result, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Legal hold
# ---------------------------------------------------------------------------


@router.post("/legal-hold/impose")
def internal_impose_legal_hold(
    payload: LegalHoldImposeRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.impose_legal_hold(
        tenant_id=tenant_id_from_request(request),
        object_type=payload.object_type,
        object_id=payload.object_id,
        reason=payload.reason,
        imposed_by=payload.imposed_by,
        trace_id=trace_id_from_request(request),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.get("/legal-hold/items")
def internal_list_legal_hold_items(
    request: Request,
    status: str | None = Query(default=None),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    items = store.list_legal_holds(tenant_id=tenant_id_from_request(request), status=status)
    return success_envelope({"items": items, "total": len(items)}, trace_id_from_request(request))


@router.post("/legal-hold/{hold_id}/release")
def internal_release_legal_hold(
    hold_id: str,
    payload: LegalHoldReleaseRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    require_approval(
        action="legal_hold_release",
        request=request,
        reviewer_id=payload.reviewer_id,
        reviewer_id_2=payload.reviewer_id_2,
        reason=payload.reason,
    )
    tool_spec = require_tool("legal_hold_release")
    req_payload = payload.model_dump(mode="json")
    started = time.monotonic()
    try:
        data = execute_tool(
            tool_spec,
            input_payload={"hold_id": hold_id, **req_payload},
            invoke=lambda: store.release_legal_hold(
                hold_id=hold_id,
                tenant_id=tenant_id_from_request(request),
                reason=payload.reason,
                reviewer_id=payload.reviewer_id,
                reviewer_id_2=payload.reviewer_id_2,
                trace_id=trace_id_from_request(request),
            ),
        )
    except ApiError as exc:
        append_tool_audit_log(
            request=request,
            tool_name=tool_spec.name,
            risk_level=tool_spec.risk_level,
            input_payload={"hold_id": hold_id, **req_payload},
            result_summary=exc.code,
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise
    except Exception:
        append_tool_audit_log(
            request=request,
            tool_name=tool_spec.name,
            risk_level=tool_spec.risk_level,
            input_payload={"hold_id": hold_id, **req_payload},
            result_summary="unexpected_error",
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise
    append_tool_audit_log(
        request=request,
        tool_name=tool_spec.name,
        risk_level=tool_spec.risk_level,
        input_payload={"hold_id": hold_id, **req_payload},
        result_summary="released",
        status="success",
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Storage cleanup
# ---------------------------------------------------------------------------


@router.post("/storage/cleanup")
def internal_execute_storage_cleanup(
    payload: StorageCleanupRequest,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    data = store.execute_storage_cleanup(
        tenant_id=tenant_id_from_request(request),
        object_type=payload.object_type,
        object_id=payload.object_id,
        reason=payload.reason,
        trace_id=trace_id_from_request(request),
    )
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------


@router.get("/outbox/events")
def internal_list_outbox_events(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    items = store.list_outbox_events(tenant_id=tenant_id, status=status, limit=limit)
    return success_envelope(
        {"items": items, "total": len(items)},
        trace_id_from_request(request),
    )


@router.post("/outbox/events/{event_id}/publish")
def internal_publish_outbox_event(
    event_id: str,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    event = store.mark_outbox_event_published(tenant_id=tenant_id, event_id=event_id)
    return success_envelope(event, trace_id_from_request(request))


@router.post("/outbox/relay")
def internal_relay_outbox_events(
    request: Request,
    queue_name: str = Query(default="jobs"),
    consumer_name: str = Query(default="default"),
    limit: int = Query(default=100, ge=1, le=1000),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    pending_events = store.list_outbox_events(tenant_id=tenant_id, status="pending", limit=limit)
    message_ids: list[str] = []
    for event in pending_events:
        existing_delivery = store.get_outbox_delivery(
            tenant_id=tenant_id,
            event_id=event["event_id"],
            consumer_name=consumer_name,
        )
        if existing_delivery is not None:
            store.mark_outbox_event_published(
                tenant_id=tenant_id,
                event_id=event["event_id"],
            )
            continue
        event_payload = event.get("payload", {})
        job_id = event_payload.get("job_id", event["aggregate_id"])
        job_type = event_payload.get("job_type", _job_type_from_event_type(event_type=event["event_type"]))
        trace_id = str(event_payload.get("trace_id") or "")
        if not trace_id:
            job = store.get_job(job_id=job_id)
            if job is not None and job.get("tenant_id") == tenant_id:
                trace_id = str(job.get("trace_id") or "")
        payload = {
            "event_id": event["event_id"],
            "job_id": job_id,
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "job_type": job_type,
            "attempt": int(event_payload.get("attempt", 0)),
            "consumer_name": consumer_name,
        }
        msg = queue_backend.enqueue(
            tenant_id=tenant_id,
            queue_name=queue_name,
            payload=payload,
        )
        message_ids.append(msg.message_id)
        store.mark_outbox_delivered(
            tenant_id=tenant_id,
            event_id=event["event_id"],
            consumer_name=consumer_name,
            message_id=msg.message_id,
        )
        store.mark_outbox_event_published(tenant_id=tenant_id, event_id=event["event_id"])
    data = {
        "published_count": len(message_ids),
        "queued_count": len(message_ids),
        "message_ids": message_ids,
        "consumer_name": consumer_name,
    }
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Queue operations
# ---------------------------------------------------------------------------


@router.post("/queue/{queue_name}/enqueue")
def internal_enqueue_queue_message(
    queue_name: str,
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    msg = queue_backend.enqueue(
        tenant_id=tenant_id,
        queue_name=queue_name,
        payload={**payload},
    )
    return success_envelope(
        {
            "message_id": msg.message_id,
            "tenant_id": msg.tenant_id,
            "queue_name": msg.queue_name,
            "attempt": msg.attempt,
            "payload": msg.payload,
        },
        trace_id_from_request(request),
    )


@router.post("/queue/{queue_name}/dequeue")
def internal_dequeue_queue_message(
    queue_name: str,
    request: Request,
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    msg = queue_backend.dequeue(tenant_id=tenant_id, queue_name=queue_name)
    if msg is None:
        data: dict[str, object] = {"message": None}
    else:
        data = {
            "message": {
                "message_id": msg.message_id,
                "tenant_id": msg.tenant_id,
                "queue_name": msg.queue_name,
                "attempt": msg.attempt,
                "payload": msg.payload,
            }
        }
    return success_envelope(data, trace_id_from_request(request))


@router.post("/queue/{queue_name}/ack")
def internal_ack_queue_message(
    queue_name: str,
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    message_id = str(payload.get("message_id") or "")
    if not message_id:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="message_id is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    try:
        queue_backend.ack(tenant_id=tenant_id, message_id=message_id)
    except RuntimeError:
        raise ApiError(
            code="TENANT_SCOPE_VIOLATION",
            message="tenant mismatch",
            error_class="security_sensitive",
            retryable=False,
            http_status=403,
        ) from None
    data = {"queue_name": queue_name, "message_id": message_id, "acked": True}
    return success_envelope(data, trace_id_from_request(request))


@router.post("/queue/{queue_name}/nack")
def internal_nack_queue_message(
    queue_name: str,
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    message_id = str(payload.get("message_id") or "")
    if not message_id:
        raise ApiError(
            code="REQ_VALIDATION_FAILED",
            message="message_id is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    requeue = bool(payload.get("requeue", True))
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    try:
        msg = queue_backend.nack(tenant_id=tenant_id, message_id=message_id, requeue=requeue)
    except RuntimeError:
        raise ApiError(
            code="TENANT_SCOPE_VIOLATION",
            message="tenant mismatch",
            error_class="security_sensitive",
            retryable=False,
            http_status=403,
        ) from None
    if msg is None:
        data: dict[str, object] = {"message": None}
    else:
        data = {
            "message": {
                "message_id": msg.message_id,
                "tenant_id": msg.tenant_id,
                "queue_name": msg.queue_name,
                "attempt": msg.attempt,
                "payload": msg.payload,
            }
        }
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Worker drain
# ---------------------------------------------------------------------------


@router.post("/worker/queues/{queue_name}/drain-once")
def internal_worker_drain_once(
    queue_name: str,
    request: Request,
    max_messages: int = Query(default=1, ge=1, le=100),
    force_fail: bool = Query(default=False),
    transient_fail: bool = Query(default=False),
    error_code: str | None = Query(default=None),
    x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
):
    _require_internal_debug(x_internal_debug)
    tenant_id = tenant_id_from_request(request)
    queue_backend = request.app.state.queue_backend
    processed = 0
    succeeded = 0
    retrying = 0
    failed = 0
    acked = 0
    requeued = 0
    message_ids: list[str] = []

    for _ in range(max_messages):
        msg = queue_backend.dequeue(tenant_id=tenant_id, queue_name=queue_name)
        if msg is None:
            break
        processed += 1
        message_ids.append(msg.message_id)
        job_id = str(msg.payload.get("job_id") or "")
        if not job_id:
            queue_backend.ack(tenant_id=tenant_id, message_id=msg.message_id)
            acked += 1
            continue
        result = store.run_job_once(
            job_id=job_id,
            tenant_id=tenant_id,
            force_fail=force_fail,
            transient_fail=transient_fail,
            force_error_code=error_code,
        )
        final_status = str(result.get("final_status"))
        if final_status == "retrying":
            retry_after_ms = int(result.get("retry_after_ms", 0) or 0)
            queue_backend.nack(
                tenant_id=tenant_id,
                message_id=msg.message_id,
                requeue=True,
                delay_ms=max(0, retry_after_ms),
            )
            requeued += 1
            retrying += 1
            continue
        queue_backend.ack(tenant_id=tenant_id, message_id=msg.message_id)
        acked += 1
        if final_status == "succeeded":
            succeeded += 1
        else:
            failed += 1

    data = {
        "queue_name": queue_name,
        "processed": processed,
        "succeeded": succeeded,
        "retrying": retrying,
        "failed": failed,
        "acked": acked,
        "requeued": requeued,
        "message_ids": message_ids,
    }
    return success_envelope(data, trace_id_from_request(request))
