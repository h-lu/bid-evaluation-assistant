from __future__ import annotations

import uuid

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import ApiError
from app.schemas import CreateEvaluationRequest, error_envelope, success_envelope
from app.store import store


def _trace_id_from_request(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return trace_id
    return uuid.uuid4().hex


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
            idempotency_key=idempotency_key,
            payload=payload.model_dump(mode="json"),
            execute=lambda: store.create_evaluation_job(payload.model_dump(mode="json")),
        )
        return JSONResponse(
            status_code=202,
            content=success_envelope(data, _trace_id_from_request(request)),
        )

    return app


app = create_app()
