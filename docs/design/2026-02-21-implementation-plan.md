# 详细实施计划

> 版本：v3.0
> 日期：2026-02-21
> 架构基线：`docs/plans/2026-02-21-end-to-end-unified-design.md`

---

## 1. 目标

8 周内交付可上线 MVP，完成可审计、可恢复、可扩展的评标端到端闭环。

---

## 2. 阶段计划

### Phase 1（Week 1-2）：基础能力

交付：

- 模块化单体骨架。
- 认证与 RBAC。
- 多租户隔离基线（`tenant_id` + RLS）。
- 项目/供应商主数据。

验收：

- 关键资源 CRUD 可用。
- 跨租户访问被拦截。
- `GET /api/v1/health` 正常。

### Phase 2（Week 3-4）：解析与检索

交付：

- MinerU/Docling 解析链路。
- LightRAG + Chroma 索引链路。
- 异步队列与 Worker（parse/index）。

验收：

- 长任务统一 `202 + job_id`。
- 状态机闭环可追踪。
- 重试超限：DLQ -> `failed`。
- 幂等冲突可判定（`409 IDEMPOTENCY_CONFLICT`）。

### Phase 3（Week 5-6）：评估与 HITL

交付：

- LangGraph 评估流程。
- HITL 中断/恢复。
- 报告与证据链。

验收：

- HITL 规则命中可中断。
- 人工处理后可恢复。
- 结果契约字段完整（`answer/citations/confidence/mode_used/trace_id`）。

### Phase 4（Week 7-8）：发布与运维

交付：

- RAGAS/DeepEval 门禁。
- 性能压测。
- HPA/KEDA 自动扩缩容。
- 容灾演练与回滚演练。

验收：

- 达到 SLO。
- RPO/RTO 演练通过。
- 成本门禁触发与降级策略验证通过。

---

## 3. 关键里程碑

1. Week 2：租户隔离 + 主数据上线。
2. Week 4：解析与检索可用。
3. Week 6：评估与 HITL 可用。
4. Week 8：门禁全通过并具备发布条件。

---

## 4. 发布准入（DoD）

1. 质量门禁全部通过。
2. 性能 SLO 达标。
3. 安全门禁通过（RLS、审计、WORM、`legal_hold`）。
4. DLQ 运营接口可用且审计闭环。
5. 成本门禁达标或降级策略生效。

---

## 5. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 解析质量波动 | 评估准确性下降 | 解析回归集 + OCR 兜底 |
| 人工复核积压 | 流程阻塞 | SLA 升级 + 任务看板 |
| 成本超预算 | 运营压力 | 预算门禁 + 自动降级 |
| 多租户越界 | 合规风险 | RLS + 契约测试 + 渗透测试 |
