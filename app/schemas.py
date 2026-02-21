from __future__ import annotations

from typing import Any


def success_envelope(data: Any, trace_id: str, message: str = "ok") -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "message": message,
        "meta": {
            "trace_id": trace_id,
        },
    }


def error_envelope(
    *,
    code: str,
    message: str,
    error_class: str,
    retryable: bool,
    trace_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
        "class": error_class,
    }
    if details is not None:
        error["details"] = details
    return {
        "success": False,
        "error": error,
        "meta": {
            "trace_id": trace_id,
        },
    }
