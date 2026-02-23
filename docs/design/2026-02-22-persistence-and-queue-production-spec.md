# 存储与队列生产化规范

> 版本：v2026.02.22-r16  
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
5. 对象存储 WORM：原始文档与报告归档、legal hold 与 cleanup 行为。

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

1. 会话变量：`SELECT set_config('app.current_tenant', :tenant_id, true)`。
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

### 5.6 P1-S6：对象存储 WORM

输入：对象存储规范与现有 upload/report 流程。  
产出：对象存储适配层 + legal hold/cleanup 联动。  
验收：上传与报告归档能在对象存储中追溯，legal hold 阻断删除。

最小交付：

1. 对象存储抽象与 `local/s3` 最小实现。
2. 原始文档写入对象存储并记录 `storage_uri`。
3. 评估报告写入对象存储并记录 `report_uri`。
4. `legal-hold` 与 `storage/cleanup` 对象存储联动。

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
11. `POSTGRES_APPLY_RLS`
12. `BEA_REQUIRE_TRUESTACK`
13. `BEA_OBJECT_STORAGE_BACKEND`
14. `OBJECT_STORAGE_BUCKET`
15. `OBJECT_STORAGE_ROOT`
16. `OBJECT_STORAGE_PREFIX`
17. `OBJECT_STORAGE_WORM_MODE`
18. `OBJECT_STORAGE_ENDPOINT`
19. `OBJECT_STORAGE_REGION`
20. `OBJECT_STORAGE_ACCESS_KEY`
21. `OBJECT_STORAGE_SECRET_KEY`
22. `OBJECT_STORAGE_FORCE_PATH_STYLE`

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

1. [x] repository 真实现可用。
2. [x] RLS 生效并有越权回归。
3. [x] Redis queue 路径通过并发回归。
4. [x] outbox relay 幂等验证通过。
5. [x] 回退脚本与演练记录完成。

## 13. 本轮实现更新（r2+）

1. 新增 `PostgresBackedStore`，支持 `BEA_STORE_BACKEND=postgres`。
2. `create_store_from_env` 新增 `POSTGRES_DSN` 校验与 `BEA_STORE_POSTGRES_TABLE` 配置。
3. 新增工厂回归：`tests/test_store_persistence_backend.py` 覆盖 postgres 分支（fake driver）。
4. 新增 `app/db/postgres.py` 事务执行器 `PostgresTxRunner`，统一 `set_config('app.current_tenant', ..., true)` 注入。
5. 新增 `RedisQueueBackend`，支持 `BEA_QUEUE_BACKEND=redis` 与 tenant 前缀 key 语义。
6. 新增回归：`tests/test_queue_backend.py` 覆盖 redis 工厂与 `enqueue/dequeue/nack/ack` 生命周期（fake driver）。
7. 新增仓储层起步实现：`app/repositories/jobs.py`（InMemory + Postgres jobs repository）与回归 `tests/test_jobs_repository.py`。
8. `InMemoryStore` 的 job 创建路径已改为通过 `InMemoryJobsRepository` 写入，降低后续切换成本。
9. `PostgresBackedStore` 已同步写入 `jobs` 表，并在 `get_job_for_tenant` 优先走 `PostgresJobsRepository`。
10. 新增 `documents/chunks` 仓储层：`app/repositories/documents.py`（InMemory + Postgres）。
11. `PostgresBackedStore` 增加 `documents/document_chunks` 表，并同步写入文档与 chunk 数据。
12. 新增 `parse_manifests` 仓储层：`app/repositories/parse_manifests.py`（InMemory + Postgres）。
13. `run_job_once` 的 parse 状态流转（running/retrying/failed/succeeded）统一通过仓储落库，避免仅内存修改。
14. `PostgresBackedStore` 增加 `parse_manifests` 表，并在查询 manifest 时优先走 PostgreSQL 仓储。
15. 新增 `workflow_checkpoints/dlq_items/audit_logs` 仓储层（InMemory + Postgres），并补齐对应单测。
16. `InMemoryStore` 将 checkpoint、DLQ、audit 写入统一收敛到仓储 helper，避免直接修改内存结构导致的持久化偏差。
17. `PostgresBackedStore` 增加 `workflow_checkpoints/dlq_items/audit_logs` 表，并将上述三类读写优先走 PostgreSQL 仓储。
18. 新增仓储同步回归：当 repository 返回副本对象时，`append_workflow_checkpoint` 与 `requeue_dlq_item` 仍可正确持久化状态。
19. outbox relay 增加消费幂等键实现：`event_id + consumer_name`，并在队列消息中携带 `consumer_name`。
20. `store_state` 快照新增 `outbox_delivery_records`，覆盖 memory/sqlite/postgres 三种后端状态恢复。
21. 新增 `app/db/rls.py`（`PostgresRlsManager`），支持核心表 RLS policy 批量下发（`ENABLE/FORCE RLS + tenant policy`）。
22. `create_store_from_env` 支持 `POSTGRES_APPLY_RLS=true` 自动下发策略，并有工厂回归测试覆盖。
23. 新增回退脚本 `scripts/rollback_to_sqlite.py`，可将 `.env` 后端开关一键切回 `sqlite`。
24. 新增命令级回退手册 `docs/ops/2026-02-22-backend-rollback-runbook.md`，包含切换、重启、验证与证据模板。
25. 新增 RLS 下发脚本 `scripts/apply_postgres_rls.py`，支持 `--dsn/--tables` 批量执行策略。
26. 新增 `evaluation_reports` 仓储层（InMemory + Postgres），并将创建/恢复路径改为仓储落库。
27. `PostgresBackedStore` 增加 `evaluation_reports` 表，并在读取评估报告时优先走 PostgreSQL 仓储。
28. 新增双写一致性比对能力：`app/ops/backend_consistency.py` + `scripts/compare_store_backends.py`。
29. 新增一致性比对 Runbook：`docs/ops/2026-02-22-backend-consistency-runbook.md`（命令级 + 证据模板）。
30. 修复真实 PostgreSQL 事务上下文注入语句兼容性：`SET LOCAL ... = %s` 改为 `SELECT set_config(..., true)`，避免参数化语法错误。
31. 修复 Postgres job 状态持久化缺口：`jobs` 仓储新增 upsert，`transition_job_status/run_job_once` 在状态与错误字段变更后立即落库。
32. 新增真栈强约束开关：`BEA_REQUIRE_TRUESTACK=true` 时，`BEA_STORE_BACKEND` 只能为 `postgres`，`BEA_QUEUE_BACKEND` 只能为 `redis`，并且 queue 初始化失败不再静默回退到 memory。
