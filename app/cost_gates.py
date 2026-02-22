from __future__ import annotations

from typing import Any

COST_THRESHOLDS: dict[str, float | bool] = {
    "task_cost_p95_ratio_max": 1.2,
    "degrade_availability_min": 0.995,
    "budget_alert_coverage_min": 1.0,
    "routing_degrade_passed_required": True,
}


def evaluate_cost_gate(*, dataset_id: str, metrics: dict[str, float | bool]) -> dict[str, Any]:
    task_cost_p95 = float(metrics["task_cost_p95"])
    baseline_task_cost_p95 = float(metrics["baseline_task_cost_p95"])
    routing_degrade_passed = bool(metrics["routing_degrade_passed"])
    degrade_availability = float(metrics["degrade_availability"])
    budget_alert_coverage = float(metrics["budget_alert_coverage"])
    task_cost_p95_ratio = task_cost_p95 / baseline_task_cost_p95

    failed_checks: list[str] = []
    if task_cost_p95_ratio > float(COST_THRESHOLDS["task_cost_p95_ratio_max"]):
        failed_checks.append("TASK_COST_P95_RATIO_HIGH")
    if routing_degrade_passed is not bool(COST_THRESHOLDS["routing_degrade_passed_required"]):
        failed_checks.append("ROUTING_DEGRADE_FAILED")
    if degrade_availability < float(COST_THRESHOLDS["degrade_availability_min"]):
        failed_checks.append("DEGRADE_AVAILABILITY_LOW")
    if budget_alert_coverage < float(COST_THRESHOLDS["budget_alert_coverage_min"]):
        failed_checks.append("BUDGET_ALERT_COVERAGE_LOW")

    return {
        "gate": "cost",
        "dataset_id": dataset_id,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "thresholds": dict(COST_THRESHOLDS),
        "values": {
            "task_cost_p95": task_cost_p95,
            "baseline_task_cost_p95": baseline_task_cost_p95,
            "task_cost_p95_ratio": task_cost_p95_ratio,
            "routing_degrade_passed": routing_degrade_passed,
            "degrade_availability": degrade_availability,
            "budget_alert_coverage": budget_alert_coverage,
        },
    }
