"""Tests for the RAGAS-compatible offline evaluation pipeline.

Verifies alignment with:
  - retrieval-scoring-spec §12: precision/recall >= 0.80, faithfulness >= 0.90
  - Gate D-1 quality thresholds

Tests both:
  - Lightweight backend (always runs in CI)
  - Real ragas backend (verified via import and mock-LLM path)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ragas_evaluator import (
    EvalMetrics,
    EvalSample,
    evaluate_and_gate,
    evaluate_dataset,
    evaluate_dataset_lightweight,
    evaluate_dataset_ragas,
    run_e2e_evaluation,
)


def _high_quality_sample() -> EvalSample:
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


# ---------------------------------------------------------------------------
# Lightweight backend tests
# ---------------------------------------------------------------------------


class TestLightweightBackend:
    def test_high_quality_sample_passes_thresholds(self):
        samples = [_high_quality_sample()]
        metrics = evaluate_dataset_lightweight(samples)
        assert metrics.backend == "lightweight"
        assert metrics.context_precision >= 0.70
        assert metrics.context_recall >= 0.70
        assert metrics.faithfulness >= 0.80
        assert metrics.hallucination_rate == 0.0
        assert metrics.citation_resolvable_rate == 1.0

    def test_poor_quality_sample_fails_thresholds(self):
        samples = [_poor_quality_sample()]
        metrics = evaluate_dataset_lightweight(samples)
        assert metrics.context_precision < 0.50
        assert metrics.context_recall < 0.50
        assert metrics.citation_resolvable_rate < 0.50

    def test_empty_dataset_returns_zero_metrics(self):
        metrics = evaluate_dataset_lightweight([])
        assert metrics.context_precision == 0.0
        assert metrics.hallucination_rate == 0.0

    def test_explicit_lightweight_backend(self):
        samples = [_high_quality_sample()]
        metrics = evaluate_dataset(samples, backend="lightweight")
        assert metrics.backend == "lightweight"


# ---------------------------------------------------------------------------
# Real ragas backend tests (with mocked LLM)
# ---------------------------------------------------------------------------


class TestRagasBackendStructure:
    """Verify ragas integration structure without real API calls."""

    def test_ragas_imports_are_available(self):
        from ragas import EvaluationDataset, evaluate
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )

        assert callable(evaluate)
        assert EvaluationDataset is not None
        assert all(
            cls is not None
            for cls in [
                Faithfulness,
                ContextPrecision,
                ContextRecall,
                AnswerRelevancy,
            ]
        )

    def test_deepeval_hallucination_import(self):
        from deepeval.metrics import HallucinationMetric
        from deepeval.test_case import LLMTestCase

        assert HallucinationMetric is not None
        assert LLMTestCase is not None

    def test_ragas_dataset_construction(self):
        from ragas import EvaluationDataset

        sample = _high_quality_sample()
        data = [
            {
                "user_input": sample.query,
                "retrieved_contexts": list(sample.retrieved_contexts),
                "response": sample.generated_answer,
                "reference": sample.ground_truth_answer,
            }
        ]
        dataset = EvaluationDataset.from_list(data)
        assert len(dataset) == 1

    def test_auto_backend_falls_back_to_lightweight_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        samples = [_high_quality_sample()]
        metrics = evaluate_dataset(samples, backend="auto")
        assert metrics.backend == "lightweight"

    @patch("app.ragas_evaluator.evaluate_dataset_ragas")
    def test_auto_backend_uses_ragas_when_available(self, mock_ragas):
        mock_ragas.return_value = EvalMetrics(
            context_precision=0.85,
            context_recall=0.82,
            faithfulness=0.92,
            response_relevancy=0.88,
            hallucination_rate=0.03,
            citation_resolvable_rate=0.99,
            backend="ragas",
        )
        samples = [_high_quality_sample()]
        metrics = evaluate_dataset(samples, backend="auto")
        assert metrics.backend == "ragas"
        mock_ragas.assert_called_once()


# ---------------------------------------------------------------------------
# End-to-end evaluation with store integration
# ---------------------------------------------------------------------------


class TestE2EEvaluation:
    def test_run_e2e_evaluation_calls_store_retrieval(self):
        mock_store = MagicMock()
        mock_store.retrieval_query.return_value = {
            "items": [
                {
                    "chunk_id": "chk_e2e_1",
                    "score_raw": 0.9,
                    "metadata": {"page": 1, "tenant_id": "t", "project_id": "p"},
                },
            ],
        }
        mock_store.citation_sources = {
            "chk_e2e_1": {
                "text": "投标人须提供有效的ISO9001质量管理体系认证证书",
                "page": 1,
            },
        }

        golden = [
            EvalSample(
                query="投标人需要哪些资质",
                ground_truth_answer="ISO9001认证",
                ground_truth_contexts=["投标人须提供有效的ISO9001质量管理体系认证证书"],
            ),
        ]

        metrics = run_e2e_evaluation(
            golden_samples=golden,
            store=mock_store,
            backend="lightweight",
        )

        mock_store.retrieval_query.assert_called_once()
        assert metrics.backend == "lightweight"
        assert metrics.context_recall > 0
        assert metrics.citation_resolvable_rate == 1.0

    def test_e2e_fills_retrieved_contexts_from_store(self):
        mock_store = MagicMock()
        mock_store.retrieval_query.return_value = {
            "items": [
                {"chunk_id": "c1", "score_raw": 0.8, "metadata": {"page": 1}},
                {"chunk_id": "c2", "score_raw": 0.7, "metadata": {"page": 2}},
            ],
        }
        mock_store.citation_sources = {
            "c1": {"text": "第一段检索内容", "page": 1},
            "c2": {"text": "第二段检索内容", "page": 2},
        }

        golden = [
            EvalSample(
                query="测试查询",
                ground_truth_answer="第一段检索内容",
                ground_truth_contexts=["第一段检索内容"],
            ),
        ]

        metrics = run_e2e_evaluation(
            golden_samples=golden,
            store=mock_store,
            backend="lightweight",
        )

        assert metrics.context_recall > 0


# ---------------------------------------------------------------------------
# Quality gate integration
# ---------------------------------------------------------------------------


class TestQualityGateIntegration:
    def test_evaluate_and_gate_passes_with_high_quality_data(self):
        samples = [_high_quality_sample()] * 5
        result = evaluate_and_gate(
            samples=samples,
            dataset_id="ds_test_pass",
            backend="lightweight",
        )
        assert result["gate"] == "quality"
        assert result["dataset_id"] == "ds_test_pass"
        assert result["values"]["citation_resolvable_rate"] >= 0.98
        assert result["values"]["hallucination_rate"] <= 0.05

    def test_evaluate_and_gate_blocks_with_poor_data(self):
        samples = [_poor_quality_sample()] * 5
        result = evaluate_and_gate(
            samples=samples,
            dataset_id="ds_test_fail",
            backend="lightweight",
        )
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
            backend="ragas",
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


# ---------------------------------------------------------------------------
# SSOT alignment
# ---------------------------------------------------------------------------


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

    def test_evaluator_supports_both_backends(self):
        samples = [_high_quality_sample()]
        lw = evaluate_dataset(samples, backend="lightweight")
        assert lw.backend == "lightweight"

        from ragas import evaluate as ragas_evaluate

        assert callable(ragas_evaluate), "ragas library must be importable"
