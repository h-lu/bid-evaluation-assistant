# 存储与队列生产化规范

> 版本：v2026.02.22-r4  
> 状态：Active  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 文档目标

1. 将当前 `memory/sqlite` 兼容实现升级为 `PostgreSQL + Redis` 生产实现。
2. 保持既有 API 契约、错误码、状态机语义不变。
3. 给实现与验收提供可直接执行的任务分解与证据格式。

## 2. 范围与非目标

### 2.1 纳入范围

1. 仓储真值迁移：`jobs/workflow_checkpoints/dlq_items/audit_logs/evaluation_reports/documents/document_chunks`。
2. 幂等与 outbox：请求幂等键、事件可靠投递、消费去重。
3. Redis 队列：enqueue/dequeue/ack/nack/retry/DLQ。
4. DB RLS 注入：`app.current_tenant` 会话级注入与强校验。

### 2.2 非目标

1. 跨地域多活。
2. 跨服务分布式事务。
3. 自动分片与在线扩容编排。

## 3. 当前基线（已完成）

1. `SqliteBackedStore` + `SqliteQueueBackend` 已提供本地持久化回归能力。
2. outbox/queue 内部联调接口已存在并有回归测试。
3. queue `ack/nack` 已有租户归属校验。

## 4. 目标架构

```text
FastAPI -> Repository Facade -> PostgreSQL (truth)
                         -> Outbox Table -> Relay Worker -> Redis Queue
Worker -> Redis Queue -> Domain Executor -> PostgreSQL + Audit
```

约束：

1. API 不直接操作 Redis 与 SQL 细节，统一经 repository/queue abstraction。
2. 业务事务与 outbox 写入同事务提交。
3. 任一重试失败不得破坏状态机时序（`dlq_pending -> dlq_recorded -> failed`）。

## 5. 实施任务（执行顺序）

### 5.1 P1-S1：Repository 真实现

输入：现有 `app/store.py` 行为与测试基线。  
产出：`app/repositories/` 按领域拆分的 PostgreSQL 实现。  
验收：现有 API 测试在 `BEA_STORE_BACKEND=postgres` 下通过。

最小交付：

1. `JobsRepository`、`WorkflowRepository`、`DlqRepository`、`AuditRepository`。
2. 所有写接口显式接收 `tenant_id` 与 `trace_id`。
3. 与当前 `InMemoryStore` 输出字段保持一致。

### 5.2 P1-S2：事务与 RLS

输入：S1 仓储实现。  
产出：`app/db/` 事务模板、tenant 注入中间层。  
验收：无 tenant 上下文请求全部失败；跨租户访问被 DB 阻断。

最小交付：

1. 会话变量：`SET app.current_tenant = :tenant_id`。
2. 核心表 RLS policy 全覆盖。
3. 事务工具：`run_in_tx(tenant_id, fn)`。

### 5.3 P1-S3：Redis 队列生产化

输入：现有 queue 抽象。  
产出：`RedisQueueBackend`。  
验收：重试、ack/nack、并发消费、tenant 前缀隔离回归通过。

最小交付：

1. key 命名：`bea:{env}:{tenant}:{queue}`。
2. 消息字段：`message_id,event_id,job_id,tenant_id,trace_id,job_type,attempt`。
3. 超阈值失败进入 DLQ 并写审计。

### 5.4 P1-S4：Outbox Relay 可靠投递

输入：S1/S3。  
产出：relay worker 与幂等消费键。  
验收：重复 relay 不重复投递业务副作用。

最小交付：

1. outbox 状态：`pending/published/failed`。
2. 幂等键：`event_id + consumer_name`。
3. 死信事件可重放并可审计。

### 5.5 P1-S5：灰度切换与回退

输入：S1-S4。  
产出：可切换配置、回退脚本、演练记录。  
验收：30 分钟内完成 `postgres+redis -> sqlite` 回退。

最小交付：

1. 开关：`BEA_STORE_BACKEND=sqlite|postgres`、`BEA_QUEUE_BACKEND=sqlite|redis`。
2. 双写观察窗口与一致性比对脚本。
3. 回退 Runbook（命令级）。

## 6. 数据与契约约束

1. 外部 REST/OpenAPI 不新增破坏性字段。
2. `job_id/thread_id/resume_token/error.code` 语义不可变。
3. 新增仅允许内部字段，不允许修改现有字段含义。

## 7. 配置清单

1. `POSTGRES_DSN`
2. `POSTGRES_POOL_MIN`
3. `POSTGRES_POOL_MAX`
4. `BEA_STORE_POSTGRES_TABLE`
5. `REDIS_DSN`
6. `REDIS_QUEUE_VISIBILITY_TIMEOUT_S`
7. `IDEMPOTENCY_TTL_HOURS`
8. `OUTBOX_POLL_INTERVAL_MS`
9. `BEA_STORE_BACKEND`
10. `BEA_QUEUE_BACKEND`

## 8. 测试与验证命令

1. 单测：repository CRUD/tenant scope/idempotency。
2. 集成：queue retry/ack/nack/DLQ/outbox relay。
3. 回放：Gate C-D 核心链路在 postgres+redis 下跑通。

建议命令：

```bash
pytest -q tests/test_store_persistence_backend.py
pytest -q tests/test_queue_backend.py tests/test_internal_outbox_queue_api.py
pytest -q
```

## 9. 验收证据模板

每次提交必须附：

1. 变更摘要（接口/数据模型/配置）。
2. 测试输出（命令 + 通过截图或日志片段）。
3. 一致性比对结果（双写窗口）。
4. 回退演练结果（开始时间、结束时间、结果）。

## 10. 退出条件（P1 完成定义）

1. 主链路关键状态完全不依赖进程内内存。
2. 重启后 `jobs/checkpoints/outbox` 可恢复。
3. 跨租户访问在 API + DB + queue 三层都被阻断。
4. 全量回归在 `postgres+redis` 模式通过。

## 11. 风险与回退

1. 风险：SQL 性能退化导致 job 超时。
2. 风险：queue 可见性超时配置不当造成重复消费。
3. 回退：切回 `sqlite` 后端，冻结高风险写操作，仅保留读与必要恢复动作。

## 12. 实施检查清单

1. [ ] repository 真实现可用。
2. [ ] RLS 生效并有越权回归。
3. [ ] Redis queue 路径通过并发回归。
4. [ ] outbox relay 幂等验证通过。
5. [ ] 回退脚本与演练记录完成。

## 13. 本轮实现更新（r2+）

1. 新增 `PostgresBackedStore`，支持 `BEA_STORE_BACKEND=postgres`。
2. `create_store_from_env` 新增 `POSTGRES_DSN` 校验与 `BEA_STORE_POSTGRES_TABLE` 配置。
3. 新增工厂回归：`tests/test_store_persistence_backend.py` 覆盖 postgres 分支（fake driver）。
4. 新增 `app/db/postgres.py` 事务执行器 `PostgresTxRunner`，统一 `SET LOCAL app.current_tenant` 注入。
5. 新增 `RedisQueueBackend`，支持 `BEA_QUEUE_BACKEND=redis` 与 tenant 前缀 key 语义。
6. 新增回归：`tests/test_queue_backend.py` 覆盖 redis 工厂与 `enqueue/dequeue/nack/ack` 生命周期（fake driver）。
