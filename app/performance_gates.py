from __future__ import annotations

from typing import Any

PERFORMANCE_THRESHOLDS: dict[str, float] = {
    "api_p95_s_max": 1.5,
    "retrieval_p95_s_max": 4.0,
    "parse_50p_p95_s_max": 180.0,
    "evaluation_p95_s_max": 120.0,
    "queue_dlq_rate_max": 0.01,
    "cache_hit_rate_min": 0.70,
}


def evaluate_performance_gate(*, dataset_id: str, metrics: dict[str, float]) -> dict[str, Any]:
    api_p95_s = float(metrics["api_p95_s"])
    retrieval_p95_s = float(metrics["retrieval_p95_s"])
    parse_50p_p95_s = float(metrics["parse_50p_p95_s"])
    evaluation_p95_s = float(metrics["evaluation_p95_s"])
    queue_dlq_rate = float(metrics["queue_dlq_rate"])
    cache_hit_rate = float(metrics["cache_hit_rate"])

    failed_checks: list[str] = []
    if api_p95_s > PERFORMANCE_THRESHOLDS["api_p95_s_max"]:
        failed_checks.append("API_P95_EXCEEDED")
    if retrieval_p95_s > PERFORMANCE_THRESHOLDS["retrieval_p95_s_max"]:
        failed_checks.append("RETRIEVAL_P95_EXCEEDED")
    if parse_50p_p95_s > PERFORMANCE_THRESHOLDS["parse_50p_p95_s_max"]:
        failed_checks.append("PARSE_P95_EXCEEDED")
    if evaluation_p95_s > PERFORMANCE_THRESHOLDS["evaluation_p95_s_max"]:
        failed_checks.append("EVALUATION_P95_EXCEEDED")
    if queue_dlq_rate > PERFORMANCE_THRESHOLDS["queue_dlq_rate_max"]:
        failed_checks.append("QUEUE_DLQ_RATE_HIGH")
    if cache_hit_rate < PERFORMANCE_THRESHOLDS["cache_hit_rate_min"]:
        failed_checks.append("CACHE_HIT_RATE_LOW")

    return {
        "gate": "performance",
        "dataset_id": dataset_id,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "thresholds": dict(PERFORMANCE_THRESHOLDS),
        "values": {
            "api_p95_s": api_p95_s,
            "retrieval_p95_s": retrieval_p95_s,
            "parse_50p_p95_s": parse_50p_p95_s,
            "evaluation_p95_s": evaluation_p95_s,
            "queue_dlq_rate": queue_dlq_rate,
            "cache_hit_rate": cache_hit_rate,
        },
    }
