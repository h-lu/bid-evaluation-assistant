# 部署配置设计

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 部署目标

1. 保障主链路生产可用。
2. 支持异步任务弹性扩缩容。
3. 支持全链路可观测与故障回滚。
4. 支持租户隔离与证据留存。

## 2. 生产拓扑（ASCII）

```text
                    +-------------------------+
Internet / Office -> | Nginx + TLS + WAF      |
                    +------------+------------+
                                 |
                 +---------------+----------------+
                 |                                |
                 v                                v
        +--------+--------+              +--------+--------+
        | Frontend        |              | FastAPI API      |
        +--------+--------+              +--------+--------+
                                                  |
                                                  v
                                           +------+------+
                                           | Redis Queue |
                                           +------+------+
                                                  |
                                                  v
                                           +------+------+
                                           | Worker Pool |
                                           +--+-------+--+
                                              |       |
                                              v       v
                                           Parser  Workflow
                                              \       /
                                               \     /
                                                v   v
                                  +-------------------------------+
                                  | PostgreSQL / Chroma / Redis   |
                                  | Object Storage (WORM)         |
                                  +-------------------------------+
```

## 3. 环境分层

1. `dev`：最小组件，本地联调。
2. `staging`：与 prod 同拓扑，用于预发回放。
3. `prod`：多副本 API/Worker，完整监控与告警。

原则：配置隔离、密钥隔离、数据隔离。

## 4. 服务配置基线

### 4.1 API

1. `API_WORKERS`
2. `REQUEST_TIMEOUT_MS`
3. `JWT_ISSUER/JWT_AUDIENCE`
4. `IDEMPOTENCY_TTL_HOURS=24`

### 4.2 Worker

1. `WORKER_CONCURRENCY`
2. `JOB_MAX_RETRY=3`
3. `JOB_BACKOFF_BASE_MS`
4. `DLQ_ENABLED=true`

### 4.3 Retrieval/Model

1. `LIGHTRAG_WORKDIR`
2. `RERANK_ENABLED`
3. `RERANK_TIMEOUT_MS`
4. `MODEL_ROUTER_PROFILE`

### 4.4 Storage

1. `POSTGRES_DSN`
2. `REDIS_DSN`
3. `CHROMA_PERSIST_DIR`
4. `OBJECT_STORAGE_BUCKET`
5. `WORM_RETENTION_DAYS`

## 5. 扩缩容策略

### 5.1 API

1. 按 CPU/延迟双指标扩容。
2. 目标：查询接口 P95 <= 1.5s。

### 5.2 Worker

1. 按队列积压与处理时延扩容。
2. 高峰期优先扩容解析队列与评估队列。

### 5.3 限流

1. 租户级速率限制。
2. 高风险写接口单独限流。

## 6. 可观测性与告警

### 6.1 必备指标

1. API QPS、错误率、P95。
2. 队列深度、重试率、DLQ 新增率。
3. 解析/检索/评估耗时分布。
4. 质量指标（幻觉率、citation 回跳率）。

### 6.2 必备日志字段

1. `trace_id`
2. `request_id`
3. `job_id`
4. `tenant_id`
5. `node_name`
6. `error_code`

### 6.3 告警策略

1. P0：越权风险、主链路不可用。
2. P1：DLQ 激增、幻觉率超阈值。
3. P2：性能退化与成本异常。

## 7. 安全与配置治理

1. 密钥通过安全配置中心注入。
2. 生产配置不可硬编码在仓库。
3. 发布前执行配置差异检查。
4. 审计日志与报告归档进入受控存储。

## 8. 发布流水线（Gate 驱动）

```text
build
 -> unit/integration/e2e
 -> offline eval (RAGAS/DeepEval)
 -> perf/security checks
 -> staging replay
 -> canary release
 -> full release
```

## 9. 回滚策略

1. 触发条件：任一门禁连续超阈值。
2. 回滚级别：
   - L1 参数回滚（检索/模型）
   - L2 工作流版本回滚
   - L3 应用版本回滚
3. 回滚后强制执行回放验证。

## 10. 灾备与数据恢复

1. RPO <= 15min，RTO <= 60min。
2. 每日增量、每周全量备份。
3. 定期恢复演练（至少每月一次）。

## 11. 验收标准

1. staging 与 prod 配置差异可追踪。
2. 可观测指标完整，告警可触发。
3. 灰度与回滚流程可实测执行。

## 12. 参考来源（核验：2026-02-21）

1. FastAPI deployment docs: https://fastapi.tiangolo.com/deployment/
2. 历史融合提交：`beef3e9`, `7f05f7e`
