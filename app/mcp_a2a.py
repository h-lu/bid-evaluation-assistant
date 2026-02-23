from __future__ import annotations

from typing import Any

from app.errors import ApiError


def enforce_mcp_baseline(*, payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    service = str(payload.get("service") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    scopes = payload.get("scopes")
    payload_tenant = str(payload.get("tenant_id") or "").strip()
    if not service or not session_id:
        raise ApiError(
            code="MCP_BASELINE_INVALID",
            message="mcp service and session_id are required",
            error_class="security_sensitive",
            retryable=False,
            http_status=400,
        )
    if payload_tenant and payload_tenant != tenant_id:
        raise ApiError(
            code="TENANT_SCOPE_VIOLATION",
            message="mcp tenant mismatch",
            error_class="security_sensitive",
            retryable=False,
            http_status=403,
        )
    if scopes is not None and not isinstance(scopes, list):
        raise ApiError(
            code="MCP_BASELINE_INVALID",
            message="mcp scopes must be list",
            error_class="security_sensitive",
            retryable=False,
            http_status=400,
        )
    return payload


def validate_a2a_result(*, payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    status = str(payload.get("status") or "").strip().lower()
    if not task_id or status not in {"succeeded", "failed", "pending"}:
        raise ApiError(
            code="A2A_RESULT_INVALID",
            message="a2a task_id or status invalid",
            error_class="security_sensitive",
            retryable=False,
            http_status=400,
        )
    return payload
