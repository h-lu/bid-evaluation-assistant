# 工作流与 Worker 生产化规范

> 版本：v2026.02.22-r3  
> 状态：Draft  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 让工作流执行脱离进程内模拟，改为真实 LangGraph + Worker 执行。
2. 确保 checkpoint 持久化、interrupt/resume 可恢复、重试与 DLQ 时序稳定。
3. 保持既有状态机与审计语义不变。

## 2. 工作流运行模型

1. API 层只受理请求并创建 `job_id`。
2. Worker 消费队列并驱动 LangGraph 执行。
3. checkpointer 持久化到 PostgreSQL。
4. 恢复通过 `thread_id` 定位最新 checkpoint。

## 3. 节点与副作用边界

1. 纯计算节点：检索、规则、评分、门禁判断。
2. 副作用节点：报告入库、审计写入、DLQ 写入。
3. 副作用节点必须声明幂等键。

## 4. interrupt/resume

1. interrupt payload 必须 JSON 可序列化。
2. `resume_token` 单次有效并绑定 `tenant_id + evaluation_id`。
3. 恢复后流程只能前进到 finalize，不允许任意回跳。

## 5. 重试与 DLQ

1. 默认 3 次重试 + 指数退避。
2. 第 4 次失败进入 `dlq_pending -> dlq_recorded -> failed`。
3. `requeue/discard` 操作必须产生日志审计。

## 6. Worker 并发模型

1. 解析任务与评估任务分队列。
2. 租户并发配额限制避免抢占。
3. 高风险任务优先进入 HITL 路径。

## 7. 测试要求

1. Workflow 单测：节点路由、状态迁移、非法流转阻断。
2. Worker 集成测：队列消费、重试、DLQ、恢复。
3. 回放测：关键失败案例可复现。

## 8. 验收标准

1. 进程重启后工作流可从 checkpoint 恢复。
2. interrupt 后 24h 内恢复成功率达标。
3. DLQ 时序与审计链闭环。

## 9. 关联文档

1. `docs/design/2026-02-21-langgraph-agent-workflow-spec.md`
2. `docs/design/2026-02-21-job-system-and-retry-spec.md`
3. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`

## 10. 当前实现增量（r3）

1. 作业模型新增 `thread_id`，并在 resume 任务中复用同一 thread。
2. 新增 workflow checkpoint 事件落库（`job_started/retrying/failed/succeeded`）。
3. 新增内部查询接口：`GET /api/v1/internal/workflows/{thread_id}/checkpoints`。
4. `SqliteBackedStore` 快照已纳入 checkpoint 状态，支持重启后恢复查询。
5. 新增回归：
   - `tests/test_workflow_checkpoints.py`
   - `tests/test_store_persistence_backend.py`（checkpoint 持久化）
6. 新增 Worker 消费接口：`POST /api/v1/internal/worker/queues/{queue_name}/drain-once`。
7. 新增回归：`tests/test_worker_drain_api.py`（队列消费、作业执行、鉴权）。
