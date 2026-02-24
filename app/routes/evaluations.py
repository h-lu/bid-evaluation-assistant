from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.errors import ApiError
from app.routes._deps import tenant_id_from_request, trace_id_from_request
from app.schemas import CreateEvaluationRequest, ResumeRequest, success_envelope
from app.store import store

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


@router.post("/evaluations")
def create_evaluation(
    payload: CreateEvaluationRequest,
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

    data = store.run_idempotent(
        endpoint="POST:/api/v1/evaluations",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=payload.model_dump(mode="json"),
        execute=lambda: store.create_evaluation_job(
            {
                **payload.model_dump(mode="json"),
                "trace_id": trace_id_from_request(request),
                "tenant_id": tenant_id_from_request(request),
            }
        ),
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


@router.post("/evaluations/{evaluation_id}/resume")
def resume_evaluation(
    evaluation_id: str,
    payload: ResumeRequest,
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
    reviewer_id = payload.editor.reviewer_id.strip()
    if not reviewer_id:
        raise ApiError(
            code="WF_INTERRUPT_REVIEWER_REQUIRED",
            message="reviewer_id is required for resume",
            error_class="business_rule",
            retryable=False,
            http_status=400,
        )

    req_payload = payload.model_dump(mode="json")

    def _execute_resume():
        if not store.consume_resume_token(
            evaluation_id=evaluation_id,
            resume_token=payload.resume_token,
            tenant_id=tenant_id_from_request(request),
        ):
            raise ApiError(
                code="WF_INTERRUPT_RESUME_INVALID",
                message="resume token expired or mismatched",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        return store.create_resume_job(
            evaluation_id=evaluation_id,
            payload={
                **req_payload,
                "trace_id": trace_id_from_request(request),
                "tenant_id": tenant_id_from_request(request),
            },
        )

    data = store.run_idempotent(
        endpoint=f"POST:/api/v1/evaluations/{evaluation_id}/resume",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=req_payload,
        execute=_execute_resume,
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


@router.get("/evaluations/{evaluation_id}/report")
def get_evaluation_report(evaluation_id: str, request: Request):
    report = store.get_evaluation_report_for_tenant(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id_from_request(request),
    )
    if report is None:
        raise ApiError(
            code="EVALUATION_REPORT_NOT_FOUND",
            message="evaluation report not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(report, trace_id_from_request(request))


@router.get("/evaluations/{evaluation_id}/audit-logs")
def list_evaluation_audit_logs(evaluation_id: str, request: Request):
    report = store.get_evaluation_report_for_tenant(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id_from_request(request),
    )
    if report is None:
        raise ApiError(
            code="EVALUATION_REPORT_NOT_FOUND",
            message="evaluation report not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    items = store.list_audit_logs_for_evaluation(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id_from_request(request),
    )
    return success_envelope(
        {
            "evaluation_id": evaluation_id,
            "items": items,
            "total": len(items),
        },
        trace_id_from_request(request),
    )
