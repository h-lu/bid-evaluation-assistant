# 观测与部署生产化规范

> 版本：v2026.02.22-r4  
> 状态：Active  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 文档目标

1. 建立可观测、可告警、可灰度、可回滚、可复盘的发布体系。
2. 将 Gate D/E/F 门禁与部署流水线联动成可执行流程。
3. 定义发布准入证据与回退动作，避免“凭感觉上线”。

## 2. 范围与非目标

### 2.1 纳入范围

1. Metrics/Logs/Traces 统一语义。
2. 告警分级（P0/P1/P2）与 runbook 联动。
3. staging replay、canary、rollback 机制。
4. P6 准入接口与发布决策流程。

### 2.2 非目标

1. 全栈 AIOps 自动调参。
2. 多云统一发布平台。

## 3. 当前基线（已完成）

1. `GET /api/v1/internal/ops/metrics/summary` 已提供租户级指标摘要。
2. `POST /api/v1/internal/release/replay/e2e` 已可执行最小回放。
3. `POST /api/v1/internal/release/readiness/evaluate` 已可执行准入评估。

## 4. 目标发布流水线

```text
build
 -> unit/integration
 -> contract regression
 -> staging replay
 -> Gate D checks
 -> Gate E rollout decision
 -> canary
 -> full release
 -> Gate F feedback/tuning
```

发布原则：

1. 无证据不发布。
2. 触发阈值即回滚，不做人工拖延。
3. 回滚后必须执行 replay 验证。

## 5. 实施任务（执行顺序）

### 5.1 P5-S1：指标语义统一

输入：当前 metrics summary。  
产出：API/Worker/Quality/Cost/SLO 指标字典与采集规范。  
验收：同一指标在 dashboard/告警/报告中口径一致。

### 5.2 P5-S2：日志与 Trace 串联

输入：S1。  
产出：`trace_id/request_id/tenant_id/job_id/error_code` 全链路贯通。  
验收：任一失败请求可从 API 追到 Worker 与 DB 事件。

### 5.3 P5-S3：门禁与流水线联动

输入：S2。  
产出：Gate D 四门禁自动判定与阻断步骤。  
验收：任一门禁失败时流水线自动停止。

### 5.4 P5-S4：灰度与回滚执行

输入：S3。  
产出：Gate E rollout/rollback 自动化执行。  
验收：连续超阈值触发回滚并在 30 分钟内恢复。

### 5.5 P5-S5：发布准入与回放

输入：S4。  
产出：P6 replay + readiness 作为发布前强制步骤。  
验收：无 replay 证据或 readiness 不通过时禁止发布。

### 5.6 P5-S6：运营优化闭环

输入：S5。  
产出：Gate F 数据回流与策略调优闭环。  
验收：每次迭代产出新数据集版本与策略版本。

## 6. 告警分级与响应

1. P0：越权风险、主链路不可用，5 分钟内止损。
2. P1：质量显著劣化、DLQ 激增，15 分钟内降级。
3. P2：性能或成本异常，30 分钟内修正或回退。

每条告警必须包含：

1. runbook 链接。
2. oncall 责任人。
3. 最近变更版本。

## 7. 契约与准入规则

1. 发布准入要求：`quality/performance/security/cost/rollout/rollback/ops` 全部通过 + `replay_passed=true`。
2. 任一项失败时 `admitted=false`，禁止发布。
3. 回滚后必须再次执行 replay，成功才允许恢复流量。

## 8. 配置清单

1. `OTEL_EXPORTER_OTLP_ENDPOINT`
2. `OBS_METRICS_NAMESPACE`
3. `OBS_ALERT_WEBHOOK`
4. `RELEASE_CANARY_RATIO`
5. `RELEASE_CANARY_DURATION_MIN`
6. `ROLLBACK_MAX_MINUTES`
7. `P6_READINESS_REQUIRED`

## 9. 测试与验证命令

1. 指标接口结构与租户隔离回归。
2. Gate D/E/F 内部接口回归。
3. P6 replay/readiness 回归。
4. 全量回归。

建议命令：

```bash
pytest -q tests/test_observability_metrics_api.py
pytest -q tests/test_gate_d_other_gates.py tests/test_gate_e_rollout_and_rollback.py tests/test_gate_f_ops_optimization.py
pytest -q tests/test_release_readiness_api.py
pytest -q
```

## 10. 验收证据模板

1. 指标看板截图与告警触发记录。
2. staging replay 报告。
3. canary 期间关键指标对比（before/after）。
4. 回滚演练记录（触发时间、完成时间、恢复状态）。
5. readiness 准入报告（failed_checks 为空）。

## 11. 退出条件（P5/P6 完成定义）

1. 观测三件套（metrics/logs/traces）可用于故障定位。
2. Gate D/E/F 与流水线自动联动。
3. 可重复执行灰度与回滚。
4. 发布前强制回放与准入评估生效。

## 12. 风险与回退

1. 风险：告警阈值配置不当导致误触发。
2. 风险：canary 样本不足导致误判。
3. 回退：降流量到稳定版本并冻结策略变更，待 replay 复核后再恢复。

## 13. 实施检查清单

1. [ ] 指标/日志/Trace 统一语义已落地。
2. [ ] Gate D/E/F 自动阻断已联动。
3. [ ] canary 与 rollback 演练通过。
4. [ ] P6 准入规则在流水线中强制执行。
5. [ ] 复盘模板与runbook链接完备。
