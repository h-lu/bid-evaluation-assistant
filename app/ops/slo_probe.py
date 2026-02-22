from __future__ import annotations

import math
from typing import Any


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if ratio <= 0:
        return min(values)
    if ratio >= 1:
        return max(values)
    ordered = sorted(values)
    rank = max(1, math.ceil(ratio * len(ordered)))
    return float(ordered[rank - 1])


def summarize_http_probe(*, latencies_ms: list[float], status_codes: list[int]) -> dict[str, float | int]:
    if len(latencies_ms) != len(status_codes):
        raise ValueError("latencies_ms and status_codes must have the same length")
    count = len(latencies_ms)
    if count == 0:
        return {
            "count": 0,
            "error_count": 0,
            "error_rate": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "max_ms": 0.0,
            "avg_ms": 0.0,
        }
    error_count = sum(1 for status in status_codes if status >= 400)
    return {
        "count": count,
        "error_count": error_count,
        "error_rate": error_count / count,
        "p50_ms": _percentile(latencies_ms, 0.50),
        "p95_ms": _percentile(latencies_ms, 0.95),
        "max_ms": max(latencies_ms),
        "avg_ms": sum(latencies_ms) / count,
    }


def evaluate_latency_slo(
    *,
    summary: dict[str, Any],
    p95_limit_ms: float,
    error_rate_limit: float,
) -> dict[str, Any]:
    failures: list[str] = []
    p95 = float(summary.get("p95_ms", 0.0))
    error_rate = float(summary.get("error_rate", 0.0))
    if p95 > p95_limit_ms:
        failures.append(f"p95 exceeded: {p95:.2f}ms > {p95_limit_ms:.2f}ms")
    if error_rate > error_rate_limit:
        failures.append(f"error_rate exceeded: {error_rate:.4f} > {error_rate_limit:.4f}")
    return {
        "passed": len(failures) == 0,
        "failed_reasons": failures,
        "p95_limit_ms": p95_limit_ms,
        "error_rate_limit": error_rate_limit,
    }
