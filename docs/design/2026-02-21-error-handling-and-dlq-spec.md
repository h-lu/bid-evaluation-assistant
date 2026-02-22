# 错误处理与 DLQ 规范

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. API/Worker/Workflow 使用同一错误语义。
2. 明确可重试与不可重试边界。
3. 固化 `failed` 与 `DLQ` 的先后关系。
4. 支持降级、回滚、审计闭环。

## 2. 错误对象契约

最小字段：

1. `code`
2. `message`
3. `class`
4. `http_status`
5. `retryable`
6. `trace_id`
7. `job_id`
8. `details`
9. `occurred_at`

错误类别：

1. `validation`
2. `business_rule`
3. `transient`
4. `permanent`
5. `security_sensitive`

## 3. 错误码基线

### 3.1 认证与权限

1. `AUTH_UNAUTHORIZED`
2. `AUTH_FORBIDDEN`
3. `TENANT_SCOPE_VIOLATION`

### 3.2 请求与幂等

1. `REQ_VALIDATION_FAILED`
2. `IDEMPOTENCY_CONFLICT`
3. `IDEMPOTENCY_MISSING`

### 3.3 解析与检索

1. `DOC_PARSE_OUTPUT_NOT_FOUND`
2. `DOC_PARSE_SCHEMA_INVALID`
3. `MINERU_BBOX_FORMAT_INVALID`
4. `TEXT_ENCODING_UNSUPPORTED`
5. `PARSER_FALLBACK_EXHAUSTED`
6. `RAG_RETRIEVAL_TIMEOUT`
7. `RAG_UPSTREAM_UNAVAILABLE`

### 3.4 工作流与恢复

1. `WF_STATE_TRANSITION_INVALID`
2. `WF_INTERRUPT_RESUME_INVALID`
3. `WF_CHECKPOINT_NOT_FOUND`

### 3.5 DLQ 与运维

1. `DLQ_ITEM_NOT_FOUND`
2. `DLQ_REQUEUE_CONFLICT`
3. `APPROVAL_REQUIRED`

## 4. API 错误响应规则

1. 生产环境不返回堆栈。
2. 必须带 `trace_id`。
3. `retryable=true` 时返回 `retry_after_seconds`（可选）。
4. 4xx 不自动重试，5xx 由客户端按策略重试。

## 5. 重试与断路器

### 5.1 Worker 重试策略

1. 最大重试 3 次。
2. 指数退避 + 抖动。
3. 默认：`transient` 才可重试。

### 5.2 断路器策略

1. 连续失败阈值：5（60 秒窗口）。
2. Open 状态维持：30 秒。
3. Half-open 探测通过后恢复。

### 5.3 降级策略

1. rerank 失败降级为原检索排序。
2. 非关键外部服务失败时切换为只读/低风险模式。
3. 降级动作必须写审计事件。

## 6. DLQ 子流程（强制）

### 6.1 状态机

```text
running
 -> retrying (1..3)
 -> dlq_pending
 -> dlq_recorded
 -> failed
```

### 6.2 时序约束

1. 先写 `dlq_items`。
2. 再把 `jobs.status` 改为 `failed`。
3. 任一步失败都不能跳过重试/补偿。

### 6.3 DLQ 数据字段

1. `dlq_id`
2. `tenant_id`
3. `job_id`
4. `error_class`
5. `error_code`
6. `payload_snapshot`
7. `context_snapshot`
8. `status`（`open/requeued/discarded`）
9. `created_at`

## 7. DLQ 运维动作

### 7.1 requeue

1. 条件：问题可修复、依赖恢复、幂等安全。
2. 动作：生成新 job，关联原 dlq_id。
3. 审计：记录 requeue 原因与操作者。

### 7.2 discard

1. 条件：确认无需重放或已人工替代处理。
2. 约束：双人复核 + 必填 reason。
3. 审计：记录 `reviewer_id/reviewer_id_2/approval_reviewers`。

## 8. 审计与告警

1. `security_sensitive` 错误即时告警。
2. 同类错误 5 分钟内超阈值触发事故流程。
3. DLQ 日增量超阈值触发 P1 排查。

## 9. 与 runbook 联动

1. P0/P1 事故必须包含错误码分布图。
2. runbook 止损动作优先关闭高风险写路径。
3. 事故后必须回补测试用例。

## 10. 验收标准

1. 全链路错误对象字段完整。
2. retry 与 DLQ 时序严格符合规范。
3. `discard` 无审批不可执行。
4. 告警与审计联动可验证。

## 11. 参考来源（核验：2026-02-21）

1. FastAPI exception handling: https://fastapi.tiangolo.com/
2. 历史融合提交：`beef3e9`, `53e3d92`
