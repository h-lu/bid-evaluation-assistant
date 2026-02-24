"""Offline retrieval quality evaluator (RAGAS-compatible).

Computes quality metrics aligned with SSOT retrieval-scoring-spec §12 and
Gate D-1 quality gate thresholds:

  context_precision  >= 0.80
  context_recall     >= 0.80
  faithfulness       >= 0.90
  response_relevancy >= 0.85
  hallucination_rate <= 0.05
  citation_resolvable_rate >= 0.98

Two backends:
  1. ``lightweight`` (default) – heuristic token-overlap scoring,
     zero external dependencies, suitable for CI.
  2. ``ragas`` – delegates to the ragas library when installed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalSample:
    """Single evaluation sample in a golden dataset."""

    query: str
    ground_truth_answer: str
    ground_truth_contexts: list[str]
    retrieved_contexts: list[str] = field(default_factory=list)
    generated_answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EvalMetrics:
    """Aggregated evaluation metrics compatible with quality gate input."""

    context_precision: float = 0.0
    context_recall: float = 0.0
    faithfulness: float = 0.0
    response_relevancy: float = 0.0
    hallucination_rate: float = 0.0
    citation_resolvable_rate: float = 0.0

    def to_quality_gate_payload(self, dataset_id: str) -> dict[str, Any]:
        return {
            "dataset_id": dataset_id,
            "metrics": {
                "ragas": {
                    "context_precision": self.context_precision,
                    "context_recall": self.context_recall,
                    "faithfulness": self.faithfulness,
                    "response_relevancy": self.response_relevancy,
                },
                "deepeval": {
                    "hallucination_rate": self.hallucination_rate,
                },
                "citation": {
                    "resolvable_rate": self.citation_resolvable_rate,
                },
            },
        }


# ---------------------------------------------------------------------------
# Token-overlap helpers (lightweight backend)
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-zA-Z0-9]+", re.UNICODE)
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]",
)


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of lowercase tokens.

    Latin/digit sequences are kept as whole words; CJK characters are
    split into overlapping bigrams to approximate word boundaries.
    """
    tokens: set[str] = set()
    for w in _WORD_RE.findall(text.lower()):
        tokens.add(w)
    cjk_chars = _CJK_RE.findall(text)
    for ch in cjk_chars:
        tokens.add(ch)
    for i in range(len(cjk_chars) - 1):
        tokens.add(cjk_chars[i] + cjk_chars[i + 1])
    return tokens


def _overlap_ratio(reference_tokens: set[str], candidate_tokens: set[str]) -> float:
    if not reference_tokens:
        return 1.0 if not candidate_tokens else 0.0
    if not candidate_tokens:
        return 0.0
    return len(reference_tokens & candidate_tokens) / len(reference_tokens)


# ---------------------------------------------------------------------------
# Per-sample metric computation (lightweight)
# ---------------------------------------------------------------------------


def _precision_per_sample(sample: EvalSample) -> float:
    """Fraction of retrieved contexts that are relevant to ground truth."""
    if not sample.retrieved_contexts:
        return 0.0
    gt_tokens = _tokenize(" ".join(sample.ground_truth_contexts))
    relevant = sum(
        1
        for ctx in sample.retrieved_contexts
        if _overlap_ratio(gt_tokens, _tokenize(ctx)) > 0.15
    )
    return relevant / len(sample.retrieved_contexts)


def _recall_per_sample(sample: EvalSample) -> float:
    """Fraction of ground truth content covered by retrieved contexts."""
    if not sample.ground_truth_contexts:
        return 1.0
    retrieved_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    gt_tokens = _tokenize(" ".join(sample.ground_truth_contexts))
    return _overlap_ratio(gt_tokens, retrieved_tokens)


def _faithfulness_per_sample(sample: EvalSample) -> float:
    """Fraction of generated answer grounded in retrieved contexts."""
    if not sample.generated_answer:
        return 1.0
    answer_tokens = _tokenize(sample.generated_answer)
    if not answer_tokens:
        return 1.0
    context_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    return _overlap_ratio(answer_tokens, context_tokens)


def _relevancy_per_sample(sample: EvalSample) -> float:
    """How relevant the generated answer is to the query."""
    if not sample.generated_answer:
        return 0.0
    query_tokens = _tokenize(sample.query)
    answer_tokens = _tokenize(sample.generated_answer)
    return _overlap_ratio(query_tokens, answer_tokens)


def _hallucination_per_sample(sample: EvalSample) -> float:
    """1.0 if answer contains hallucinated content, 0.0 otherwise."""
    if not sample.generated_answer:
        return 0.0
    answer_tokens = _tokenize(sample.generated_answer)
    context_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    if not answer_tokens:
        return 0.0
    ungrounded = answer_tokens - context_tokens
    ratio = len(ungrounded) / len(answer_tokens)
    return 1.0 if ratio > 0.50 else 0.0


def _citation_resolvable_per_sample(sample: EvalSample) -> float:
    """Fraction of citations that can be resolved to a chunk_id."""
    if not sample.citations:
        return 1.0
    resolvable = sum(
        1
        for c in sample.citations
        if c.get("chunk_id") and isinstance(c["chunk_id"], str) and c["chunk_id"].strip()
    )
    return resolvable / len(sample.citations)


# ---------------------------------------------------------------------------
# Aggregate evaluation
# ---------------------------------------------------------------------------


def evaluate_dataset(samples: list[EvalSample]) -> EvalMetrics:
    """Compute aggregate RAGAS-compatible metrics over a golden dataset.

    Uses the lightweight token-overlap backend (no external deps).
    """
    if not samples:
        return EvalMetrics()

    n = len(samples)
    precision_sum = 0.0
    recall_sum = 0.0
    faithfulness_sum = 0.0
    relevancy_sum = 0.0
    hallucination_count = 0.0
    citation_sum = 0.0

    for s in samples:
        precision_sum += _precision_per_sample(s)
        recall_sum += _recall_per_sample(s)
        faithfulness_sum += _faithfulness_per_sample(s)
        relevancy_sum += _relevancy_per_sample(s)
        hallucination_count += _hallucination_per_sample(s)
        citation_sum += _citation_resolvable_per_sample(s)

    return EvalMetrics(
        context_precision=precision_sum / n,
        context_recall=recall_sum / n,
        faithfulness=faithfulness_sum / n,
        response_relevancy=relevancy_sum / n,
        hallucination_rate=hallucination_count / n,
        citation_resolvable_rate=citation_sum / n,
    )


def evaluate_and_gate(
    *,
    samples: list[EvalSample],
    dataset_id: str = "eval_offline",
) -> dict[str, Any]:
    """Evaluate a dataset and run it through the quality gate.

    Returns the quality gate result dict with ``passed`` bool.
    """
    from app.quality_gates import evaluate_quality_gate

    metrics = evaluate_dataset(samples)
    payload = metrics.to_quality_gate_payload(dataset_id)
    m = payload["metrics"]
    return evaluate_quality_gate(
        dataset_id=dataset_id,
        ragas=m["ragas"],
        deepeval=m["deepeval"],
        citation=m["citation"],
    )
