"""Performance benchmark tests.

Aligned with:
  - retrieval-scoring-spec §12.2 online thresholds
  - Gate D-2 performance gate:
      api_p95_s        <= 1.5
      retrieval_p95_s  <= 4.0
      parse_50p_p95_s  <= 180.0
      evaluation_p95_s <= 120.0
"""

from __future__ import annotations

import time
from io import BytesIO

from app.performance_benchmark import (
    BenchmarkResult,
    aggregate_to_gate_payload,
    run_benchmark,
)

# ---------------------------------------------------------------------------
# Unit tests for benchmark utilities
# ---------------------------------------------------------------------------


class TestBenchmarkResult:
    def test_percentile_computation(self):
        result = BenchmarkResult(name="test")
        result.latencies_ms = list(range(1, 101))
        assert result.count == 100
        assert 49 <= result.p50_ms <= 51
        assert 94 <= result.p95_ms <= 96
        assert 98 <= result.p99_ms <= 100
        assert abs(result.mean_ms - 50.5) < 0.1

    def test_empty_result(self):
        result = BenchmarkResult(name="empty")
        assert result.p50_ms == 0.0
        assert result.p95_ms == 0.0
        assert result.p99_ms == 0.0
        assert result.mean_ms == 0.0
        assert result.p95_s == 0.0

    def test_to_dict(self):
        result = BenchmarkResult(name="api", latencies_ms=[10.0, 20.0, 30.0])
        d = result.to_dict()
        assert d["name"] == "api"
        assert d["count"] == 3
        assert d["p95_ms"] > 0

    def test_single_element(self):
        result = BenchmarkResult(name="one", latencies_ms=[42.0])
        assert result.p50_ms == 42.0
        assert result.p95_ms == 42.0


class TestRunBenchmark:
    def test_benchmark_records_latencies(self):
        counter = {"n": 0}

        def work():
            counter["n"] += 1
            time.sleep(0.001)

        result = run_benchmark("test_work", work, iterations=5)
        assert result.count == 5
        assert counter["n"] == 5
        assert all(lat > 0 for lat in result.latencies_ms)
        assert result.errors == 0

    def test_benchmark_records_errors(self):
        def failing():
            raise ValueError("boom")

        result = run_benchmark("failing", failing, iterations=3)
        assert result.count == 3
        assert result.errors == 3


class TestAggregateToGatePayload:
    def test_payload_schema_matches_gate(self):
        api = BenchmarkResult(name="api", latencies_ms=[100, 200, 300])
        retrieval = BenchmarkResult(name="retrieval", latencies_ms=[500, 600, 700])
        parse = BenchmarkResult(name="parse", latencies_ms=[1000, 2000, 3000])
        evaluation = BenchmarkResult(name="evaluation", latencies_ms=[5000, 6000, 7000])

        payload = aggregate_to_gate_payload(
            api_result=api,
            retrieval_result=retrieval,
            parse_result=parse,
            evaluation_result=evaluation,
            dataset_id="bench_test",
        )
        metrics = payload["metrics"]
        assert "api_p95_s" in metrics
        assert "retrieval_p95_s" in metrics
        assert "parse_50p_p95_s" in metrics
        assert "evaluation_p95_s" in metrics
        assert "queue_dlq_rate" in metrics
        assert "cache_hit_rate" in metrics
        assert payload["dataset_id"] == "bench_test"


# ---------------------------------------------------------------------------
# API baseline benchmarks (lightweight, run in CI)
# ---------------------------------------------------------------------------


class TestAPIPerformanceBaseline:
    """Verify API responses are fast enough under mock/in-memory conditions.

    These tests use the TestClient (in-process) so they measure application
    logic overhead, not network latency. The P95 thresholds are set very
    conservatively for CI: real production thresholds are in Gate D-2.
    """

    def test_health_endpoint_under_100ms_p95(self, client):
        result = run_benchmark(
            "health",
            lambda: client.get("/api/v1/health"),
            iterations=20,
        )
        assert result.p95_ms < 100, f"health P95 = {result.p95_ms:.1f}ms"
        assert result.errors == 0

    def test_list_projects_under_200ms_p95(self, client):
        result = run_benchmark(
            "list_projects",
            lambda: client.get("/api/v1/projects"),
            iterations=20,
        )
        assert result.p95_ms < 200, f"list_projects P95 = {result.p95_ms:.1f}ms"
        assert result.errors == 0

    def test_upload_document_under_500ms_p95(self, client):
        file_bytes = b"%PDF-1.4 benchmark content"
        counter = {"i": 0}

        def do_upload():
            counter["i"] += 1
            client.post(
                "/api/v1/documents/upload",
                data={"project_id": "prj_bench", "supplier_id": "sup_bench", "doc_type": "bid"},
                files={"file": ("bench.pdf", BytesIO(file_bytes), "application/pdf")},
                headers={"Idempotency-Key": f"idem_bench_{counter['i']}"},
            )

        result = run_benchmark("upload_document", do_upload, iterations=10)
        assert result.p95_ms < 500, f"upload P95 = {result.p95_ms:.1f}ms"
        assert result.errors == 0


# ---------------------------------------------------------------------------
# SSOT alignment
# ---------------------------------------------------------------------------


class TestSSOTPerformanceAlignment:
    """Verify Gate D-2 thresholds match SSOT §12.2."""

    def test_performance_thresholds_match_ssot(self):
        from app.performance_gates import PERFORMANCE_THRESHOLDS

        assert PERFORMANCE_THRESHOLDS["api_p95_s_max"] == 1.5
        assert PERFORMANCE_THRESHOLDS["retrieval_p95_s_max"] == 4.0
        assert PERFORMANCE_THRESHOLDS["parse_50p_p95_s_max"] == 180.0
        assert PERFORMANCE_THRESHOLDS["evaluation_p95_s_max"] == 120.0
        assert PERFORMANCE_THRESHOLDS["queue_dlq_rate_max"] == 0.01
        assert PERFORMANCE_THRESHOLDS["cache_hit_rate_min"] == 0.70

    def test_gate_passes_with_good_metrics(self, client):
        resp = client.post(
            "/api/v1/internal/performance-gates/evaluate",
            headers={"x-internal-debug": "true"},
            json={
                "dataset_id": "ds_perf_baseline",
                "metrics": {
                    "api_p95_s": 0.8,
                    "retrieval_p95_s": 2.5,
                    "parse_50p_p95_s": 90.0,
                    "evaluation_p95_s": 60.0,
                    "queue_dlq_rate": 0.005,
                    "cache_hit_rate": 0.80,
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["passed"] is True

    def test_gate_blocks_when_thresholds_exceeded(self, client):
        resp = client.post(
            "/api/v1/internal/performance-gates/evaluate",
            headers={"x-internal-debug": "true"},
            json={
                "dataset_id": "ds_perf_bad",
                "metrics": {
                    "api_p95_s": 2.0,
                    "retrieval_p95_s": 5.0,
                    "parse_50p_p95_s": 200.0,
                    "evaluation_p95_s": 150.0,
                    "queue_dlq_rate": 0.02,
                    "cache_hit_rate": 0.50,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["passed"] is False
        assert len(data["failed_checks"]) == 6
