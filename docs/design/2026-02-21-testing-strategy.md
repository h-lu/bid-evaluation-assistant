# 测试策略

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 测试目标

1. 保证主链路端到端稳定可运行。
2. 保证多租户隔离不可绕过。
3. 保证评分输出可追溯、可复核。
4. 保证失败恢复、DLQ 流程可执行。

## 2. 分层测试策略

### 2.1 单元测试（60%-70%）

覆盖：

1. 规则引擎判定器。
2. 检索模式选择器。
3. 评分与置信度计算器。
4. 错误分类与重试决策。
5. bbox 归一化与引用映射。

### 2.2 集成测试（20%-30%）

覆盖：

1. API + DB + Queue。
2. 解析链路（MinerU/Docling/fallback）。
3. 检索链路（LightRAG + SQL 支路 + rerank）。
4. LangGraph 中断恢复与 checkpoint。
5. DLQ 子流程。

### 2.3 E2E 测试（10%）

覆盖主业务场景：

```text
upload -> parse/index -> evaluate -> hitl(optional) -> report -> archive
```

## 3. 关键测试矩阵

| 维度 | 场景 | 预期 |
| --- | --- | --- |
| 租户隔离 | 跨租户读取评估结果 | 403 `TENANT_SCOPE_VIOLATION` |
| 异步 | 写接口触发长任务 | 202 + `job_id` |
| 状态机 | 非法流转 | 409 `WF_STATE_TRANSITION_INVALID` |
| HITL | 命中阈值 | 进入 `needs_manual_decision` |
| Resume | 合法恢复 | 回到 `running` 并完成 |
| DLQ | 重试耗尽 | `dlq_recorded` 后 `failed` |
| 引用 | citation 回跳 | 页码+bbox 可定位 |
| 幂等 | 同 key 同 body | 返回同结果 |
| 幂等冲突 | 同 key 异 body | 409 `IDEMPOTENCY_CONFLICT` |
| 约束改写 | 改写不破坏硬约束 | `constraints_preserved=true` |

## 4. 质量门禁测试

### 4.1 指标阈值

1. RAGAS:
   - Context Precision >= 0.80
   - Context Recall >= 0.80
   - Faithfulness >= 0.90
   - Response Relevancy >= 0.85
2. DeepEval:
   - Hallucination Rate <= 5%
3. 引用可回跳率 >= 98%
4. P1：RAGChecker 输出 retriever/generator 诊断报告

### 4.2 数据集构成

1. 黄金集：稳定基准。
2. 反例集：冲突信息、诱导幻觉、证据缺失。
3. 漂移集：新版模板、扫描噪声、版式变化。
4. 回流集：线上失败与人工改判样本。

## 5. 性能与稳定性测试

1. API P95 <= 1.5s。
2. 检索 P95 <= 4.0s。
3. 50 页解析 P95 <= 180s。
4. 评估 P95 <= 120s。
5. 并发场景下 DLQ 率 <= 1%（日均）。

## 6. 安全测试

1. 租户越权访问测试（API/DB/retrieval）。
2. 角色权限绕过测试。
3. token 重放与失效测试。
4. Prompt 注入与工具越权测试。

## 7. 可靠性与故障注入

1. 上游模型超时注入。
2. rerank 服务不可用注入。
3. 队列堆积与重试风暴注入。
4. checkpoint 存储异常注入。

目标：验证降级、断路器与回滚策略是否生效。

## 8. 前端 E2E 场景

1. 上传与状态追踪。
2. 评估页点对点表格与引用联动。
3. PDF 页码跳转与 bbox 高亮。
4. HITL 提交与恢复闭环。
5. DLQ requeue/discard 受控流程。

## 9. Agent 开发执行模式

1. 每次变更至少运行：单元 + 核心集成 + E2E 冒烟。
2. 触发门禁时运行：全量离线评估 + 压测 + 安全回归。
3. 失败测试必须记录根因并补齐回归用例。

## 10. 发布阻断条件

任一命中即阻断：

1. 质量指标低于阈值。
2. 跨租户越权。
3. 性能 P95 超阈值且无可接受降级策略。
4. 高风险动作审计缺失。

## 11. 验收标准

1. 四门禁报告可复核。
2. 关键路径回归稳定。
3. 失败样本可定位并可复现。

## 12. 参考来源（核验：2026-02-21）

1. RAGAS: https://github.com/explodinggradients/ragas
2. RAGChecker: https://github.com/amazon-science/RAGChecker
3. DeepEval: https://github.com/confident-ai/deepeval
4. 历史融合提交：`53e3d92`, `7f05f7e`
