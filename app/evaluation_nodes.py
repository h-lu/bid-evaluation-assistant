"""Real evaluation graph node functions.

Aligned with SSOT langgraph-agent-workflow-spec §2-§4:
  - EvaluationState TypedDict matches §2
  - Node functions match §4 (load_context .. persist_result)
  - quality_gate returns routing key for conditional edges
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State definition (SSOT §2)
# ---------------------------------------------------------------------------

class EvaluationState(TypedDict, total=False):
    # identity (immutable after init)
    tenant_id: str
    project_id: str
    evaluation_id: str
    supplier_id: str
    # trace
    trace_id: str
    thread_id: str
    job_id: str
    # inputs
    payload: dict[str, Any]
    rule_pack_version: str
    include_doc_types: list[str]
    force_hitl: bool
    # load_context outputs
    rule_pack: dict[str, Any]
    rules: dict[str, Any]
    criteria_defs: list[dict[str, Any]]
    criteria_weights: dict[str, float]
    hard_constraint_pass: bool
    include_doc_types_normalized: set[str]
    # retrieve_evidence outputs
    criteria_evidence: dict[str, list[dict[str, Any]]]
    citations_all_ids: list[str]
    # evaluate_rules outputs
    redline_conflict: bool
    # score_with_llm outputs
    criteria_results: list[dict[str, Any]]
    unsupported_claims: list[str]
    # quality_gate outputs
    total_score: float
    confidence: float
    citation_coverage: float
    score_deviation_pct: float
    needs_human_review: bool
    hitl_reasons: list[str]
    interrupt_payload: dict[str, Any] | None
    # output
    report: dict[str, Any]
    status: str
    # resume (HITL)
    resume_payload: dict[str, Any]
    # runtime
    retry_count: int
    errors: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Node implementations (SSOT §4)
# ---------------------------------------------------------------------------

def node_load_context(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Load project / tenant / rule context.  No side effects."""
    tenant_id = state["tenant_id"]
    rule_pack = store.get_rule_pack_for_tenant(
        rule_pack_version=str(state.get("rule_pack_version") or ""),
        tenant_id=tenant_id,
    )
    rules = rule_pack.get("rules") if isinstance(rule_pack, dict) else {}
    criteria_defs = rules.get("criteria") if isinstance(rules, dict) else None
    if not isinstance(criteria_defs, list) or not criteria_defs:
        criteria_defs = [{"criteria_id": "delivery", "max_score": 20.0, "weight": 1.0}]

    criteria_weights: dict[str, float] = {}
    for c in criteria_defs:
        if isinstance(c, dict):
            criteria_weights[str(c.get("criteria_id", ""))] = float(c.get("weight", 1.0))

    include_doc_types = state.get("include_doc_types", [])
    include_doc_types_normalized = {str(x).lower() for x in include_doc_types}
    hard_constraint_pass = "bid" in include_doc_types_normalized

    return {
        "rule_pack": rule_pack,
        "rules": rules,
        "criteria_defs": criteria_defs,
        "criteria_weights": criteria_weights,
        "hard_constraint_pass": hard_constraint_pass,
        "include_doc_types_normalized": include_doc_types_normalized,
    }


def node_retrieve_evidence(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Retrieve and pack evidence for every criteria.  No side effects on store
    except citation_source registration (read-like)."""
    from app.token_budget import apply_report_budget

    tenant_id = state["tenant_id"]
    project_id = state.get("project_id", "")
    supplier_id = state.get("supplier_id", "")
    evaluation_id = state["evaluation_id"]
    include_doc_types = state.get("include_doc_types", [])
    hard_constraint_pass = state.get("hard_constraint_pass", True)
    criteria_defs = state.get("criteria_defs", [])

    criteria_evidence: dict[str, list[dict[str, Any]]] = {}
    for criteria in criteria_defs:
        if not isinstance(criteria, dict):
            continue
        cid = str(criteria.get("criteria_id") or "criteria")
        req = str(criteria.get("requirement_text") or criteria.get("requirement") or "")
        evidence = store._retrieve_evidence_for_criteria(
            query=req,
            tenant_id=tenant_id,
            project_id=str(project_id),
            supplier_id=str(supplier_id),
            doc_scope=include_doc_types,
            top_k=5,
            criteria_id=cid,
            evaluation_id=evaluation_id,
            hard_constraint_pass=hard_constraint_pass,
        )
        criteria_evidence[cid] = evidence

    criteria_evidence = apply_report_budget(criteria_evidence)
    citations_all_ids = [
        ev["chunk_id"]
        for ev_list in criteria_evidence.values()
        for ev in ev_list
        if ev.get("chunk_id")
    ]

    _register_citation_sources(
        store=store,
        criteria_evidence=criteria_evidence,
        citations_all_ids=citations_all_ids,
        evaluation_id=evaluation_id,
        tenant_id=tenant_id,
        payload=state.get("payload", {}),
        include_doc_types=include_doc_types,
    )

    return {
        "criteria_evidence": criteria_evidence,
        "citations_all_ids": citations_all_ids,
    }


def node_evaluate_rules(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Hard-constraint rule engine checks.  No side effects."""
    rules = state.get("rules", {})
    include_doc_types_normalized = state.get("include_doc_types_normalized", set())
    redline_conflict = False

    if isinstance(rules, dict):
        redlines = rules.get("redlines")
        if isinstance(redlines, list):
            for item in redlines:
                if not isinstance(item, dict):
                    continue
                if item.get("violated") is True:
                    redline_conflict = True
                    break
                status = str(item.get("status") or "").strip().lower()
                if status in {"blocked", "violation", "failed", "conflict"}:
                    redline_conflict = True
                    break
        required_doc_types = rules.get("required_doc_types")
        if isinstance(required_doc_types, list) and required_doc_types:
            required = {str(x).lower() for x in required_doc_types}
            if not required.issubset(include_doc_types_normalized):
                redline_conflict = True

    return {"redline_conflict": redline_conflict}


def node_score_with_llm(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """LLM soft-scoring for each criteria.  No side effects."""
    from app.llm_provider import llm_score_criteria

    criteria_defs = state.get("criteria_defs", [])
    criteria_evidence = state.get("criteria_evidence", {})
    hard_constraint_pass = state.get("hard_constraint_pass", True)
    citations_all_ids = state.get("citations_all_ids", [])

    criteria_results: list[dict[str, Any]] = []
    unsupported_claims: list[str] = []

    for criteria in criteria_defs:
        if not isinstance(criteria, dict):
            continue
        cid = str(criteria.get("criteria_id") or "criteria")
        max_score = float(criteria.get("max_score", 20.0))
        criteria_name = criteria.get("criteria_name") or criteria.get("name") or cid
        requirement_text = criteria.get("requirement_text") or criteria.get("requirement")
        response_text = criteria.get("response_text") or criteria.get("response")

        evidence = criteria_evidence.get(cid, [])
        citation_ids = [ev.get("chunk_id") for ev in evidence if ev.get("chunk_id")]

        llm_result = llm_score_criteria(
            criteria_id=cid,
            requirement_text=str(requirement_text or ""),
            evidence_chunks=evidence,
            max_score=max_score,
            criteria_name=str(criteria_name),
            hard_constraint_pass=hard_constraint_pass,
        )
        score = llm_result["score"]
        hard_pass = llm_result.get("hard_pass", True) and hard_constraint_pass
        reason = llm_result.get("reason", "evaluation completed")
        confidence = float(llm_result.get("confidence", 0.85 if hard_pass else 0.65))

        resolved_citations = store._resolve_citations_batch(citation_ids, include_quote=False)
        criteria_results.append({
            "criteria_id": cid,
            "criteria_name": str(criteria_name),
            "requirement_text": str(requirement_text) if requirement_text is not None else None,
            "response_text": str(response_text) if response_text is not None else None,
            "score": score,
            "max_score": max_score,
            "hard_pass": hard_pass,
            "reason": reason,
            "citations": resolved_citations,
            "confidence": confidence,
        })
        if criteria.get("require_citation") and not resolved_citations:
            unsupported_claims.append(cid)

    resolvable = [cid for cid in citations_all_ids if store.citation_sources.get(cid) is not None]
    if len(resolvable) < len(citations_all_ids):
        for missing in set(citations_all_ids) - set(resolvable):
            unsupported_claims.append(missing)

    return {
        "criteria_results": criteria_results,
        "unsupported_claims": unsupported_claims,
    }


def node_quality_gate(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Compute totals, confidence, HITL conditions.  No side effects.

    The returned ``needs_human_review`` is used by the conditional edge
    to route to ``finalize_report`` (pass) or ``human_review_interrupt`` (hitl).
    """
    criteria_results = state.get("criteria_results", [])
    criteria_weights = state.get("criteria_weights", {})
    hard_constraint_pass = state.get("hard_constraint_pass", True)
    citations_all_ids = state.get("citations_all_ids", [])
    force_hitl = state.get("force_hitl", False)
    redline_conflict = state.get("redline_conflict", False)
    unsupported_claims = state.get("unsupported_claims", [])
    evaluation_id = state["evaluation_id"]
    tenant_id = state["tenant_id"]

    total_score = 0.0
    max_total = 0.0
    for item in criteria_results:
        cid = item.get("criteria_id", "")
        w = criteria_weights.get(cid, 1.0)
        total_score += float(item.get("score", 0.0)) * w
        max_total += float(item.get("max_score", 0.0)) * w
    max_total = max_total or 1.0

    resolvable = [cid for cid in citations_all_ids if store.citation_sources.get(cid) is not None]
    citation_coverage = len(resolvable) / max(len(citations_all_ids), 1)
    evidence_quality = citation_coverage
    retrieval_agreement = store._calculate_retrieval_agreement(citations_all_ids)
    model_stability = _compute_model_stability(criteria_results, hard_constraint_pass)
    base_confidence = 0.4 * evidence_quality + 0.3 * retrieval_agreement + 0.3 * model_stability

    score_calibration = store.strategy_config.get("score_calibration", {})
    confidence_scale = float(score_calibration.get("confidence_scale", 1.0))
    score_bias = float(score_calibration.get("score_bias", 0.0))
    confidence_avg = max(0.0, min(1.0, base_confidence * confidence_scale + score_bias))
    score_deviation_pct = abs(total_score - max_total) / max_total * 100.0

    hitl_reasons: list[str] = []
    if force_hitl:
        hitl_reasons.append("force_hitl")
    if confidence_avg < 0.65:
        hitl_reasons.append(f"confidence_low ({confidence_avg:.2f} < 0.65)")
    if citation_coverage < 0.90:
        hitl_reasons.append(f"citation_coverage_low ({citation_coverage:.2%} < 90%)")
    if score_deviation_pct > 20.0:
        hitl_reasons.append(f"score_deviation_high ({score_deviation_pct:.1f}% > 20%)")
    if redline_conflict:
        hitl_reasons.append("redline_conflict")
    if unsupported_claims:
        hitl_reasons.append("unsupported_claims")

    needs_human_review = bool(hitl_reasons)
    interrupt_payload: dict[str, Any] | None = None
    if needs_human_review:
        resume_token = f"rt_{uuid.uuid4().hex[:12]}"
        interrupt_payload = {
            "type": "human_review",
            "evaluation_id": evaluation_id,
            "reasons": hitl_reasons,
            "suggested_actions": ["approve", "reject", "edit_scores"],
            "resume_token": resume_token,
        }
        store.register_resume_token(
            evaluation_id=evaluation_id,
            resume_token=resume_token,
            tenant_id=tenant_id,
            reasons=hitl_reasons,
        )

    return {
        "total_score": total_score if hard_constraint_pass else 0.0,
        "confidence": confidence_avg,
        "citation_coverage": citation_coverage,
        "score_deviation_pct": round(score_deviation_pct, 2),
        "needs_human_review": needs_human_review,
        "hitl_reasons": hitl_reasons,
        "interrupt_payload": interrupt_payload,
    }


def node_finalize_report(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Assemble the evaluation report dict.  No side effects."""
    criteria_results = [
        dict(cr) for cr in state.get("criteria_results", [])
    ]

    resume_payload = state.get("resume_payload") or {}
    edited_scores: dict[str, Any] = resume_payload.get("edited_scores", {})
    if edited_scores:
        for cr in criteria_results:
            cid = cr.get("criteria_id", "")
            if cid in edited_scores:
                cr["score"] = float(edited_scores[cid])
                cr["human_edited"] = True

    report = {
        "evaluation_id": state["evaluation_id"],
        "supplier_id": state.get("supplier_id", ""),
        "total_score": state.get("total_score", 0.0),
        "confidence": state.get("confidence", 0.0),
        "citation_coverage": state.get("citation_coverage", 0.0),
        "score_deviation_pct": state.get("score_deviation_pct", 0.0),
        "risk_level": "medium" if state.get("hard_constraint_pass", True) else "high",
        "criteria_results": criteria_results,
        "citations": store._resolve_citations_batch(
            state.get("citations_all_ids", []), include_quote=True,
        ),
        "needs_human_review": state.get("needs_human_review", False),
        "trace_id": state.get("trace_id", ""),
        "tenant_id": state["tenant_id"],
        "thread_id": state.get("thread_id", ""),
        "interrupt": state.get("interrupt_payload"),
        "unsupported_claims": state.get("unsupported_claims", []),
        "redline_conflict": state.get("redline_conflict", False),
    }
    return {"report": report}


def node_persist_result(state: EvaluationState, *, store: Any) -> dict[str, Any]:
    """Write DB / object storage / audit.  **SIDE EFFECT** node.
    Idempotency key: evaluation_id + job_id."""
    report = state.get("report", {})
    store._persist_evaluation_report(report=report)
    return {"status": "persisted"}


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------

def _compute_model_stability(
    criteria_results: list[dict[str, Any]],
    hard_constraint_pass: bool,
) -> float:
    """Derive model_stability from score coefficient of variation.

    With >= 2 scores: stability = clamp(1.0 - CV, 0.5, 1.0).
    With < 2 scores: default 0.75.
    If hard_constraint_pass is False, apply a 0.15 penalty (floor 0.5).
    """
    scores = [float(r["score"]) for r in criteria_results if "score" in r]
    if len(scores) >= 2:
        mean = sum(scores) / len(scores)
        if mean > 0:
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std = math.sqrt(variance)
            cv = std / mean
        else:
            cv = 0.0
        stability = max(0.5, min(1.0, 1.0 - cv))
    else:
        stability = 0.75

    if not hard_constraint_pass:
        stability = max(0.5, stability - 0.15)

    return stability


def _register_citation_sources(
    *,
    store: Any,
    criteria_evidence: dict[str, list[dict[str, Any]]],
    citations_all_ids: list[str],
    evaluation_id: str,
    tenant_id: str,
    payload: dict[str, Any],
    include_doc_types: list[str],
) -> None:
    """Register citation sources from retrieved evidence."""
    from app.store import MOCK_LLM_ENABLED

    for chunk_id in citations_all_ids:
        if chunk_id not in store.citation_sources:
            source_data = None
            for ev_list in criteria_evidence.values():
                for ev in ev_list:
                    if ev.get("chunk_id") == chunk_id:
                        source_data = ev
                        break
                if source_data:
                    break
            if source_data:
                store.register_citation_source(
                    chunk_id=chunk_id,
                    source={
                        "chunk_id": chunk_id,
                        "document_id": f"doc_{evaluation_id[:8]}",
                        "tenant_id": tenant_id,
                        "project_id": payload.get("project_id"),
                        "supplier_id": payload.get("supplier_id"),
                        "doc_type": include_doc_types[0] if include_doc_types else "bid",
                        "page": source_data.get("page", 1),
                        "bbox": source_data.get("bbox", [0.0, 0.0, 1.0, 1.0]),
                        "heading_path": ["auto", "mock_llm"],
                        "chunk_type": "text",
                        "content_source": "mock_llm" if MOCK_LLM_ENABLED else "stub",
                        "text": source_data.get("text", "mock citation"),
                        "context": source_data.get("text", "")[:200],
                        "score_raw": source_data.get("score_raw", 0.78),
                        "chunk_hash": f"hash_{chunk_id}",
                    },
                )


def run_evaluation_nodes_sequentially(
    state: EvaluationState, *, store: Any
) -> EvaluationState:
    """Run all evaluation nodes in sequence (non-graph mode).

    Used by ``create_evaluation_job`` as a direct execution path that
    guarantees identical results whether or not LangGraph is available.
    """
    result = dict(state)
    for node_fn in [
        node_load_context,
        node_retrieve_evidence,
        node_evaluate_rules,
        node_score_with_llm,
        node_quality_gate,
        node_finalize_report,
        node_persist_result,
    ]:
        updates = node_fn(result, store=store)  # type: ignore[arg-type]
        result.update(updates)
    return result  # type: ignore[return-value]
