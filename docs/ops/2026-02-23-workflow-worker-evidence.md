# Workflow & Worker 生产化证据（P3）

> 日期：2026-02-23  
> 分支：`codex/p3-workflow-worker`

## 1. 覆盖范围

1. Worker 常驻运行时（轮询消费）能力。
2. 重试指数退避 + 延迟重投能力。
3. HITL token TTL 配置化能力。
4. checkpoint backend 与 worker 运行参数观测字段。
5. 多租户轮询公平性（防单租户挤占）。

## 2. 关键变更

1. 新增 `app/worker_runtime.py`。
2. 新增 `scripts/run_worker.py`。
3. 队列后端新增 `available_at` 与 `nack(delay_ms)`：
   - `app/queue_backend.py`
4. `store` 新增 worker/retry/token TTL 配置项并用于重试逻辑：
   - `app/store.py`
5. worker drain 路径接入 `delay_ms`：
   - `app/main.py`
6. 新增 LangGraph runtime 入口与兼容执行路径：
   - `app/store.py`
   - `pyproject.toml`

## 3. 验证命令与结果

```bash
pytest -q tests/test_queue_backend.py tests/test_worker_drain_api.py tests/test_worker_runtime.py
```

结果：`18 passed`

```bash
pytest -q tests/test_internal_job_run.py tests/test_workflow_checkpoints.py tests/test_resume_and_citation.py tests/test_internal_outbox_queue_api.py tests/test_store_persistence_backend.py tests/test_queue_backend.py tests/test_worker_drain_api.py tests/test_worker_runtime.py
```

结果：`53 passed`

```bash
pytest -q
```

结果：`全部通过`

## 4. 结论

1. P3-S1：已具备常驻 worker 运行时与脚本入口。
2. P3-S2：checkpoint 持久化仍通过 repository 后端（含 postgres/sqlite 路径）读取恢复。
3. P3-S3：resume token 单次消费 + TTL + 审计链路保持有效。
4. P3-S4：重试路径已使用指数退避并在队列层执行延迟重投。
5. P3-S5：worker 轮询采用 tenant burst 限制，已通过公平消费单测。
6. LangGraph runtime 与兼容执行路径具备回归证据；真栈可通过依赖启用 LangGraph。
