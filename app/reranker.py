"""Configurable reranker: cross-encoder, API, or simple stub.

Backends controlled by RERANK_BACKEND env var:
  - simple   : stub (+0.05 on score_raw), safe for tests
  - cross-encoder : local cross-encoder model via sentence-transformers
  - cohere/jina   : API-based rerank (placeholder)
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

logger = logging.getLogger(__name__)

RERANK_BACKEND = os.environ.get("RERANK_BACKEND", "simple").strip().lower()
RERANK_MODEL_NAME = os.environ.get(
    "RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "0"))

_cross_encoder_cache: dict[str, Any] = {}


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
        result = _rerank_simple(items)

    if k > 0:
        result = result[:k]
    return result


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _rerank_simple(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stub reranker: ``score_rerank = min(1.0, score_raw + 0.05)``."""
    ranked: list[dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        copied["score_rerank"] = min(1.0, float(copied.get("score_raw", 0.5)) + 0.05)
        ranked.append(copied)
    return sorted(ranked, key=lambda x: float(x.get("score_rerank", 0.0)), reverse=True)


def _rerank_cross_encoder(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cross-encoder reranker using sentence-transformers ``CrossEncoder``."""
    try:
        from sentence_transformers import CrossEncoder  # noqa: F811
    except ImportError:
        logger.warning("sentence-transformers not installed; falling back to simple reranker")
        return _rerank_simple(items)

    model = _get_cross_encoder(RERANK_MODEL_NAME)
    pairs = [(query, str(item.get("text", ""))) for item in items]
    raw_scores = model.predict(pairs)

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
    return _rerank_simple(items)


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
