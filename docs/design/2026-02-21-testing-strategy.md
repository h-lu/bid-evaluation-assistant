# 测试策略

> 版本：v3.0
> 日期：2026-02-21
> 架构基线：`docs/plans/2026-02-21-end-to-end-unified-design.md`

---

## 1. 测试目标

- 保证 E2E 主流程稳定。
- 保证多租户隔离与审计链可靠。
- 保证性能、质量、成本门禁可执行。

---

## 2. 分层测试

1. 单元测试（约 70%）：领域规则、权限、契约转换。
2. 集成测试（约 20%）：数据库、检索、工作流、队列。
3. E2E 测试（约 10%）：上传 -> 解析 -> 检索 -> 评估 -> HITL -> 报告。

---

## 3. 质量门禁

- RAGAS
  - Context Precision >= 0.80
  - Context Recall >= 0.80
  - Faithfulness >= 0.90
  - Response Relevancy >= 0.85
- DeepEval：Hallucination Rate <= 5%
- E2E 关键链路通过率：100%
- 发布前 P0/P1：0

---

## 4. 性能与可靠性

1. 普通 API：P95 <= 1.5s
2. 检索查询：P95 <= 4.0s
3. 50 页解析：P95 <= 180s
4. 单供应商评估：P95 <= 120s
5. 队列积压压测 + 自动扩缩容验证
6. 预警阈值（2.5s）与违约阈值（4.0s）分层告警验证

---

## 5. 安全与合规场景

1. 跨租户越权访问拦截（API/检索/缓存/任务）。
2. `job.tenant_id` 篡改防护与执行期二次校验。
3. `legal_hold` 与 WORM 存储策略验证。
4. 审计字段完整性校验（`who/when/what/why/trace_id`）。
5. `DLQ discard` 高风险操作复核链验证。

---

## 6. 任务与 DLQ 场景

1. 任务重试与退避策略验证。
2. 重试超限进入 DLQ，再标记 `failed`。
3. DLQ `requeue/discard` 权限边界验证。
4. HITL 中断、人工恢复、继续执行闭环验证。

---

## 7. 幂等与成本场景

1. 同 `Idempotency-Key` + 同请求体返回同 `job_id`。
2. 同 `Idempotency-Key` + 异请求体返回 `409 IDEMPOTENCY_CONFLICT`。
3. 月度成本偏差门禁验证（<= 15%）。
4. 连续 3 天超预算触发降级策略验证。

---

## 8. CI/CD 流水线建议

1. `lint + unit`
2. `integration`
3. `e2e`
4. `evaluation gate (RAGAS/DeepEval)`
5. `performance smoke`
6. `security scan`

任一阻断项失败即停止发布。
