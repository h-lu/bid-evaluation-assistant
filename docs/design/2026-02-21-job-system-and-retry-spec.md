# 任务系统与重试规范（Gate B-2）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 固化异步任务状态机与合法流转。
2. 固化 3 次重试 + 指数退避 + 抖动策略。
3. 固化 DLQ 入列时序与失败终态规则。
4. 提供“可回放验证”的最小测试场景集合。

## 2. 任务模型

核心实体：`jobs`。

最小字段：

1. `job_id`
2. `tenant_id`
3. `job_type`
4. `status`
5. `retry_count`
6. `idempotency_key`
7. `trace_id`
8. `error_code`
9. `payload_json`
10. `created_at/updated_at`

## 3. 状态机（冻结）

```text
queued
 -> running
 -> succeeded

running
 -> retrying
 -> dlq_pending

retrying
 -> running
 -> dlq_pending

dlq_pending
 -> dlq_recorded
 -> failed
```

状态集合：

1. `queued`
2. `running`
3. `retrying`
4. `succeeded`
5. `dlq_pending`
6. `dlq_recorded`
7. `failed`

强约束：

1. `failed` 只能出现在 `dlq_recorded` 之后。
2. `succeeded` 与 `failed` 为互斥终态。
3. 非法流转返回 `WF_STATE_TRANSITION_INVALID`。

## 4. 重试策略（冻结）

### 4.1 触发条件

1. 仅 `retryable=true` 错误允许重试。
2. 最大重试次数：3（第 4 次失败进入 DLQ）。

### 4.2 退避算法

```text
delay_ms = min(max_backoff_ms, base_ms * 2^(retry_count-1)) + jitter_ms
jitter_ms in [0, 300]
```

默认参数：

1. `base_ms = 1000`
2. `max_backoff_ms = 30000`
3. `retry_count` 从 1 开始计数

### 4.3 幂等要求

1. 同一任务重试不得改变 `job_id`。
2. 同一次重试执行必须有幂等键：`job_id + retry_count`。
3. 已提交副作用节点禁止重复提交。

## 5. DLQ 子流程接入

### 5.1 入列时序

```text
running/retrying
 -> dlq_pending
 -> write dlq_items
 -> dlq_recorded
 -> failed
```

### 5.2 子流程动作

1. `requeue`：创建新 job，关联原 `dlq_id`。
2. `discard`：双人复核 + 必填 reason。

## 6. 回放验证规范（Gate B-2 验收）

| Replay ID | 初始状态 | 触发事件 | 期望流转 | 期望结果 |
| --- | --- | --- | --- | --- |
| `RP-001` | `queued` | worker 获取任务 | `queued -> running -> succeeded` | 成功终态 |
| `RP-002` | `running` | transient 错误（重试 1 次后成功） | `running -> retrying -> running -> succeeded` | `retry_count=1` |
| `RP-003` | `running` | transient 错误连续 3 次后成功 | `running -> retrying -> running -> retrying -> running -> retrying -> running -> succeeded` | `retry_count=3` |
| `RP-004` | `running` | transient 错误第 4 次仍失败 | `running/retrying -> dlq_pending -> dlq_recorded -> failed` | `failed` 且可关联 `dlq_id` |
| `RP-005` | `succeeded` | 非法重复终态写入 | 拒绝流转 | `WF_STATE_TRANSITION_INVALID` |

执行要求：

1. 每次回放记录 `trace_id/job_id/retry_count/status_transition`。
2. 任一案例失败，Gate B-2 不通过。

### 6.1 开发态回放触发（内测接口）

用于 Gate C 骨架验证的内部接口：

1. `POST /api/v1/internal/jobs/{job_id}/run`：成功路径（`queued/running -> succeeded`）。
2. `POST /api/v1/internal/jobs/{job_id}/run?force_fail=true`：直接进入 DLQ 终态路径。
3. `POST /api/v1/internal/jobs/{job_id}/run?transient_fail=true`：
   - 第 1~3 次：`running -> retrying`，并累加 `retry_count`。
   - 第 4 次：`running/retrying -> dlq_pending -> dlq_recorded -> failed`。

## 7. 监控与告警

1. `retrying` 比例超过阈值触发告警。
2. 单租户 `dlq_pending` 增速异常触发告警。
3. `WF_STATE_TRANSITION_INVALID` 连续出现触发 P1 排查。

## 8. 验收标准

1. 状态机定义与 `jobs.status` 字段一致。
2. 重试次数与退避规则可回放复现。
3. 第 4 次失败严格进入 `dlq_pending -> dlq_recorded -> failed`。
4. 回放样例 `RP-001` 至 `RP-005` 全通过。

## 9. 参考文档

1. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`
2. `docs/design/2026-02-21-data-model-and-storage-spec.md`
3. `docs/design/2026-02-21-rest-api-specification.md`
4. `docs/design/2026-02-21-testing-strategy.md`
