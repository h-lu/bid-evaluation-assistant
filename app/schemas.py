from __future__ import annotations

from typing import Literal
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


class ResumeRequest(BaseModel):
    resume_token: str
    decision: str
    comment: str
    edited_scores: list[dict[str, Any]] = Field(default_factory=list)


class DlqDiscardRequest(BaseModel):
    reason: str = ""
    reviewer_id: str = ""


class InternalTransitionRequest(BaseModel):
    new_status: str


class RetrievalQueryRequest(BaseModel):
    project_id: str
    supplier_id: str
    query: str = Field(min_length=1)
    query_type: Literal["fact", "relation", "comparison", "summary", "risk"]
    high_risk: bool = False
    top_k: int = Field(default=20, ge=1, le=100)
    enable_rerank: bool = True
    doc_scope: list[Literal["tender", "bid", "attachment"]] = Field(default_factory=list)
    must_include_terms: list[str] = Field(default_factory=list)
    must_exclude_terms: list[str] = Field(default_factory=list)


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
