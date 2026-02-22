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
    class Editor(BaseModel):
        reviewer_id: str

    resume_token: str
    decision: str
    comment: str
    editor: Editor
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


class QualityGateRagasMetrics(BaseModel):
    context_precision: float = Field(ge=0, le=1)
    context_recall: float = Field(ge=0, le=1)
    faithfulness: float = Field(ge=0, le=1)
    response_relevancy: float = Field(ge=0, le=1)


class QualityGateDeepEvalMetrics(BaseModel):
    hallucination_rate: float = Field(ge=0, le=1)


class QualityGateCitationMetrics(BaseModel):
    resolvable_rate: float = Field(ge=0, le=1)


class QualityGateMetrics(BaseModel):
    ragas: QualityGateRagasMetrics
    deepeval: QualityGateDeepEvalMetrics
    citation: QualityGateCitationMetrics


class QualityGateEvaluateRequest(BaseModel):
    dataset_id: str
    metrics: QualityGateMetrics


class PerformanceGateMetrics(BaseModel):
    api_p95_s: float = Field(ge=0)
    retrieval_p95_s: float = Field(ge=0)
    parse_50p_p95_s: float = Field(ge=0)
    evaluation_p95_s: float = Field(ge=0)
    queue_dlq_rate: float = Field(ge=0, le=1)
    cache_hit_rate: float = Field(ge=0, le=1)


class PerformanceGateEvaluateRequest(BaseModel):
    dataset_id: str
    metrics: PerformanceGateMetrics


class SecurityGateMetrics(BaseModel):
    tenant_scope_violations: int = Field(ge=0)
    auth_bypass_findings: int = Field(ge=0)
    high_risk_approval_coverage: float = Field(ge=0, le=1)
    log_redaction_failures: int = Field(ge=0)
    secret_scan_findings: int = Field(ge=0)


class SecurityGateEvaluateRequest(BaseModel):
    dataset_id: str
    metrics: SecurityGateMetrics


class CostGateMetrics(BaseModel):
    task_cost_p95: float = Field(ge=0)
    baseline_task_cost_p95: float = Field(gt=0)
    routing_degrade_passed: bool
    degrade_availability: float = Field(ge=0, le=1)
    budget_alert_coverage: float = Field(ge=0, le=1)


class CostGateEvaluateRequest(BaseModel):
    dataset_id: str
    metrics: CostGateMetrics


class RolloutPlanRequest(BaseModel):
    release_id: str
    tenant_whitelist: list[str] = Field(min_length=1)
    enabled_project_sizes: list[Literal["small", "medium", "large"]] = Field(min_length=1)
    high_risk_hitl_enforced: bool = True


class RolloutDecisionRequest(BaseModel):
    release_id: str
    tenant_id: str
    project_size: Literal["small", "medium", "large"]
    high_risk: bool = False


class RollbackBreach(BaseModel):
    gate: Literal["quality", "performance", "security", "cost"]
    metric_code: str
    consecutive_failures: int = Field(ge=1)


class RollbackExecuteRequest(BaseModel):
    release_id: str
    consecutive_threshold: int = Field(default=2, ge=1)
    breaches: list[RollbackBreach] = Field(min_length=1)


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
