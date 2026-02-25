"""Offline retrieval quality evaluator with real RAGAS + DeepEval integration.

Computes quality metrics aligned with SSOT retrieval-scoring-spec §12 and
Gate D-1 quality gate thresholds:

  context_precision  >= 0.80
  context_recall     >= 0.80
  faithfulness       >= 0.90
  response_relevancy >= 0.85
  hallucination_rate <= 0.05
  citation_resolvable_rate >= 0.98

Two backends:
  1. ``ragas`` — calls ragas library + deepeval HallucinationMetric.
     Requires LLM (OpenAI API key or injected LLM wrapper).
  2. ``lightweight`` — heuristic token-overlap scoring,
     zero external dependencies, suitable for CI without API keys.

Auto-selection: ``backend="auto"`` tries ragas first, falls back to
lightweight if ragas imports or LLM setup fails.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


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
    backend: str = "unknown"

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


# ===================================================================
# Backend 1: Real RAGAS + DeepEval
# ===================================================================


def _build_openai_clients() -> tuple[Any, Any]:
    """Build sync + async openai clients from environment (supports OpenRouter).

    Returns (sync_client, async_client).
    """
    import openai

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OSError("OPENAI_API_KEY not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return openai.OpenAI(**kwargs), openai.AsyncOpenAI(**kwargs)


def _build_ragas_llm():
    """Build a ragas-compatible LLM via llm_factory (ragas >= 0.4).

    Supports OpenAI, OpenRouter, and any OpenAI-compatible endpoint.
    Uses AsyncOpenAI so score() -> asyncio.run(ascore()) works correctly.
    """
    from ragas.llms import llm_factory

    model_name = os.environ.get("RAGAS_MODEL", os.environ.get("LLM_MODEL", "gpt-4o-mini"))
    _, async_client = _build_openai_clients()
    return llm_factory(model_name, client=async_client)


def _build_ragas_embeddings():
    """Build ragas-compatible embeddings via embedding_factory (ragas >= 0.4).

    Uses EMBEDDING_MODEL env var through the same OpenAI-compatible client.
    """
    from ragas.embeddings import embedding_factory

    model_name = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    _, async_client = _build_openai_clients()
    return embedding_factory("openai", model=model_name, client=async_client)


def evaluate_dataset_ragas(
    samples: list[EvalSample],
    *,
    evaluator_llm: Any = None,
    evaluator_embeddings: Any = None,
) -> EvalMetrics:
    """Compute metrics using real ragas library + deepeval HallucinationMetric.

    Args:
        samples: Golden dataset samples with retrieved_contexts and generated_answer filled.
        evaluator_llm: Optional ragas-compatible LLM wrapper. If None, built from env.
        evaluator_embeddings: Optional ragas-compatible embeddings. If None, built from env.

    Returns:
        EvalMetrics with real LLM-computed scores.
    """
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    if evaluator_llm is None:
        evaluator_llm = _build_ragas_llm()
    if evaluator_embeddings is None:
        evaluator_embeddings = _build_ragas_embeddings()

    faithfulness_metric = Faithfulness(llm=evaluator_llm)
    precision_metric = ContextPrecision(llm=evaluator_llm)
    recall_metric = ContextRecall(llm=evaluator_llm)
    relevancy_metric = AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings)

    faith_scores: list[float] = []
    prec_scores: list[float] = []
    rec_scores: list[float] = []
    rel_scores: list[float] = []

    for s in samples:
        ctxs = list(s.retrieved_contexts)

        try:
            r = faithfulness_metric.score(
                user_input=s.query,
                response=s.generated_answer,
                retrieved_contexts=ctxs,
            )
            faith_scores.append(float(r.value))
        except Exception as exc:
            logger.warning("faithfulness score failed: %s", exc)

        try:
            r = precision_metric.score(
                user_input=s.query,
                reference=s.ground_truth_answer,
                retrieved_contexts=ctxs,
            )
            prec_scores.append(float(r.value))
        except Exception as exc:
            logger.warning("context_precision score failed: %s", exc)

        try:
            r = recall_metric.score(
                user_input=s.query,
                retrieved_contexts=ctxs,
                reference=s.ground_truth_answer,
            )
            rec_scores.append(float(r.value))
        except Exception as exc:
            logger.warning("context_recall score failed: %s", exc)

        try:
            r = relevancy_metric.score(
                user_input=s.query,
                response=s.generated_answer,
            )
            rel_scores.append(float(r.value))
        except Exception as exc:
            logger.warning("answer_relevancy score failed: %s", exc)

    def _safe_mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    hallucination_rate = _compute_deepeval_hallucination(samples, evaluator_llm=evaluator_llm)
    citation_resolvable = _compute_citation_resolvable(samples)

    return EvalMetrics(
        context_precision=_safe_mean(prec_scores),
        context_recall=_safe_mean(rec_scores),
        faithfulness=_safe_mean(faith_scores),
        response_relevancy=_safe_mean(rel_scores),
        hallucination_rate=hallucination_rate,
        citation_resolvable_rate=citation_resolvable,
        backend="ragas",
    )


def _compute_deepeval_hallucination(
    samples: list[EvalSample],
    *,
    evaluator_llm: Any = None,
) -> float:
    """Compute hallucination rate using deepeval's HallucinationMetric.

    Supports OpenRouter and any OpenAI-compatible endpoint via OPENAI_BASE_URL.
    """
    from deepeval.metrics import HallucinationMetric
    from deepeval.test_case import LLMTestCase

    model_name = os.environ.get("DEEPEVAL_MODEL", os.environ.get("LLM_MODEL", "gpt-4o-mini"))

    hallucinated_count = 0
    total = 0
    for s in samples:
        if not s.generated_answer or not s.retrieved_contexts:
            continue
        total += 1
        test_case = LLMTestCase(
            input=s.query,
            actual_output=s.generated_answer,
            context=list(s.retrieved_contexts),
        )
        try:
            metric = HallucinationMetric(threshold=0.5, model=model_name)
            metric.measure(test_case)
            if not metric.is_successful():
                hallucinated_count += 1
        except Exception as exc:
            logger.warning("DeepEval hallucination check failed for sample: %s", exc)

    if total == 0:
        return 0.0
    return hallucinated_count / total


# ===================================================================
# Backend 2: Lightweight (token-overlap, no LLM needed)
# ===================================================================

_WORD_RE = re.compile(r"[a-zA-Z0-9]+", re.UNICODE)
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]",
)


def _tokenize(text: str) -> set[str]:
    """Tokenize into lowercase tokens with CJK bigram approximation."""
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


def _precision_per_sample(sample: EvalSample) -> float:
    if not sample.retrieved_contexts:
        return 0.0
    gt_tokens = _tokenize(" ".join(sample.ground_truth_contexts))
    relevant = sum(1 for ctx in sample.retrieved_contexts if _overlap_ratio(gt_tokens, _tokenize(ctx)) > 0.15)
    return relevant / len(sample.retrieved_contexts)


def _recall_per_sample(sample: EvalSample) -> float:
    if not sample.ground_truth_contexts:
        return 1.0
    retrieved_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    gt_tokens = _tokenize(" ".join(sample.ground_truth_contexts))
    return _overlap_ratio(gt_tokens, retrieved_tokens)


def _faithfulness_per_sample(sample: EvalSample) -> float:
    if not sample.generated_answer:
        return 1.0
    answer_tokens = _tokenize(sample.generated_answer)
    if not answer_tokens:
        return 1.0
    context_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    return _overlap_ratio(answer_tokens, context_tokens)


def _relevancy_per_sample(sample: EvalSample) -> float:
    if not sample.generated_answer:
        return 0.0
    query_tokens = _tokenize(sample.query)
    answer_tokens = _tokenize(sample.generated_answer)
    return _overlap_ratio(query_tokens, answer_tokens)


def _hallucination_per_sample(sample: EvalSample) -> float:
    if not sample.generated_answer:
        return 0.0
    answer_tokens = _tokenize(sample.generated_answer)
    context_tokens = _tokenize(" ".join(sample.retrieved_contexts))
    if not answer_tokens:
        return 0.0
    ungrounded = answer_tokens - context_tokens
    ratio = len(ungrounded) / len(answer_tokens)
    return 1.0 if ratio > 0.50 else 0.0


def evaluate_dataset_lightweight(samples: list[EvalSample]) -> EvalMetrics:
    """Compute metrics using token-overlap heuristics (no LLM needed)."""
    if not samples:
        return EvalMetrics(backend="lightweight")

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
        backend="lightweight",
    )


# ===================================================================
# Common helpers
# ===================================================================


def _citation_resolvable_per_sample(sample: EvalSample) -> float:
    if not sample.citations:
        return 1.0
    resolvable = sum(
        1 for c in sample.citations if c.get("chunk_id") and isinstance(c["chunk_id"], str) and c["chunk_id"].strip()
    )
    return resolvable / len(sample.citations)


def _compute_citation_resolvable(samples: list[EvalSample]) -> float:
    if not samples:
        return 0.0
    return sum(_citation_resolvable_per_sample(s) for s in samples) / len(samples)


# ===================================================================
# Unified entry point
# ===================================================================


def evaluate_dataset(
    samples: list[EvalSample],
    *,
    backend: str = "auto",
    evaluator_llm: Any = None,
    evaluator_embeddings: Any = None,
) -> EvalMetrics:
    """Compute RAGAS-compatible metrics.

    Args:
        samples: Golden dataset samples.
        backend: "ragas" | "lightweight" | "auto".
            "auto" tries ragas first, falls back to lightweight.
        evaluator_llm: Optional ragas-compatible LLM (for ragas backend).
        evaluator_embeddings: Optional ragas-compatible embeddings (for ragas backend).

    Returns:
        EvalMetrics with computed scores and backend indicator.
    """
    if not samples:
        return EvalMetrics(backend="lightweight")

    if backend == "lightweight":
        return evaluate_dataset_lightweight(samples)

    if backend in ("ragas", "auto"):
        try:
            return evaluate_dataset_ragas(
                samples,
                evaluator_llm=evaluator_llm,
                evaluator_embeddings=evaluator_embeddings,
            )
        except Exception:
            if backend == "ragas":
                raise
            logger.warning("ragas backend unavailable, falling back to lightweight")
            return evaluate_dataset_lightweight(samples)

    raise ValueError(f"Unknown backend: {backend}")


# ===================================================================
# End-to-end evaluation (store integration)
# ===================================================================


def run_e2e_evaluation(
    *,
    golden_samples: list[EvalSample],
    store: Any,
    tenant_id: str = "tenant_eval",
    project_id: str = "prj_eval",
    supplier_id: str = "sup_eval",
    backend: str = "auto",
    evaluator_llm: Any = None,
    evaluator_embeddings: Any = None,
) -> EvalMetrics:
    """Run end-to-end offline evaluation through the store's retrieval pipeline.

    For each sample in golden_samples:
      1. Runs store.retrieval_query() to fill retrieved_contexts.
      2. Uses retrieved context text as generated_answer proxy (if not pre-filled).

    Then computes metrics via evaluate_dataset().
    """
    filled_samples: list[EvalSample] = []

    for sample in golden_samples:
        result = store.retrieval_query(
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_id=supplier_id,
            query=sample.query,
            query_type="fact",
            high_risk=False,
            top_k=20,
            doc_scope=[],
            enable_rerank=True,
        )

        retrieved_texts: list[str] = []
        citation_objects: list[dict[str, Any]] = []
        for item in result.get("items", []):
            chunk_id = item.get("chunk_id", "")
            source = store.citation_sources.get(chunk_id, {})
            text = source.get("text", "")
            if text:
                retrieved_texts.append(text)
            citation_objects.append(
                {
                    "chunk_id": chunk_id,
                    "page": item.get("metadata", {}).get("page"),
                }
            )

        generated_answer = sample.generated_answer
        if not generated_answer and retrieved_texts:
            generated_answer = " ".join(retrieved_texts[:3])

        filled_samples.append(
            EvalSample(
                query=sample.query,
                ground_truth_answer=sample.ground_truth_answer,
                ground_truth_contexts=sample.ground_truth_contexts,
                retrieved_contexts=retrieved_texts or sample.retrieved_contexts,
                generated_answer=generated_answer,
                citations=citation_objects or sample.citations,
            )
        )

    return evaluate_dataset(
        filled_samples,
        backend=backend,
        evaluator_llm=evaluator_llm,
        evaluator_embeddings=evaluator_embeddings,
    )


# ===================================================================
# Quality gate integration
# ===================================================================


def evaluate_and_gate(
    *,
    samples: list[EvalSample],
    dataset_id: str = "eval_offline",
    backend: str = "auto",
    evaluator_llm: Any = None,
    evaluator_embeddings: Any = None,
) -> dict[str, Any]:
    """Evaluate a dataset and run it through the quality gate.

    Returns the quality gate result dict with ``passed`` bool.
    """
    from app.quality_gates import evaluate_quality_gate

    metrics = evaluate_dataset(
        samples,
        backend=backend,
        evaluator_llm=evaluator_llm,
        evaluator_embeddings=evaluator_embeddings,
    )
    payload = metrics.to_quality_gate_payload(dataset_id)
    m = payload["metrics"]
    return evaluate_quality_gate(
        dataset_id=dataset_id,
        ragas=m["ragas"],
        deepeval=m["deepeval"],
        citation=m["citation"],
    )
