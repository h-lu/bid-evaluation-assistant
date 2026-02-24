from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.errors import ApiError
from app.queue_backend import InMemoryQueueBackend, create_queue_from_env
from app.routes._deps import (
    append_security_audit_log,
    error_response,
    request_id_from_request,
    tenant_id_from_request,
    trace_id_from_request,
)
from app.routes.admin import router as admin_router
from app.routes.documents import router as documents_router
from app.routes.evaluations import router as evaluations_router
from app.routes.internal import router as internal_router
from app.routes.retrieval import router as retrieval_router
from app.runtime_profile import true_stack_required
from app.schemas import success_envelope
from app.security import JwtSecurityConfig, parse_and_validate_bearer_token
from app.store import store


def _create_queue_backend_for_runtime(
    environ: Mapping[str, str] | None = None,
) -> InMemoryQueueBackend | object:
    env = os.environ if environ is None else environ
    try:
        return create_queue_from_env(env)
    except RuntimeError:
        if true_stack_required(env):
            raise
        return InMemoryQueueBackend()


queue_backend = _create_queue_backend_for_runtime()


def create_app() -> FastAPI:
    app = FastAPI(title="Bid Evaluation Assistant API", version="0.1.0")
    security_cfg = JwtSecurityConfig.from_env()

    app.state.security_cfg = security_cfg
    app.state.queue_backend = queue_backend

    cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    allow_origins = [x.strip() for x in cors_origins.split(",") if x.strip()]
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        incoming_trace_id = request.headers.get("x-trace-id", "").strip()
        request.state.trace_id = incoming_trace_id or uuid.uuid4().hex
        request.state.request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex[:12]}")
        request.state.auth_subject = "anonymous"
        if (
            security_cfg.trace_id_strict_required
            and request.url.path.startswith("/api/v1/")
            and request.url.path != "/api/v1/health"
            and not incoming_trace_id
        ):
            response = error_response(
                request,
                code="TRACE_ID_REQUIRED",
                message="x-trace-id header is required",
                error_class="validation",
                retryable=False,
                status_code=400,
            )
            response.headers["x-trace-id"] = trace_id_from_request(request)
            response.headers["x-request-id"] = request_id_from_request(request)
            return response
        try:
            path = request.url.path
            header_tenant_explicit = request.headers.get("x-tenant-id")
            if security_cfg.enabled and path.startswith("/api/v1/") and not path.startswith("/api/v1/internal/"):
                auth_ctx = parse_and_validate_bearer_token(
                    authorization=request.headers.get("Authorization"),
                    cfg=security_cfg,
                )
                request.state.auth_subject = auth_ctx.subject
                request.state.tenant_id = auth_ctx.tenant_id
                if header_tenant_explicit and header_tenant_explicit != auth_ctx.tenant_id:
                    raise ApiError(
                        code="TENANT_SCOPE_VIOLATION",
                        message="tenant mismatch",
                        error_class="security_sensitive",
                        retryable=False,
                        http_status=403,
                    )
            else:
                request.state.tenant_id = header_tenant_explicit or "tenant_default"
            response = await call_next(request)
            response.headers["x-trace-id"] = trace_id_from_request(request)
            response.headers["x-request-id"] = request_id_from_request(request)
            return response
        except ApiError as exc:
            append_security_audit_log(
                request=request,
                action="security_blocked",
                code=exc.code,
                detail=exc.message,
            )
            response = error_response(
                request,
                code=exc.code,
                message=exc.message,
                error_class=exc.error_class,
                retryable=exc.retryable,
                status_code=exc.http_status,
            )
            response.headers["x-trace-id"] = trace_id_from_request(request)
            response.headers["x-request-id"] = request_id_from_request(request)
            return response

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        if exc.code in {
            "AUTH_UNAUTHORIZED",
            "AUTH_FORBIDDEN",
            "TENANT_SCOPE_VIOLATION",
            "APPROVAL_REQUIRED",
        }:
            append_security_audit_log(
                request=request,
                action="security_blocked",
                code=exc.code,
                detail=exc.message,
            )
        return error_response(
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
                    return error_response(
                        request,
                        code="WF_INTERRUPT_REVIEWER_REQUIRED",
                        message="reviewer_id is required for resume",
                        error_class="business_rule",
                        retryable=False,
                        status_code=400,
                    )
        return error_response(
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
            return error_response(
                request,
                code="REQ_NOT_FOUND",
                message="resource not found",
                error_class="validation",
                retryable=False,
                status_code=404,
            )
        return error_response(
            request,
            code="REQ_HTTP_ERROR",
            message=str(exc.detail),
            error_class="validation",
            retryable=False,
            status_code=exc.status_code,
        )

    # ------------------------------------------------------------------
    # Health endpoints (remain in main)
    # ------------------------------------------------------------------

    @app.get("/healthz")
    def healthz(request: Request) -> dict[str, object]:
        return success_envelope({"status": "ok"}, trace_id_from_request(request))

    @app.get("/api/v1/health")
    def health_api(request: Request) -> dict[str, object]:
        return success_envelope({"status": "ok"}, trace_id_from_request(request))

    # ------------------------------------------------------------------
    # Include route modules
    # ------------------------------------------------------------------

    app.include_router(documents_router)
    app.include_router(evaluations_router)
    app.include_router(retrieval_router)
    app.include_router(admin_router)
    app.include_router(internal_router)

    return app


app = create_app()
