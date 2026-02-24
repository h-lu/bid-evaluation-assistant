from __future__ import annotations

import time

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from app.errors import ApiError
from app.routes._deps import (
    append_tool_audit_log,
    require_approval,
    tenant_id_from_request,
    trace_id_from_request,
)
from app.schemas import (
    DlqDiscardRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    RulePackCreateRequest,
    RulePackUpdateRequest,
    SupplierCreateRequest,
    SupplierUpdateRequest,
    success_envelope,
)
from app.store import store
from app.tools_registry import execute_tool, require_tool

router = APIRouter(prefix="/api/v1", tags=["admin"])

# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/projects")
def list_projects(request: Request):
    items = store.list_projects(tenant_id=tenant_id_from_request(request))
    return success_envelope({"items": items, "total": len(items)}, trace_id_from_request(request))


@router.post("/projects")
def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    req_payload = payload.model_dump()
    req_payload["tenant_id"] = tenant_id_from_request(request)
    data = store.run_idempotent(
        endpoint="POST:/api/v1/projects",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=req_payload,
        execute=lambda: store.create_project(payload=req_payload),
    )
    return JSONResponse(status_code=201, content=success_envelope(data, trace_id_from_request(request)))


@router.get("/projects/{project_id}")
def get_project(project_id: str, request: Request):
    project = store.get_project_for_tenant(project_id=project_id, tenant_id=tenant_id_from_request(request))
    if project is None:
        raise ApiError(
            code="PROJECT_NOT_FOUND",
            message="project not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(project, trace_id_from_request(request))


@router.put("/projects/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    request: Request,
):
    data = store.update_project(
        project_id=project_id,
        tenant_id=tenant_id_from_request(request),
        payload=payload.model_dump(exclude_unset=True),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    data = store.delete_project(project_id=project_id, tenant_id=tenant_id_from_request(request))
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


@router.get("/suppliers")
def list_suppliers(request: Request):
    items = store.list_suppliers(tenant_id=tenant_id_from_request(request))
    return success_envelope({"items": items, "total": len(items)}, trace_id_from_request(request))


@router.post("/suppliers")
def create_supplier(
    payload: SupplierCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    req_payload = payload.model_dump()
    req_payload["tenant_id"] = tenant_id_from_request(request)
    data = store.run_idempotent(
        endpoint="POST:/api/v1/suppliers",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=req_payload,
        execute=lambda: store.create_supplier(payload=req_payload),
    )
    return JSONResponse(status_code=201, content=success_envelope(data, trace_id_from_request(request)))


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: str, request: Request):
    supplier = store.get_supplier_for_tenant(supplier_id=supplier_id, tenant_id=tenant_id_from_request(request))
    if supplier is None:
        raise ApiError(
            code="SUPPLIER_NOT_FOUND",
            message="supplier not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(supplier, trace_id_from_request(request))


@router.put("/suppliers/{supplier_id}")
def update_supplier(
    supplier_id: str,
    payload: SupplierUpdateRequest,
    request: Request,
):
    data = store.update_supplier(
        supplier_id=supplier_id,
        tenant_id=tenant_id_from_request(request),
        payload=payload.model_dump(exclude_unset=True),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: str, request: Request):
    data = store.delete_supplier(supplier_id=supplier_id, tenant_id=tenant_id_from_request(request))
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Rule Packs
# ---------------------------------------------------------------------------


@router.get("/rules")
def list_rule_packs(request: Request):
    items = store.list_rule_packs(tenant_id=tenant_id_from_request(request))
    return success_envelope({"items": items, "total": len(items)}, trace_id_from_request(request))


@router.post("/rules")
def create_rule_pack(
    payload: RulePackCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    req_payload = payload.model_dump()
    req_payload["tenant_id"] = tenant_id_from_request(request)
    data = store.run_idempotent(
        endpoint="POST:/api/v1/rules",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=req_payload,
        execute=lambda: store.create_rule_pack(payload=req_payload),
    )
    return JSONResponse(status_code=201, content=success_envelope(data, trace_id_from_request(request)))


@router.get("/rules/{rule_pack_version}")
def get_rule_pack(rule_pack_version: str, request: Request):
    rule_pack = store.get_rule_pack_for_tenant(
        rule_pack_version=rule_pack_version,
        tenant_id=tenant_id_from_request(request),
    )
    if rule_pack is None:
        raise ApiError(
            code="RULE_PACK_NOT_FOUND",
            message="rule pack not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(rule_pack, trace_id_from_request(request))


@router.put("/rules/{rule_pack_version}")
def update_rule_pack(
    rule_pack_version: str,
    payload: RulePackUpdateRequest,
    request: Request,
):
    data = store.update_rule_pack(
        rule_pack_version=rule_pack_version,
        tenant_id=tenant_id_from_request(request),
        payload=payload.model_dump(exclude_unset=True),
    )
    return success_envelope(data, trace_id_from_request(request))


@router.delete("/rules/{rule_pack_version}")
def delete_rule_pack(rule_pack_version: str, request: Request):
    data = store.delete_rule_pack(rule_pack_version=rule_pack_version, tenant_id=tenant_id_from_request(request))
    return success_envelope(data, trace_id_from_request(request))


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs")
def list_jobs(
    request: Request,
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    result = store.list_jobs(
        tenant_id=tenant_id_from_request(request),
        status=status,
        job_type=type,
        cursor=cursor,
        limit=limit,
    )
    items = []
    for job in result["items"]:
        items.append(
            {
                "job_id": job["job_id"],
                "job_type": job["job_type"],
                "status": job["status"],
                "retry_count": job.get("retry_count", 0),
                "thread_id": job.get("thread_id"),
                "trace_id": job.get("trace_id") or trace_id_from_request(request),
                "resource": job["resource"],
                "last_error": job.get("last_error"),
            }
        )
    return success_envelope(
        {"items": items, "total": result["total"], "next_cursor": result["next_cursor"]},
        trace_id_from_request(request),
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    job = store.get_job_for_tenant(job_id=job_id, tenant_id=tenant_id_from_request(request))
    if job is None:
        raise ApiError(
            code="JOB_NOT_FOUND",
            message="job not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )

    data = {
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "progress_pct": 0,
        "retry_count": job["retry_count"],
        "thread_id": job.get("thread_id"),
        "trace_id": job.get("trace_id") or trace_id_from_request(request),
        "resource": job["resource"],
        "last_error": job.get("last_error"),
    }
    return success_envelope(data, trace_id_from_request(request))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    payload = {"job_id": job_id}
    data = store.run_idempotent(
        endpoint=f"POST:/api/v1/jobs/{job_id}/cancel",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=payload,
        execute=lambda: store.cancel_job(
            job_id=job_id,
            tenant_id=tenant_id_from_request(request),
        ),
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


# ---------------------------------------------------------------------------
# DLQ
# ---------------------------------------------------------------------------


@router.get("/dlq/items")
def list_dlq_items(request: Request):
    items = store.list_dlq_items(tenant_id=tenant_id_from_request(request))
    return success_envelope({"items": items, "total": len(items)}, trace_id_from_request(request))


@router.post("/dlq/items/{item_id}/requeue")
def requeue_dlq_item(
    item_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    payload = {"dlq_id": item_id}
    data = store.run_idempotent(
        endpoint=f"POST:/api/v1/dlq/items/{item_id}/requeue",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=payload,
        execute=lambda: store.requeue_dlq_item(
            dlq_id=item_id,
            trace_id=trace_id_from_request(request),
            tenant_id=tenant_id_from_request(request),
        ),
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


@router.post("/dlq/items/{item_id}/discard")
def discard_dlq_item(
    item_id: str,
    payload: DlqDiscardRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    require_approval(
        action="dlq_discard",
        request=request,
        reviewer_id=payload.reviewer_id,
        reviewer_id_2=payload.reviewer_id_2,
        reason=payload.reason,
    )
    req_payload = payload.model_dump(mode="json")
    tool_spec = require_tool("dlq_discard")
    started = time.monotonic()
    try:
        data = store.run_idempotent(
            endpoint=f"POST:/api/v1/dlq/items/{item_id}/discard",
            tenant_id=tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=req_payload,
            execute=lambda: execute_tool(
                tool_spec,
                input_payload={"item_id": item_id, **req_payload},
                invoke=lambda: store.discard_dlq_item(
                    dlq_id=item_id,
                    reason=payload.reason,
                    reviewer_id=payload.reviewer_id,
                    reviewer_id_2=payload.reviewer_id_2,
                    tenant_id=tenant_id_from_request(request),
                    trace_id=trace_id_from_request(request),
                ),
            ),
        )
    except ApiError as exc:
        append_tool_audit_log(
            request=request,
            tool_name=tool_spec.name,
            risk_level=tool_spec.risk_level,
            input_payload={"item_id": item_id, **req_payload},
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
            input_payload={"item_id": item_id, **req_payload},
            result_summary="unexpected_error",
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise
    append_tool_audit_log(
        request=request,
        tool_name=tool_spec.name,
        risk_level=tool_spec.risk_level,
        input_payload={"item_id": item_id, **req_payload},
        result_summary="discarded",
        status="success",
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    return success_envelope(data, trace_id_from_request(request))
