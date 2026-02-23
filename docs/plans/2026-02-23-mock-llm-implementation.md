# Mock LLM 实现

> 版本：v1.0
> 状态：Draft
> 日期：2026-02-23
> 分支：`codex/mock-llm-implementation`
> 对齐：`docs/design/2026-02-21-langgraph-agent-workflow-spec.md`

## 1. 目标

实现 Mock LLM 层，使端到端流程可运行，无需真实 LLM API 调用。

## 2. 范围

### 2.1 覆盖节点

| 节点 | Mock 实现 | 说明 |
|------|-----------|------|
| `load_context` | 加载项目/规则 | 已有实现 |
| `retrieve_evidence` | `mock_retrieve_evidence()` | Mock 向量检索 |
| `evaluate_rules` | 硬约束判定 | 已有逻辑 |
| `score_with_llm` | `mock_score_criteria()` | Mock LLM 评分 |
| `quality_gate` | 置信度判断 | 已有逻辑 |
| `finalize_report` | 组装报告 | 已有逻辑 |

### 2.2 不在范围

- 真实 LLM API 集成
- 向量数据库集成
- 真实文档解析（PDF/Word）

## 3. 实现设计

### 3.1 新增模块 `app/mock_llm.py`

```python
"""Mock LLM 模块 - 用于端到端流程验证"""

import os
from typing import Any

MOCK_LLM_ENABLED = os.getenv("MOCK_LLM_ENABLED", "true").lower() == "true"

def mock_retrieve_evidence(
    query: str,
    top_k: int = 5,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Mock 证据检索。

    返回模拟的检索结果，包含 chunk_id、page、text 等字段。
    """
    ...

def mock_score_criteria(
    criteria_id: str,
    requirement_text: str,
    evidence_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Mock LLM 评分。

    基于规则生成确定性评分：
    - 包含关键词 → 高分
    - 无匹配 → 低分
    """
    ...

def mock_generate_explanation(
    criteria_id: str,
    score: float,
    evidence: list[dict[str, Any]],
) -> str:
    """
    Mock 解释生成。

    生成标准格式的评分解释。
    """
    ...
```

### 3.2 集成点

在 `store.py` 的 `_finalize_evaluation_report()` 中使用 Mock LLM：

```python
if MOCK_LLM_ENABLED:
    from app.mock_llm import mock_score_criteria, mock_generate_explanation
    # 使用 mock 实现
else:
    # 未来：真实 LLM 调用
    pass
```

### 3.3 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MOCK_LLM_ENABLED` | `true` | 启用 Mock LLM |
| `MOCK_LLM_SCORE_BASELINE` | `0.7` | 基础分数 |
| `MOCK_LLM_CONFIDENCE` | `0.85` | 默认置信度 |

## 4. 确定性规则

为确保测试可重复，Mock LLM 使用确定性规则：

| 条件 | 分数 | 说明 |
|------|------|------|
| evidence 包含 "资质" | 0.9 | 高相关性 |
| evidence 包含 "交付" | 0.85 | 高相关性 |
| evidence 包含 "价格" | 0.75 | 中等相关性 |
| evidence 为空 | 0.3 | 低分 |
| 默认 | 0.7 | 基线 |

## 5. 验收标准

1. 端到端流程可运行：上传 → 解析 → 评分 → 报告
2. Mock LLM 输出确定性（相同输入 → 相同输出）
3. 所有现有测试继续通过
4. 新增 Mock LLM 单元测试

## 6. 后续步骤

完成 Mock LLM 后：
- 实现真实 LLM 集成（Claude API）
- 实现向量检索（pgvector / Qdrant）
- 实现文档解析（Unstructured / PyMuPDF）
