"""Configurable reranker: cross-encoder, API, or TF-IDF fallback.

Backends controlled by RERANK_BACKEND env var:
  - simple         : lightweight TF-IDF reranker with CJK support
  - cross-encoder  : local cross-encoder model via sentence-transformers
  - cohere/jina    : API-based rerank (placeholder)

Cross-encoder timeout controlled by RERANK_TIMEOUT_MS (default 2000).
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

logger = logging.getLogger(__name__)

RERANK_BACKEND = os.environ.get("RERANK_BACKEND", "simple").strip().lower()
RERANK_MODEL_NAME = os.environ.get(
    "RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "0"))
RERANK_TIMEOUT_MS = int(os.environ.get("RERANK_TIMEOUT_MS", "2000"))

_cross_encoder_cache: dict[str, Any] = {}

_CJK_RANGES = (
    "\u4e00-\u9fff"    # CJK Unified Ideographs
    "\u3400-\u4dbf"    # CJK Unified Ideographs Extension A
    "\uf900-\ufaff"    # CJK Compatibility Ideographs
)
_TOKENIZE_RE = re.compile(
    rf"[{_CJK_RANGES}]|[a-zA-Z0-9]+",
)


def rerank_items(
    query: str,
    items: list[dict[str, Any]],
    *,
    backend: str | None = None,
    top_k: int = 0,
) -> list[dict[str, Any]]:
    """Rerank *items* against *query*. Returns copies with ``score_rerank`` set."""
    if not items:
        return []

    be = (backend or RERANK_BACKEND).strip().lower()
    k = top_k or RERANK_TOP_K

    if be == "cross-encoder":
        result = _rerank_cross_encoder(query, items)
    elif be in ("cohere", "jina"):
        result = _rerank_api(query, items, backend=be)
    else:
        result = _rerank_simple(query, items)

    if k > 0:
        result = result[:k]
    return result


# ---------------------------------------------------------------------------
# Tokenisation (CJK-aware)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Split text into tokens: each CJK character is its own token,
    contiguous Latin/digit sequences form a single token. Lowercased."""
    return [t.lower() for t in _TOKENIZE_RE.findall(text)]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _rerank_simple(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """TF-IDF style reranker: ``score_rerank = 0.4 * tfidf + 0.6 * score_raw``."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        ranked = []
        for item in items:
            copied = dict(item)
            copied["score_rerank"] = round(float(copied.get("score_raw", 0.5)), 4)
            ranked.append(copied)
        return sorted(ranked, key=lambda x: float(x.get("score_rerank", 0)), reverse=True)

    query_tf = Counter(query_tokens)
    n_docs = len(items)

    doc_tokens_list = [_tokenize(str(item.get("text", ""))) for item in items]

    df: Counter[str] = Counter()
    for tokens in doc_tokens_list:
        df.update(set(tokens))

    ranked: list[dict[str, Any]] = []
    for item, doc_tokens in zip(items, doc_tokens_list):
        if not doc_tokens:
            tfidf_score = 0.0
        else:
            doc_tf = Counter(doc_tokens)
            score_sum = 0.0
            for term, q_count in query_tf.items():
                if term not in doc_tf:
                    continue
                tf = doc_tf[term] / len(doc_tokens)
                idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1.0
                score_sum += q_count * tf * idf
            max_possible = sum(
                q * (1.0 * (math.log((n_docs + 1) / 2) + 1.0))
                for q in query_tf.values()
            )
            tfidf_score = score_sum / max_possible if max_possible > 0 else 0.0

        score_raw = float(item.get("score_raw", 0.5))
        combined = 0.4 * tfidf_score + 0.6 * score_raw

        copied = dict(item)
        copied["score_rerank"] = round(min(1.0, combined), 4)
        ranked.append(copied)

    return sorted(ranked, key=lambda x: float(x.get("score_rerank", 0)), reverse=True)


def _rerank_cross_encoder(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cross-encoder reranker using sentence-transformers ``CrossEncoder``.

    Wraps ``model.predict`` in a timeout (RERANK_TIMEOUT_MS). Falls back to
    the TF-IDF simple reranker on timeout or import failure.
    """
    try:
        from sentence_transformers import CrossEncoder  # noqa: F811
    except ImportError:
        logger.warning("sentence-transformers not installed; falling back to simple reranker")
        return _rerank_simple(query, items)

    model = _get_cross_encoder(RERANK_MODEL_NAME)
    pairs = [(query, str(item.get("text", ""))) for item in items]

    timeout_s = RERANK_TIMEOUT_MS / 1000.0
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(model.predict, pairs)
            raw_scores = future.result(timeout=timeout_s)
    except FuturesTimeoutError:
        logger.warning(
            "cross-encoder predict timed out after %dms; falling back to simple reranker",
            RERANK_TIMEOUT_MS,
        )
        return _rerank_simple(query, items)

    ranked: list[dict[str, Any]] = []
    for item, raw in zip(items, raw_scores):
        copied = dict(item)
        copied["score_rerank"] = round(_sigmoid(float(raw)), 4)
        ranked.append(copied)
    return sorted(ranked, key=lambda x: float(x.get("score_rerank", 0.0)), reverse=True)


def _rerank_api(
    query: str, items: list[dict[str, Any]], *, backend: str = "cohere"
) -> list[dict[str, Any]]:
    """Placeholder for API-based rerankers (Cohere / Jina)."""
    logger.warning("API rerank backend '%s' not yet implemented; falling back to simple", backend)
    return _rerank_simple(query, items)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ez = math.exp(x)
    return ez / (1.0 + ez)


def _get_cross_encoder(model_name: str) -> Any:
    if model_name not in _cross_encoder_cache:
        from sentence_transformers import CrossEncoder
        _cross_encoder_cache[model_name] = CrossEncoder(model_name)
    return _cross_encoder_cache[model_name]
