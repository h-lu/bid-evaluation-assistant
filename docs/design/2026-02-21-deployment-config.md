# 部署配置设计

> 版本：v3.0
> 日期：2026-02-21
> 架构基线：`docs/plans/2026-02-21-end-to-end-unified-design.md`

---

## 1. 部署拓扑（MVP）

```text
Nginx (TLS)
  -> Frontend (Vue3)
  -> FastAPI API
  -> Worker

Data:
  PostgreSQL / Redis / Chroma / LightRAG
```

关键约束：

- API 不阻塞长任务。
- Worker 统一处理 parse/index/evaluate/report。
- 任务执行必须校验 `tenant_id`。

---

## 2. 环境分层

- `dev`：本地容器，最小可运行集。
- `staging`：同生产拓扑，做发布前验证。
- `prod`：API/Worker 多副本，托管数据服务。

---

## 3. 自动扩缩容

机制：Kubernetes HPA + KEDA（Redis 队列）。

触发条件（预警）：

1. API CPU > 70% 持续 15 分钟。
2. 队列积压 > 200 持续 10 分钟。
3. 检索 P95 > 2.5s 持续 15 分钟。
4. Worker 失败率 > 2% 持续 10 分钟。

违约判定（SLO breach）：

- 检索 P95 > 4.0s 持续 5 分钟。

执行策略：

- API/Worker 副本范围：`min=2`，`max=10`
- 扩容冷却：5 分钟
- 缩容冷却：15 分钟
- 扩缩容事件入审计并告警

---

## 4. 可观测性（生产必选）

- Trace：全链路追踪（API/Worker/Workflow）
- Metrics：延迟、错误率、队列积压、成本
- Logs：结构化日志 + `trace_id`

---

## 5. 备份与容灾

目标：

- RPO <= 15 分钟
- RTO <= 60 分钟

策略：

1. PostgreSQL 每日全量 + 持续增量。
2. 索引定期快照。
3. 审计/报告进入 WORM（锁定 5 年）。
4. `legal_hold` 对象禁止删除/覆盖，直至解除。
5. 每月恢复演练。

---

## 6. 发布要求

1. 质量门禁通过（RAGAS + DeepEval + E2E）。
2. 回滚脚本演练通过。
3. 容灾演练通过。
4. DLQ 运营流程演练通过。
5. 成本门禁与降级策略演练通过。
