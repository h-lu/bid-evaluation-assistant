#!/usr/bin/env python3
"""Offline RAGAS evaluation CLI.

Usage:
    # Real RAGAS (requires OPENAI_API_KEY):
    python scripts/eval_ragas.py --dataset golden_qa.json --backend ragas

    # Lightweight (CI, no API key needed):
    python scripts/eval_ragas.py --dataset golden_qa.json --backend lightweight

    # Auto-detect (tries ragas, falls back to lightweight):
    python scripts/eval_ragas.py --demo

    # End-to-end through store retrieval pipeline:
    python scripts/eval_ragas.py --demo --e2e

Aligned with:
  - retrieval-scoring-spec §12 (precision/recall >= 0.80, faithfulness >= 0.90)
  - Gate D-1 quality gate thresholds
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import sys
from pathlib import Path

from app.ragas_evaluator import (
    EvalSample,
    evaluate_and_gate,
    evaluate_dataset,
    run_e2e_evaluation,
)


def _load_dataset(path: str) -> list[EvalSample]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    samples: list[EvalSample] = []
    for item in data:
        samples.append(
            EvalSample(
                query=item["query"],
                ground_truth_answer=item.get("ground_truth_answer", ""),
                ground_truth_contexts=item.get("ground_truth_contexts", []),
                retrieved_contexts=item.get("retrieved_contexts", []),
                generated_answer=item.get("generated_answer", ""),
                citations=item.get("citations", []),
            )
        )
    return samples


def _demo_samples() -> list[EvalSample]:
    return [
        EvalSample(
            query="投标人需要哪些资质要求",
            ground_truth_answer="投标人需提供ISO9001认证、注册资金不低于500万、近三年无重大安全事故",
            ground_truth_contexts=[
                "投标人须提供有效的ISO9001质量管理体系认证证书",
                "注册资金不低于500万元人民币",
                "近三年无重大安全事故记录",
            ],
            retrieved_contexts=[
                "投标人须提供有效的ISO9001质量管理体系认证证书复印件",
                "注册资金不低于500万元人民币的营业执照",
                "近三年无重大安全事故记录证明",
            ],
            generated_answer="投标人需提供ISO9001质量管理体系认证证书、注册资金不低于500万元人民币、近三年无重大安全事故记录",
            citations=[
                {"chunk_id": "chk_001", "page": 1},
                {"chunk_id": "chk_002", "page": 2},
                {"chunk_id": "chk_003", "page": 3},
            ],
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline RAGAS evaluation")
    parser.add_argument("--dataset", help="Path to golden QA dataset JSON")
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo samples")
    parser.add_argument("--dataset-id", default="eval_offline", help="Dataset ID for gate report")
    parser.add_argument(
        "--backend",
        choices=["ragas", "lightweight", "auto"],
        default="auto",
        help="Evaluation backend (default: auto)",
    )
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end through store retrieval")
    args = parser.parse_args()

    if args.dataset:
        samples = _load_dataset(args.dataset)
    elif args.demo:
        samples = _demo_samples()
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Evaluating {len(samples)} sample(s) [backend={args.backend}]...")

    if args.e2e:
        from app.store import store

        metrics = run_e2e_evaluation(
            golden_samples=samples,
            store=store,
            backend=args.backend,
        )
    else:
        metrics = evaluate_dataset(samples, backend=args.backend)

    print(f"  backend:                {metrics.backend}")
    print(f"  context_precision:      {metrics.context_precision:.4f}")
    print(f"  context_recall:         {metrics.context_recall:.4f}")
    print(f"  faithfulness:           {metrics.faithfulness:.4f}")
    print(f"  response_relevancy:     {metrics.response_relevancy:.4f}")
    print(f"  hallucination_rate:     {metrics.hallucination_rate:.4f}")
    print(f"  citation_resolvable:    {metrics.citation_resolvable_rate:.4f}")

    result = evaluate_and_gate(
        samples=samples,
        dataset_id=args.dataset_id,
        backend=args.backend,
    )
    passed = result["passed"]
    print(f"\nQuality Gate: {'PASSED' if passed else 'BLOCKED'}")
    if result["failed_checks"]:
        for check in result["failed_checks"]:
            print(f"  FAIL: {check}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
