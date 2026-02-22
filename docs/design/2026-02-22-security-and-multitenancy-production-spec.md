# 安全与多租户生产化规范

> 版本：v2026.02.22-r2  
> 状态：Draft  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 将当前测试级隔离能力升级为生产级强隔离。
2. 建立 API/DB/Vector/Cache/Queue 五层一致隔离策略。
3. 固化高风险动作审批与不可抵赖审计。

## 2. 身份与租户注入

1. `tenant_id` 仅来自 JWT，不接受请求体注入。
2. 请求中间件将 `tenant_id/trace_id/request_id` 注入上下文。
3. 缺失或伪造租户上下文直接拒绝。

## 3. 五层隔离控制

### 3.1 API 层

1. 所有资源查询先做 tenant scope 检查。
2. 越权统一返回 `TENANT_SCOPE_VIOLATION`。

### 3.2 DB 层

1. 核心表全量 `tenant_id`。
2. 全量 RLS 策略启用。
3. 无 `app.current_tenant` 的会话拒绝读写。

### 3.3 Vector 层

1. 检索查询必须携带 `tenant_id + project_id` metadata 过滤。
2. 禁止不带 tenant 过滤的召回请求。

### 3.4 Cache/Queue 层

1. key 与消息头强制 tenant 前缀。
2. 禁止跨租户消费同一队列分片。

### 3.5 Object Storage

1. 路径命名强制 tenant 分区。
2. 下载鉴权必须二次校验租户与权限。

## 4. 高风险动作治理

1. `dlq discard`、终审确认、策略变更等动作需要双人审批。
2. 审批字段：`reviewer_id, reason, trace_id` 必填。
3. 所有审批事件写入审计日志。

## 5. 敏感信息与日志

1. token/密钥/PII 不得明文写日志。
2. 安全日志必须具备可追踪但不可泄密字段。
3. 密钥扫描纳入 CI 阻断。

## 6. 测试要求

1. 越权回归：API/DB/Vector 三层穿透测试。
2. 权限绕过与审批缺失测试。
3. 日志脱敏与密钥扫描测试。

## 7. 验收标准

1. 越权阻断项为 0。
2. 高风险动作审计覆盖率 100%。
3. 租户隔离策略在压测并发下稳定。

## 8. 关联文档

1. `docs/design/2026-02-21-security-design.md`
2. `docs/design/2026-02-21-data-model-and-storage-spec.md`
3. `docs/ops/agent-change-management.md`
4. `docs/ops/agent-incident-runbook.md`

## 9. 当前实现增量（r2）

1. 队列内部接口 `ack/nack` 已增加 inflight 消息 tenant 归属校验。
2. 跨租户 `ack/nack` 统一返回 `403 + TENANT_SCOPE_VIOLATION`。
3. 新增回归：`tests/test_internal_outbox_queue_api.py::test_internal_queue_ack_nack_blocks_cross_tenant`。
