# Gate E 灰度与回滚验收清单

> 版本：v2026.02.22-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-21-implementation-plan.md`

## 1. 目标

1. 固化 Gate E 的灰度发布策略与回滚策略契约。
2. 将“触发条件、执行顺序、回放验证”落为可测试行为。
3. 给出 Gate E 最小验收证据清单。

## 2. E-1 灰度策略（Rollout）

接口：

1. `POST /api/v1/internal/release/rollout/plan`
2. `POST /api/v1/internal/release/rollout/decision`

策略要求：

1. 灰度顺序固定：租户白名单 -> 项目规模分层放量。
2. 项目规模使用 `small/medium/large` 三层。
3. `high_risk=true` 的任务始终返回 `force_hitl=true`。

阻断规则：

1. tenant 不在白名单：`TENANT_NOT_IN_WHITELIST`。
2. 项目规模不在已放量层级：`PROJECT_SIZE_NOT_ENABLED`。

证据测试：`tests/test_gate_e_rollout_and_rollback.py`（rollout 场景）

## 3. E-2 回滚策略（Rollback）

接口：`POST /api/v1/internal/release/rollback/execute`

触发条件：

1. 任一门禁 breach 满足 `consecutive_failures >= consecutive_threshold`（默认阈值 2）。

执行顺序（固定）：

1. `model_config`
2. `retrieval_params`
3. `workflow_version`
4. `release_version`

回放验证要求：

1. 回滚后必须创建并执行一次回放验证任务。
2. 返回 `replay_verification.job_id` 与 `replay_verification.status`。

验收约束：

1. `rollback_completed_within_30m=true`
2. `service_restored=true`

证据测试：`tests/test_gate_e_rollout_and_rollback.py`（rollback 场景）

## 4. 内部接口约束

1. 三个 Gate E 内部接口均要求 `x-internal-debug: true`。
2. 未携带内部标识统一返回 `403 + AUTH_FORBIDDEN`。
3. 入参字段由 schema 强校验，非法值返回 `400 + REQ_VALIDATION_FAILED`。

## 5. 契约同步范围

1. `docs/design/2026-02-21-rest-api-specification.md`
2. `docs/design/2026-02-21-openapi-v1.yaml`
3. `docs/design/2026-02-21-api-contract-test-samples.md`

## 6. 运行验证证据

1. 运行命令：`pytest -v`
2. OpenAPI 解析：`openapi=3.1.0`
3. 文档禁词检查：占位词与非约定图示关键字不得出现
4. 文档引用检查：显式引用路径全部存在

当前分支验证结果（2026-02-22）：

1. `pytest -q` 退出码 `0`
2. Gate E 新增用例 `tests/test_gate_e_rollout_and_rollback.py` 通过
3. OpenAPI 新增 Gate E 三个内部路径存在并可解析

## 7. 结论判定

同时满足以下条件可判定 Gate E 通过：

1. rollout 决策满足白名单与分层放量规则，且高风险强制 HITL。
2. rollback 在触发条件命中时按固定顺序执行并触发回放验证。
3. rollback 输出满足 30 分钟内恢复约束字段。
