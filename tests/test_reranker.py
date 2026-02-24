"""Tests for app.reranker – configurable reranker backends."""

from __future__ import annotations

import pytest

from app.reranker import _rerank_simple, _sigmoid, _tokenize, rerank_items

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_items(n: int = 5) -> list[dict]:
    return [
        {"chunk_id": f"ck_{i}", "score_raw": round(0.3 + 0.1 * i, 2), "text": f"chunk text {i}"}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# _sigmoid
# ---------------------------------------------------------------------------

class TestSigmoid:
    def test_zero(self):
        assert _sigmoid(0.0) == pytest.approx(0.5)

    def test_large_positive(self):
        assert _sigmoid(100.0) == pytest.approx(1.0, abs=1e-6)

    def test_large_negative(self):
        assert _sigmoid(-100.0) == pytest.approx(0.0, abs=1e-6)

    def test_symmetry(self):
        assert _sigmoid(2.0) + _sigmoid(-2.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _tokenize (CJK-aware)
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_english_words(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_cjk_characters(self):
        assert _tokenize("招标文件") == ["招", "标", "文", "件"]

    def test_mixed_cjk_and_english(self):
        tokens = _tokenize("Python招标test")
        assert tokens == ["python", "招", "标", "test"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_punctuation_ignored(self):
        assert _tokenize("hello, world!") == ["hello", "world"]


# ---------------------------------------------------------------------------
# simple backend (TF-IDF)
# ---------------------------------------------------------------------------

class TestSimpleBackend:
    def test_adds_score_rerank(self):
        items = _make_items(3)
        result = _rerank_simple("chunk text", items)
        assert len(result) == 3
        for item in result:
            assert "score_rerank" in item

    def test_relevant_query_boosts_score(self):
        items = [
            {"chunk_id": "match", "score_raw": 0.5, "text": "chunk text about bidding"},
            {"chunk_id": "no_match", "score_raw": 0.5, "text": "unrelated document xyz"},
        ]
        result = _rerank_simple("bidding", items)
        scores = {it["chunk_id"]: it["score_rerank"] for it in result}
        assert scores["match"] > scores["no_match"]

    def test_cjk_query_affects_ranking(self):
        items = [
            {"chunk_id": "cn", "score_raw": 0.5, "text": "招标文件评审标准"},
            {"chunk_id": "en", "score_raw": 0.5, "text": "hello world document"},
        ]
        result = _rerank_simple("招标", items)
        assert result[0]["chunk_id"] == "cn"

    def test_score_formula_combines_tfidf_and_raw(self):
        items = [{"chunk_id": "ck", "score_raw": 0.5, "text": "exact match query"}]
        result = _rerank_simple("exact match query", items)
        score = result[0]["score_rerank"]
        assert score > 0.6 * 0.5, "tfidf contribution should push score above pure score_raw"
        assert score <= 1.0

    def test_capped_at_one(self):
        items = [{"chunk_id": "ck_1", "score_raw": 0.98, "text": "test"}]
        result = _rerank_simple("test", items)
        assert result[0]["score_rerank"] <= 1.0

    def test_sorted_descending(self):
        items = _make_items(5)
        result = _rerank_simple("chunk", items)
        scores = [it["score_rerank"] for it in result]
        assert scores == sorted(scores, reverse=True)

    def test_does_not_mutate_originals(self):
        items = _make_items(2)
        original_ids = [it["chunk_id"] for it in items]
        _rerank_simple("query", items)
        assert [it["chunk_id"] for it in items] == original_ids
        assert "score_rerank" not in items[0]

    def test_empty_query_falls_back_to_score_raw(self):
        items = [{"chunk_id": "ck", "score_raw": 0.7, "text": "some text"}]
        result = _rerank_simple("", items)
        assert result[0]["score_rerank"] == pytest.approx(0.7, abs=0.001)


# ---------------------------------------------------------------------------
# rerank_items dispatcher
# ---------------------------------------------------------------------------

class TestRerankItems:
    def test_empty_input(self):
        assert rerank_items("q", []) == []

    def test_default_backend_is_simple(self, monkeypatch):
        monkeypatch.setenv("RERANK_BACKEND", "simple")
        items = _make_items(3)
        result = rerank_items("some query", items)
        assert len(result) == 3
        assert all("score_rerank" in it for it in result)

    def test_explicit_backend_override(self):
        items = _make_items(3)
        result = rerank_items("q", items, backend="simple")
        assert len(result) == 3

    def test_top_k_truncation(self):
        items = _make_items(10)
        result = rerank_items("q", items, backend="simple", top_k=3)
        assert len(result) == 3

    def test_unknown_api_backend_falls_back(self):
        items = _make_items(3)
        result = rerank_items("q", items, backend="cohere")
        assert len(result) == 3
        assert all("score_rerank" in it for it in result)

    def test_cross_encoder_falls_back_when_not_installed(self, monkeypatch):
        import app.reranker as mod
        monkeypatch.setattr(mod, "_cross_encoder_cache", {})
        items = _make_items(3)
        result = rerank_items("q", items, backend="cross-encoder")
        assert len(result) == 3
        assert all("score_rerank" in it for it in result)
