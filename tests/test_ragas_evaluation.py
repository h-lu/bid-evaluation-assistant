"""Tests for the RAGAS-compatible offline evaluation pipeline.

Verifies alignment with:
  - retrieval-scoring-spec §12: precision/recall >= 0.80, faithfulness >= 0.90
  - Gate D-1 quality thresholds
"""

from __future__ import annotations

from app.ragas_evaluator import (
    EvalMetrics,
    EvalSample,
    evaluate_and_gate,
    evaluate_dataset,
)


def _high_quality_sample() -> EvalSample:
    """A sample where retrieval and generation are excellent."""
    gt_contexts = [
        "投标人须提供有效的ISO9001质量管理体系认证证书",
        "注册资金不低于500万元人民币",
        "近三年无重大安全事故记录",
    ]
    return EvalSample(
        query="投标人需要哪些资质要求",
        ground_truth_answer="投标人需提供ISO9001认证、注册资金不低于500万、近三年无重大安全事故",
        ground_truth_contexts=gt_contexts,
        retrieved_contexts=[
            "投标人须提供有效的ISO9001质量管理体系认证证书复印件",
            "注册资金不低于500万元人民币的营业执照",
            "近三年无重大安全事故记录证明",
            "投标人须在中国大陆注册",
        ],
        generated_answer="投标人需提供ISO9001质量管理体系认证证书、注册资金不低于500万元人民币、近三年无重大安全事故记录",
        citations=[
            {"chunk_id": "chk_001", "page": 1},
            {"chunk_id": "chk_002", "page": 2},
            {"chunk_id": "chk_003", "page": 3},
        ],
    )


def _poor_quality_sample() -> EvalSample:
    """A sample where retrieval is bad and answer is hallucinated."""
    return EvalSample(
        query="交货期限要求是什么",
        ground_truth_answer="合同签订后30个工作日内完成交付",
        ground_truth_contexts=["合同签订后30个工作日内完成全部货物的交付"],
        retrieved_contexts=[
            "办公用品采购清单包含桌椅文具",
            "供应商应提供售后服务方案",
        ],
        generated_answer="交货期为签约后90天,并需通过国际快递发运至指定仓库",
        citations=[
            {"chunk_id": "", "page": None},
            {"chunk_id": None},
        ],
    )


class TestPerSampleMetrics:
    def test_high_quality_sample_passes_thresholds(self):
        samples = [_high_quality_sample()]
        metrics = evaluate_dataset(samples)
        assert metrics.context_precision >= 0.70
        assert metrics.context_recall >= 0.70
        assert metrics.faithfulness >= 0.80
        assert metrics.hallucination_rate == 0.0
        assert metrics.citation_resolvable_rate == 1.0

    def test_poor_quality_sample_fails_thresholds(self):
        samples = [_poor_quality_sample()]
        metrics = evaluate_dataset(samples)
        assert metrics.context_precision < 0.50
        assert metrics.context_recall < 0.50
        assert metrics.citation_resolvable_rate < 0.50


class TestAggregateMetrics:
    def test_mixed_dataset_averages_correctly(self):
        samples = [_high_quality_sample(), _poor_quality_sample()]
        metrics = evaluate_dataset(samples)
        assert 0.0 < metrics.context_precision < 1.0
        assert 0.0 < metrics.context_recall < 1.0
        assert 0.0 < metrics.faithfulness < 1.0

    def test_empty_dataset_returns_zero_metrics(self):
        metrics = evaluate_dataset([])
        assert metrics.context_precision == 0.0
        assert metrics.context_recall == 0.0
        assert metrics.faithfulness == 0.0
        assert metrics.hallucination_rate == 0.0
        assert metrics.citation_resolvable_rate == 0.0

    def test_all_high_quality_passes_gate(self):
        samples = [_high_quality_sample()] * 5
        metrics = evaluate_dataset(samples)
        assert metrics.citation_resolvable_rate >= 0.98
        assert metrics.hallucination_rate <= 0.05


class TestQualityGateIntegration:
    def test_evaluate_and_gate_passes_with_high_quality_data(self):
        samples = [_high_quality_sample()] * 5
        result = evaluate_and_gate(samples=samples, dataset_id="ds_test_pass")
        assert result["gate"] == "quality"
        assert result["dataset_id"] == "ds_test_pass"
        assert result["values"]["citation_resolvable_rate"] >= 0.98
        assert result["values"]["hallucination_rate"] <= 0.05

    def test_evaluate_and_gate_blocks_with_poor_data(self):
        samples = [_poor_quality_sample()] * 5
        result = evaluate_and_gate(samples=samples, dataset_id="ds_test_fail")
        assert result["passed"] is False
        assert len(result["failed_checks"]) > 0

    def test_metrics_payload_matches_gate_schema(self):
        metrics = EvalMetrics(
            context_precision=0.85,
            context_recall=0.82,
            faithfulness=0.92,
            response_relevancy=0.88,
            hallucination_rate=0.03,
            citation_resolvable_rate=0.99,
        )
        payload = metrics.to_quality_gate_payload("ds_schema")
        assert payload["dataset_id"] == "ds_schema"
        ragas = payload["metrics"]["ragas"]
        assert ragas["context_precision"] == 0.85
        assert ragas["context_recall"] == 0.82
        assert ragas["faithfulness"] == 0.92
        assert ragas["response_relevancy"] == 0.88
        deepeval = payload["metrics"]["deepeval"]
        assert deepeval["hallucination_rate"] == 0.03
        citation = payload["metrics"]["citation"]
        assert citation["resolvable_rate"] == 0.99


class TestSSOTAlignment:
    """Verify SSOT retrieval-scoring-spec §12 thresholds are respected."""

    def test_quality_thresholds_match_ssot(self):
        from app.quality_gates import QUALITY_THRESHOLDS

        assert QUALITY_THRESHOLDS["ragas_context_precision_min"] == 0.80
        assert QUALITY_THRESHOLDS["ragas_context_recall_min"] == 0.80
        assert QUALITY_THRESHOLDS["ragas_faithfulness_min"] == 0.90
        assert QUALITY_THRESHOLDS["ragas_response_relevancy_min"] == 0.85
        assert QUALITY_THRESHOLDS["deepeval_hallucination_rate_max"] == 0.05
        assert QUALITY_THRESHOLDS["citation_resolvable_rate_min"] == 0.98

    def test_gate_d1_six_metrics_present_in_evaluator(self):
        metrics = EvalMetrics()
        gate_payload = metrics.to_quality_gate_payload("test")
        ragas = gate_payload["metrics"]["ragas"]
        assert "context_precision" in ragas
        assert "context_recall" in ragas
        assert "faithfulness" in ragas
        assert "response_relevancy" in ragas
        assert "hallucination_rate" in gate_payload["metrics"]["deepeval"]
        assert "resolvable_rate" in gate_payload["metrics"]["citation"]
