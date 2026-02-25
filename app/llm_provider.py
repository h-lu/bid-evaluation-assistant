"""
LLM Provider abstraction for scoring, explanation generation, and retrieval.

Architecture:
  - ProviderConfig: per-provider settings (model, api_key, base_url, etc.)
  - Degradation chain: primary -> fallback -> mock
  - Cost tracking: token counts per call
  - Supports: OpenAI, Ollama, any OpenAI-compatible API (vLLM, LiteLLM, etc.)

Configuration via environment variables:
  LLM_PROVIDER          = openai | ollama | custom   (default: openai)
  LLM_MODEL             = gpt-4o-mini                (primary model)
  LLM_FALLBACK_MODEL    = gpt-3.5-turbo              (fallback on primary failure)
  LLM_TEMPERATURE       = 0.1
  OPENAI_API_KEY        = sk-...
  OPENAI_BASE_URL       = https://api.openai.com/v1  (or custom endpoint)
  OLLAMA_BASE_URL       = http://localhost:11434/v1   (Ollama OpenAI-compat endpoint)
  OLLAMA_MODEL          = qwen2.5:7b
  MOCK_LLM_ENABLED      = true                       (force mock mode)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    provider: str = "openai"
    model: str = ""
    fallback_model: str = ""
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 1024

    def __post_init__(self) -> None:
        if not self.model:
            self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini").strip()


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    latency_ms: float = 0.0
    degraded: bool = False
    degrade_reason: str = ""


_call_usage_log: list[LLMUsage] = []

_TASK_TOKEN_BUDGET = int(os.environ.get("TASK_TOKEN_BUDGET", "50000"))
_TASK_COST_WARN_RATIO = float(os.environ.get("TASK_COST_WARN_RATIO", "0.8"))
_TASK_COST_HARD_RATIO = float(os.environ.get("TASK_COST_HARD_RATIO", "1.2"))


@dataclass
class CostBudgetTracker:
    """Per-task cost budget tracker.

    Tracks cumulative token usage for a single evaluation task.
    When cost exceeds budget thresholds, triggers degradation or blocking.

    SSOT §7.4: "单任务成本 P95 不高于基线 1.2x"
    """

    task_id: str
    max_tokens_budget: int = field(default_factory=lambda: _TASK_TOKEN_BUDGET)
    warn_threshold_ratio: float = field(default_factory=lambda: _TASK_COST_WARN_RATIO)
    hard_threshold_ratio: float = field(default_factory=lambda: _TASK_COST_HARD_RATIO)

    _cumulative_prompt_tokens: int = field(default=0, init=False)
    _cumulative_completion_tokens: int = field(default=0, init=False)
    _cumulative_total_tokens: int = field(default=0, init=False)
    _degraded: bool = field(default=False, init=False)
    _blocked: bool = field(default=False, init=False)

    def record_usage(self, usage: LLMUsage) -> None:
        self._cumulative_prompt_tokens += usage.prompt_tokens
        self._cumulative_completion_tokens += usage.completion_tokens
        self._cumulative_total_tokens += usage.total_tokens

    @property
    def total_tokens(self) -> int:
        return self._cumulative_total_tokens

    @property
    def is_over_budget(self) -> bool:
        if self.max_tokens_budget <= 0:
            return False
        return self._cumulative_total_tokens > int(self.max_tokens_budget * self.hard_threshold_ratio)

    @property
    def should_degrade(self) -> bool:
        if self.max_tokens_budget <= 0:
            return False
        return self._cumulative_total_tokens >= int(self.max_tokens_budget * self.warn_threshold_ratio)

    def check_budget(self) -> str:
        """Returns 'ok', 'warn', 'degrade', or 'blocked'."""
        if self._blocked:
            return "blocked"
        if self.max_tokens_budget <= 0:
            return "ok"

        if self.is_over_budget:
            self._blocked = True
            return "blocked"
        if self._degraded:
            return "degrade"
        if self.should_degrade:
            self._degraded = True
            return "degrade"
        return "ok"


def get_usage_log() -> list[LLMUsage]:
    return list(_call_usage_log)


def reset_usage_log() -> None:
    _call_usage_log.clear()


def _get_provider_config() -> ProviderConfig:
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    fallback = os.environ.get("LLM_FALLBACK_MODEL", "").strip()
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1").strip())

    if provider == "ollama":
        return ProviderConfig(
            provider="ollama",
            model=os.environ.get("OLLAMA_MODEL", os.environ.get("LLM_MODEL", "")).strip(),
            fallback_model=fallback,
            api_key=os.environ.get("OPENAI_API_KEY", "ollama").strip() or "ollama",
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip(),
            temperature=temperature,
        )

    return ProviderConfig(
        provider=provider,
        model=os.environ.get("LLM_MODEL", "").strip(),
        fallback_model=fallback,
        api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        base_url=os.environ.get("OPENAI_BASE_URL", "").strip(),
        temperature=temperature,
    )


def is_real_llm_available() -> bool:
    from app.mock_llm import MOCK_LLM_ENABLED

    if MOCK_LLM_ENABLED:
        return False
    config = _get_provider_config()
    if config.provider == "ollama":
        return bool(config.base_url)
    return bool(config.api_key)


def _create_client(config: ProviderConfig):
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package is required. Install with: pip install 'bid-evaluation-assistant[openai]'")

    kwargs: dict[str, Any] = {}
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url

    if config.provider == "ollama" and "api_key" not in kwargs:
        kwargs["api_key"] = "ollama"

    return openai.OpenAI(**kwargs)


def _call_chat(
    *,
    client,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> tuple[str, LLMUsage]:
    """Call chat completions and return (content, usage)."""
    t0 = time.monotonic()
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    elapsed_ms = (time.monotonic() - t0) * 1000

    content = response.choices[0].message.content or ""
    usage_data = response.usage
    usage = LLMUsage(
        prompt_tokens=getattr(usage_data, "prompt_tokens", 0) if usage_data else 0,
        completion_tokens=getattr(usage_data, "completion_tokens", 0) if usage_data else 0,
        total_tokens=getattr(usage_data, "total_tokens", 0) if usage_data else 0,
        model=model,
        latency_ms=round(elapsed_ms, 1),
    )
    _call_usage_log.append(usage)
    return content, usage


def _call_with_degradation(
    *,
    config: ProviderConfig,
    messages: list[dict[str, str]],
    json_mode: bool = False,
    max_tokens: int = 1024,
) -> tuple[str, LLMUsage]:
    """Try primary model, then fallback model, raising on total failure."""
    client = _create_client(config)

    try:
        return _call_chat(
            client=client,
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )
    except Exception as primary_exc:
        if not config.fallback_model:
            raise

        logger.warning(
            "Primary model %s failed (%s), degrading to %s",
            config.model,
            type(primary_exc).__name__,
            config.fallback_model,
        )
        content, usage = _call_chat(
            client=client,
            model=config.fallback_model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )
        usage.degraded = True
        usage.degrade_reason = f"primary_failed:{type(primary_exc).__name__}"
        return content, usage


_SCORE_SYSTEM_PROMPT = """你是一个专业的评标专家AI助手。你需要根据提供的证据对评分项进行评分。

要求：
1. 严格基于证据评分，不得编造不存在的信息
2. 每个评分都必须引用具体的证据来源
3. 使用JSON格式返回结构化结果

评分标准：
- 完全符合要求：90-100% 的满分
- 基本符合要求：70-89% 的满分
- 部分符合要求：40-69% 的满分
- 不符合要求：0-39% 的满分
"""

_SCORE_USER_TEMPLATE = """评分项ID: {criteria_id}
评分项名称: {criteria_name}
要求描述: {requirement_text}
满分: {max_score}

相关证据:
{evidence_text}

请按以下JSON格式返回评分结果:
{{
  "score": <float, 0 到 max_score>,
  "hard_pass": <bool, 是否通过硬性要求>,
  "reason": "<string, 评分理由，必须引用证据>",
  "confidence": <float, 0.0-1.0, 评分置信度>
}}"""


def llm_score_criteria(
    criteria_id: str,
    requirement_text: str,
    evidence_chunks: list[dict[str, Any]],
    *,
    max_score: float = 10.0,
    criteria_name: str = "",
    hard_constraint_pass: bool = True,
) -> dict[str, Any]:
    """Score a criteria item. Chain: real LLM (primary -> fallback) -> mock."""
    if not is_real_llm_available():
        from app.mock_llm import mock_score_criteria

        return mock_score_criteria(
            criteria_id=criteria_id,
            requirement_text=requirement_text,
            evidence_chunks=evidence_chunks,
            max_score=max_score,
            hard_constraint_pass=hard_constraint_pass,
        )

    config = _get_provider_config()

    evidence_text = ""
    for i, chunk in enumerate(evidence_chunks, 1):
        page = chunk.get("page", "?")
        text = chunk.get("text", "")[:500]
        evidence_text += f"[证据{i}] (第{page}页): {text}\n\n"

    if not evidence_text.strip():
        evidence_text = "（无相关证据）"

    user_msg = _SCORE_USER_TEMPLATE.format(
        criteria_id=criteria_id,
        criteria_name=criteria_name or criteria_id,
        requirement_text=requirement_text or "未提供具体要求",
        max_score=max_score,
        evidence_text=evidence_text,
    )

    messages = [
        {"role": "system", "content": _SCORE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        content, usage = _call_with_degradation(
            config=config,
            messages=messages,
            json_mode=True,
            max_tokens=4096,
        )
        result = json.loads(content)
        score = float(result.get("score", max_score * 0.5))
        score = max(0.0, min(max_score, score))

        return {
            "score": round(score, 2),
            "max_score": max_score,
            "hard_pass": bool(result.get("hard_pass", score >= max_score * 0.6)),
            "reason": str(result.get("reason", "LLM evaluation completed")),
            "confidence": float(result.get("confidence", 0.75)),
            "model": usage.model,
            "degraded": usage.degraded,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "latency_ms": usage.latency_ms,
            },
        }

    except Exception as exc:
        logger.warning("LLM scoring failed (%s), falling back to mock", type(exc).__name__)
        from app.mock_llm import mock_score_criteria

        result = mock_score_criteria(
            criteria_id=criteria_id,
            requirement_text=requirement_text,
            evidence_chunks=evidence_chunks,
            max_score=max_score,
            hard_constraint_pass=hard_constraint_pass,
        )
        result["reason"] = f"[LLM fallback] {result['reason']} (error: {type(exc).__name__})"
        result["degraded"] = True
        return result


_EXPLAIN_SYSTEM_PROMPT = """你是一个专业的评标专家AI助手。根据评分结果和证据，生成清晰、专业的评分解释。
解释应该简洁明了，引用具体的证据来源页码。"""

_EXPLAIN_USER_TEMPLATE = """评分项: {criteria_id}
得分: {score}/{max_score}
证据数量: {evidence_count}

证据摘要:
{evidence_summary}

请生成一段简洁的评分解释（100-200字）。"""


def llm_generate_explanation(
    criteria_id: str,
    score: float,
    max_score: float,
    evidence: list[dict[str, Any]],
    *,
    response_text: str | None = None,
) -> str:
    """Generate scoring explanation. Chain: real LLM (primary -> fallback) -> mock."""
    if not is_real_llm_available():
        from app.mock_llm import mock_generate_explanation

        return mock_generate_explanation(
            criteria_id=criteria_id,
            score=score,
            max_score=max_score,
            evidence=evidence,
            response_text=response_text,
        )

    config = _get_provider_config()

    evidence_summary = ""
    for i, ev in enumerate(evidence[:5], 1):
        page = ev.get("page", "?")
        text = ev.get("text", "")[:200]
        evidence_summary += f"[{i}] 第{page}页: {text}\n"

    user_msg = _EXPLAIN_USER_TEMPLATE.format(
        criteria_id=criteria_id,
        score=score,
        max_score=max_score,
        evidence_count=len(evidence),
        evidence_summary=evidence_summary or "无证据",
    )

    messages = [
        {"role": "system", "content": _EXPLAIN_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        content, _ = _call_with_degradation(
            config=config,
            messages=messages,
            max_tokens=2048,
        )
        return content or f"评分项 {criteria_id}: {score}/{max_score}"
    except Exception:
        from app.mock_llm import mock_generate_explanation

        return mock_generate_explanation(
            criteria_id=criteria_id,
            score=score,
            max_score=max_score,
            evidence=evidence,
            response_text=response_text,
        )


def llm_retrieve_and_score(
    query: str,
    evidence_chunks: list[dict[str, Any]],
    *,
    criteria_id: str = "general",
    max_score: float = 10.0,
    criteria_name: str = "",
) -> dict[str, Any]:
    """Combined retrieval scoring: score evidence relevance for a query."""
    return llm_score_criteria(
        criteria_id=criteria_id,
        requirement_text=query,
        evidence_chunks=evidence_chunks,
        max_score=max_score,
        criteria_name=criteria_name,
    )


def get_provider_info() -> dict[str, Any]:
    """Return current provider configuration (safe for logging, no secrets)."""
    config = _get_provider_config()
    return {
        "provider": config.provider,
        "model": config.model,
        "fallback_model": config.fallback_model or None,
        "base_url": config.base_url or "(default)",
        "has_api_key": bool(config.api_key),
        "real_llm_available": is_real_llm_available(),
        "temperature": config.temperature,
    }
