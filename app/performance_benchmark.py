"""Performance benchmarking utilities.

Aligned with:
  - retrieval-scoring-spec §12.2 online thresholds
  - Gate D-2 performance gate thresholds:
      api_p95_s        <= 1.5
      retrieval_p95_s  <= 4.0
      parse_50p_p95_s  <= 180.0
      evaluation_p95_s <= 120.0
      queue_dlq_rate   <= 0.01
      cache_hit_rate   >= 0.70
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    """Timing results for a benchmark run."""

    name: str
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0

    @property
    def count(self) -> int:
        return len(self.latencies_ms)

    @property
    def p50_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.50)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.99)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def mean_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)

    @property
    def p95_s(self) -> float:
        return self.p95_ms / 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "errors": self.errors,
            "mean_ms": round(self.mean_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "p95_s": round(self.p95_s, 4),
        }


def run_benchmark(
    name: str,
    fn: Callable[[], Any],
    iterations: int = 10,
) -> BenchmarkResult:
    """Execute *fn* multiple times and record latencies."""
    result = BenchmarkResult(name=name)
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            fn()
        except Exception:
            result.errors += 1
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        result.latencies_ms.append(elapsed_ms)
    return result


def aggregate_to_gate_payload(
    *,
    api_result: BenchmarkResult,
    retrieval_result: BenchmarkResult,
    parse_result: BenchmarkResult,
    evaluation_result: BenchmarkResult,
    dlq_rate: float = 0.0,
    cache_hit_rate: float = 1.0,
    dataset_id: str = "bench_run",
) -> dict[str, Any]:
    """Build a performance gate payload from benchmark results."""
    return {
        "dataset_id": dataset_id,
        "metrics": {
            "api_p95_s": api_result.p95_s,
            "retrieval_p95_s": retrieval_result.p95_s,
            "parse_50p_p95_s": parse_result.p95_s,
            "evaluation_p95_s": evaluation_result.p95_s,
            "queue_dlq_rate": dlq_rate,
            "cache_hit_rate": cache_hit_rate,
        },
    }
