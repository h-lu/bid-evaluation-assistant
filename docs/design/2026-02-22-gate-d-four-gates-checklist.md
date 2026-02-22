# Gate D 四门禁验收清单

> 版本：v2026.02.22-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-21-implementation-plan.md`

## 1. 目标

1. 为 Gate D（D-1~D-4）提供统一、可复核的运行证据。
2. 将质量/性能/安全/成本门禁阈值与接口契约绑定。
3. 明确“通过/阻断”判定标准与失败码。

## 2. D-1 质量门禁（Quality）

接口：`POST /api/v1/internal/quality-gates/evaluate`

阈值：

1. `context_precision >= 0.80`
2. `context_recall >= 0.80`
3. `faithfulness >= 0.90`
4. `response_relevancy >= 0.85`
5. `hallucination_rate <= 0.05`
6. `citation_resolvable_rate >= 0.98`

阻断行为：

1. 任一阈值不达标时 `passed=false`
2. 触发 `ragchecker.triggered=true`

证据测试：`tests/test_quality_gate_evaluation.py`

## 3. D-2 性能门禁（Performance）

接口：`POST /api/v1/internal/performance-gates/evaluate`

阈值：

1. `api_p95_s <= 1.5`
2. `retrieval_p95_s <= 4.0`
3. `parse_50p_p95_s <= 180.0`
4. `evaluation_p95_s <= 120.0`
5. `queue_dlq_rate <= 0.01`
6. `cache_hit_rate >= 0.70`

阻断行为：

1. 任一指标越界时 `passed=false`
2. 返回失败码（如 `API_P95_EXCEEDED`）

证据测试：`tests/test_gate_d_other_gates.py`（performance 场景）

## 4. D-3 安全门禁（Security）

接口：`POST /api/v1/internal/security-gates/evaluate`

阈值：

1. `tenant_scope_violations == 0`
2. `auth_bypass_findings == 0`
3. `high_risk_approval_coverage == 1.0`
4. `log_redaction_failures == 0`
5. `secret_scan_findings == 0`

阻断行为：

1. 任一阻断项失败时 `passed=false`
2. 返回失败码（如 `TENANT_SCOPE_VIOLATION_FOUND`）

证据测试：`tests/test_gate_d_other_gates.py`（security 场景）

## 5. D-4 成本门禁（Cost）

接口：`POST /api/v1/internal/cost-gates/evaluate`

阈值：

1. `task_cost_p95 / baseline_task_cost_p95 <= 1.2`
2. `routing_degrade_passed == true`
3. `degrade_availability >= 0.995`
4. `budget_alert_coverage == 1.0`

阻断行为：

1. 任一条件不满足时 `passed=false`
2. 返回失败码（如 `TASK_COST_P95_RATIO_HIGH`）

证据测试：`tests/test_gate_d_other_gates.py`（cost 场景）

## 6. 内部接口约束

1. 四个门禁接口均要求 `x-internal-debug: true`
2. 未携带内部标识统一返回 `403 + AUTH_FORBIDDEN`
3. 请求体字段范围由 Pydantic schema 强校验

## 7. 运行验证证据

1. 运行命令：`pytest -v`
2. 结果：`92 passed`
3. OpenAPI 校验：`openapi=3.1.0` 且四个 Gate D 接口路径存在
4. 文档检查：无占位残留关键字
5. 文档引用检查：`DOC_REFS_OK`

## 8. 结论

1. Gate D 四门禁接口契约、阈值判定与阻断逻辑已闭环。
2. Gate D 的“门禁执行能力”在本分支已具备运行与回归证据。

## 9. Gate C 补充收口

1. `resume_token` 增加 24h 失效约束并完成回归验证。
2. `dlq requeue/discard` 成功路径增加审计日志落库并完成回归验证。
