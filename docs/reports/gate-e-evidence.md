# Gate E 灰度与回滚证据报告

> 日期：2026-02-24
> 分支：`feat/gate-e-release-prep`
> 测试基线：538 passed, 0 failed, 0 errors
> 对齐：`docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md`

---

## 1. 总体结论

| 验收项 | 状态 | 说明 |
|--------|------|------|
| E-1 灰度策略 | PASS | 白名单 + 分层放量 + 高风险强制 HITL |
| E-2 回滚策略 | PASS | 固定顺序执行 + 回放验证 + 30m 恢复 |
| 内部接口约束 | PASS | x-internal-debug 守卫 + schema 校验 |
| D-1 质量数值 | 框架就绪 | lightweight 模式产出（需真实 LLM 产出最终数值） |
| D-2 性能数值 | 框架就绪 | 本地基准产出（需生产环境产出最终数值） |
| 安全强化 | PASS | 索引注入防护 + 跨租户审计 + 外部响应校验 |

---

## 2. E-1 灰度策略证据

### 2.1 接口覆盖

| 接口 | 测试 | 状态 |
|------|------|------|
| `POST /api/v1/internal/release/rollout/plan` | rollout plan 白名单检查 | PASS |
| `POST /api/v1/internal/release/rollout/decision` | 放量决策 + 高风险 HITL | PASS |

### 2.2 策略验证

| 规则 | 测试场景 | 结果 |
|------|----------|------|
| 租户白名单阻断 | 非白名单租户请求灰度 | `TENANT_NOT_IN_WHITELIST` |
| 分层放量阻断 | 项目规模超出已放量层级 | `PROJECT_SIZE_NOT_ENABLED` |
| 高风险强制 HITL | `high_risk=true` 的任务 | `force_hitl=true` |
| 灰度顺序 | 白名单 -> small -> medium -> large | 固定顺序执行 |

---

## 3. E-2 回滚策略证据

### 3.1 接口覆盖

| 接口 | 测试 | 状态 |
|------|------|------|
| `POST /api/v1/internal/release/rollback/execute` | 回滚执行 + 回放验证 | PASS |

### 3.2 触发与执行验证

| 规则 | 测试场景 | 结果 |
|------|----------|------|
| 连续失败触发 | `consecutive_failures >= threshold` | 触发回滚 |
| 固定执行顺序 | model_config -> retrieval_params -> workflow_version -> release_version | 按序执行 |
| 回放验证 | 回滚后创建回放任务 | `replay_verification.job_id` 非空 |
| 恢复约束 | 30 分钟内完成 | `rollback_completed_within_30m=true` |

---

## 4. D-1 质量门禁数值（lightweight 模式）

运行命令：`python scripts/eval_ragas.py --demo --backend lightweight`

| 指标 | 阈值 | 实测值 | 状态 |
|------|------|--------|------|
| context_precision | >= 0.80 | 1.0000 | PASS |
| context_recall | >= 0.80 | 0.9765 | PASS |
| faithfulness | >= 0.90 | 0.9241 | PASS |
| response_relevancy | >= 0.85 | 0.4500 | BLOCKED (lightweight 局限) |
| hallucination_rate | <= 0.05 | 0.0000 | PASS |
| citation_resolvable | >= 0.98 | 1.0000 | PASS |

说明：`response_relevancy` 使用 token overlap 启发式计算，精度有限。
需要真实 RAGAS（LLM）后端才能产出准确数值。5/6 指标通过。

---

## 5. D-2 性能门禁数值（本地基准）

运行命令：`python scripts/benchmark_performance.py --iterations 10`

| 指标 | 阈值 | 实测值 | 状态 |
|------|------|--------|------|
| api_health P95 | <= 1.5s | 6.9ms | PASS |
| retrieval_query P95 | <= 4.0s | 12546.2ms | BLOCKED (Chroma 冷启动) |
| parse_upload P95 | <= 180.0s | 5.7ms | PASS |
| evaluation_create P95 | <= 120.0s | 154.4ms | PASS |

说明：`retrieval_query` P95 受 Chroma 首次初始化影响（冷启动开销约 12s）。
稳态性能（mean=1256ms）接近阈值。需生产环境预热后产出最终数值。

---

## 6. 安全强化证据

### 6.1 本次新增安全措施

| 措施 | 文件 | 测试 |
|------|------|------|
| 索引名称注入防护 | `app/store_retrieval.py` `_validate_index_segment()` | 3 tests |
| 跨租户后处理审计 | `app/store_retrieval.py` `_query_lightrag()` | 1 test |
| 外部 LightRAG 响应校验 | `app/store_retrieval.py` `_query_lightrag()` | 1 test |
| 安全指标计数器 | `retrieval_cross_tenant_drops_total` | 内建 |

### 6.2 测试覆盖

| 测试文件 | 新增测试数 | 覆盖范围 |
|----------|-----------|---------|
| `tests/test_retrieval_query.py` | 5 | 注入防护、空值拒绝、合法值放行、跨租户丢弃指标 |

---

## 7. 生产能力阶段状态

### 7.1 五条轨道完成度

| 轨道 | 完成度 | 检查清单 |
|------|--------|---------|
| P1 存储与队列 | ~95% | 全部通过 |
| P2 解析与检索 | ~90% | 全部通过 |
| P3 工作流与 Worker | ~95% | 全部通过 |
| P4 安全与隔离 | ~95% (本次强化) | 全部通过 |
| P5 观测与部署 | ~85% | 全部通过 |

### 7.2 关键组件确认

| 组件 | 状态 |
|------|------|
| 对象存储 WORM（Local + S3） | 已完整实现 |
| Repository 层（11 个仓储） | 已完整实现 |
| PostgreSQL + RLS | 已实现（fake driver 回归通过） |
| Redis 队列 | 已实现（fake driver 回归通过） |
| 向量检索双层过滤 | 已强化（Chroma where + 后处理 + 审计） |

---

## 8. 运行验证

```text
命令:   python -m pytest tests/ --tb=no
结果:   538 passed, 0 failed, 5 warnings
Lint:   ruff check app/ -> All checks passed!
分支:   feat/gate-e-release-prep
```

---

## 9. Gate E 判定

根据 Gate E 验收清单 §7 的三项条件：

1. rollout 决策满足白名单与分层放量规则，且高风险强制 HITL —— **已满足**
2. rollback 在触发条件命中时按固定顺序执行并触发回放验证 —— **已满足**
3. rollback 输出满足 30 分钟内恢复约束字段 —— **已满足**

**Gate E 判定：PASS**

### 进入生产部署的前提条件

1. 配置真实 LLM API 环境，运行 `scripts/eval_ragas.py --backend ragas` 产出 D-1 最终数值
2. 在生产环境运行 `scripts/benchmark_performance.py` 产出 D-2 最终数值
3. 合并 `feat/gate-e-release-prep` 到 `main`
