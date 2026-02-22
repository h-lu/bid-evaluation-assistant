# 存储与队列生产化规范

> 版本：v2026.02.22-r1  
> 状态：Draft  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 将 `app/store.py` 的 InMemory 关键路径替换为真实持久化与队列实现。
2. 保持既有 API 契约、错误码、状态机不变。
3. 提供可回滚的数据迁移与运行切换策略。

## 2. 范围

### 2.1 本阶段纳入

1. PostgreSQL：jobs/checkpoints/dlq/audit/report/document/chunk 真值落库。
2. Redis：队列、幂等键、分布式锁、短时缓存。
3. outbox：领域事件可靠投递。

### 2.2 本阶段不纳入

1. 跨服务分布式事务。
2. 多数据库主从拓扑自动切换。

## 3. 模块与目录改造

1. 新增 `app/repositories/`：按领域拆分仓储接口与实现。
2. 新增 `app/db/`：连接管理、事务模板、RLS tenant 注入。
3. 新增 `app/queue/`：Redis 队列适配与消费确认。
4. 保留 `app/store.py` 作为兼容门面，逐步迁移调用方。

## 4. 关键设计

### 4.1 Repository 抽象

每个聚合提供：

1. `create/get/list/update`
2. 幂等 `run_idempotent`
3. 审计 `append_audit`

要求：

1. 所有仓储方法必须显式接收 `tenant_id`。
2. 所有写事务必须返回可审计 `trace_id`。

### 4.2 事务与一致性

1. 单请求内使用单事务提交业务状态与 outbox。
2. outbox 消费失败仅重试投递，不回滚业务主事务。
3. `dlq_pending -> dlq_recorded -> failed` 必须在同一事务窗口内保证顺序可见。

### 4.3 队列语义

1. 入队消息最小字段：`job_id, tenant_id, trace_id, job_type, attempt`。
2. 消费成功后 ack；失败按重试策略回投。
3. 超重试进入 DLQ 并写审计。

## 5. 数据迁移策略

## 5.1 迁移顺序

1. 建表与索引。
2. 下发 RLS 策略。
3. 先双写（InMemory + DB）验证。
4. 切读到 DB。
5. 关闭 InMemory 写路径。

### 5.2 回滚策略

1. 保留上个稳定 schema 标签。
2. 任一校验失败立即切回 InMemory 读路径并冻结写流量。
3. 回滚脚本需与迁移脚本同 PR 交付。

## 6. 配置项

1. `POSTGRES_DSN`
2. `REDIS_DSN`
3. `QUEUE_NAME_JOB`
4. `IDEMPOTENCY_TTL_HOURS`
5. `OUTBOX_POLL_INTERVAL_MS`
6. `BEA_STORE_BACKEND`
7. `BEA_STORE_SQLITE_PATH`
8. `BEA_QUEUE_BACKEND`

## 7. 测试要求

1. Repository 单元测试：CRUD、幂等冲突、租户隔离。
2. 队列集成测试：重试、DLQ、顺序。
3. 迁移测试：升级/回滚脚本可执行。
4. 回放测试：Gate C-D 关键流程在真存储下通过。

## 8. 验收标准

1. 关键状态不再依赖进程内内存。
2. 重启进程后 `jobs/checkpoints` 可恢复。
3. 租户越权在仓储层与 DB RLS 双重阻断。

## 9. 关联文档

1. `docs/design/2026-02-21-data-model-and-storage-spec.md`
2. `docs/design/2026-02-21-job-system-and-retry-spec.md`
3. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`

## 10. 当前实现增量（r1）

1. 新增 Store 后端工厂：`BEA_STORE_BACKEND=memory|sqlite`。
2. 新增本地持久化后端：`SqliteBackedStore`（用于开发与回归阶段持久化验证）。
3. 新增 outbox 事件能力：`append/list/mark_published`，并接入关键 `job.created` 事件写入。
4. 新增队列抽象：`InMemoryQueueBackend`，包含 tenant 前缀、ack/nack、重试回投语义。
5. 新增回归测试：
   - `tests/test_store_persistence_backend.py`
   - `tests/test_outbox_events.py`
   - `tests/test_queue_backend.py`
