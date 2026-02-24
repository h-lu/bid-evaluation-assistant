#!/usr/bin/env python3
"""Performance benchmark CLI.

Usage:
    python scripts/benchmark_performance.py [--iterations 20]

Runs API benchmarks against a local test server and reports P95 latencies.
Aligned with Gate D-2 performance gate thresholds.
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.performance_benchmark import BenchmarkResult, aggregate_to_gate_payload, run_benchmark
from app.performance_gates import PERFORMANCE_THRESHOLDS, evaluate_performance_gate
from app.store import store


def main() -> None:
    parser = argparse.ArgumentParser(description="Performance benchmark")
    parser.add_argument("--iterations", type=int, default=20, help="Iterations per benchmark")
    args = parser.parse_args()
    n = args.iterations

    store.reset()
    app = create_app()
    client = TestClient(app)
    headers = {"x-internal-debug": "true"}

    print(f"Running benchmarks ({n} iterations each)...\n")

    api_result = run_benchmark(
        "api_health",
        lambda: client.get("/api/v1/health"),
        iterations=n,
    )

    retrieval_result = run_benchmark(
        "retrieval_query",
        lambda: client.post(
            "/api/v1/retrieval/query",
            json={
                "project_id": "prj_b", "supplier_id": "sup_b",
                "query": "资质要求", "query_type": "fact",
                "top_k": 10, "doc_scope": [],
            },
        ),
        iterations=n,
    )

    counter = {"i": 0}

    def do_upload():
        counter["i"] += 1
        client.post(
            "/api/v1/documents/upload",
            data={"project_id": "prj_b", "supplier_id": "sup_b", "doc_type": "bid"},
            files={"file": ("b.pdf", BytesIO(b"%PDF-1.4 bench"), "application/pdf")},
            headers={"Idempotency-Key": f"bench_{counter['i']}"},
        )

    parse_result = run_benchmark("parse_upload", do_upload, iterations=n)

    eval_counter = {"i": 0}

    def do_eval():
        eval_counter["i"] += 1
        client.post(
            "/api/v1/evaluations",
            json={
                "project_id": "prj_b", "supplier_id": "sup_b",
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            },
            headers={"Idempotency-Key": f"eval_bench_{eval_counter['i']}"},
        )

    evaluation_result = run_benchmark("evaluation_create", do_eval, iterations=n)

    for r in [api_result, retrieval_result, parse_result, evaluation_result]:
        d = r.to_dict()
        print(f"  {d['name']:25s}  P95={d['p95_ms']:8.1f}ms  mean={d['mean_ms']:8.1f}ms  errors={d['errors']}")

    payload = aggregate_to_gate_payload(
        api_result=api_result,
        retrieval_result=retrieval_result,
        parse_result=parse_result,
        evaluation_result=evaluation_result,
    )
    gate_result = evaluate_performance_gate(
        dataset_id="bench_local",
        metrics=payload["metrics"],
    )

    print(f"\nPerformance Gate: {'PASSED' if gate_result['passed'] else 'BLOCKED'}")
    if gate_result["failed_checks"]:
        for check in gate_result["failed_checks"]:
            print(f"  FAIL: {check}")
    print(f"\nThresholds: {PERFORMANCE_THRESHOLDS}")

    sys.exit(0 if gate_result["passed"] else 1)


if __name__ == "__main__":
    main()
