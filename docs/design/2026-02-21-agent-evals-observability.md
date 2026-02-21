# AI Agent 评估与可观测性规范（2026）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 发布前可评估，发布后可监控，异常时可快速回滚。
2. 评估不只看最终答案，还覆盖轨迹质量。
3. 线上问题可定位到具体节点、工具、模型与版本。

## 2. 评估分层

```text
离线评估
 -> 预发回放
 -> 灰度在线评估
 -> 全量持续监控
```

### 2.1 离线评估（必选）

评估对象：

1. 最终输出质量。
2. 轨迹步骤正确性（state transition correctness）。
3. 工具调用正确性（schema + side effect）。
4. citation 可回跳性。

### 2.2 预发回放（必选）

1. 使用历史真实样本回放候选版本。
2. 与基线版本做差异分析。
3. 任一核心指标劣化超阈值即阻断。

### 2.3 在线评估（必选）

1. 按租户/项目分层采样。
2. 高风险任务提高人工抽检比例。
3. 线上失败样本回流到离线数据集。

## 3. 指标体系

### 3.1 质量指标

1. RAGAS（precision/recall/faithfulness/relevancy）。
2. DeepEval（hallucination）。
3. citation resolvable rate。
4. 人审后改判率。

### 3.2 轨迹指标

1. 非法状态流转率。
2. interrupt 触发准确率。
3. resume 成功率。
4. 副作用重复执行率。

### 3.3 性能指标

1. API/检索/解析/评估 P95。
2. 队列等待时延。
3. DLQ 日增长率。

### 3.4 成本指标

1. 单任务成本 P95。
2. 租户预算偏差率。
3. 模型降级触发率。

## 4. Trace 规范

每次请求必须贯穿：

1. `trace_id`
2. `request_id`
3. `job_id`
4. `thread_id`
5. `tenant_id`
6. `evaluation_id`

每个节点日志必须记录：

1. `node_name`
2. `input_hash/output_hash`
3. `latency_ms`
4. `tool_calls[]`
5. `error_code`

## 5. 评估执行流程

```text
准备数据集 -> 冻结候选版本 -> 执行离线评估 -> 预发回放 -> 结果对比 -> 决策放行/阻断
```

阻断条件：

1. 质量核心指标跌破阈值。
2. citation 回跳率低于 98%。
3. 安全回归失败。

## 6. 漂移检测

1. 文档分布漂移（版式、语言、噪声）。
2. 查询分布漂移（查询意图变化）。
3. 结果漂移（评分分布异常）。

检测到漂移后：

1. 触发快速回放验证。
2. 调整 selector/评分阈值。
3. 更新数据集版本。

## 7. 看板与告警

### 7.1 看板最小视图

1. 质量看板：RAGAS/DeepEval/citation。
2. 流程看板：状态机、HITL、DLQ。
3. 成本看板：任务成本、模型分布。

### 7.2 告警分级

1. P0：越权、主链路不可用。
2. P1：质量显著劣化、DLQ 激增。
3. P2：性能退化与成本异常。

## 8. 与发布流程联动

1. 每次发布必须附评估报告链接。
2. 灰度期间启用加严告警阈值。
3. 触发回滚后自动创建复盘任务。

## 9. 本项目落地清单

1. 指标采集 SDK 与日志规范。
2. 评估流水线（离线 + 预发 + 灰度）。
3. 漂移检测作业。
4. 失败样本回流机制。
5. 统一评估报告模板。

## 10. 验收标准

1. 可从任一结果追溯到完整执行轨迹。
2. 门禁阻断逻辑可自动执行。
3. 告警触发到处置流程闭环可验证。

## 11. 参考来源（核验：2026-02-21）

1. LangSmith/LangChain eval docs: https://docs.langchain.com/
2. RAGAS: https://github.com/explodinggradients/ragas
3. DeepEval: https://github.com/confident-ai/deepeval
4. RAGChecker: https://github.com/amazon-science/RAGChecker
