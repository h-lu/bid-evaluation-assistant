# 检索与评分规范（LightRAG + 规则引擎 + LLM）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 检索链路可复现、可解释、可审计。
2. 评分链路可追溯、可复核、可校准。
3. 规则引擎与 LLM 分工清晰，避免黑盒决策。
4. 输出必须带证据引用，支持原文回跳。

## 2. 端到端流程（ASCII）

```text
query
 -> normalize
 -> extract_constraints
 -> rewrite(constraint-safe)
 -> mode_selector
 -> retrieve(lightrag + sql_branch)
 -> metadata_filter
 -> rerank
 -> evidence_packing
 -> rule_engine_hard_checks
 -> llm_soft_scoring
 -> confidence_and_citation_checks
 -> finalize_or_hitl
```

## 3. 查询处理

### 3.1 标准化

1. 全半角、大小写、空白归一。
2. 术语同义映射（项目词典）。
3. 数值/时间/金额标准化。
4. query_type 判定：`fact/relation/comparison/summary/risk`。

### 3.2 约束抽取

抽取最小结构：

1. `entity_constraints`
2. `numeric_constraints`
3. `time_constraints`
4. `must_include_terms`
5. `must_exclude_terms`

### 3.3 约束保持改写

允许：同义词替换、表达压缩、实体标准名替换。  
禁止：修改硬约束、扩展未授权范围。

输出字段：

1. `rewritten_query`
2. `rewrite_reason`
3. `constraints_preserved=true`
4. `constraint_diff=[]`

## 4. 检索模式选择

### 4.1 模式映射

| query_type | 默认 mode | 说明 |
| --- | --- | --- |
| fact | local | 定位具体实体/字段 |
| relation | global | 强调关系与全局关联 |
| comparison | hybrid | 兼顾实体与全局对比 |
| summary | hybrid | 概览型任务 |
| risk/trace | mix | 强证据召回与关系追溯 |

### 4.2 推荐参数

1. `top_k=60`
2. `chunk_top_k=20`
3. `include_references=true`
4. `enable_rerank=true`
5. `max_entity_tokens=6000`
6. `max_relation_tokens=8000`

### 4.3 selector 兜底

1. 无法分类时使用 `hybrid`。
2. 高风险任务强制 `mix`。
3. 任何模式都必须启用租户过滤。

## 5. 召回与过滤

### 5.1 召回来源

1. LightRAG 主召回。
2. SQL 白名单支路（结构化字段）。
3. 合并去重后进入 rerank。

### 5.2 强制过滤顺序

```text
tenant_id -> project_id -> doc_scope -> supplier_scope -> rule_scope
```

### 5.3 SQL 白名单支路

仅允许字段：

1. `supplier_code`
2. `qualification_level`
3. `registered_capital`
4. `bid_price`
5. `delivery_period`
6. `warranty_period`

禁止：

1. 任意 SQL 拼接。
2. 跨租户 JOIN。
3. 绕过 API 层租户过滤。

## 6. 重排与证据打包

### 6.1 rerank 输出

每条候选至少包含：

1. `chunk_id`
2. `score_raw`
3. `score_rerank`
4. `reason`
5. `metadata`

### 6.2 evidence packing

打包规则：

1. 按评分项分别打包证据。
2. 每项最少 2 条证据，最多 8 条证据。
3. 证据优先级：高相关 + 高置信 + 多样来源。

### 6.3 token budget

1. 单项评分上下文 `<= 6k tokens`。
2. 全报告上下文 `<= 24k tokens`。
3. 超预算按“低相关 -> 冗余来源”顺序裁剪。

### 6.4 rerank 降级

1. rerank 超时：降级到召回分排序。
2. rerank 异常：记录降级事件，不中断主流程。
3. 降级比例超阈值触发告警。

## 7. 规则引擎与 LLM 分工

### 7.1 规则引擎（硬约束）

1. 合规红线判定（是否一票否决）。
2. 明确公式项计算（价格分、交付分）。
3. 缺失关键材料判定。

### 7.2 LLM（软约束）

1. 语义匹配评分。
2. 方案可行性分析。
3. 风险说明与建议。

约束：

1. LLM 不得覆盖规则引擎红线结论。
2. LLM 每条 claim 必须关联 citation。

## 8. 评分模型

### 8.1 分项结构

每个评分项输出：

1. `criteria_id`
2. `score`
3. `max_score`
4. `hard_pass`
5. `reason`
6. `citations[]`
7. `confidence`

### 8.2 总分公式

```text
total_score = Σ(criteria_score * criteria_weight)
```

### 8.3 置信度

```text
confidence = 0.4 * evidence_quality + 0.3 * retrieval_agreement + 0.3 * model_stability
```

### 8.4 一致性校准（P1）

1. 同样本多次评估波动超过阈值触发校准。
2. 校准过程记录 anchor 样本与校准参数。

## 9. HITL 触发条件

任一条件命中即触发：

1. `confidence < 0.65`
2. `citation_coverage < 0.90`
3. `score_deviation_pct > 20%`
4. 红线项判定冲突
5. 人工强制复核标记

## 10. 防幻觉与引用约束

1. `claim -> citation` 一一映射校验。
2. citation 必须可解析到 `chunk_id/page/bbox`。
3. 无证据 claim 标记为 `unsupported_claim` 并阻断终审建议。

## 11. 输出契约（最小）

```json
{
  "evaluation_id": "ev_xxx",
  "supplier_id": "sp_xxx",
  "total_score": 88.5,
  "confidence": 0.78,
  "risk_level": "medium",
  "criteria_results": [],
  "citations": [],
  "needs_human_review": false,
  "trace_id": "trace_xxx"
}
```

## 12. 验收门禁

### 12.1 离线

1. RAGAS `precision/recall >= 0.80`。
2. Faithfulness `>= 0.90`。
3. citation 回跳率 `>= 98%`。

### 12.2 在线

1. 检索 P95 `<= 4s`。
2. 评分 P95 `<= 120s`。
3. 幻觉率 `<= 5%`。

## 13. 参考来源（核验：2026-02-21）

1. LightRAG: https://github.com/HKUDS/LightRAG
2. RAGAS: https://github.com/explodinggradients/ragas
3. RAGChecker: https://github.com/amazon-science/RAGChecker
4. DeepEval: https://github.com/confident-ai/deepeval
5. 历史融合提交：`7f05f7e`, `53e3d92`, `72a64da`
