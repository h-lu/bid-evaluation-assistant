"""Tests for Mock LLM module."""

from app.mock_llm import (
    MOCK_LLM_ENABLED,
    mock_classify_intent,
    mock_generate_explanation,
    mock_quality_gate_check,
    mock_retrieve_evidence,
    mock_score_criteria,
)


def test_mock_llm_is_enabled_by_default(monkeypatch):
    """Mock LLM should be enabled by default when MOCK_LLM_ENABLED is not set."""
    # Remove any existing setting to test default behavior
    monkeypatch.delenv("MOCK_LLM_ENABLED", raising=False)
    # Re-import to get fresh value
    import importlib

    import app.mock_llm as mock_llm_module
    importlib.reload(mock_llm_module)
    assert mock_llm_module.MOCK_LLM_ENABLED is True


def test_mock_retrieve_evidence_returns_results():
    """Mock retrieval should return evidence chunks."""
    results = mock_retrieve_evidence(
        query="资质要求",
        top_k=3,
        tenant_id="tenant_1",
        supplier_id="sup_1",
    )

    assert len(results) <= 3
    assert all("chunk_id" in r for r in results)
    assert all("page" in r for r in results)
    assert all("text" in r for r in results)


def test_mock_retrieve_evidence_matches_keywords():
    """Mock retrieval should match keywords in query."""
    results = mock_retrieve_evidence(query="资质认证")

    assert len(results) >= 1
    # Should contain keyword-related evidence
    assert any("ISO" in r.get("text", "") or "认证" in r.get("text", "") for r in results)


def test_mock_retrieve_evidence_deterministic():
    """Mock retrieval should be deterministic for same inputs."""
    results1 = mock_retrieve_evidence(
        query="测试查询",
        tenant_id="tenant_a",
        supplier_id="sup_a",
    )
    results2 = mock_retrieve_evidence(
        query="测试查询",
        tenant_id="tenant_a",
        supplier_id="sup_a",
    )

    assert len(results1) == len(results2)
    assert [r["chunk_id"] for r in results1] == [r["chunk_id"] for r in results2]


def test_mock_score_criteria_with_evidence():
    """Mock scoring should return valid results with evidence."""
    evidence = [
        {"chunk_id": "ck_1", "text": "test", "score_raw": 0.85, "page": 1, "bbox": []},
    ]

    result = mock_score_criteria(
        criteria_id="delivery",
        requirement_text="交付能力要求",
        evidence_chunks=evidence,
        max_score=20.0,
        hard_constraint_pass=True,
    )

    assert "score" in result
    assert "max_score" in result
    assert "hard_pass" in result
    assert "reason" in result
    assert result["max_score"] == 20.0
    assert 0 <= result["score"] <= 20.0


def test_mock_score_criteria_no_evidence_hard_pass():
    """Mock scoring should return high score when hard_constraint_pass=True."""
    result = mock_score_criteria(
        criteria_id="test",
        requirement_text="test requirement",
        evidence_chunks=[],
        max_score=10.0,
        hard_constraint_pass=True,
    )

    # Should return 90% score when hard_constraint_pass is True
    assert result["score"] == 9.0
    assert result["hard_pass"] is True


def test_mock_score_criteria_no_evidence_hard_fail():
    """Mock scoring should return low score when hard_constraint_pass=False."""
    result = mock_score_criteria(
        criteria_id="test",
        requirement_text="test requirement",
        evidence_chunks=[],
        max_score=10.0,
        hard_constraint_pass=False,
    )

    # Should return 30% score when hard_constraint_pass is False
    assert result["score"] == 3.0
    assert result["hard_pass"] is False


def test_mock_score_criteria_high_score_when_hard_constraint_pass():
    """Mock scoring should ensure high score when hard_constraint_pass=True."""
    # Even with low score_raw evidence
    evidence = [
        {"chunk_id": "ck_1", "text": "test", "score_raw": 0.5, "page": 1, "bbox": []},
    ]

    result = mock_score_criteria(
        criteria_id="test",
        requirement_text="test",
        evidence_chunks=evidence,
        max_score=10.0,
        hard_constraint_pass=True,
    )

    # Score should be boosted to at least 90%
    assert result["score"] >= 9.0


def test_mock_generate_explanation():
    """Mock explanation generation should return formatted text."""
    evidence = [
        {"chunk_id": "ck_1", "page": 5, "text": "test", "score_raw": 0.8, "bbox": []},
        {"chunk_id": "ck_2", "page": 8, "text": "test", "score_raw": 0.9, "bbox": []},
    ]

    explanation = mock_generate_explanation(
        criteria_id="delivery",
        score=18.0,
        max_score=20.0,
        evidence=evidence,
    )

    assert "delivery" in explanation
    assert "18" in explanation
    assert "20" in explanation
    assert "5" in explanation or "8" in explanation  # Page numbers


def test_mock_classify_intent():
    """Mock intent classification should work correctly."""
    # Test qualification intent
    result = mock_classify_intent("请检查资质认证")
    assert result["intent"] == "qualification_check"
    assert result["confidence"] > 0.8

    # Test price intent
    result = mock_classify_intent("价格是多少")
    assert result["intent"] == "price_inquiry"

    # Test delivery intent
    result = mock_classify_intent("交付时间")
    assert result["intent"] == "delivery_check"

    # Test general intent
    result = mock_classify_intent("其他问题")
    assert result["intent"] == "general_query"


def test_mock_quality_gate_check_pass():
    """Quality gate should pass with good metrics."""
    result = mock_quality_gate_check(
        confidence=0.85,
        citation_coverage=0.95,
        score_deviation_pct=10.0,
    )

    assert result["gate_result"] == "pass"
    assert result["reasons"] == []


def test_mock_quality_gate_check_hitl_low_confidence():
    """Quality gate should trigger HITL with low confidence."""
    result = mock_quality_gate_check(
        confidence=0.50,  # < 0.65
        citation_coverage=0.95,
        score_deviation_pct=10.0,
    )

    assert result["gate_result"] == "hitl"
    assert any("置信度" in r for r in result["reasons"])


def test_mock_quality_gate_check_hitl_low_citation_coverage():
    """Quality gate should trigger HITL with low citation coverage."""
    result = mock_quality_gate_check(
        confidence=0.85,
        citation_coverage=0.80,  # < 0.90
        score_deviation_pct=10.0,
    )

    assert result["gate_result"] == "hitl"
    assert any("引用覆盖" in r for r in result["reasons"])


def test_mock_quality_gate_check_hitl_high_score_deviation():
    """Quality gate should trigger HITL with high score deviation."""
    result = mock_quality_gate_check(
        confidence=0.85,
        citation_coverage=0.95,
        score_deviation_pct=25.0,  # > 20%
    )

    assert result["gate_result"] == "hitl"
    assert any("评分偏差" in r for r in result["reasons"])
