from __future__ import annotations

from app.ops.slo_probe import evaluate_latency_slo, summarize_http_probe


def test_summarize_http_probe_reports_percentiles_and_error_rate():
    report = summarize_http_probe(
        latencies_ms=[120.0, 150.0, 210.0, 95.0, 130.0],
        status_codes=[200, 200, 503, 200, 200],
    )
    assert report["count"] == 5
    assert report["error_count"] == 1
    assert report["error_rate"] == 0.2
    assert report["p95_ms"] >= report["p50_ms"]
    assert report["max_ms"] == 210.0


def test_evaluate_latency_slo_returns_gate_result():
    summary = {
        "count": 5,
        "error_count": 0,
        "error_rate": 0.0,
        "p50_ms": 110.0,
        "p95_ms": 140.0,
        "max_ms": 155.0,
        "avg_ms": 118.0,
    }
    passed = evaluate_latency_slo(summary=summary, p95_limit_ms=150.0, error_rate_limit=0.01)
    assert passed["passed"] is True
    assert passed["failed_reasons"] == []

    failed = evaluate_latency_slo(summary=summary, p95_limit_ms=100.0, error_rate_limit=0.01)
    assert failed["passed"] is False
    assert any("p95" in item for item in failed["failed_reasons"])
