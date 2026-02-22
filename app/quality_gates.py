from __future__ import annotations

from typing import Any

QUALITY_THRESHOLDS: dict[str, float] = {
    "ragas_context_precision_min": 0.80,
    "ragas_context_recall_min": 0.80,
    "ragas_faithfulness_min": 0.90,
    "ragas_response_relevancy_min": 0.85,
    "deepeval_hallucination_rate_max": 0.05,
    "citation_resolvable_rate_min": 0.98,
}


def evaluate_quality_gate(
    *,
    dataset_id: str,
    ragas: dict[str, float],
    deepeval: dict[str, float],
    citation: dict[str, float],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    context_precision = float(ragas["context_precision"])
    context_recall = float(ragas["context_recall"])
    faithfulness = float(ragas["faithfulness"])
    response_relevancy = float(ragas["response_relevancy"])
    hallucination_rate = float(deepeval["hallucination_rate"])
    citation_resolvable_rate = float(citation["resolvable_rate"])

    if context_precision < QUALITY_THRESHOLDS["ragas_context_precision_min"]:
        failed_checks.append("RAGAS_CONTEXT_PRECISION_LOW")
    if context_recall < QUALITY_THRESHOLDS["ragas_context_recall_min"]:
        failed_checks.append("RAGAS_CONTEXT_RECALL_LOW")
    if faithfulness < QUALITY_THRESHOLDS["ragas_faithfulness_min"]:
        failed_checks.append("RAGAS_FAITHFULNESS_LOW")
    if response_relevancy < QUALITY_THRESHOLDS["ragas_response_relevancy_min"]:
        failed_checks.append("RAGAS_RESPONSE_RELEVANCY_LOW")
    if hallucination_rate > QUALITY_THRESHOLDS["deepeval_hallucination_rate_max"]:
        failed_checks.append("DEEPEVAL_HALLUCINATION_RATE_HIGH")
    if citation_resolvable_rate < QUALITY_THRESHOLDS["citation_resolvable_rate_min"]:
        failed_checks.append("CITATION_RESOLVABLE_RATE_LOW")

    return {
        "gate": "quality",
        "dataset_id": dataset_id,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "thresholds": dict(QUALITY_THRESHOLDS),
        "values": {
            "context_precision": context_precision,
            "context_recall": context_recall,
            "faithfulness": faithfulness,
            "response_relevancy": response_relevancy,
            "hallucination_rate": hallucination_rate,
            "citation_resolvable_rate": citation_resolvable_rate,
        },
        "ragchecker": {
            "triggered": len(failed_checks) > 0,
            "reason_codes": list(failed_checks),
        },
    }
