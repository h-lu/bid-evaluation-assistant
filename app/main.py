from __future__ import annotations

import hashlib
import uuid

from fastapi import FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import ApiError
from app.schemas import (
    CreateEvaluationRequest,
    DlqDiscardRequest,
    ResumeRequest,
    error_envelope,
    success_envelope,
)
from app.store import store


def _trace_id_from_request(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return trace_id
    return uuid.uuid4().hex


def _tenant_id_from_request(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return tenant_id
    return "tenant_default"


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    error_class: str,
    retryable: bool,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_envelope(
            code=code,
            message=message,
            error_class=error_class,
            retryable=retryable,
            trace_id=_trace_id_from_request(request),
        ),
    )

def create_app() -> FastAPI:
    app = FastAPI(title="Bid Evaluation Assistant API", version="0.1.0")

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        request.state.trace_id = request.headers.get("x-trace-id", uuid.uuid4().hex)
        request.state.tenant_id = request.headers.get("x-tenant-id", "tenant_default")
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return _error_response(
            request,
            code=exc.code,
            message=exc.message,
            error_class=exc.error_class,
            retryable=exc.retryable,
            status_code=exc.http_status,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return _error_response(
            request,
            code="REQ_VALIDATION_FAILED",
            message="invalid payload",
            error_class="validation",
            retryable=False,
            status_code=400,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _error_response(
                request,
                code="REQ_NOT_FOUND",
                message="resource not found",
                error_class="validation",
                retryable=False,
                status_code=404,
            )
        return _error_response(
            request,
            code="REQ_HTTP_ERROR",
            message=str(exc.detail),
            error_class="validation",
            retryable=False,
            status_code=exc.status_code,
        )

    @app.get("/healthz")
    def healthz(request: Request) -> dict[str, object]:
        return success_envelope({"status": "ok"}, _trace_id_from_request(request))

    @app.post("/api/v1/evaluations")
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
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=payload.model_dump(mode="json"),
            execute=lambda: store.create_evaluation_job(
                {
                    **payload.model_dump(mode="json"),
                    "trace_id": _trace_id_from_request(request),
                    "tenant_id": _tenant_id_from_request(request),
                }
            ),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.post("/api/v1/documents/upload")
    async def upload_document(
        request: Request,
        project_id: str = Form(...),
        supplier_id: str = Form(...),
        doc_type: str = Form(...),
        file: UploadFile = File(...),
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

        file_bytes = await file.read()
        payload = {
            "project_id": project_id,
            "supplier_id": supplier_id,
            "doc_type": doc_type,
            "filename": file.filename or "upload.bin",
            "file_sha256": hashlib.sha256(file_bytes).hexdigest(),
            "trace_id": _trace_id_from_request(request),
            "tenant_id": _tenant_id_from_request(request),
        }
        data = store.run_idempotent(
            endpoint="POST:/api/v1/documents/upload",
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=payload,
            execute=lambda: store.create_upload_job(payload),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.post("/api/v1/documents/{document_id}/parse")
    def parse_document(
        document_id: str,
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
        payload = {
            "document_id": document_id,
            "trace_id": _trace_id_from_request(request),
            "tenant_id": _tenant_id_from_request(request),
        }
        data = store.run_idempotent(
            endpoint=f"POST:/api/v1/documents/{document_id}/parse",
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=payload,
            execute=lambda: store.create_parse_job(document_id=document_id, payload=payload),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.get("/api/v1/jobs")
    def list_jobs(
        request: Request,
        status: str | None = Query(default=None),
        type: str | None = Query(default=None),
        cursor: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        result = store.list_jobs(
            tenant_id=_tenant_id_from_request(request),
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
                    "trace_id": job.get("trace_id") or _trace_id_from_request(request),
                    "resource": job["resource"],
                    "last_error": job.get("last_error"),
                }
            )
        return success_envelope(
            {"items": items, "total": result["total"], "next_cursor": result["next_cursor"]},
            _trace_id_from_request(request),
        )

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str, request: Request):
        job = store.get_job_for_tenant(job_id=job_id, tenant_id=_tenant_id_from_request(request))
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
            "trace_id": job.get("trace_id") or _trace_id_from_request(request),
            "resource": job["resource"],
            "last_error": job.get("last_error"),
        }
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/jobs/{job_id}/cancel")
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
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=payload,
            execute=lambda: store.cancel_job(
                job_id=job_id,
                tenant_id=_tenant_id_from_request(request),
            ),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.post("/api/v1/evaluations/{evaluation_id}/resume")
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
        if not store.validate_resume_token(
            evaluation_id=evaluation_id,
            resume_token=payload.resume_token,
        ):
            raise ApiError(
                code="WF_INTERRUPT_RESUME_INVALID",
                message="resume token expired or mismatched",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )

        req_payload = payload.model_dump(mode="json")
        data = store.run_idempotent(
            endpoint=f"POST:/api/v1/evaluations/{evaluation_id}/resume",
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=req_payload,
            execute=lambda: store.create_resume_job(
                evaluation_id=evaluation_id,
                payload={
                    **req_payload,
                    "trace_id": _trace_id_from_request(request),
                    "tenant_id": _tenant_id_from_request(request),
                },
            ),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.get("/api/v1/citations/{chunk_id}/source")
    def get_citation_source(chunk_id: str, request: Request):
        source = store.get_citation_source(
            chunk_id=chunk_id,
            tenant_id=_tenant_id_from_request(request),
        )
        if source is None:
            raise ApiError(
                code="CITATION_NOT_FOUND",
                message="citation source not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        return success_envelope(source, _trace_id_from_request(request))

    @app.get("/api/v1/dlq/items")
    def list_dlq_items(request: Request):
        items = store.list_dlq_items(tenant_id=_tenant_id_from_request(request))
        return success_envelope({"items": items, "total": len(items)}, _trace_id_from_request(request))

    @app.post("/api/v1/dlq/items/{item_id}/requeue")
    def requeue_dlq_item(item_id: str, request: Request):
        data = store.requeue_dlq_item(
            dlq_id=item_id,
            trace_id=_trace_id_from_request(request),
            tenant_id=_tenant_id_from_request(request),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.post("/api/v1/dlq/items/{item_id}/discard")
    def discard_dlq_item(item_id: str, payload: DlqDiscardRequest, request: Request):
        data = store.discard_dlq_item(
            dlq_id=item_id,
            reason=payload.reason,
            reviewer_id=payload.reviewer_id,
            tenant_id=_tenant_id_from_request(request),
        )
        return success_envelope(data, _trace_id_from_request(request))

    return app


app = create_app()
