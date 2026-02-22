# 观测与部署生产化规范

> 版本：v2026.02.22-r1  
> 状态：Draft  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 建立可观测、可告警、可回滚、可复盘的生产运行体系。
2. 将 Gate D/E/F 门禁与部署流水线联动。
3. 保证事故时可快速止损与恢复。

## 2. 观测基线

### 2.1 Metrics

1. API：QPS、错误率、P95、P99。
2. Worker：队列深度、处理时延、重试率、DLQ 增量。
3. 质量：faithfulness、hallucination_rate、citation 回跳率。
4. 成本：任务成本分位、降级触发率。

### 2.2 Logs

统一字段：

1. `timestamp`
2. `trace_id`
3. `request_id`
4. `tenant_id`
5. `job_id`
6. `node_name`
7. `error_code`

### 2.3 Traces

1. 主链路跨 API -> Queue -> Worker -> DB 完整串联。
2. HITL interrupt/resume 两段 trace 必须可关联。

## 3. 告警与升级

1. P0：越权风险、主链路不可用。
2. P1：DLQ 激增、幻觉率超阈值。
3. P2：性能或成本异常。
4. 每个告警必须绑定 runbook 链接与责任人。

## 4. 部署流水线

```text
build
 -> unit/integration
 -> contract regression
 -> staging replay
 -> gate checks (quality/perf/security/cost)
 -> canary
 -> full release
```

## 5. 灰度与回滚联动

1. 灰度准入基于租户白名单与项目规模。
2. 任一门禁连续超阈值触发回滚流程。
3. 回滚后强制执行一次 replay verification。

## 6. 运行手册联动

1. 变更前：`docs/ops/agent-change-management.md`
2. 事故中：`docs/ops/agent-incident-runbook.md`
3. 事故后：复盘报告与改进任务回写。

## 7. 测试与演练要求

1. 每次发布至少一次 staging 全链路回放。
2. 每月一次回滚演练。
3. 每月一次灾备恢复演练。

## 8. 验收标准

1. 可观测指标覆盖主链路与关键异常路径。
2. 告警触发到止损动作链路可验证。
3. 部署、灰度、回滚三套流程可重复执行。

## 9. 关联文档

1. `docs/design/2026-02-21-deployment-config.md`
2. `docs/design/2026-02-21-testing-strategy.md`
3. `docs/design/2026-02-21-agent-evals-observability.md`
4. `docs/ops/agent-incident-runbook.md`
