# 工作流与 Worker 生产化规范

> 版本：v2026.02.23-r5  
> 状态：Active  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 文档目标

1. 将工作流执行从进程内模拟升级为真实 Worker 执行模型。
2. 落实 LangGraph checkpoint 持久化恢复与 HITL 中断恢复一致性。
3. 保障重试、DLQ、审计链路在并发下稳定可回放。

## 2. 范围与非目标

### 2.1 纳入范围

1. API 受理与 Worker 执行解耦。
2. `thread_id` 生命周期与 checkpoint 恢复。
3. HITL interrupt/resume token 约束。
4. Worker 并发、重试、DLQ 路由。

### 2.2 非目标

1. 多区域 Worker 调度。
2. 动态工作流 DSL 编排平台。

## 3. 当前基线（已完成）

1. `thread_id` 已在 job 中生成并复用。
2. checkpoint 查询接口已提供。
3. `drain-once` Worker 调试接口已提供并有回归。

## 4. 目标运行模型

```text
API: validate + enqueue job -> return 202/job_id
Worker: dequeue -> run workflow node chain -> persist checkpoint/events
Failure: retry (<=3) -> DLQ pipeline -> final failed
HITL: interrupt -> wait resume_token -> resume -> finalize
```

约束：

1. API 线程不执行长任务。
2. interrupt payload 必须 JSON 可序列化。
3. resume 仅允许单次消费且绑定 `tenant_id + evaluation_id`。

## 5. 实施任务（执行顺序）

### 5.1 P3-S1：Worker 进程化

输入：当前内部 `drain-once` 能力。  
产出：常驻 Worker（解析队列/评估队列）。  
验收：API 高并发下仅受理，不阻塞业务线程。

### 5.2 P3-S2：LangGraph checkpointer 真实后端

输入：S1。  
产出：真实持久化 checkpoint（PostgreSQL）。  
验收：进程重启后可从最近 checkpoint 恢复。

### 5.3 P3-S3：HITL 一致性收口

输入：S2。  
产出：interrupt/resume 审计与状态一致。  
验收：24h 内恢复成功率达到目标且审计闭环。

最小交付：

1. `resume_token` TTL 与单次消费约束。
2. `resume_submitted` 审计事件强制写入。
3. 非法 resume 返回稳定错误码。

### 5.4 P3-S4：重试与 DLQ 时序

输入：S3。  
产出：重试指数退避与 DLQ 顺序保证。  
验收：`dlq_pending -> dlq_recorded -> failed` 时序在回放中稳定。

### 5.5 P3-S5：并发与配额

输入：S4。  
产出：租户并发配额、队列隔离。  
验收：单租户突发流量不压垮全局队列。

## 6. 契约与数据约束

1. 任务状态机定义保持不变。
2. `job_id/thread_id/evaluation_id/resume_token` 语义不可变。
3. 新增内部字段仅允许追加，不允许语义漂移。

## 7. 配置清单

1. `WORKER_CONCURRENCY_PARSE`
2. `WORKER_CONCURRENCY_EVAL`
3. `WORKER_MAX_RETRIES`
4. `WORKER_RETRY_BACKOFF_BASE_MS`
5. `RESUME_TOKEN_TTL_HOURS`
6. `WORKFLOW_CHECKPOINT_BACKEND`
7. `WORKFLOW_RUNTIME`（`langgraph|compat`）

## 8. 测试与验证命令

1. workflow 单测：节点流转、非法流转阻断。
2. Worker 集成：消费、重试、DLQ、恢复。
3. 回放：HITL 中断恢复链路与审计链路。

建议命令：

```bash
pytest -q tests/test_workflow_checkpoints.py
pytest -q tests/test_worker_drain_api.py tests/test_internal_job_run.py
pytest -q
```

## 9. 验收证据模板

1. 重启恢复证明（重启前后 thread_id/checkpoint 一致）。
2. HITL 恢复成功率与失败原因统计。
3. 重试/DLQ 时序回放日志。
4. 并发压测结果（延迟、失败率、队列积压）。

## 10. 退出条件（P3 完成定义）

1. API 与 Worker 职责彻底解耦。
2. checkpoint 可持久化恢复。
3. HITL 中断恢复与审计完整。
4. 重试与 DLQ 时序可稳定复现。

## 11. 风险与回退

1. 风险：Worker 并发配置错误导致重复执行。
2. 风险：checkpoint 持久化瓶颈导致吞吐下降。
3. 回退：降并发 + 临时强制 HITL + 仅保留关键任务入队。

## 12. 实施检查清单

1. [x] Worker 常驻进程可用。
2. [x] checkpointer 真实后端可恢复。
3. [x] HITL token/审计一致性通过。
4. [x] 重试与 DLQ 时序通过。
5. [x] 并发配额压测通过。

## 13. 实施更新（2026-02-23）

1. 新增常驻 Worker 运行时：`app/worker_runtime.py` + `scripts/run_worker.py`，支持按队列持续轮询执行。
2. 队列层新增延迟可见能力（available_at）与 `nack(delay_ms)`，用于指数退避重试。
3. `run_job_once` 接入配置化重试参数：`WORKER_MAX_RETRIES`、`WORKER_RETRY_BACKOFF_BASE_MS`、`WORKER_RETRY_BACKOFF_MAX_MS`。
4. HITL token TTL 接入 `RESUME_TOKEN_TTL_HOURS` 配置，保持单次消费与租户绑定约束。
5. Worker 调度引入按 tenant 轮询与 `tenant_burst_limit`，避免单租户突发独占消费窗口。
6. 新增 `WORKFLOW_RUNTIME`，默认启用 LangGraph runtime；当依赖缺失且非真栈环境时降级为兼容执行路径。
