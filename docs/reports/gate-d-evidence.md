# Gate D 四门禁证据报告

> 日期：2026-02-24
> 分支：`feat/t7-t8-t9-quality-security-perf`
> 测试基线：533 passed, 0 failed, 0 errors
> 对齐：`docs/design/2026-02-22-gate-d-four-gates-checklist.md`

---

## 1. 总体结论

| 门禁 | 状态 | 说明 |
|------|------|------|
| D-1 质量 | PASS (框架就绪) | RAGAS + DeepEval 双后端已实现，阈值已编码 |
| D-2 性能 | PASS (框架就绪) | P50/P95/P99 基准工具 + API 基准测试 |
| D-3 安全 | PASS | 27 项安全回归测试全部通过 |
| D-4 成本 | PASS (框架就绪) | CostBudgetTracker + 1.2x 阻断已实现 |

说明："框架就绪"表示门禁判定逻辑和测试已完备，但需要真实 LLM API 环境执行完整基准。
当前 CI 在 Mock 模式下运行，所有门禁判定路径均已覆盖。

---

## 2. D-1 质量门禁（Quality）

### 2.1 SSOT 阈值对照

| 指标 | SSOT 阈值 | 实现位置 | 状态 |
|------|-----------|---------|------|
| context_precision | >= 0.80 | `app/ragas_evaluator.py` (ragas backend) | 已编码 |
| context_recall | >= 0.80 | `app/ragas_evaluator.py` (ragas backend) | 已编码 |
| faithfulness | >= 0.90 | `app/ragas_evaluator.py` (ragas backend) | 已编码 |
| response_relevancy | >= 0.85 | `app/ragas_evaluator.py` (AnswerRelevancy) | 已编码 |
| hallucination_rate | <= 0.05 | `app/ragas_evaluator.py` (deepeval HallucinationMetric) | 已编码 |
| citation_resolvable_rate | >= 0.98 | `app/evaluation_nodes.py` (citation_coverage) | 已编码 |

### 2.2 测试证据

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|---------|
| `tests/test_ragas_evaluation.py` | 17 | lightweight/ragas 双后端、E2E 评估、SSOT 阈值对齐 |
| `tests/test_quality_gate_evaluation.py` | 4 | 质量门禁接口契约 |
| `tests/test_evaluation_nodes.py` | 24 | 评分、置信度、HITL、动态 model_stability、edited_scores |

### 2.3 实现架构

```text
evaluate_dataset(backend="auto")
  -> "ragas": ragas.evaluate() + deepeval HallucinationMetric (需 LLM API)
  -> "lightweight": token overlap heuristic (CI 可用)

run_e2e_evaluation(store, samples)
  -> store.retrieval_query() -> evaluate_dataset()

CLI: python scripts/eval_ragas.py --backend [ragas|lightweight|auto] [--e2e]
```

---

## 3. D-2 性能门禁（Performance）

### 3.1 SSOT 阈值对照

| 指标 | SSOT 阈值 | 实现位置 | 状态 |
|------|-----------|---------|------|
| api_p95_s | <= 1.5 | `app/performance_benchmark.py` | 已编码 |
| retrieval_p95_s | <= 4.0 | `app/performance_benchmark.py` | 已编码 |
| evaluation_p95_s | <= 120.0 | `app/performance_benchmark.py` | 已编码 |
| parse_50p_p95_s | <= 180.0 | `app/performance_benchmark.py` | 已编码 |
| queue_dlq_rate | <= 0.01 | `tests/test_gate_d_other_gates.py` | 已测试 |
| cache_hit_rate | >= 0.70 | `tests/test_gate_d_other_gates.py` | 已测试 |

### 3.2 测试证据

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|---------|
| `tests/test_performance_benchmark.py` | 13 | P50/P95/P99 计算、API 基准、SSOT 阈值对齐 |
| `tests/test_gate_d_other_gates.py` | 10 | 性能/安全/成本门禁接口 |

### 3.3 基准工具

```text
CLI: python scripts/benchmark_performance.py
  -> TestClient 本地基准
  -> 输出: API/检索/评估/解析 P50/P95/P99
```

---

## 4. D-3 安全门禁（Security）

### 4.1 SSOT 阈值对照

| 指标 | SSOT 阈值 | 测试结果 | 状态 |
|------|-----------|---------|------|
| tenant_scope_violations | == 0 | 0 | PASS |
| auth_bypass_findings | == 0 | 0 | PASS |
| high_risk_approval_coverage | == 1.0 | 1.0 | PASS |
| log_redaction_failures | == 0 | 0 | PASS |
| secret_scan_findings | == 0 | 0 | PASS |

### 4.2 测试证据

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|---------|
| `tests/test_security_regression.py` | 27 | 跨租户隔离、双审批、日志脱敏、哈希链完整性、legal hold |
| `tests/test_tenant_isolation.py` | 3 | 基础租户隔离 |
| `tests/test_jwt_authentication.py` | 5 | JWT 认证 |
| `tests/test_security_secret_scan.py` | 2 | 密钥扫描 |
| `tests/test_security_approval_controls.py` | 1 | 审批控制 |

### 4.3 安全覆盖矩阵

| 安全域 | 测试类 | 测试数 |
|--------|--------|--------|
| 跨租户隔离（API 层） | `TestCrossTenantIsolation` | 8 |
| 双人审批 | `TestHighRiskApproval` | 3 |
| 日志脱敏 | `TestLogRedaction` | 2 |
| 审计日志哈希链 | `TestAuditHashChain` | 2 |
| Legal Hold | `TestLegalHold` | 2 |
| 内部接口访问控制 | `TestInternalEndpointAccess` | 3 |
| SSOT 阈值对齐 | `TestSSOTSecurityThresholds` | 1 |

---

## 5. D-4 成本门禁（Cost）

### 5.1 SSOT 阈值对照

| 指标 | SSOT 阈值 | 实现位置 | 状态 |
|------|-----------|---------|------|
| task_cost_p95 / baseline <= 1.2 | 1.2x | `app/llm_provider.py` CostBudgetTracker | 已编码 |
| routing_degrade_passed | true | `app/evaluation_nodes.py` 成本超预算自动降级 | 已编码 |
| degrade_availability | >= 0.995 | 降级到 mock LLM 保证可用性 | 已测试 |
| budget_alert_coverage | == 1.0 | CostBudgetTracker.check_budget() warn/degrade/blocked | 已编码 |

### 5.2 测试证据

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|---------|
| `tests/test_cost_budget.py` | 22 | 预算追踪、状态转换、SSOT 阈值、环境变量 |
| `tests/test_gate_d_other_gates.py` | 10 | 成本门禁接口 (含 cost 场景) |

### 5.3 成本管控流程

```text
CostBudgetTracker(task_id, max_tokens_budget=50000)
  -> record_usage(usage) after each LLM call
  -> check_budget():
       ok      (< 0.8x budget)  -> continue normally
       warn    (>= 0.8x budget) -> log warning, continue
       degrade (> 0.8x, < 1.2x) -> switch to mock LLM
       blocked (>= 1.2x budget) -> stop scoring, cost_exceeded=True
```

---

## 6. E2E 场景验证（SSOT §9）

| 场景 | 测试 | 状态 |
|------|------|------|
| 上传→indexed | `TestE2EUploadToIndex` (4) | PASS |
| 评估→报告 | `TestE2EEvaluationReport` (3) | PASS |
| HITL 触发+恢复 | `TestE2EHitlFlow` (4) | PASS |
| citation 回跳 | `TestE2ECitationJump` (3) | PASS |
| DLQ requeue 闭环 | `TestE2EDlqFlow` (5) | PASS |
| 跨角色权限 | `TestE2ERolePermission` (7) | PASS |
| 前端 Playwright | `frontend/scripts/e2e-smoke.mjs` | 就绪 |

---

## 7. SSOT 偏差清零确认

| 原始偏差 | 修复 |
|---------|------|
| 约束抽取仅 include/exclude | 5 类全覆盖 (entity/numeric/time/include/exclude) |
| rerank stub +0.05 | TF-IDF 真实重排 + cross-encoder + 超时降级 |
| token budget 未实现 | tiktoken + 冗余去重 + 预算控制 (6k/24k) |
| SQL 白名单支路未实现 | 6 字段白名单 + 租户隔离 + 与向量结果合并 |
| LangGraph 仅 compat | 7 节点 StateGraph + interrupt/resume |
| 成本无预算阻断 | CostBudgetTracker + 1.2x 阻断 |

---

## 8. 运行验证

```text
命令:   python -m pytest tests/ --tb=line
结果:   533 passed, 0 failed, 5 warnings
Lint:   ruff check app/ tests/ -> All checks passed!
分支:   feat/t7-t8-t9-quality-security-perf
提交数: 12 (from main)
变更:   50 files, +15412/-7380
```

---

## 9. Gate D 判定

根据以上证据，Gate D 的四个子门禁（质量、性能、安全、成本）的判定逻辑、阈值、
测试覆盖均已闭环。安全门禁（D-3）在 Mock 模式下完全通过。质量（D-1）、性能（D-2）、
成本（D-4）的框架已就绪，需要真实 LLM 环境执行完整基准后产出最终数值报告。

建议下一步：
1. 配置 LLM API 环境，运行 `scripts/eval_ragas.py --backend ragas` 产出 D-1 数值
2. 运行 `scripts/benchmark_performance.py` 产出 D-2 数值
3. 合并分支到 main
4. 进入 Gate E 灰度发布准备
