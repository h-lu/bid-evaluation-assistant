"""
Mock LLM 模块 - 用于端到端流程验证

在 MOCK_LLM_ENABLED=true 时启用，提供确定性的模拟 LLM 输出。
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

# 配置
MOCK_LLM_ENABLED = os.getenv("MOCK_LLM_ENABLED", "true").lower() == "true"
MOCK_LLM_SCORE_BASELINE = float(os.getenv("MOCK_LLM_SCORE_BASELINE", "0.7"))
MOCK_LLM_CONFIDENCE = float(os.getenv("MOCK_LLM_CONFIDENCE", "0.85"))


def _deterministic_float(seed: str, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    基于种子生成确定性浮点数。

    确保相同输入始终产生相同输出。
    """
    h = hashlib.sha256(seed.encode()).hexdigest()
    val = int(h[:8], 16) / 0xFFFFFFFF
    return min_val + val * (max_val - min_val)


def mock_retrieve_evidence(
    query: str,
    *,
    top_k: int = 5,
    tenant_id: str | None = None,
    supplier_id: str | None = None,
    doc_scope: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Mock 证据检索。

    返回模拟的检索结果，包含 chunk_id、page、text 等字段。
    基于查询内容生成确定性结果。

    Args:
        query: 检索查询
        top_k: 返回数量
        tenant_id: 租户 ID
        supplier_id: 供应商 ID
        doc_scope: 文档范围

    Returns:
        检索到的证据块列表
    """
    results = []

    # 基于查询关键词生成模拟证据
    keywords = {
        "资质": {
            "text": "供应商具备 ISO9001 质量管理体系认证，证书编号 CN12345，有效期至 2026-12-31。",
            "page": 8,
            "score_raw": 0.92,
        },
        "交付": {
            "text": "承诺在合同签订后 30 个工作日内完成全部交付，验收标准详见附件 A。",
            "page": 12,
            "score_raw": 0.88,
        },
        "价格": {
            "text": "总报价人民币 1,280,000 元，含税含运，价格有效期 90 天。",
            "page": 5,
            "score_raw": 0.78,
        },
        "技术": {
            "text": "技术方案采用分布式微服务架构，支持高可用和水平扩展。",
            "page": 15,
            "score_raw": 0.85,
        },
        "服务": {
            "text": "提供 7x24 小时技术支持，响应时间不超过 2 小时。",
            "page": 20,
            "score_raw": 0.82,
        },
        "经验": {
            "text": "近三年完成同类项目 15 个，累计合同金额超过 5000 万元。",
            "page": 3,
            "score_raw": 0.90,
        },
    }

    # 检查查询中包含的关键词
    matched_keywords = []
    for kw, data in keywords.items():
        if kw in query:
            matched_keywords.append((kw, data))

    # 如果没有匹配，生成通用证据
    if not matched_keywords:
        matched_keywords = [
            (
                "通用",
                {
                    "text": f"关于 {query[:20]}... 的相关内容",
                    "page": 1,
                    "score_raw": MOCK_LLM_SCORE_BASELINE,
                },
            )
        ]

    # 生成确定性 chunk_id 和结果
    for i, (kw, data) in enumerate(matched_keywords[:top_k]):
        seed = f"{tenant_id or 'default'}:{supplier_id or 'default'}:{kw}:{i}"
        chunk_id = f"ck_{hashlib.sha256(seed.encode()).hexdigest()[:16]}"

        results.append(
            {
                "chunk_id": chunk_id,
                "page": data["page"],
                "bbox": [100.0 + i * 10, 200.0 + i * 5, 400.0 + i * 10, 250.0 + i * 5],
                "text": data["text"],
                "score_raw": data["score_raw"],
                "tenant_id": tenant_id or "tenant_default",
                "supplier_id": supplier_id,
            }
        )

    return results


def mock_score_criteria(
    criteria_id: str,
    requirement_text: str,
    evidence_chunks: list[dict[str, Any]],
    *,
    max_score: float = 10.0,
    hard_constraint_pass: bool = True,
) -> dict[str, Any]:
    """
    Mock LLM 评分。

    基于证据质量生成确定性评分：
    - 高 score_raw 证据 → 高分
    - 无证据 → 低分
    - hard_constraint_pass=True → 确保高分（避免误触发 HITL）

    Args:
        criteria_id: 评分项 ID
        requirement_text: 要求文本
        evidence_chunks: 证据块列表
        max_score: 最高分
        hard_constraint_pass: 硬约束是否通过

    Returns:
        评分结果 {score, max_score, hard_pass, reason}
    """
    if not evidence_chunks:
        # 无证据时，根据 hard_constraint_pass 决定分数
        base_score = 0.9 if hard_constraint_pass else 0.3
        return {
            "score": round(max_score * base_score, 2),
            "max_score": max_score,
            "hard_pass": hard_constraint_pass,
            "reason": "使用 Mock LLM 默认评分" if hard_constraint_pass else "未找到相关证据支持",
        }

    # 计算基于证据的分数
    avg_score_raw = sum(c.get("score_raw", 0.7) for c in evidence_chunks) / len(evidence_chunks)

    # 如果 hard_constraint_pass=True，确保分数不低于 85%
    if hard_constraint_pass:
        avg_score_raw = max(avg_score_raw, 0.9)

    # 映射到 0-max_score
    score = round(avg_score_raw * max_score, 2)
    score = min(max_score, max(0.0, score))  # clamp

    # 硬约束判定（score >= 60% 为 pass）
    hard_pass = score >= max_score * 0.6

    # 生成原因
    if hard_pass:
        reason = f"依据 {len(evidence_chunks)} 条证据，评分项符合要求"
    else:
        reason = f"依据 {len(evidence_chunks)} 条证据，评分项部分符合要求"

    return {
        "score": score,
        "max_score": max_score,
        "hard_pass": hard_pass,
        "reason": reason,
    }


def mock_generate_explanation(
    criteria_id: str,
    score: float,
    max_score: float,
    evidence: list[dict[str, Any]],
    *,
    response_text: str | None = None,
) -> str:
    """
    Mock 解释生成。

    生成标准格式的评分解释。

    Args:
        criteria_id: 评分项 ID
        score: 得分
        max_score: 最高分
        evidence: 证据列表
        response_text: 响应文本

    Returns:
        评分解释文本
    """
    percentage = (score / max_score) * 100 if max_score > 0 else 0

    if percentage >= 80:
        level = "优秀"
    elif percentage >= 60:
        level = "合格"
    elif percentage >= 40:
        level = "待改进"
    else:
        level = "不合格"

    evidence_count = len(evidence)
    pages = sorted(set(e.get("page") for e in evidence if e.get("page")))

    explanation = f"【{criteria_id}】评分：{score}/{max_score}（{level}）\n"
    explanation += f"依据 {evidence_count} 条证据"
    if pages:
        explanation += f"（参见第 {', '.join(map(str, pages[:3]))} 页{'等' if len(pages) > 3 else ''}）"
    explanation += "。"

    if response_text:
        explanation += f"\n响应摘要：{response_text[:100]}..."

    return explanation


def mock_classify_intent(query: str) -> dict[str, Any]:
    """
    Mock 意图分类。

    Args:
        query: 用户查询

    Returns:
        {intent, confidence, entities}
    """
    # 简单关键词匹配
    if any(kw in query for kw in ["资质", "认证", "证书"]):
        return {"intent": "qualification_check", "confidence": 0.92, "entities": ["资质"]}
    elif any(kw in query for kw in ["价格", "报价", "费用"]):
        return {"intent": "price_inquiry", "confidence": 0.88, "entities": ["价格"]}
    elif any(kw in query for kw in ["交付", "工期", "进度"]):
        return {"intent": "delivery_check", "confidence": 0.90, "entities": ["交付"]}
    else:
        return {"intent": "general_query", "confidence": 0.75, "entities": []}


def mock_quality_gate_check(
    confidence: float,
    citation_coverage: float,
    score_deviation_pct: float,
) -> dict[str, Any]:
    """
    Mock 质量门检查。

    根据 SSOT 规范判断是否需要 HITL。

    Args:
        confidence: 置信度
        citation_coverage: 引用覆盖率
        score_deviation_pct: 评分偏差百分比

    Returns:
        {gate_result, reasons}
    """
    reasons = []

    # HITL 触发条件（来自 SSOT）
    if confidence < 0.65:
        reasons.append(f"置信度过低 ({confidence:.2f} < 0.65)")
    if citation_coverage < 0.90:
        reasons.append(f"引用覆盖率不足 ({citation_coverage:.2%} < 90%)")
    if score_deviation_pct > 20.0:
        reasons.append(f"评分偏差过大 ({score_deviation_pct:.1f}% > 20%)")

    if reasons:
        return {"gate_result": "hitl", "reasons": reasons}
    else:
        return {"gate_result": "pass", "reasons": []}


# 便捷函数
def is_mock_llm_enabled() -> bool:
    """检查 Mock LLM 是否启用"""
    return MOCK_LLM_ENABLED
