from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvaluationScope(BaseModel):
    include_doc_types: list[str]
    force_hitl: bool


class QueryOptions(BaseModel):
    mode_hint: str
    top_k: int = Field(ge=1, le=200)


class CreateEvaluationRequest(BaseModel):
    project_id: str
    supplier_id: str
    rule_pack_version: str
    evaluation_scope: EvaluationScope
    query_options: QueryOptions


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
