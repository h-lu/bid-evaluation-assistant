from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.errors import ApiError
from app.schemas import error_envelope
from app.security import redact_sensitive
from app.store import store
from app.tools_registry import hash_payload


def trace_id_from_request(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return trace_id
    return uuid.uuid4().hex


def tenant_id_from_request(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return tenant_id
    return "tenant_default"


def request_id_from_request(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    return f"req_{uuid.uuid4().hex[:12]}"


def error_response(
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
            trace_id=trace_id_from_request(request),
        ),
    )


def append_security_audit_log(
    *,
    request: Request,
    action: str,
    code: str,
    detail: str,
) -> None:
    security_cfg = request.app.state.security_cfg
    headers_obj = dict(request.headers.items())
    headers_payload = redact_sensitive(headers_obj) if security_cfg.log_redaction_enabled else headers_obj
    try:
        store._append_audit_log(  # type: ignore[attr-defined]
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id_from_request(request),
                "action": action,
                "error_code": code,
                "detail": detail,
                "trace_id": trace_id_from_request(request),
                "headers": headers_payload,
                "occurred_at": store._utcnow_iso(),  # type: ignore[attr-defined]
            }
        )
    except Exception:
        return


def append_tool_audit_log(
    *,
    request: Request,
    tool_name: str,
    risk_level: str,
    input_payload: dict[str, Any],
    result_summary: str,
    status: str,
    latency_ms: int,
) -> None:
    try:
        store._append_audit_log(  # type: ignore[attr-defined]
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id_from_request(request),
                "action": "tool_call",
                "trace_id": trace_id_from_request(request),
                "occurred_at": store._utcnow_iso(),  # type: ignore[attr-defined]
                "payload": {
                    "tool_name": tool_name,
                    "risk_level": risk_level,
                    "agent_id": getattr(request.state, "auth_subject", "anonymous"),
                    "input_hash": hash_payload(input_payload),
                    "result_summary": result_summary,
                    "status": status,
                    "latency_ms": latency_ms,
                },
            }
        )
    except Exception:
        return


def require_approval(
    *,
    action: str,
    request: Request,
    reviewer_id: str,
    reason: str,
    reviewer_id_2: str = "",
) -> None:
    security_cfg = request.app.state.security_cfg
    if action not in security_cfg.approval_required_actions:
        return
    reviewer_a = reviewer_id.strip()
    reviewer_b = reviewer_id_2.strip()
    if not reviewer_a or not reason.strip() or not trace_id_from_request(request).strip():
        raise ApiError(
            code="APPROVAL_REQUIRED",
            message=f"approval required for action: {action}",
            error_class="business_rule",
            retryable=False,
            http_status=400,
        )
    if action in security_cfg.dual_approval_required_actions:
        if not reviewer_b or reviewer_a == reviewer_b:
            raise ApiError(
                code="APPROVAL_REQUIRED",
                message=f"dual approval required for action: {action}",
                error_class="business_rule",
                retryable=False,
                http_status=400,
            )
