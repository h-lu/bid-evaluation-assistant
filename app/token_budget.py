"""Token budget management for evidence packing.

Spec: retrieval-and-scoring-spec §6.3
  - single criteria <= 6 000 tokens
  - full report     <= 24 000 tokens
  - over-budget trim order: low relevance -> redundant source
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SINGLE_CRITERIA_BUDGET = int(os.environ.get("EVIDENCE_SINGLE_BUDGET", "6000"))
TOTAL_REPORT_BUDGET = int(os.environ.get("EVIDENCE_TOTAL_BUDGET", "24000"))
MIN_EVIDENCE_PER_CRITERIA = 2
MAX_EVIDENCE_PER_CRITERIA = 8

_encoder: Any = None
_encoder_loaded = False


def _get_encoder() -> Any:
    global _encoder, _encoder_loaded
    if not _encoder_loaded:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _encoder = None
        _encoder_loaded = True
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens. Uses tiktoken (cl100k_base) when available, else ~3.5 chars/token."""
    enc = _get_encoder()
    if enc is None:
        return max(1, len(text.encode("utf-8")) // 4)
    return len(enc.encode(text))


def trim_evidence_to_budget(
    evidence: list[dict[str, Any]],
    max_tokens: int = 0,
) -> list[dict[str, Any]]:
    """Trim a single criteria's evidence list to fit within *max_tokens*.

    Keeps highest ``score_raw`` items first.  Always tries to keep at least
    ``MIN_EVIDENCE_PER_CRITERIA`` items.
    """
    budget = max_tokens or SINGLE_CRITERIA_BUDGET
    if not evidence:
        return evidence

    ranked = sorted(
        evidence,
        key=lambda x: float(x.get("score_raw", 0.0)),
        reverse=True,
    )
    ranked = ranked[:MAX_EVIDENCE_PER_CRITERIA]

    result: list[dict[str, Any]] = []
    total = 0
    for item in ranked:
        tokens = count_tokens(item.get("text", ""))
        if total + tokens > budget and len(result) >= MIN_EVIDENCE_PER_CRITERIA:
            break
        result.append(item)
        total += tokens
    return result


def apply_report_budget(
    criteria_evidence: dict[str, list[dict[str, Any]]],
    max_tokens: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """Trim all criteria evidence to fit within total report budget.

    Steps:
      1. Apply per-criteria budgets.
      2. If total still exceeds report budget, remove lowest-scored items
         across all criteria (keeping ``MIN_EVIDENCE_PER_CRITERIA`` per criteria).
    """
    budget = max_tokens or TOTAL_REPORT_BUDGET

    trimmed: dict[str, list[dict[str, Any]]] = {
        cid: trim_evidence_to_budget(ev) for cid, ev in criteria_evidence.items()
    }

    total = _total_tokens(trimmed)
    if total <= budget:
        return trimmed

    scored_refs: list[tuple[str, int, float]] = []
    for cid, ev_list in trimmed.items():
        for idx, item in enumerate(ev_list):
            scored_refs.append((cid, idx, float(item.get("score_raw", 0.0))))
    scored_refs.sort(key=lambda x: x[2])

    removed: set[tuple[str, int]] = set()
    for cid, idx, _ in scored_refs:
        if total <= budget:
            break
        remaining = sum(1 for i, it in enumerate(trimmed[cid]) if (cid, i) not in removed)
        if remaining <= MIN_EVIDENCE_PER_CRITERIA:
            continue
        tokens = count_tokens(trimmed[cid][idx].get("text", ""))
        removed.add((cid, idx))
        total -= tokens

    result: dict[str, list[dict[str, Any]]] = {}
    for cid, ev_list in trimmed.items():
        result[cid] = [it for i, it in enumerate(ev_list) if (cid, i) not in removed]
    return result


def _total_tokens(criteria_evidence: dict[str, list[dict[str, Any]]]) -> int:
    return sum(
        count_tokens(item.get("text", ""))
        for ev_list in criteria_evidence.values()
        for item in ev_list
    )
