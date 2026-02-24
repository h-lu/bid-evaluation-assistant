"""Tests for LLM provider module: multi-provider support, degradation, cost tracking."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from app.llm_provider import (
    LLMUsage,
    ProviderConfig,
    _get_provider_config,
    get_provider_info,
    get_usage_log,
    is_real_llm_available,
    llm_generate_explanation,
    llm_score_criteria,
    reset_usage_log,
)


class TestProviderConfig:
    def test_default_config_is_openai(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = _get_provider_config()
            assert config.provider == "openai"
            assert config.model == "gpt-4o-mini"

    def test_ollama_provider_config(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_MODEL": "qwen2.5:14b",
            "OLLAMA_BASE_URL": "http://192.168.1.100:11434/v1",
        }, clear=True):
            config = _get_provider_config()
            assert config.provider == "ollama"
            assert config.model == "qwen2.5:14b"
            assert config.base_url == "http://192.168.1.100:11434/v1"
            assert config.api_key == "ollama"

    def test_custom_provider_with_base_url(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "custom",
            "LLM_MODEL": "deepseek-chat",
            "OPENAI_API_KEY": "sk-custom-key",
            "OPENAI_BASE_URL": "https://api.deepseek.com/v1",
        }, clear=True):
            config = _get_provider_config()
            assert config.provider == "custom"
            assert config.model == "deepseek-chat"
            assert config.base_url == "https://api.deepseek.com/v1"
            assert config.api_key == "sk-custom-key"

    def test_fallback_model_config(self):
        with mock.patch.dict(os.environ, {
            "LLM_MODEL": "gpt-4o",
            "LLM_FALLBACK_MODEL": "gpt-4o-mini",
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            config = _get_provider_config()
            assert config.model == "gpt-4o"
            assert config.fallback_model == "gpt-4o-mini"

    def test_temperature_config(self):
        with mock.patch.dict(os.environ, {
            "LLM_TEMPERATURE": "0.3",
        }, clear=True):
            config = _get_provider_config()
            assert config.temperature == 0.3


class TestIsRealLlmAvailable:
    def test_mock_enabled_returns_false(self):
        with mock.patch.dict(os.environ, {"MOCK_LLM_ENABLED": "true", "OPENAI_API_KEY": "sk-test"}):
            from app import mock_llm
            original = mock_llm.MOCK_LLM_ENABLED
            mock_llm.MOCK_LLM_ENABLED = True
            try:
                assert is_real_llm_available() is False
            finally:
                mock_llm.MOCK_LLM_ENABLED = original

    def test_no_api_key_returns_false(self):
        with mock.patch.dict(os.environ, {"MOCK_LLM_ENABLED": "false", "OPENAI_API_KEY": ""}, clear=False):
            from app import mock_llm
            original = mock_llm.MOCK_LLM_ENABLED
            mock_llm.MOCK_LLM_ENABLED = False
            try:
                assert is_real_llm_available() is False
            finally:
                mock_llm.MOCK_LLM_ENABLED = original

    def test_ollama_available_without_api_key(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "",
        }, clear=False):
            from app import mock_llm
            original = mock_llm.MOCK_LLM_ENABLED
            mock_llm.MOCK_LLM_ENABLED = False
            try:
                assert is_real_llm_available() is True
            finally:
                mock_llm.MOCK_LLM_ENABLED = original

    def test_openai_available_with_api_key(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            from app import mock_llm
            original = mock_llm.MOCK_LLM_ENABLED
            mock_llm.MOCK_LLM_ENABLED = False
            try:
                assert is_real_llm_available() is True
            finally:
                mock_llm.MOCK_LLM_ENABLED = original


class TestLlmScoreCriteria:
    def test_fallback_to_mock_when_mock_enabled(self, monkeypatch):
        # Ensure mock is enabled for this test
        monkeypatch.setenv("MOCK_LLM_ENABLED", "true")
        from app import mock_llm
        import importlib
        importlib.reload(mock_llm)

        result = llm_score_criteria(
            criteria_id="delivery",
            requirement_text="交付时间不超过30天",
            evidence_chunks=[
                {"chunk_id": "ck_1", "text": "承诺30个工作日交付", "page": 5, "score_raw": 0.9}
            ],
            max_score=20.0,
            hard_constraint_pass=True,
        )
        assert "score" in result
        assert "max_score" in result
        assert "hard_pass" in result
        assert "reason" in result
        assert 0 <= result["score"] <= 20.0

    def test_no_evidence_returns_result(self, monkeypatch):
        # Ensure mock is enabled for this test
        monkeypatch.setenv("MOCK_LLM_ENABLED", "true")
        from app import mock_llm
        import importlib
        importlib.reload(mock_llm)

        result = llm_score_criteria(
            criteria_id="price",
            requirement_text="报价合理",
            evidence_chunks=[],
            max_score=10.0,
        )
        assert "score" in result
        assert result["max_score"] == 10.0

    def test_multiple_evidence_chunks(self, monkeypatch):
        # Ensure mock is enabled for this test
        monkeypatch.setenv("MOCK_LLM_ENABLED", "true")
        from app import mock_llm
        import importlib
        importlib.reload(mock_llm)

        evidence = [
            {"chunk_id": f"ck_{i}", "text": f"证据 {i} 的内容", "page": i, "score_raw": 0.8}
            for i in range(5)
        ]
        result = llm_score_criteria(
            criteria_id="technical",
            requirement_text="技术方案完整性",
            evidence_chunks=evidence,
            max_score=30.0,
            hard_constraint_pass=True,
        )
        assert result["score"] > 0
        assert result["max_score"] == 30.0


class TestLlmGenerateExplanation:
    def test_generates_explanation(self):
        explanation = llm_generate_explanation(
            criteria_id="delivery",
            score=18.0,
            max_score=20.0,
            evidence=[
                {"chunk_id": "ck_1", "text": "承诺30天交付", "page": 5}
            ],
        )
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "delivery" in explanation.lower() or "评分" in explanation

    def test_empty_evidence(self):
        explanation = llm_generate_explanation(
            criteria_id="test",
            score=5.0,
            max_score=10.0,
            evidence=[],
        )
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestProviderInfo:
    def test_provider_info_does_not_leak_secrets(self):
        info = get_provider_info()
        assert "provider" in info
        assert "model" in info
        assert "has_api_key" in info
        assert "real_llm_available" in info
        assert "api_key" not in info

    def test_provider_info_reports_ollama(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_MODEL": "llama3",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        }, clear=False):
            info = get_provider_info()
            assert info["provider"] == "ollama"
            assert info["model"] == "llama3"


class TestUsageTracking:
    def test_usage_log_starts_empty(self):
        reset_usage_log()
        assert get_usage_log() == []

    def test_usage_dataclass_fields(self):
        usage = LLMUsage(
            prompt_tokens=100, completion_tokens=50, total_tokens=150,
            model="gpt-4o-mini", latency_ms=234.5,
        )
        assert usage.prompt_tokens == 100
        assert usage.total_tokens == 150
        assert usage.model == "gpt-4o-mini"
        assert usage.degraded is False
