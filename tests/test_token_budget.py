"""Tests for app.token_budget – token counting and budget trimming."""

from __future__ import annotations

import pytest

from app.token_budget import (
    MAX_EVIDENCE_PER_CRITERIA,
    MIN_EVIDENCE_PER_CRITERIA,
    _dedup_by_document,
    apply_report_budget,
    count_tokens,
    trim_evidence_to_budget,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(
    n: int, text_len: int = 200, base_score: float = 0.5, doc_id: str | None = None,
) -> list[dict]:
    return [
        {
            "chunk_id": f"ck_{i}",
            "document_id": doc_id or f"doc_{i}",
            "score_raw": round(base_score + 0.05 * i, 3),
            "text": f"x{'あ' * text_len}",
            "page": 1,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------

class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") >= 0

    def test_short_english(self):
        n = count_tokens("hello world")
        assert 1 <= n <= 10

    def test_chinese_text(self):
        n = count_tokens("招标文件要求投标人具有一级资质")
        assert n >= 3

    def test_long_text_monotonic(self):
        short = count_tokens("abc")
        long_ = count_tokens("abc" * 1000)
        assert long_ > short


# ---------------------------------------------------------------------------
# trim_evidence_to_budget
# ---------------------------------------------------------------------------

class TestTrimEvidence:
    def test_empty_list(self):
        assert trim_evidence_to_budget([]) == []

    def test_within_budget_keeps_all(self):
        ev = _make_evidence(3, text_len=10)
        result = trim_evidence_to_budget(ev, max_tokens=100_000)
        assert len(result) == 3

    def test_over_budget_trims(self):
        ev = _make_evidence(20, text_len=500)
        result = trim_evidence_to_budget(ev, max_tokens=500)
        assert len(result) < 20

    def test_keeps_highest_scored(self):
        ev = _make_evidence(10, text_len=200)
        result = trim_evidence_to_budget(ev, max_tokens=500)
        scores = [it["score_raw"] for it in result]
        assert scores == sorted(scores, reverse=True)

    def test_keeps_min_evidence(self):
        ev = _make_evidence(5, text_len=5000)
        result = trim_evidence_to_budget(ev, max_tokens=1)
        assert len(result) >= MIN_EVIDENCE_PER_CRITERIA

    def test_caps_at_max_evidence(self):
        ev = _make_evidence(20, text_len=5)
        result = trim_evidence_to_budget(ev, max_tokens=100_000)
        assert len(result) <= MAX_EVIDENCE_PER_CRITERIA


# ---------------------------------------------------------------------------
# apply_report_budget
# ---------------------------------------------------------------------------

class TestApplyReportBudget:
    def test_within_budget(self):
        data = {
            "c1": _make_evidence(3, text_len=10),
            "c2": _make_evidence(3, text_len=10),
        }
        result = apply_report_budget(data, max_tokens=100_000)
        assert sum(len(v) for v in result.values()) == 6

    def test_over_budget_trims_global(self):
        data = {
            "c1": _make_evidence(10, text_len=500),
            "c2": _make_evidence(10, text_len=500),
        }
        result = apply_report_budget(data, max_tokens=500)
        total_items = sum(len(v) for v in result.values())
        assert total_items < 20

    def test_preserves_min_per_criteria(self):
        data = {
            "c1": _make_evidence(5, text_len=3000),
            "c2": _make_evidence(5, text_len=3000),
        }
        result = apply_report_budget(data, max_tokens=100)
        for cid, ev_list in result.items():
            assert len(ev_list) >= MIN_EVIDENCE_PER_CRITERIA

    def test_multiple_criteria_keys_preserved(self):
        data = {
            "c1": _make_evidence(2, text_len=10),
            "c2": _make_evidence(2, text_len=10),
            "c3": _make_evidence(2, text_len=10),
        }
        result = apply_report_budget(data, max_tokens=100_000)
        assert set(result.keys()) == {"c1", "c2", "c3"}


# ---------------------------------------------------------------------------
# _dedup_by_document (P1-6: redundant source trimming)
# ---------------------------------------------------------------------------

class TestDedupByDocument:
    def test_removes_duplicates_keeps_highest(self):
        items = [
            {"chunk_id": "a", "document_id": "d1", "score_raw": 0.9},
            {"chunk_id": "b", "document_id": "d1", "score_raw": 0.8},
            {"chunk_id": "c", "document_id": "d2", "score_raw": 0.7},
        ]
        result = _dedup_by_document(items)
        assert len(result) == 2
        ids = {r["chunk_id"] for r in result}
        assert "a" in ids
        assert "c" in ids

    def test_no_document_id_kept(self):
        items = [
            {"chunk_id": "a", "score_raw": 0.9},
            {"chunk_id": "b", "score_raw": 0.8},
        ]
        result = _dedup_by_document(items)
        assert len(result) == 2

    def test_retains_duplicates_to_meet_minimum(self):
        items = [
            {"chunk_id": "a", "document_id": "d1", "score_raw": 0.9},
            {"chunk_id": "b", "document_id": "d1", "score_raw": 0.8},
        ]
        result = _dedup_by_document(items)
        assert len(result) >= MIN_EVIDENCE_PER_CRITERIA

    def test_all_unique_documents_unchanged(self):
        items = [
            {"chunk_id": "a", "document_id": "d1", "score_raw": 0.9},
            {"chunk_id": "b", "document_id": "d2", "score_raw": 0.8},
            {"chunk_id": "c", "document_id": "d3", "score_raw": 0.7},
        ]
        result = _dedup_by_document(items)
        assert len(result) == 3


class TestTrimEvidenceDedup:
    def test_trim_deduplicates_same_document(self):
        ev = [
            {"chunk_id": "a", "document_id": "d1", "score_raw": 0.9, "text": "short"},
            {"chunk_id": "b", "document_id": "d1", "score_raw": 0.8, "text": "short"},
            {"chunk_id": "c", "document_id": "d2", "score_raw": 0.7, "text": "short"},
            {"chunk_id": "d", "document_id": "d3", "score_raw": 0.6, "text": "short"},
        ]
        result = trim_evidence_to_budget(ev, max_tokens=100_000)
        doc_ids = [r["document_id"] for r in result]
        assert doc_ids.count("d1") == 1
