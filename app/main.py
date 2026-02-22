from __future__ import annotations

import hashlib
import uuid

from fastapi import Body, FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.cost_gates import evaluate_cost_gate
from app.errors import ApiError
from app.performance_gates import evaluate_performance_gate
from app.queue_backend import InMemoryQueueBackend, create_queue_from_env
from app.quality_gates import evaluate_quality_gate
from app.schemas import (
    CostGateEvaluateRequest,
    CreateEvaluationRequest,
    DataFeedbackRunRequest,
    DlqDiscardRequest,
    InternalTransitionRequest,
    PerformanceGateEvaluateRequest,
    QualityGateEvaluateRequest,
    RollbackExecuteRequest,
    RolloutDecisionRequest,
    RolloutPlanRequest,
    RetrievalQueryRequest,
    ResumeRequest,
    SecurityGateEvaluateRequest,
    StrategyTuningApplyRequest,
    error_envelope,
    success_envelope,
)
from app.security_gates import evaluate_security_gate
from app.store import store

try:
    queue_backend = create_queue_from_env()
except RuntimeError:
    queue_backend = InMemoryQueueBackend()


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


def _job_type_from_event_type(event_type: str) -> str:
    if event_type.endswith(".job.created"):
        return event_type.split(".", maxsplit=1)[0]
    if event_type.endswith(".created"):
        return event_type.rsplit(".", maxsplit=1)[0]
    return "unknown"


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
        if request.url.path.startswith("/api/v1/evaluations/") and request.url.path.endswith("/resume"):
            for err in exc.errors():
                loc = tuple(err.get("loc", ()))
                if "editor" in loc or "reviewer_id" in loc:
                    return _error_response(
                        request,
                        code="WF_INTERRUPT_REVIEWER_REQUIRED",
                        message="reviewer_id is required for resume",
                        error_class="business_rule",
                        retryable=False,
                        status_code=400,
                    )
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

    @app.post("/api/v1/retrieval/query")
    def retrieval_query(payload: RetrievalQueryRequest, request: Request):
        data = store.retrieval_query(
            tenant_id=_tenant_id_from_request(request),
            project_id=payload.project_id,
            supplier_id=payload.supplier_id,
            query=payload.query,
            query_type=payload.query_type,
            high_risk=payload.high_risk,
            top_k=payload.top_k,
            doc_scope=list(payload.doc_scope),
            enable_rerank=payload.enable_rerank,
            must_include_terms=payload.must_include_terms,
            must_exclude_terms=payload.must_exclude_terms,
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/retrieval/preview")
    def retrieval_preview(payload: RetrievalQueryRequest, request: Request):
        data = store.retrieval_preview(
            tenant_id=_tenant_id_from_request(request),
            project_id=payload.project_id,
            supplier_id=payload.supplier_id,
            query=payload.query,
            query_type=payload.query_type,
            high_risk=payload.high_risk,
            top_k=payload.top_k,
            doc_scope=list(payload.doc_scope),
            enable_rerank=payload.enable_rerank,
            must_include_terms=payload.must_include_terms,
            must_exclude_terms=payload.must_exclude_terms,
        )
        return success_envelope(data, _trace_id_from_request(request))

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
            "file_size": len(file_bytes),
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

    @app.get("/api/v1/documents/{document_id}")
    def get_document(document_id: str, request: Request):
        document = store.get_document_for_tenant(
            document_id=document_id,
            tenant_id=_tenant_id_from_request(request),
        )
        if document is None:
            raise ApiError(
                code="DOC_NOT_FOUND",
                message="document not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        return success_envelope(
            {
                "document_id": document["document_id"],
                "project_id": document["project_id"],
                "supplier_id": document["supplier_id"],
                "doc_type": document["doc_type"],
                "filename": document["filename"],
                "status": document["status"],
            },
            _trace_id_from_request(request),
        )

    @app.get("/api/v1/documents/{document_id}/chunks")
    def get_document_chunks(document_id: str, request: Request):
        chunks = store.list_document_chunks_for_tenant(
            document_id=document_id,
            tenant_id=_tenant_id_from_request(request),
        )
        return success_envelope(
            {
                "document_id": document_id,
                "items": chunks,
                "total": len(chunks),
            },
            _trace_id_from_request(request),
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
                    "thread_id": job.get("thread_id"),
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
            "thread_id": job.get("thread_id"),
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
                tenant_id=_tenant_id_from_request(request),
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
                    "trace_id": _trace_id_from_request(request),
                    "tenant_id": _tenant_id_from_request(request),
                },
            )

        data = store.run_idempotent(
            endpoint=f"POST:/api/v1/evaluations/{evaluation_id}/resume",
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=req_payload,
            execute=_execute_resume,
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.get("/api/v1/evaluations/{evaluation_id}/report")
    def get_evaluation_report(evaluation_id: str, request: Request):
        report = store.get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=_tenant_id_from_request(request),
        )
        if report is None:
            raise ApiError(
                code="EVALUATION_REPORT_NOT_FOUND",
                message="evaluation report not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        return success_envelope(report, _trace_id_from_request(request))

    @app.get("/api/v1/evaluations/{evaluation_id}/audit-logs")
    def list_evaluation_audit_logs(evaluation_id: str, request: Request):
        report = store.get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=_tenant_id_from_request(request),
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
            tenant_id=_tenant_id_from_request(request),
        )
        return success_envelope(
            {
                "evaluation_id": evaluation_id,
                "items": items,
                "total": len(items),
            },
            _trace_id_from_request(request),
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
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=payload,
            execute=lambda: store.requeue_dlq_item(
                dlq_id=item_id,
                trace_id=_trace_id_from_request(request),
                tenant_id=_tenant_id_from_request(request),
            ),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    @app.post("/api/v1/dlq/items/{item_id}/discard")
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
        req_payload = payload.model_dump(mode="json")
        data = store.run_idempotent(
            endpoint=f"POST:/api/v1/dlq/items/{item_id}/discard",
            tenant_id=_tenant_id_from_request(request),
            idempotency_key=idempotency_key,
            payload=req_payload,
            execute=lambda: store.discard_dlq_item(
                dlq_id=item_id,
                reason=payload.reason,
                reviewer_id=payload.reviewer_id,
                tenant_id=_tenant_id_from_request(request),
            ),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/jobs/{job_id}/transition")
    def internal_transition_job(
        job_id: str,
        payload: InternalTransitionRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        updated = store.transition_job_status(
            job_id=job_id,
            new_status=payload.new_status,
            tenant_id=_tenant_id_from_request(request),
        )
        return success_envelope(
            {
                "job_id": updated["job_id"],
                "status": updated["status"],
                "retry_count": updated.get("retry_count", 0),
            },
            _trace_id_from_request(request),
        )

    @app.post("/api/v1/internal/jobs/{job_id}/run")
    def internal_run_job(
        job_id: str,
        request: Request,
        force_fail: bool = Query(default=False),
        transient_fail: bool = Query(default=False),
        error_code: str | None = Query(default=None),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        result = store.run_job_once(
            job_id=job_id,
            tenant_id=_tenant_id_from_request(request),
            force_fail=force_fail,
            transient_fail=transient_fail,
            force_error_code=error_code,
        )
        return success_envelope(result, _trace_id_from_request(request))

    @app.get("/api/v1/internal/parse-manifests/{job_id}")
    def internal_get_parse_manifest(
        job_id: str,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        manifest = store.get_parse_manifest_for_tenant(
            job_id=job_id,
            tenant_id=_tenant_id_from_request(request),
        )
        if manifest is None:
            raise ApiError(
                code="DOC_PARSE_OUTPUT_NOT_FOUND",
                message="parse manifest not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        return success_envelope(manifest, _trace_id_from_request(request))

    @app.get("/api/v1/internal/workflows/{thread_id}/checkpoints")
    def internal_list_workflow_checkpoints(
        thread_id: str,
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        items = store.list_workflow_checkpoints(
            thread_id=thread_id,
            tenant_id=_tenant_id_from_request(request),
            limit=limit,
        )
        return success_envelope(
            {"thread_id": thread_id, "items": items, "total": len(items)},
            _trace_id_from_request(request),
        )

    @app.post("/api/v1/internal/quality-gates/evaluate")
    def internal_evaluate_quality_gate(
        payload: QualityGateEvaluateRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = evaluate_quality_gate(
            dataset_id=payload.dataset_id,
            ragas=payload.metrics.ragas.model_dump(mode="json"),
            deepeval=payload.metrics.deepeval.model_dump(mode="json"),
            citation=payload.metrics.citation.model_dump(mode="json"),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/performance-gates/evaluate")
    def internal_evaluate_performance_gate(
        payload: PerformanceGateEvaluateRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = evaluate_performance_gate(
            dataset_id=payload.dataset_id,
            metrics=payload.metrics.model_dump(mode="json"),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/security-gates/evaluate")
    def internal_evaluate_security_gate(
        payload: SecurityGateEvaluateRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = evaluate_security_gate(
            dataset_id=payload.dataset_id,
            metrics=payload.metrics.model_dump(mode="json"),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/cost-gates/evaluate")
    def internal_evaluate_cost_gate(
        payload: CostGateEvaluateRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = evaluate_cost_gate(
            dataset_id=payload.dataset_id,
            metrics=payload.metrics.model_dump(mode="json"),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/release/rollout/plan")
    def internal_plan_release_rollout(
        payload: RolloutPlanRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = store.upsert_rollout_policy(
            release_id=payload.release_id,
            tenant_whitelist=list(payload.tenant_whitelist),
            enabled_project_sizes=list(payload.enabled_project_sizes),
            high_risk_hitl_enforced=payload.high_risk_hitl_enforced,
            tenant_id=_tenant_id_from_request(request),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/release/rollout/decision")
    def internal_decide_release_rollout(
        payload: RolloutDecisionRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = store.decide_rollout(
            release_id=payload.release_id,
            tenant_id=payload.tenant_id,
            project_size=payload.project_size,
            high_risk=payload.high_risk,
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/release/rollback/execute")
    def internal_execute_release_rollback(
        payload: RollbackExecuteRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = store.execute_rollback(
            release_id=payload.release_id,
            consecutive_threshold=payload.consecutive_threshold,
            breaches=[x.model_dump(mode="json") for x in payload.breaches],
            tenant_id=_tenant_id_from_request(request),
            trace_id=_trace_id_from_request(request),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/release/replay/e2e")
    def internal_run_release_replay_e2e(
        request: Request,
        payload: dict[str, object] = Body(default_factory=dict),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
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
            tenant_id=_tenant_id_from_request(request),
            trace_id=_trace_id_from_request(request),
            project_id=project_id,
            supplier_id=supplier_id,
            doc_type=doc_type,
            force_hitl=force_hitl,
            decision=decision,
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/release/readiness/evaluate")
    def internal_evaluate_release_readiness(
        request: Request,
        payload: dict[str, object] = Body(default_factory=dict),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
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
        gate_results_obj = payload.get("gate_results", {})
        gate_results = gate_results_obj if isinstance(gate_results_obj, dict) else {}
        data = store.evaluate_release_readiness(
            release_id=release_id,
            tenant_id=_tenant_id_from_request(request),
            trace_id=_trace_id_from_request(request),
            replay_passed=replay_passed,
            gate_results=gate_results,
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.get("/api/v1/internal/ops/metrics/summary")
    def internal_get_ops_metrics_summary(
        request: Request,
        queue_name: str = Query(default="jobs"),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
        summary = store.summarize_ops_metrics(tenant_id=tenant_id)
        summary["worker"]["queue_name"] = queue_name
        summary["worker"]["queue_pending"] = queue_backend.pending_count(
            tenant_id=tenant_id,
            queue_name=queue_name,
        )
        return success_envelope(summary, _trace_id_from_request(request))

    @app.post("/api/v1/internal/ops/data-feedback/run")
    def internal_run_data_feedback(
        payload: DataFeedbackRunRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = store.run_data_feedback(
            release_id=payload.release_id,
            dlq_ids=list(payload.dlq_ids),
            version_bump=payload.version_bump,
            include_manual_override_candidates=payload.include_manual_override_candidates,
            tenant_id=_tenant_id_from_request(request),
            trace_id=_trace_id_from_request(request),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/ops/strategy-tuning/apply")
    def internal_apply_strategy_tuning(
        payload: StrategyTuningApplyRequest,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        data = store.apply_strategy_tuning(
            release_id=payload.release_id,
            selector=payload.selector.model_dump(mode="json"),
            score_calibration=payload.score_calibration.model_dump(mode="json"),
            tool_policy=payload.tool_policy.model_dump(mode="json"),
            tenant_id=_tenant_id_from_request(request),
            trace_id=_trace_id_from_request(request),
        )
        return success_envelope(data, _trace_id_from_request(request))

    @app.get("/api/v1/internal/outbox/events")
    def internal_list_outbox_events(
        request: Request,
        status: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
        items = store.list_outbox_events(tenant_id=tenant_id, status=status, limit=limit)
        return success_envelope(
            {"items": items, "total": len(items)},
            _trace_id_from_request(request),
        )

    @app.post("/api/v1/internal/outbox/events/{event_id}/publish")
    def internal_publish_outbox_event(
        event_id: str,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
        event = store.mark_outbox_event_published(tenant_id=tenant_id, event_id=event_id)
        return success_envelope(event, _trace_id_from_request(request))

    @app.post("/api/v1/internal/outbox/relay")
    def internal_relay_outbox_events(
        request: Request,
        queue_name: str = Query(default="jobs"),
        consumer_name: str = Query(default="default"),
        limit: int = Query(default=100, ge=1, le=1000),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
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
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/queue/{queue_name}/enqueue")
    def internal_enqueue_queue_message(
        queue_name: str,
        request: Request,
        payload: dict[str, object] = Body(default_factory=dict),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
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
            _trace_id_from_request(request),
        )

    @app.post("/api/v1/internal/queue/{queue_name}/dequeue")
    def internal_dequeue_queue_message(
        queue_name: str,
        request: Request,
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
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
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/queue/{queue_name}/ack")
    def internal_ack_queue_message(
        queue_name: str,
        request: Request,
        payload: dict[str, object] = Body(default_factory=dict),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        message_id = str(payload.get("message_id") or "")
        if not message_id:
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message="message_id is required",
                error_class="validation",
                retryable=False,
                http_status=400,
            )
        tenant_id = _tenant_id_from_request(request)
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
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/queue/{queue_name}/nack")
    def internal_nack_queue_message(
        queue_name: str,
        request: Request,
        payload: dict[str, object] = Body(default_factory=dict),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
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
        tenant_id = _tenant_id_from_request(request)
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
        return success_envelope(data, _trace_id_from_request(request))

    @app.post("/api/v1/internal/worker/queues/{queue_name}/drain-once")
    def internal_worker_drain_once(
        queue_name: str,
        request: Request,
        max_messages: int = Query(default=1, ge=1, le=100),
        force_fail: bool = Query(default=False),
        transient_fail: bool = Query(default=False),
        error_code: str | None = Query(default=None),
        x_internal_debug: str | None = Header(default=None, alias="x-internal-debug"),
    ):
        if x_internal_debug != "true":
            raise ApiError(
                code="AUTH_FORBIDDEN",
                message="internal endpoint forbidden",
                error_class="security_sensitive",
                retryable=False,
                http_status=403,
            )
        tenant_id = _tenant_id_from_request(request)
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
                queue_backend.nack(tenant_id=tenant_id, message_id=msg.message_id, requeue=True)
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
        return success_envelope(data, _trace_id_from_request(request))

    return app


app = create_app()
