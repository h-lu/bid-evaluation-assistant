# 存储与队列回退 Runbook（sqlite）

> 版本：v2026.02.22-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-22-persistence-and-queue-production-spec.md`

## 1. 目的

1. 在 `postgres+redis` 出现持续异常时，30 分钟内切回 `sqlite` 后端。
2. 保留可审计的命令级执行证据。

## 2. 触发条件

1. 关键链路持续失败且超过告警阈值。
2. 任一门禁连续超阈值且无法在短时修复。
3. 值班负责人明确下达回退指令。

## 3. 回退步骤（命令级）

### 3.1 生成回退配置

```bash
python scripts/rollback_to_sqlite.py --env-file .env.local
```

说明：

1. 脚本会将 `.env.local` 中 `BEA_STORE_BACKEND`、`BEA_QUEUE_BACKEND` 统一改为 `sqlite`。
2. 可先用 `--dry-run` 预览。

### 3.2 重启服务

```bash
# 示例：按本地/环境实际启动命令执行
pkill -f "uvicorn app.main:create_app" || true
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

### 3.3 最小验证

```bash
pytest -q tests/test_store_persistence_backend.py
pytest -q tests/test_queue_backend.py
pytest -q tests/test_internal_outbox_queue_api.py tests/test_worker_drain_api.py
```

## 4. 证据记录模板

1. 回退开始时间：`YYYY-MM-DDTHH:MM:SSZ`
2. 回退完成时间：`YYYY-MM-DDTHH:MM:SSZ`
3. 执行人：`owner`
4. 命令输出摘要：
   - 配置切换结果
   - 服务重启结果
   - 验证测试结果

## 5. 回退后动作

1. 冻结高风险写操作（如必要）。
2. 在变更管理文档补充 `change_id` 与 `rollback_plan` 执行结果。
3. 24 小时内完成复盘并补充长期修复计划。
